"""테스트 실행 도구(conftest.py 가 쓴다) — 겹친 -n 실행 줄 세우기(잠금) · 실패만 혼자 다시 · 바깥 글꼴 막기.

판단(decide·classify)은 I/O 없는 순수 함수 — test_canvas_unit_testrun.py 가 브라우저 없이 본다.
잠금은 디렉터리 하나(LOCK): mkdir 로 잡고 안에 owner.json(pid·시작·cwd·인자)을 쓴다 — 손으로 `mkdir` 하는 세션도 같은 경로라 서로 기다린다.
"""
import json, os, sys, time
from pathlib import Path

LOCK = Path("C:/Users/eungshin/AppData/Local/Temp/claude/hd-testrun.lock") if os.name == "nt" \
    else Path(os.environ.get("TMPDIR", "/tmp")) / "hd-testrun.lock"
STALE_SEC = 2 * 3600          # owner.json 이 없는 잠금(손으로 mkdir)을 버려진 것으로 볼 나이
POLL_SEC = 5
ENV_NOLOCK = "HD_TEST_NOLOCK"     # 1 이면 잠금을 건너뜀
ENV_RERUN = "HD_TEST_RERUN"       # 다시 돌리는 하위 실행 — 또 다시 돌리거나 잠그지 않는다
ENV_RERUN_OUT = "HD_TEST_RERUN_OUT"
ENV_ALLOW_NET = "HD_TEST_ALLOW_NET"  # 1 이면 바깥 글꼴을 막지 않는다(실제 글꼴로 보거나 전후 시간 비교)
RERUN_MAX = 40                    # 이보다 많이 깨지면 부하가 아니라 진짜 고장 — 다시 돌리지 않는다

# 테스트 페이지가 부르는 바깥 글꼴(foundation/derive.py 의 tokens.css @import) — 받지 않고 빈 응답을 준다. load 가 글꼴 ~45개를 기다리지 않게.
EXTERNAL_FONT_HOSTS = ("cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com")


# ── 순수 판단 ────────────────────────────────────────────────

def decide(exists, owner, owner_alive, age_sec, me_pid):
    """잠금 디렉터리 상태로 할 일: 'take'(비었다) · 'wait'(다른 실행 중) · 'clear'(버려짐 — 지우고 잡는다) · 'mine'(이미 내 것).
    owner: owner.json 내용(없으면 None) · owner_alive: 그 pid 가 살아 있나 · age_sec: 디렉터리 나이."""
    if not exists:
        return "take"
    if owner is None:                                   # 손으로 mkdir 한 세션 또는 막 owner.json 을 쓰는 중
        return "clear" if age_sec > STALE_SEC else "wait"
    if owner.get("pid") == me_pid:
        return "mine"
    return "wait" if owner_alive else "clear"


def wait_line(owner, age_sec, note=""):
    """기다릴 때 한 줄. note: 손으로 잡은 잠금 안의 글(다른 세션이 남긴 'owner' 파일)."""
    if owner:
        return f"[hd-test] 다른 실행 중: {owner.get('cwd', '?')} {owner.get('start', '?')} — 기다림"
    who = f"{note.strip()[:80]}, " if note and note.strip() else ""
    return f"[hd-test] 다른 실행 중: ({who}손으로 잡은 잠금, {int(age_sec // 60)}분 전) — 기다림"


def classify(first_failed, rerun_failed, rerun_ok):
    """처음 -n 실행에서 깨진 것(first_failed)을 혼자 다시 돌린 결과로 나눈다 → (진짜 실패, 혼자 통과).
    rerun_ok=False(다시 돌리기가 안 돌았음)면 모두 진짜로 둔다."""
    first = list(dict.fromkeys(first_failed))
    if not rerun_ok:
        return first, []
    bad = set(rerun_failed)
    return [n for n in first if n in bad], [n for n in first if n not in bad]


def summary_line(real, flaky):
    return f"진짜 실패 {len(real)} · 혼자 통과(부하로 보임) {len(flaky)}"


# ── I/O ─────────────────────────────────────────────────────

