"""Client — I/O 만: 떠 있는 표지 읽기 · 도우미 살아 있나 보기 · 상태 파일·screens.json 읽기 · 답 보내기. 규칙은 hd_model.

표지 = <HD_HOME | ~/.hyper-design>/active/<pid>.json (helper.py 가 쓰고 지운다). 죽은 표지(강제 종료)는 1초 핑으로 걸러 내고 지우지 않는다.
상태 파일은 읽기만 한다 — 쓰기는 늘 도우미(POST /api/reply)로(쓰는 곳 하나).
프로젝트 목록 <HD_HOME>/projects.json 은 이 파일만 읽고 쓴다(임시 파일 + os.replace). 규칙은 hd_projects.
도우미 띄우기(hd open): 떠 있는 것(표지 · <out>/.hd-helper.json 의 살아 있는 pid + 답하는 주소)이 있으면 그것 →
  아니면 build_ref.py 로 빌드 → helper.py 를 떼어 낸 프로세스로 → 표지가 생길 때까지 기다림.
  open_project 가 그 일 전부(브라우저 빼고) — hd open 과 도우미 POST /api/open 이 같이 쓴다.
덮개: claim(POST /api/claim) · release(POST /api/release).
왕복: stop(POST /api/stop → 표지·포트가 없어질 때까지, 안 되면 pid 강제 종료) · attach(POST /api/attach) · wait_pending(GET /api/state 2초마다).
"""
import datetime, json, os, pathlib, signal, socket, subprocess, sys, time, urllib.error, urllib.request, webbrowser

import hd_model
import hd_projects as P

STATE_FILE = ".hd-canvas.json"
PING_TIMEOUT = 1.0


class HdError(Exception):
    """사용자에게 그대로 보일 한 줄 오류."""


def home():
    return pathlib.Path(os.environ.get("HD_HOME") or pathlib.Path.home() / ".hyper-design")


def markers():
    """표지 전부(읽을 수 없는 것은 건너뜀) — 살아 있는지는 모른다. 파일 표지(옛 도우미) + 허브 안 세션(hub_markers, task 47-2)."""
    return file_markers() + hub_markers()


# ---------------------------------------------------------------- 허브 안 세션(task 47-2 '서버 하나')
LOCAL = None                                          # 허브 프로세스 안에서만: () → 열린 세션 표지들(ProjectRegistry.markers) — 자기에게 HTTP 를 보내지 않게
HUB_FILE = "home.json"


def hub_record():
    """<HD_HOME>/home.json → {port, pid, url, token} | None(없음·깨짐·죽은 pid)."""
    p = home() / HUB_FILE
    try:
        rec = hd_model.helper_record(json.loads(p.read_text(encoding="utf-8"))) if p.is_file() else None
    except (OSError, ValueError):
        return None
    if not rec or not rec.get("port") or not rec.get("token") or not rec.get("pid") or not pid_alive(rec["pid"]):
        return None
    return rec


def hub_markers():
    """허브가 연 프로젝트 세션의 표지들 — {pid(허브), project, out, url, token(세션), port(허브), agent, prefix:/v1/p/<이름>, hub:true}.
    허브 안이면 LOCAL(핑 없이 살아 있음 local:true), 밖이면 home.json 의 허브에 GET /v1/sessions. 허브가 없거나 답이 없으면 []."""
    if LOCAL is not None:
        return [dict(m, local=True) for m in LOCAL()]
    rec = hub_record()
    if rec is None:
        return []
    req = urllib.request.Request("http://127.0.0.1:%d/v1/sessions" % int(rec["port"]), headers={"X-HD-Token": rec["token"]})
    try:
        with urllib.request.urlopen(req, timeout=PING_TIMEOUT) as r:
            rows = json.loads(r.read())
    except (OSError, ValueError):
        return []
    return [m for m in rows.get("sessions", []) if isinstance(m, dict) and m.get("port") and m.get("token") and m.get("out")]         if isinstance(rows, dict) else []


