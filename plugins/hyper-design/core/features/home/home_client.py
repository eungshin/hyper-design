"""Client — Home I/O: tabs.json · home.json(허브 기록) · 새 프로젝트 폴더 · 탐색기로 폴더 열기 · 폴더 고르기 대화상자 · 허브 띄우기.
규칙은 home_model(순수) · 프로젝트 목록 읽고 쓰기는 hd_client(주인 하나).

<HD_HOME> = env HD_HOME | ~/.hyper-design
- tabs.json = {version:1, tabs:[name]} — 주인 = 이 파일(임시 파일 + os.replace). 깨진 파일은 [hd] 한 줄 + 빈 탭(파일은 다음 쓰기가 덮는다)
- home.json = {url, pid, port, token} — 허브(home_server)가 시작 때 쓰고 정상 종료 때 지운다. 재사용 = 살아 있는 pid + 답하는 주소
  (helper 의 .hd-helper.json 과 같은 규칙 hd_model.start_verdict)
- 새 프로젝트 out = <HD_HOME>/projects/<name>/out (screens.json 만 — 빌드·도우미는 hd_client.open_project)
"""
import base64, json, os, pathlib, subprocess, sys, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hd"))
import hd_client as C  # noqa: E402
import hd_model  # noqa: E402
import hd_projects as P  # noqa: E402
import home_model as M  # noqa: E402

HD_PY = HERE.parent / "hd" / "hd.py"
TABS_FILE = "tabs.json"
HUB_FILE = "home.json"
HUB_WAIT = 10.0
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def home():
    return C.home()


def _write_json(p, doc):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp-%d" % os.getpid())
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


# ---------------------------------------------------------------- 탭
def known_names(reg=None):
    """탭에 올 수 있는 이름 = 휴지통에 없는 프로젝트."""
    reg = reg or C.load_projects()
    return {e["name"] for e in reg["projects"] if not e.get("trashed")}


def load_tabs(known=None):
    p = home() / TABS_FILE
    known = known_names() if known is None else known
    if not p.is_file():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        C.warn("탭 파일을 읽지 못했어요(%s) — 빈 탭으로: %s" % (e, p))
        return []
    tabs, why = M.tabs_parse(doc, known)
    if why:
        C.warn("%s — 빈 탭으로: %s" % (why, p))
    return tabs


def save_tabs(tabs):
    _write_json(home() / TABS_FILE, M.tabs_doc(tabs))
    return list(tabs)


def change_tabs(fn):
    """탭 목록 고치기(읽고 → fn → 씀) → 새 목록."""
    known = known_names()
    return save_tabs(M.tabs_set(fn(load_tabs(known)), known))


# ---------------------------------------------------------------- 허브 기록 (home.json)
def hub_path():
    return home() / HUB_FILE


def read_hub():
    """home.json → {url, pid, port, token, code} | None(없음 · 깨짐 — 깨지면 [hd] 한 줄)."""
    p = hub_path()
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        C.warn("허브 기록을 읽지 못했어요(%s): %s" % (e, p))
        return None
    rec = hd_model.helper_record(doc)
    if rec is not None and isinstance(doc, dict):
        rec["code"] = doc.get("code") if isinstance(doc.get("code"), str) else None   # 그 허브가 뜬 코드 도장(옛 허브는 없음)
    return rec


def write_hub(url, port, token, code=None):
    _write_json(hub_path(), {"url": url, "pid": os.getpid(), "port": port, "token": token, "code": code})


def clear_hub():
    """정상 종료 — 이 프로세스가 쓴 기록일 때만 지운다."""
    rec = read_hub()
    if rec and rec.get("pid") == os.getpid():
        hub_path().unlink(missing_ok=True)


