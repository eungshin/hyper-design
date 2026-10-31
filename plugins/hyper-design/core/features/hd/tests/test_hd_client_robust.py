"""허브·CLI 견고함·고정비(W10 F3) — 연결 대기 줄 · 바쁜 서버를 꺼졌다고 보지 않기(핑 다시 한 번 · 오프라인이면 한 줄) ·
127.0.0.1 http 에 인증서 저장소를 읽지 않기 · pid 살아 있나에 tasklist 를 부르지 않기. 브라우저 없음."""
import json, os, socket, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
sys.path.append(str(HD.parent / "canvas"))
sys.path.append(str(HD.parent / "home"))
import hd_client as C  # noqa: E402


# ---------------------------------------------------------------- 연결 대기 줄
def test_servers_have_roomy_accept_queue():
    import helper, home_server, registry
    for cls in (helper.Server, home_server.Hub, registry._Alias):
        assert cls.request_queue_size >= 64, cls      # 기본 5 — 새로고침 몰림에 연결 거부(ERR_CONNECTION_REFUSED)가 났다


# ---------------------------------------------------------------- 핑
def test_ping_waits_longer_and_retries_once_on_timeout(monkeypatch):
    assert C.PING_TIMEOUT >= 3.0
    calls = []

    def fake(req, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise socket.timeout("timed out")
        return 200
    monkeypatch.setattr(C, "_get_status", fake)
    assert C.ping({"port": 1, "token": "t"}) is True and len(calls) == 2, "바쁜 서버 = 한 번 더"


def test_ping_refused_is_not_retried_and_says_nothing(monkeypatch, capsys):
    calls = []

    def fake(req, timeout):
        calls.append(1)
        raise ConnectionRefusedError("refused")
    monkeypatch.setattr(C, "_get_status", fake)
    assert C.ping({"port": 1, "token": "t"}) is False and len(calls) == 1, "꺼진 서버(거부)는 다시 묻지 않는다"
    assert capsys.readouterr().err == ""


def test_ping_busy_twice_is_offline_with_one_line(monkeypatch, capsys):
    def fake(req, timeout):
        raise socket.timeout("timed out")
    monkeypatch.setattr(C, "_get_status", fake)
    monkeypatch.setattr(C, "_SLOW_SAID", set())
    m = {"port": 4321, "token": "t"}
    assert C.ping(m) is False and C.ping(m) is False
    err = [ln for ln in capsys.readouterr().err.splitlines() if ln]
    assert len(err) == 1 and err[0].startswith("[hd] ") and "4321" in err[0], err


def test_hub_markers_busy_hub_says_one_line(monkeypatch, capsys):
    monkeypatch.setattr(C, "hub_record", lambda: {"port": 4322, "token": "t", "pid": 1, "url": "u"})
    monkeypatch.setattr(C, "_get_json", lambda req, timeout: (_ for _ in ()).throw(socket.timeout("timed out")))
    monkeypatch.setattr(C, "_SLOW_SAID", set())
    assert C.hub_markers() == []
    err = [ln for ln in capsys.readouterr().err.splitlines() if ln]
    assert len(err) == 1 and "홈 서버" in err[0] and "4322" in err[0], err


# ---------------------------------------------------------------- 고정비
class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"rev": 0, "state": {}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


def test_local_http_does_not_load_certificate_store():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        code = ("import ssl, sys\n"
                "def boom(*a, **k): raise SystemExit('인증서 저장소를 읽었어요')\n"
                "ssl.create_default_context = boom; ssl.SSLContext.load_default_certs = boom\n"
                "sys.path.insert(0, %r)\n"
                "import hd_client as C\n"
                "m = {'port': %d, 'token': 't'}\n"
                "assert C.ping(m) is True\n"
                "assert C.call(m, '/api/state', method='GET')[0] == 200\n"
                "print('ok')\n") % (str(HD), srv.server_address[1])
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr
    finally:
        srv.shutdown(); srv.server_close()


@pytest.mark.skipif(sys.platform != "win32", reason="tasklist 는 Windows 만")
def test_pid_check_does_not_spawn_tasklist(monkeypatch):
    def no_spawn(*a, **k):
        raise AssertionError("tasklist 를 불렀어요: %r" % (a,))
    monkeypatch.setattr(C.subprocess, "run", no_spawn)
    assert "python" in (C._image(os.getpid()) or "")
    assert C.pid_alive(os.getpid()) is True
    p = subprocess.Popen([sys.executable, "-c", "pass"]); p.wait()
    assert C._image(p.pid) is None, "끝난 프로세스"


def test_running_skips_ping_for_dead_pid(monkeypatch):
    """Windows 에서 닫힌 포트에 붙기는 거부까지 약 2초 — 죽은 pid 의 표지는 묻지 않는다(살아 있나는 이제 싸다)."""
    pinged = []
    monkeypatch.setattr(C, "markers", lambda: [{"pid": 11, "port": 1, "token": "t", "out": "a"}, {"pid": 22, "port": 2, "token": "t", "out": "b"}])
    monkeypatch.setattr(C, "pid_alive", lambda pid: pid == 22)
    monkeypatch.setattr(C, "ping", lambda m, timeout=None: pinged.append(m["pid"]) or True)
    assert [m["pid"] for m in C.running()] == [22] and pinged == [22]