def file_markers():
    """~/.hyper-design/active/<pid>.json 표지 전부(옛 helper.py 가 쓰고 지움)."""
    d = home() / "active"
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(m, dict) and m.get("port") and m.get("token") and m.get("out"):
            out.append(m)
    return out


def _base(m):
    return "http://127.0.0.1:%d" % int(m["port"]) + (m.get("prefix") or "")   # 허브 세션 = /v1/p/<이름> 아래


def ping(m, timeout=PING_TIMEOUT):
    if m.get("local"):                                # 이 허브 프로세스 안 세션 — 열려 있으면 살아 있다
        return True
    req = urllib.request.Request(_base(m) + "/api/state", headers={"X-HD-Token": m["token"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False


def running():
    """살아 있는 도우미의 표지만."""
    return [m for m in markers() if ping(m)]


def read_state(out):
    """<out>/.hd-canvas.json → {rev, state}. 없으면 rev 0 · 깨졌으면 HdError."""
    p = pathlib.Path(out) / STATE_FILE
    if not p.is_file():
        return {"rev": 0, "state": {}}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HdError("상태 파일을 읽지 못했어요(%s): %s" % (e, p))
    if not isinstance(doc, dict) or not isinstance(doc.get("state"), dict):
        raise HdError("상태 파일 모양이 아니에요: %s" % p)
    return {"rev": doc.get("rev", 0), "state": doc["state"]}


def screen_ids(out):
    """screens.json 의 화면 id 집합 | None(못 읽음)."""
    try:
        return {s["id"] for s in json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("screens", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def call(m, path, body=None, method="POST", timeout=10):
    """도우미 API 하나 → (code, 답 객체). 닿지 않으면 HdError."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(_base(m) + path, data=data, method=method,
                                 headers={"X-HD-Token": m["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {"error": "HTTP %d" % e.code}
    except (OSError, ValueError) as e:
        raise HdError("도우미에 닿지 않아요(%s): %s" % (e, _base(m)))


def post_reply(m, body, timeout=10):
    """POST /api/reply → (code, 답 객체). 닿지 않으면 HdError."""
    return call(m, "/api/reply", body, timeout=timeout)


# ---------------------------------------------------------------- 프로젝트 목록 (링크만)
CANVAS = pathlib.Path(__file__).resolve().parent.parent / "canvas"
HELPER = CANVAS / "helper.py"
BUILD_REF = CANVAS / "build_ref.py"
START_WAIT = 10.0


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def projects_path():
    return home() / "projects.json"


def warn(msg):
    print("[hd] " + msg, file=sys.stderr)


def load_projects():
    """projects.json → 목록. 없으면 빈 목록. 깨졌으면 projects.json.corrupt-<시각> 으로 옮기고 [hd] 경고 + 빈 목록."""
    p = projects_path()
    if not p.is_file():
        return P.empty()
    try:
        reg, why, broken = P.parse(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        why, broken = "읽지 못했어요(%s)" % e, True
    if not broken:
        if why:
            warn("%s: %s" % (why, p))
        return reg
    aside = p.with_name("projects.json.corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        os.replace(p, aside)
        warn("프로젝트 목록이 깨져 옆으로 옮겼어요(%s) → %s · 빈 목록으로 시작" % (why, aside))
    except OSError as e:
        warn("프로젝트 목록이 깨졌어요(%s), 옮기지도 못했어요(%s): %s" % (why, e, p))
    return P.empty()


def save_projects(reg):
    p = projects_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name("projects.json.tmp-%d" % os.getpid())
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def abs_out(path):
    return str(pathlib.Path(path).expanduser().resolve())


def is_out(path):
    return (pathlib.Path(path) / "screens.json").is_file()


def exists_map(reg):
    return {P.key(e["out"]): is_out(e["out"]) for e in reg["projects"]}


def register(out):
    """목록에 없는 out 이면 넣는다(helper.py 시작 때). → 항목. 실패는 HdError 가 아니라 OSError 그대로."""
    reg = load_projects()
    e = P.by_out(reg, out)
    if e:
        return e
    o = pathlib.Path(out)
    new, e, _ = P.save(reg, str(o), now(), default_name=project_from(o))
    save_projects(new)
    return e


def project_from(o):
    """out 경로 → 기본 프로젝트 이름(hd_model.project_name 과 같은 규칙)."""
    o = pathlib.Path(o)
    return hd_model.project_name(o.name, o.parent.name)


def serving(out):
    """그 out 을 띄운 살아 있는 표지 | None."""
    k = P.key(abs_out(out))
    return next((m for m in running() if P.key(abs_out(m["out"])) == k), None)


HELPER_FILE = ".hd-helper.json"
HELPER_LOG = ".hd-helper.log"


def read_record(out):
    """<out>/.hd-helper.json → hd_model.helper_record 의 {port, pid, url, token} | None(없음·깨짐 — 깨지면 [hd] 한 줄)."""
    p = pathlib.Path(out) / HELPER_FILE
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        warn("도우미 기록을 읽지 못했어요(%s): %s" % (e, p))
        return None
    return hd_model.helper_record(doc)


def pid_alive(pid):
    return _image(int(pid)) is not None


def live_record(out, rec=None):
    """.hd-helper.json 이 가리키는 도우미가 살아 있고 답하면 표지 모양 {pid, project, out, url, token, port, agent} | None.
    다른 HD_HOME 으로 떴거나 표지가 없어도 그 out 의 도우미를 다시 쓰게(hd open · helper.py 시작 검사가 같이 쓴다)."""
    rec = read_record(out) if rec is None else rec
    if not rec or not rec.get("pid") or not rec.get("port") or not rec.get("token"):
        return None
    m = {"pid": rec["pid"], "out": abs_out(out), "url": rec["url"], "token": rec["token"], "port": rec["port"]}
    alive = pid_alive(rec["pid"])                         # 죽은 pid 면 핑하지 않는다(Windows 에서 닫힌 포트 연결은 1초를 다 쓴다)
    if hd_model.start_verdict(rec, alive, alive and ping(m)) != "refuse":
        return None
    try:
        mk = json.loads(marker_path(m).read_text(encoding="utf-8"))
        if isinstance(mk, dict) and mk.get("token") == m["token"]:
            return dict(mk, out=mk.get("out") or m["out"])
    except (OSError, ValueError):
        pass                                          # 표지가 없으면(다른 HD_HOME) 기록만으로
    return dict(m, project=project_from(out), agent=None)


def build(out):
    """커밋된 캔버스 코드로 index.html 을 만든다 → (종료 코드, 출력 끝 몇 줄)."""
    r = subprocess.run([sys.executable, str(BUILD_REF), str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=NO_WINDOW)   # 창 없는 허브·도우미(pythonw)에서 콘솔 창이 깜빡이지 않게
    tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:])
    return r.returncode, tail


def spawn_helper(out, agent=None):
    """helper.py <out> --no-open [--paseo-agent ID] 를 이 터미널과 떼어 띄운다 → (Popen, 로그 경로). 출력은 <out>/.hd-helper.log(out 안 — 점 파일이라 정적 경로로 내주지 않음, #281)."""
    out = pathlib.Path(out)
    log = out / HELPER_LOG
    args = [sys.executable, str(HELPER), str(out), "--no-open"] + (["--paseo-agent", agent] if agent else [])
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    with open(log, "ab") as f:
        p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, close_fds=True,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1"), **kw)
    return p, log


def wait_serving(out, proc=None, timeout=START_WAIT):
    """표지가 생기고 핑이 될 때까지 → 표지 | None(시간 넘음 · 프로세스가 먼저 끝남)."""
    end = time.time() + timeout
    while time.time() < end:
        m = serving(out)
        if m:
            return m
        if proc is not None and proc.poll() is not None:
            return None
        time.sleep(0.1)
    return serving(out)


def log_tail(log, n=5):
    try:
        return "\n".join(pathlib.Path(log).read_text(encoding="utf-8", errors="replace").strip().splitlines()[-n:])
    except OSError:
        return ""


def open_browser(url):
    webbrowser.open(url)


class NotFound(HdError):
    """없는 프로젝트·out — 도우미는 404 로 돌려준다."""


class TimedOut(HdError):
    """hd wait 시간 넘음 — 종료 코드 2."""
    code = 2


def resolve(target):
    """이름 | out 경로 → (항목, out Path). out 경로가 목록에 없으면 넣는다. 모르는 이름·없어진 out → NotFound."""
    reg = load_projects()
    e = P.find(reg, target)
    if e is None and is_out(target):
        o = abs_out(target)
        reg, e, _ = P.save(reg, o, now(), default_name=project_from(o))
        save_projects(reg)
    if e is None:
        raise NotFound("모르는 프로젝트예요: %s — hd projects 로 이름을 보거나 out 경로를 주세요" % target)
    o = pathlib.Path(e["out"])
    if not is_out(o):
        raise NotFound("'%s' 의 out 폴더가 없어요(없음): %s — 링크만 지우려면 hd forget %s" % (e["name"], o, e["name"]))
    return e, o


def open_in_hub(hub, e, agent=None):
    """허브에 POST /api/open → (항목, 그 세션 표지, reused). 허브가 거절하면 HdError(모름 = NotFound)."""
    body = {"name": e["name"]}
    if agent:
        body["agent"] = agent
    code, res = call({"port": hub["port"], "token": hub["token"]}, "/api/open", body, timeout=120)
    if code == 404:
        raise NotFound(res.get("error", "모르는 프로젝트예요"))
    if code != 200:
        raise HdError("홈 서버가 열지 못했어요(%d): %s" % (code, res.get("error", "")))
    k = P.key(abs_out(e["out"]))
    m = next((x for x in hub_markers() if P.key(abs_out(x["out"])) == k), None)
    if m is None:                                     # 허브가 따로 떠 있던 옛 도우미를 돌려줬다
        m = serving(e["out"]) or {"url": res["url"], "pid": res.get("pid"), "agent": res.get("agent"), "out": e["out"]}
    return e, m, bool(res.get("reused"))


def open_project(target, agent=None):
    """이름 | out 경로 → (항목, 표지, reused). 떠 있으면 그 도우미, 아니면 빌드 후 떼어 띄움. 브라우저는 열지 않는다.
    모르는 이름·없어진 out → NotFound, 빌드·띄우기 실패 → HdError. hd open 과 도우미 POST /api/open 이 같이 쓴다."""
    e, o = resolve(target)
    m = serving(o) or live_record(o)                   # 표지가 없어도 .hd-helper.json 의 도우미가 답하면 그것(#271 — 둘째를 띄우지 않는다)
    reused = m is not None
    hub = None if reused or LOCAL is not None else hub_record()
    if hub is not None:                                # 허브가 떠 있으면 그 안에서 연다(한 주소 — task 47-2). 옛 도우미 띄우기는 허브가 없을 때만
        return open_in_hub(hub, e, agent)
    if not reused:
        code, tail = build(o)
        if code != 0:
            if not (o / "index.html").is_file():
                raise HdError("빌드 실패(build_ref.py %d): %s" % (code, " / ".join(tail.splitlines())))
            warn("빌드 실패(%d) — 있던 index.html 로 띄워요: %s" % (code, tail.splitlines()[-1] if tail else ""))
        proc, log = spawn_helper(o, agent)
        m = wait_serving(o, proc) or live_record(o)    # 그 사이 다른 쪽이 띄웠으면 이 도우미는 거절하고 끝난다 — 그 도우미를 쓴다
        if m is None:
            raise HdError("도우미가 %d초 안에 뜨지 않았어요 — 로그 %s: %s" % (START_WAIT, log, " / ".join(log_tail(log).splitlines())))
    save_projects(P.touch(load_projects(), e["out"], now()))   # 도우미가 그 사이 목록을 썼을 수 있어 다시 읽는다
    return e, m, reused


def manifest_title(out):
    """<out>/screens.json 의 title | None(없음·못 읽음 — 제목이 없을 뿐이라 경고하지 않는다: 이름으로 보인다)."""
    try:
        t = json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("title")
    except (OSError, ValueError, AttributeError):
        return None
    return t.strip() if isinstance(t, str) and t.strip() else None


def titles_map(reg):
    return {P.key(e["out"]): manifest_title(e["out"]) for e in reg["projects"] if not e.get("title")}


def project_rows():
    """hd projects --json 과 같은 줄 객체(도우미·허브 GET /api/projects 도 이것 — 허브 썸네일 주소는 home_api 가 붙인다)."""
    reg = load_projects()
    return P.rows(reg, running(), exists_map(reg), titles_map(reg))


def update_project(name, **fields):
    """POST /api/project — 제목·별표·휴지통 바꾸기 → 그 줄 객체. 모르는 이름 → NotFound, 틀린 값 → HdError."""
    reg = load_projects()
    if not any(e["name"] == name for e in reg["projects"]):
        raise NotFound("모르는 프로젝트예요: %s" % name)
    try:
        reg, _ = P.update(reg, name, now(), **fields)
    except P.ProjectError as e:
        raise HdError(str(e))
    save_projects(reg)
    return next(r for r in project_rows() if r["name"] == name)


def forget_trashed(name):
    """POST /api/forget — 휴지통에 든 링크만 뺀다(파일은 그대로) → 뺀 항목."""
    reg = load_projects()
    if not any(e["name"] == name for e in reg["projects"]):
        raise NotFound("모르는 프로젝트예요: %s" % name)
    try:
        reg, hit = P.forget_trashed(reg, name)
    except P.ProjectError as e:
        raise HdError(str(e))
    save_projects(reg)
    return hit


# ---------------------------------------------------------------- 왕복: stop · attach · wait
STOP_WAIT = 5.0
POLL = 2.0
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def stale():
    """응답 없는 표지(강제 종료로 남았거나 멈춘 도우미)."""
    return [m for m in markers() if not ping(m)]


def marker_path(m):
    return home() / "active" / ("%d.json" % int(m["pid"]))


def port_open(port, timeout=0.3):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _sys32(name):
    return str(pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / name)


def _image(pid):
    """pid → 실행 파일 이름(소문자) | None(프로세스 없음)."""
    if sys.platform == "win32":
        r = subprocess.run([_sys32("tasklist.exe"), "/FI", "PID eq %d" % pid, "/FO", "CSV", "/NH"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        lines = (r.stdout or "").strip().splitlines()
        return lines[0].split('","')[0].strip('"').lower() if lines and lines[0].startswith('"') else None
    try:
        return pathlib.Path("/proc/%d/comm" % pid).read_text().strip().lower()
    except OSError:
        try:
            os.kill(pid, 0)
        except OSError:
            return None
        return "python?"                                  # /proc 없음(macOS) — 살아 있으니 python 으로 본다


def kill_pid(pid):
    """pid 강제 종료 → 'kill' | 'gone'(이미 없음) | 'other'(python 이 아님 — 다른 프로그램이 그 번호를 받았으니 죽이지 않는다)."""
    img = _image(pid)
    if img is None:
        return "gone"
    if "python" not in img:
        return "other"
    if sys.platform == "win32":
        r = subprocess.run([_sys32("taskkill.exe"), "/PID", str(pid), "/F"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=NO_WINDOW)
        if r.returncode != 0 and _image(pid) is not None:
            raise HdError("pid %d 를 끄지 못했어요: %s" % (pid, ((r.stdout or "") + (r.stderr or "")).strip()))
    else:
        os.kill(pid, signal.SIGKILL)
    return "kill"


def _gone(m):
    return not marker_path(m).exists() and not port_open(m["port"])


def stop(m, wait=STOP_WAIT):
    """도우미 끄기 → 'route'(POST /api/stop 으로 스스로 끔) | 'kill'(답이 없어 pid 강제 종료) |
    'gone'(프로세스가 이미 없어 표지만 지움) | 'other'(그 pid 를 다른 프로그램이 씀 — 표지만 지움). 프로젝트 목록은 건드리지 않는다."""
    try:
        code, _ = call(m, "/api/stop", {}, timeout=2)
    except HdError:
        code = None
    if m.get("hub"):                                  # 허브 안 세션 — 그 세션만 닫는다(허브 pid 는 절대 끄지 않음)
        k = P.key(abs_out(m["out"]))
        end = time.time() + wait
        while code == 200 and time.time() < end:
            if not any(P.key(abs_out(x["out"])) == k for x in hub_markers()):
                return "route"
            time.sleep(0.1)
        return "gone" if code != 200 else "route"
    if code == 200:
        end = time.time() + wait
        while time.time() < end:
            if _gone(m):
                return "route"
            time.sleep(0.1)
    how = kill_pid(int(m["pid"]))
    if how == "kill":
        end = time.time() + wait
        while time.time() < end and _image(int(m["pid"])) is not None:
            time.sleep(0.1)
    marker_path(m).unlink(missing_ok=True)
    return how


def attach(m, agent):
    """POST /api/attach {agent} → 도우미가 받은 agent. 거절되면 HdError."""
    code, res = call(m, "/api/attach", {"agent": agent})
    if code != 200:
        raise HdError("도우미가 거절했어요(%d): %s" % (code, res.get("error", "")))
    return res.get("agent")


def claim(m, screen, by=None, note=None):
    """POST /api/claim → 도우미 답 {rev, screen, file}. 거절되면 HdError."""
    body = {"screen": screen}
    if by:
        body["by"] = by
    if note is not None:
        body["note"] = note
    code, res = call(m, "/api/claim", body)
    if code != 200:
        raise HdError("도우미가 거절했어요(%d): %s" % (code, res.get("error", "")))
    return res


def release(m, screen):
    """POST /api/release → {rev, released}. 거절되면 HdError."""
    code, res = call(m, "/api/release", {"screen": screen})
    if code != 200:
        raise HdError("도우미가 거절했어요(%d): %s" % (code, res.get("error", "")))
    return res


def get_state(m, timeout=5):
    code, res = call(m, "/api/state", method="GET", timeout=timeout)
    if code != 200 or not isinstance(res, dict) or not isinstance(res.get("state"), dict):
        raise HdError("상태를 읽지 못했어요(%s): %s" % (code, _base(m)))
    return res


def wait_pending(m, timeout, poll=POLL):
    """working 메모가 생길 때까지 poll 초마다 GET /api/state → (표지, {rev, state}, 줄 객체). 시간 넘으면 TimedOut.
    도우미에 닿지 않으면 그 out 의 표지를 다시 읽어 이어 간다(다시 뜬 도우미) — [hd] 경고는 한 줄만."""
    out, end, warned = m["out"], time.time() + timeout, False
    while True:
        try:
            st = get_state(m)
            rs = hd_model.pending(st["state"])
            if rs:
                return m, st, rs
        except HdError:
            if not warned:
                warn("도우미에 닿지 않아요 — 표지를 다시 읽으며 기다려요(%s)" % out); warned = True
            again = serving(out)
            if again and again.get("token") != m.get("token"):
                m = again
                continue
        left = end - time.time()
        if left <= 0:
            raise TimedOut("%g초 동안 보낸 메모가 없어요(%s)" % (timeout, out))
        time.sleep(min(poll, left))
