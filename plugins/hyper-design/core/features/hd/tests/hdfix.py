"""hd 테스트 공용: 작은 out 만들기 · 도우미를 자식 프로세스로 띄우고 정상 종료하기. 브라우저 없음."""
import json, os, signal, subprocess, sys, time
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
CANVAS = HD.parent / "canvas"
HELPER = CANVAS / "helper.py"

NOTES = [
    {"id": "n1", "screen": "home", "no": 1, "intent": "change", "sent": True, "note": "버튼 문구를 '계속'으로",
     "targets": [{"path": "body > button:nth-of-type(1)", "text": "다음"}], "path": "body > button:nth-of-type(1)", "text": "다음"},
    {"id": "n2", "screen": "home", "no": 2, "intent": "question", "sent": True, "note": "이 색은 토큰인가요?", "path": "h1", "text": "제목"},
    {"id": "n3", "screen": "list", "intent": "change", "sent": True, "note": "목록 간격 줄이기", "path": "ul", "text": ""},
    {"id": "n4", "screen": "list", "intent": "change", "sent": False, "note": "아직 안 보냄", "path": "ul", "text": ""},
]


def make_out(root, notes=NOTES):
    """root/<proj>/out — screens.json(home·list) · 화면 파일 · index.html · .hd-canvas.json(rev 3, notes)."""
    out = Path(root) / "proj-a" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens.json").write_text(json.dumps({"groups": [], "screens": [
        {"id": "home", "file": "screens/home.html", "title": "Home"}, {"id": "list", "file": "screens/list.html", "title": "List"}]}),
        encoding="utf-8")
    for s in ("home", "list"):
        (out / "screens" / (s + ".html")).write_text("<html><body><h1>%s</h1><button>다음</button></body></html>" % s, encoding="utf-8")
    (out / "index.html").write_text("<html><head></head><body>canvas</body></html>", encoding="utf-8")
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 3, "updated": "x", "state": {"notes": notes, "card-pos": {"home": [1, 2]}}},
                                                    ensure_ascii=False), encoding="utf-8")
    return out


def env(home):
    return dict(os.environ, HD_HOME=str(home), PYTHONIOENCODING="utf-8")


def start_helper(out, home, agent=None, extra_env=None):
    """도우미 자식 프로세스 → (proc, url). 표지는 url 을 찍기 전에 쓰인다. extra_env = 더할 환경 변수(예: HD_PASEO_CMD)."""
    args = [sys.executable, str(HELPER), str(out), "--no-open"] + (["--paseo-agent", agent] if agent else [])
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    e = env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):   # 테스트 도우미가 실제 에이전트로 보내지 않게
        e.pop(k, None)
    e.update(extra_env or {})
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                         env=e, creationflags=flags)
    url = p.stdout.readline().strip()
    assert url.startswith("http://127.0.0.1:"), (url, p.stderr.read() if p.poll() is not None else "")
    return p, url


def stop_helper(p, timeout=10):
    """정상 종료(Windows CTRL_BREAK · 그 밖 SIGTERM) → 끝날 때까지 기다림. 안 끝나면 죽이고 False."""
    if p.poll() is None:
        p.send_signal(signal.CTRL_BREAK_EVENT if sys.platform == "win32" else signal.SIGTERM)
        try:
            p.wait(timeout)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait(); return False
    return True


def wait_for(pred, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return pred()
