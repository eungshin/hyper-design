"""Client — I/O 만: 떠 있는 표지 읽기 · 도우미 살아 있나 보기 · 상태 파일·screens.json 읽기 · 답 보내기. 규칙은 hd_model.

표지 = <HD_HOME | ~/.hyper-design>/active/<pid>.json (helper.py 가 쓰고 지운다). 죽은 표지(강제 종료)는 1초 핑으로 걸러 내고 지우지 않는다.
상태 파일은 읽기만 한다 — 쓰기는 늘 도우미(POST /api/reply)로(쓰는 곳 하나).
프로젝트 목록 <HD_HOME>/projects.json 은 이 파일만 읽고 쓴다(임시 파일 + os.replace). 규칙은 hd_projects.
도우미 띄우기(hd open): build_ref.py 로 빌드 → helper.py 를 떼어 낸 프로세스로 → 표지가 생길 때까지 기다림.
"""
import datetime, json, os, pathlib, subprocess, sys, time, urllib.error, urllib.request, webbrowser

import hd_model
import hd_projects as P

STATE_FILE = ".hd-canvas.json"
PING_TIMEOUT = 1.0


class HdError(Exception):
    """사용자에게 그대로 보일 한 줄 오류."""


def home():
    return pathlib.Path(os.environ.get("HD_HOME") or pathlib.Path.home() / ".hyper-design")


def markers():
    """표지 전부(읽을 수 없는 것은 건너뜀) — 살아 있는지는 모른다."""
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
    return "http://127.0.0.1:%d" % int(m["port"])


def ping(m, timeout=PING_TIMEOUT):
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


def post_reply(m, body, timeout=10):
    """POST /api/reply → (code, 답 객체). 닿지 않으면 HdError."""
    req = urllib.request.Request(_base(m) + "/api/reply", data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
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


def build(out):
    """커밋된 캔버스 코드로 index.html 을 만든다 → (종료 코드, 출력 끝 몇 줄)."""
    r = subprocess.run([sys.executable, str(BUILD_REF), str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:])
    return r.returncode, tail


def spawn_helper(out, agent=None):
    """helper.py <out> --no-open [--paseo-agent ID] 를 이 터미널과 떼어 띄운다 → (Popen, 로그 경로). 출력은 <out>/../helper.log."""
    out = pathlib.Path(out)
    log = out.parent / "helper.log"
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