def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":                                 # os.kill(pid, 0) 은 윈도에서 프로세스를 끝낸다 — 쓰지 않는다
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)           # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.GetLastError() == 5           # 접근 거부 = 있다
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259           # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_owner(lock):
    try:
        return json.loads((lock / "owner.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_note(lock):
    try:
        return " ".join((lock / "owner").read_text(encoding="utf-8", errors="replace").split())
    except OSError:
        return ""


def say(out, line):                                    # 윈도 콘솔 기본 인코딩(cp949)에서도 한글·— 가 깨지지 않게 utf-8 바이트로
    buf = getattr(out, "buffer", None)
    if buf is not None:
        buf.write((line + "\n").encode("utf-8")); buf.flush()
    else:
        out.write(line + "\n"); out.flush()


def _clear(lock):
    try:
        (lock / "owner.json").unlink()
    except OSError:
        pass
    try:
        lock.rmdir()
    except OSError:
        pass


def acquire(args, lock=LOCK, poll=POLL_SEC, out=None, sleep=time.sleep):
    """잠금을 잡을 때까지 기다린다. 기다리기 시작할 때 한 줄만 쓴다. 잡은 owner 를 돌려준다."""
    out = out or sys.__stderr__
    me = {"pid": os.getpid(), "start": time.strftime("%Y-%m-%dT%H:%M:%S"), "cwd": os.getcwd(), "args": list(args)}
    said = False
    while True:
        exists = lock.is_dir()
        owner = _read_owner(lock) if exists else None
        try:
            age = time.time() - lock.stat().st_mtime if exists else 0.0
        except OSError:
            age = 0.0
        what = decide(exists, owner, pid_alive(owner.get("pid")) if owner else False, age, me["pid"])
        if what == "mine":
            return me
        if what == "clear":
            _clear(lock)
            what = "take"
        if what == "take":
            try:
                lock.mkdir(parents=False)
            except FileExistsError:
                continue                                 # 누가 먼저 잡았다 — 다시 본다
            except FileNotFoundError:
                lock.parent.mkdir(parents=True, exist_ok=True)
                continue
            (lock / "owner.json").write_text(json.dumps(me, ensure_ascii=False), encoding="utf-8")
            return me
        if not said:
            say(out, wait_line(owner, age, "" if owner else _read_note(lock)))
            said = True
        sleep(poll)


def release(lock=LOCK):
    """내가 잡은 잠금만 푼다(owner.json 의 pid 가 나)."""
    owner = _read_owner(lock)
    if owner and owner.get("pid") == os.getpid():
        _clear(lock)


def block_external_fonts():
    """playwright 의 새 브라우저 맥락(new_context·new_page·launch_persistent_context)마다 바깥 글꼴 요청을 빈 200 으로 막는다.
    테스트 파일마다 브라우저를 따로 띄우므로 한 곳(conftest 가져올 때)에서 감싼다. 두 번 불러도 한 번만."""
    if os.environ.get(ENV_ALLOW_NET) == "1":
        return False
    try:
        from playwright.sync_api import _generated as g
    except Exception:
        return False
    if getattr(g.Browser, "_hd_fonts_blocked", False):
        return True
    import re
    pat = re.compile(r"^https?://(" + "|".join(re.escape(h) for h in EXTERNAL_FONT_HOSTS) + r")/")

    def fulfil(route):
        u = route.request.url.split("?")[0].lower()
        ctype = "text/css" if u.endswith(".css") or "fonts.googleapis.com" in u else "application/octet-stream"
        route.fulfill(status=200, content_type=ctype, body="")

    def guard(c):
        try:
            c.route(pat, fulfil)
        except Exception:
            pass
        return c

    nc, np_, lp = g.Browser.new_context, g.Browser.new_page, g.BrowserType.launch_persistent_context
    g.Browser.new_context = lambda self, *a, **k: guard(nc(self, *a, **k))
    g.BrowserType.launch_persistent_context = lambda self, *a, **k: guard(lp(self, *a, **k))

    def new_page(self, *a, **k):
        p = np_(self, *a, **k)
        guard(p.context)
        return p
    g.Browser.new_page = new_page
    g.Browser._hd_fonts_blocked = True
    return True
