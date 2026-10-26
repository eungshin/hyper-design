"""이벤트 계약 잠금(task 47-4a) — events.json 을 이 프로세스 안 진짜 허브(home_server.make_hub)에 다시 보낸다.

임시 HD_HOME · 가짜 빌드(모드 ok | fail-once | slow — 실제 build_ref 를 띄우지 않음) · 빈 포트(12270·12279 아님) · paseo 없음.
routes = 줄마다 한 요청(흐름이면 첫 덩어리들), flows = 여러 요청·흐름을 차례로(흐름마다 새 세션). 끊긴 구독자가 빠지는지 · 도우미(helper.py) 의 /api/events · 실제 빌드로 async apply 도 여기서.
"""
import http.client, json, os, pathlib, subprocess, sys, threading, time

import pytest

HERE = pathlib.Path(__file__).resolve().parent
CANVAS = HERE.parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(HERE), str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "hd" / "tests"), str(FEATURES / "home")]
import hd_client as C  # noqa: E402
import hdfix  # noqa: E402
import home_server  # noqa: E402
import busy  # noqa: E402
import session as S  # noqa: E402
from test_protocol_v1 import check, send  # noqa: E402

pytestmark = pytest.mark.slow                        # 서버·스레드 — unit 에서 빠진다
DOC = json.loads((HERE / "events.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 가짜 빌드
class FakeBuild:
    def __init__(self):
        self.mode, self.calls = "ok", 0

    def __call__(self, out):
        self.calls += 1
        if self.mode == "slow":
            time.sleep(0.6)
        if self.mode == "fail-once":
            self.mode = "ok"
            return subprocess.CompletedProcess([], 1, "", "fake build failed")
        return subprocess.CompletedProcess([], 0, "", "")


@pytest.fixture
def hub(tmp_path, monkeypatch):
    """허브 하나(이 프로세스) + proj-c(hdfix out) 를 연 세션 → dict(port, vars, build, srv, out)."""
    monkeypatch.setenv("HD_HOME", str(tmp_path / "hd-home"))
    monkeypatch.setattr(C, "build", lambda out: (0, ""))   # 여는 빌드도 가짜(index.html 은 hdfix 가 둔다)
    hdfix.make_out(tmp_path / "w")
    out = tmp_path / "w" / "proj-c" / "out"
    (tmp_path / "w" / "proj-a").rename(out.parent)
    C.register(C.abs_out(out))
    fb = FakeBuild()
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=fb)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    st, _, raw = send(port, srv.token, {"method": "POST", "path": "/api/open", "body": {"name": "proj-c"}}, {})
    res = json.loads(raw)
    assert st == 200 and "/v1/p/proj-c/" in res["url"], res
    srv.registry.get("proj-c").builder._check = fb   # 쓰기 확인도 가짜(figma-lite 5: 쓰기 = 데이터 확인 — build 단계가 이것을 바꾼다)
    try:
        yield {"port": port, "srv": srv, "build": fb, "out": out,
               "vars": {"hub": srv.token, "session": res["url"].split("?hd=")[1], "project": "proj-c"}}
    finally:
        srv.shutdown(); srv.server_close()


# ---------------------------------------------------------------- 흐름 읽기
def fill(x, vars_):
    """${이름} 채우기 — 글 전체가 ${이름} 하나면 값 그대로(정수 id 를 $eq 로 비교), 아니면 글 안에서 바꾼다."""
    if isinstance(x, str):
        if x.startswith("${") and x.endswith("}") and x[2:-1] in vars_:
            return vars_[x[2:-1]]
        for k, v in vars_.items():
            x = x.replace("${%s}" % k, str(v))
        return x
    if isinstance(x, list):
        return [fill(i, vars_) for i in x]
    if isinstance(x, dict):
        return {k: fill(v, vars_) for k, v in x.items()}
    return x


class Stream:
    def __init__(self, port, req, vars_):
        h = {"Host": req.get("host", "127.0.0.1:%d" % port)}
        tok = req.get("token", True)
        if isinstance(tok, str):
            h["X-HD-Token"] = fill(tok, vars_)
        if "last" in req:
            h["Last-Event-ID"] = str(fill(req["last"], vars_))
        self.c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        self.c.request("GET", fill(req["path"], vars_), headers=h)
        self.r = self.c.getresponse()
        self.status, self.ctype = self.r.status, self.r.getheader("Content-Type") or ""
        self.body = self.r.read() if self.status != 200 else None

    def frame(self):
        """다음 덩어리 → {'retry'|'comment'|'id','event','data'}."""
        f = {}
        while True:
            line = self.r.fp.readline()
            if not line:
                raise EOFError("흐름이 끊겼어요")
            line = line.decode("utf-8").rstrip("\n")
            if line == "":
                if f:
                    return f
                continue
            if line.startswith(":"):
                f["comment"] = line[1:].strip()
            else:
                k, _, v = line.partition(": ")
                f[k] = v

    def event(self):
        while True:
            f = self.frame()
            if "data" in f:
                ev = json.loads(f["data"])
                assert f["id"] == str(ev["id"]) and f["event"] == ev["type"], f
                return ev

    def close(self):                                 # 답 객체가 소켓을 쥐고 있다 — 둘 다 닫아야 실제로 끊긴다
        self.r.close()
        self.c.close()


def event_errs(ev, extra, label):
    errs = check(DOC["event"], ev, label)
    t = DOC["types"].get(ev.get("type"))
    if t is None:
        return errs + ["%s: 모르는 이벤트 %r" % (label, ev.get("type"))]
    return errs + check(t["shape"], ev, label) + check(extra or {}, ev, label)


def read_events(s, types, shapes, vars_, label):
    errs, got = [], []
    for i, t in enumerate(types):
        ev = s.event()
        got.append(ev)
        if ev["type"] != t:
            return got, errs + ["%s[%d]: %s 이어야 하는데 %s %r" % (label, i, t, ev["type"], ev)]
        errs += event_errs(ev, fill((shapes or [{}] * len(types))[i], vars_), "%s[%d]" % (label, i))
    return got, errs


# ---------------------------------------------------------------- routes
def test_events_routes(hub):
    port, vars_ = hub["port"], hub["vars"]
    errs = []
    for route in DOC["routes"]:
        for case in route["cases"]:
            label = "%s %s [%s]" % (route["method"], route["path"], case["name"])
            exp, req = case["expect"], case["request"]
            if "stream" not in exp:
                status, ctype, raw = send(port, None, dict(req, token=req.get("token", False)), vars_)
                if status != exp["status"]:
                    errs.append("%s: 상태 %s 이어야 하는데 %s %s" % (label, exp["status"], status, raw[:200]))
                elif "json" in exp:
                    errs += ["%s: %s" % (label, e) for e in check(fill(exp["json"], vars_), json.loads(raw))]
                continue
            s = Stream(port, req, vars_)
            try:
                if s.status != exp["status"] or not s.ctype.startswith(exp["ctype"]):
                    errs.append("%s: %s %s %r" % (label, s.status, s.ctype, s.body))
                    continue
                if "retry" in exp["stream"]:
                    f = s.frame()
                    if f.get("retry") != str(exp["stream"]["retry"]):
                        errs.append("%s: 첫 덩어리가 retry 가 아니에요 %r" % (label, f))
                for i, shape in enumerate(exp["stream"]["events"]):
                    errs += event_errs(s.event(), shape, "%s[%d]" % (label, i))
            finally:
                s.close()
    assert not errs, "\n".join(errs)


# ---------------------------------------------------------------- flows(흐름마다 새 세션)
@pytest.mark.parametrize("flow", DOC["flows"]["cases"], ids=lambda f: f["name"])
def test_events_flow(hub, flow):
    port, vars_ = hub["port"], dict(hub["vars"])
    streams, errs = {}, []
    try:
        for n, step in enumerate(flow["steps"]):
            label = "%s #%d" % (flow["name"], n)
            if "build" in step:
                hub["build"].mode = step["build"]
            elif "open" in step:
                s = streams[step["open"]] = Stream(port, step["request"], vars_)
                assert s.status == 200, (label, s.status, s.body)
                assert s.frame().get("retry") == "2000", label
            elif "send" in step:
                status, _, raw = send(port, None, fill(step["send"], vars_), vars_)
                exp = step["expect"]
                assert status == exp["status"], (label, status, raw[:300])
                body = json.loads(raw) if raw else None
                if "json" in exp:
                    errs += ["%s: %s" % (label, e) for e in check(fill(exp["json"], vars_), body)]
                for var, key in step.get("save", {}).items():
                    vars_[var] = body[key]
            elif "events" in step:
                got, e = read_events(streams[step["events"]], step["types"], step.get("shapes"), vars_, label)
                errs += e
                for var, key in step.get("save", {}).items():
                    vars_[var] = got[-1][key]
            elif "get" in step:
                status, _, raw = send(port, None, {"path": step["get"], "token": False}, vars_)
                assert status == 200 and step["contains"] in raw.decode("utf-8"), (label, status, raw[:300])
            else:
                raise AssertionError("모르는 단계: %r" % step)
    finally:
        for s in streams.values():
            s.close()
    assert not errs, "\n".join(errs)


# ---------------------------------------------------------------- 끊긴 구독자 · 맥박 · 닫기
def test_closed_client_is_dropped_and_heartbeat_flows(hub, monkeypatch):
    import router as R
    monkeypatch.setattr(R, "HEARTBEAT", 0.2)
    monkeypatch.setattr(R, "POLL", 0.1)
    sess = hub["srv"].registry.get("proj-c")
    s = Stream(hub["port"], {"path": "/v1/p/proj-c/events", "token": "${session}"}, hub["vars"])
    assert s.frame().get("retry") == "2000"
    assert s.frame().get("comment") == "hb", "조용하면 맥박 주석"
    assert sess.events.count() == 1
    before = threading.active_count()
    monkeypatch.setattr(R, "HEARTBEAT", 60.0)       # 맥박 쓰기 실패가 아니라 소켓 엿보기(POLL)로 알아채야 한다
    s.close()
    assert hdfix.wait_for(lambda: sess.events.count() == 0, 5), "닫은 손님은 버스에서 빠진다"
    assert hdfix.wait_for(lambda: threading.active_count() < before, 5), "흐름 스레드가 끝난다"


def test_closing_the_session_ends_its_streams(hub):
    s = Stream(hub["port"], {"path": "/v1/p/proj-c/events", "token": "${session}"}, hub["vars"])
    assert s.frame().get("retry") == "2000"
    assert hub["srv"].registry.close("proj-c")
    with pytest.raises((EOFError, OSError)):
        s.frame()
    s.close()


# ---------------------------------------------------------------- 도우미(helper.py) 도 같은 흐름 · 실제 빌드로 async apply
def test_helper_serves_events_and_real_build_async_apply(tmp_path, monkeypatch):
    import helper
    monkeypatch.setenv("HD_HOME", str(tmp_path / "hd-home"))
    import board_data, code_stamp
    out = hdfix.make_out(tmp_path / "w")
    r = subprocess.run([sys.executable, str(CANVAS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr               # 데이터 도장을 품은 진짜 페이지
    built = (out / "index.html").read_text(encoding="utf-8")
    srv = helper.make_server(out)                    # 작업 트리 build_canvas(같은 프로세스 make_server)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port, tok = srv.server_address[1], srv.token
    try:
        s = Stream(port, {"path": "/api/events?hd=" + tok, "token": False}, {})
        assert s.status == 200 and s.frame().get("retry") == "2000"
        assert send(port, None, {"path": "/api/events", "token": False}, {})[0] == 403
        st, _, raw = send(port, tok, {"method": "POST", "path": "/api/apply", "body": {"async": True, "edits": [
            {"id": "r1", "screen": "home", "edit": "text", "path": "h1", "value": "Real"},
            {"id": "r2", "screen": "home", "edit": "title", "value": "Real Home"}]}}, {})
        res = json.loads(raw)
        assert st == 200 and res["accepted"] == ["r1", "r2"], res
        got, errs = read_events(s, ["screen.written", "build.started", "build.done"], None, {}, "helper")
        assert not errs and got[0]["id"] == res["rev"] and got[2]["stamps"] == [res["stamp"]], (errs, got)
        assert "Real" in (out / "screens" / "home.html").read_text(encoding="utf-8")
        assert (out / "index.html").read_text(encoding="utf-8") == built, "쓰기는 데이터만 확인 — index.html 은 굽지 않는다(figma-lite 5)"
        st, _, raw = send(port, tok, {"method": "POST", "path": "/api/data", "body": {}}, {})
        assert st == 200 and "Real Home" in [c["title"] for row in json.loads(raw)["rows"] for c in row["screens"]], "/api/data 는 쓰기 바로 뒤에도 맞다"
        st, _, raw = send(port, None, {"path": "/index.html", "token": False}, {})
        assert st == 200 and "Real Home" in raw.decode("utf-8"), "페이지를 줄 때 옛 데이터면 다시 빌드"
        assert code_stamp.page_inputs((out / "index.html").read_text(encoding="utf-8")) == board_data.input_stamp(out)
        s.close()
    finally:
        srv.shutdown(); srv.server_close()


# ---------------------------------------------------------------- AI 쓰기(지켜보기) → screen.written by ai · ai.write
def test_ai_write_events_from_the_file_watch(tmp_path, monkeypatch):
    monkeypatch.setattr(busy, "WATCH_EVERY", 0.1)
    out = hdfix.make_out(tmp_path / "w")
    sess = S.ProjectSession(out, build=FakeBuild()).open().start()
    try:
        sub = sess.events.subscribe(None)[0]
        assert sess.busy.claim({"screen": "home", "by": "agent"})[0] == 200
        time.sleep(0.3)                              # 지켜보기 기준이 잡힌 뒤
        f = out / "screens" / "home.html"
        f.write_text(f.read_text(encoding="utf-8").replace("<h1>home</h1>", "<h1>AI</h1>"), encoding="utf-8")
        os.utime(f, (time.time() + 5, time.time() + 5))
        got = []
        end = time.time() + 5
        while time.time() < end and not any(e["type"] == "ai.write" for e in got):
            e = sub.get(0.2)
            if isinstance(e, dict):
                got.append(e)
        types = [e["type"] for e in got]
        assert types[:3] == ["claim", "screen.written", "ai.write"], types
        errs = [x for e in got for x in event_errs(e, {}, e["type"])]
        assert not errs, errs
        assert got[1]["by"] == "ai" and got[1]["screens"] == ["home"] and got[2]["act"] == "record" and got[2]["screen"] == "home"
        assert sess.busy.release({"screen": "home"})[0] == 200
        assert sub.get(1)["type"] == "release"
    finally:
        sess.close()