def hub_answers(rec, timeout=1.0):
    req = urllib.request.Request("http://127.0.0.1:%d/api/tabs" % int(rec["port"]), headers={"X-HD-Token": rec["token"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False


def live_hub(rec=None):
    """살아 있고 답하는 허브의 기록 | None."""
    rec = read_hub() if rec is None else rec
    if not rec or not rec.get("pid") or not rec.get("port") or not rec.get("token"):
        return None
    alive = C.pid_alive(rec["pid"])
    return rec if hd_model.start_verdict(rec, alive, alive and hub_answers(rec)) == "refuse" else None


def hub_port():
    """도우미가 썸네일 주소에 쓸 허브 포트 | None — 기록만 본다(요청마다 핑하지 않는다. 허브가 꺼졌으면 카드가 빈 그림을 보인다)."""
    rec = read_hub()
    return rec.get("port") if rec and rec.get("pid") else None


def spawn_hub():
    """hd.py home --no-browser 를 떼어 띄운다 → (Popen, 로그 경로). 출력은 <HD_HOME>/home.log."""
    log = home() / "home.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    kw = {}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    with open(log, "ab") as f:
        p = subprocess.Popen([sys.executable, str(HD_PY), "home", "--no-browser"], stdin=subprocess.DEVNULL, stdout=f,
                             stderr=subprocess.STDOUT, close_fds=True,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1"), **kw)
    return p, log


def ensure_hub(timeout=HUB_WAIT):
    """허브 주소 — 떠 있으면 그것, 아니면 떼어 띄우고 기다린다. 못 띄우면 HdError."""
    rec = live_hub()
    if rec:
        return rec["url"]
    proc, log = spawn_hub()
    end = time.time() + timeout
    while time.time() < end:
        rec = live_hub()
        if rec:
            return rec["url"]
        if proc.poll() is not None and not live_hub():
            break
        time.sleep(0.1)
    raise C.HdError("홈을 띄우지 못했어요 — 로그 %s: %s" % (log, " / ".join(C.log_tail(log).splitlines())))


# ---------------------------------------------------------------- 새 프로젝트
def projects_dir():
    return home() / "projects"


def create_project(title=None):
    """빈 캔버스 프로젝트를 만들고 목록에 넣는다 → 항목. 제목이 없으면 '새 프로젝트 N'. 빌드·도우미는 부르는 쪽(open_project)."""
    reg = C.load_projects()
    if title is None or (isinstance(title, str) and not title.strip()):
        rows = P.rows(reg, [], {}, C.titles_map(reg))
        title = M.default_title([r["title"] for r in rows])
    err = P.title_error(title)
    if err:
        raise C.HdError(err)
    title = title.strip()
    d = projects_dir()
    taken = {e["name"] for e in reg["projects"]} | ({p.name for p in d.iterdir()} if d.is_dir() else set())
    name = M.new_name(title, taken)
    out = d / name / "out"
    out.mkdir(parents=True, exist_ok=False)            # 이름은 폴더와도 겹치지 않게 골랐다 — 있으면 덮지 않고 오류
    (out / "screens.json").write_text(json.dumps(M.empty_manifest(title), ensure_ascii=False, indent=1), encoding="utf-8")
    now = C.now()
    reg, e, _ = P.save(reg, str(out), now, name=name)
    reg, e = P.update(reg, name, now, title=title)
    C.save_projects(reg)
    return e


# ---------------------------------------------------------------- 폴더
def canvas_folder(path):
    """고른 폴더 → 캔버스 out 경로 | None. 그 폴더에 index.html · .hd-canvas.json · screens.json 이 있으면 그것, 아니면 그 아래 out/."""
    p = pathlib.Path(path)
    for o in (p, p / "out"):
        if any((o / f).is_file() for f in ("index.html", ".hd-canvas.json", "screens.json")):
            return pathlib.Path(C.abs_out(o))
    return None


def register_folder(path):
    """캔버스 폴더를 목록에 넣는다(이미 있으면 그 항목, 휴지통이면 꺼냄) → 항목. 캔버스가 아니면 HdError."""
    o = canvas_folder(path)
    if o is None:
        raise C.HdError("캔버스 폴더가 아니에요(index.html · .hd-canvas.json 이 없음): %s" % path)
    reg = C.load_projects()
    reg, e, _ = P.save(reg, str(o), C.now(), default_name=C.project_from(o))
    if e.get("trashed"):
        reg, e = P.update(reg, e["name"], C.now(), trashed=False)
    C.save_projects(reg)
    return e


def reveal(out):
    """out 폴더를 탐색기(맥 open · 그 밖 xdg-open)로 연다. 없는 폴더 → NotFound."""
    o = pathlib.Path(out)
    if not o.is_dir():
        raise C.NotFound("폴더가 없어요: %s" % o)
    if sys.platform == "win32":
        subprocess.Popen([str(pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "explorer.exe"), str(o)], creationflags=NO_WINDOW)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(o)], creationflags=NO_WINDOW)   # NO_WINDOW = 0 밖 Windows


PICK_PS = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false; Opacity = 0}
$owner.Show(); $owner.Activate()
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = '캔버스 폴더를 고르세요 (index.html 이 있는 out 폴더 또는 그 위 폴더)'
$d.ShowNewFolderButton = $false
if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }
$owner.Close()
"""


def pick_folder():
    """폴더 고르기 대화상자(Windows) → 경로 | None(취소). 대화상자를 띄우지 못하면 HdError."""
    if sys.platform != "win32":
        raise C.HdError("폴더 고르기는 Windows 에서만 돼요 — hd open <경로> 를 쓰세요")
    ps = str(pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")
    enc = base64.b64encode(PICK_PS.encode("utf-16-le")).decode("ascii")
    r = subprocess.run([ps, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc], capture_output=True,
                       encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise C.HdError("폴더 고르기를 띄우지 못했어요(%d): %s" % (r.returncode, " / ".join((r.stderr or "").strip().splitlines()[-2:])))
    path = (r.stdout or "").strip()
    return path or None
