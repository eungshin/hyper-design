"""hd_sdk unit — 가짜 Transport 로 Hub·Project·Note·Event·HdError 가족을 본다. 서버·자식 프로세스 없음(out 폴더 파일만 임시로)."""
import ast, json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.HD))
import hd_client as C  # noqa: E402
import hd_model as M  # noqa: E402
import hd_sdk as S  # noqa: E402

SDK = hdfix.HD / "hd_sdk"


class FakeTransport:
    """request(method, path, body) → 대본의 답. 대본 = {(method, path): (code, body) | callable(body) | Exception}."""

    def __init__(self, script):
        self.script, self.calls = dict(script), []

    def request(self, method, path, body=None, timeout=10):
        self.calls.append((method, path, body))
        r = self.script.get((method, path))
        if r is None:
            return 404, {"error": "모르는 주소"}
        if isinstance(r, Exception):
            raise r
        return r(body) if callable(r) else r


def state_of(out):
    return json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))


@pytest.fixture()
def out(tmp_path):
    return hdfix.make_out(tmp_path / "w")


def project(out, script):
    t = FakeTransport(script)
    st = state_of(out)
    t.script.setdefault(("GET", "/api/state"), (200, {"rev": st["rev"], "state": st["state"]}))
    m = {"pid": 1, "project": "proj-a", "out": str(out), "url": "http://x/", "token": "t", "port": 1, "agent": None}
    return S.Project(m, transport=t), t


# ---------------------------------------------------------------- HdError 가족
def test_errors_map_status_keep_message_and_add_next():
    e = S.from_status(409, {"error": "rev 가 달라요"})
    assert isinstance(e, S.Conflict) and str(e) == "도우미가 거절했어요(409): rev 가 달라요" and e.next and e.code == 1
    assert e.line() == str(e) + " — 다음: " + e.next
    assert type(S.from_status(413, {"error": "x"})) is S.TooLarge and type(S.from_status(403, {})) is S.Unauthorized
    assert type(S.from_status(404, {"error": "x"})) is S.NotFound and type(S.from_status(500, {"error": "x"})) is S.HdError
    e = S.from_status(400, {"errors": ["a: 없어요", "b: 길어요"]}, "홈 서버")
    assert isinstance(e, S.Invalid) and str(e) == "홈 서버가 거절했어요(400): a: 없어요\n  b: 길어요"
    assert S.TimedOut("x").code == 2 and S.NotYet("x").next
    assert S.Offline("m").as_dict() == {"error": "m", "kind": "Offline", "next": S.Offline.default_next}
    assert S.Offline("m", next="").line() == "m", "next='' = 메시지가 이미 다음 행동을 말함"
    assert S.HdError("a — hd ls", next="hd ls").line() == "a — hd ls", "메시지에 이미 있으면 붙이지 않음"
    assert all(issubclass(k, S.HdError) for k in (S.Offline, S.NotFound, S.Conflict, S.TooLarge, S.Unauthorized, S.Invalid, S.TimedOut, S.NotYet))


def test_client_errors_become_the_sdk_family():
    for raw, want in ((C.TimedOut("t"), S.TimedOut), (C.NotFound("n"), S.NotFound), (C.Offline("o"), S.Offline), (C.HdError("h"), S.HdError)):
        with pytest.raises(want) as ei:
            with S.client_errors():
                raise raw
        assert str(ei.value) == str(raw) and type(ei.value) is want


def test_model_modules_are_pure():
    """errors · values 는 I/O 를 모른다(층: Model)."""
    for name, allowed in (("errors.py", set()), ("values.py", {"dataclasses", "hd_model"})):
        tree = ast.parse((SDK / name).read_text(encoding="utf-8"))
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
               {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert mods <= allowed, (name, mods - allowed)


# ---------------------------------------------------------------- Note · Event
def test_note_is_the_hd_model_row(out):
    st = state_of(out)["state"]
    ns = S.Note.from_state(st)
    rows = M.pick(M.rows(st["notes"], st.get("note-seq")))
    assert [n.as_dict() for n in ns] == rows and [list(n.as_dict()) for n in ns] == [list(r) for r in rows], "같은 값·같은 키 순서"
    assert [n.ref for n in ns] == ["home#1", "home#2", "list#1"] and all(n.is_open for n in ns)
    assert [n.ref for n in S.Note.from_state(st, "all")][-1] == "list#2"
    assert S.Note.from_state({"notes": "broken"}) == [] and S.Note.from_state(None) == []
    assert ns[0].line() == M.format_rows([rows[0]]) and S.text.notes(ns) == M.format_rows(rows)


def test_event_from_protocol_shape():
    e = S.Event.from_dict({"id": 7, "type": "screen.written", "ts": 5, "project": "p", "screen": "home"})
    assert (e.id, e.type, e.ts, e.project, e.data) == (7, "screen.written", 5, "p", {"screen": "home"})
    for bad in ({"type": "x"}, {"id": "7", "type": "x"}, {"id": 1}, None):
        with pytest.raises(ValueError):
            S.Event.from_dict(bad)


# ---------------------------------------------------------------- Project
def test_notes_read_through_the_server(out):
    p, t = project(out, {})
    assert [n.ref for n in p.notes()] == ["home#1", "home#2", "list#1"] and t.calls == [("GET", "/api/state", None)]
    assert p.name == "proj-a" and p.online and p.url == "http://x/"


def test_offline_project_reads_the_file_and_refuses_writes(out):
    p = S.Project(out=out)
    assert not p.online and p.name == "proj-a" and len(p.notes("all")) == 4 and p.state()["rev"] == 3
    with pytest.raises(S.Offline) as ei:
        p.reply("home#1", {"kind": "대체됨", "where": "x"})
    assert "도우미가 없어요" in str(ei.value) and "helper.py" in str(ei.value) and ei.value.line() == str(ei.value)


def test_reply_checks_locally_then_posts(out):
    p, t = project(out, {("POST", "/api/reply"): (200, {"rev": 4, "status": "done", "note": "n1", "screen": "home"})})
    with pytest.raises(S.NotFound, match="없는 메모: home#9"):
        p.reply("home#9", {"kind": "대체됨", "where": "x"})
    with pytest.raises(S.Invalid) as ei:
        p.reply("home#1", {"kind": "반영됨", "what": "x", "screens": ["ghost"]})
    assert "screens: 없는 화면 ghost" in str(ei.value) and "captured: 없어요" in str(ei.value)
    assert not [c for c in t.calls if c[0] == "POST"], "규칙에 어긋나면 보내지 않는다"
    r = {"kind": "반영됨", "what": "버튼", "screens": ["home"], "captured": True}
    assert p.reply("home#1", r)["status"] == "done"
    assert t.calls[-1] == ("POST", "/api/reply", {"note": {"screen": "home", "no": 1}, "reply": r})
    p.reply("n2", {"kind": "답변", "text": "네"})
    assert t.calls[-1][2]["note"] == "n2"


@pytest.mark.parametrize("code,kind", [(409, S.Conflict), (413, S.TooLarge), (403, S.Unauthorized), (400, S.Invalid), (500, S.HdError)])
def test_server_refusals_are_typed(out, code, kind):
    p, _ = project(out, {("POST", "/api/claim"): (code, {"error": "왜"})})
    with pytest.raises(kind) as ei:
        p.claim("home")
    assert str(ei.value) == "도우미가 거절했어요(%d): 왜" % code


def test_unreachable_server_is_offline(out):
    p, _ = project(out, {("GET", "/api/state"): S.Offline("도우미에 닿지 않아요(x): y")})
    with pytest.raises(S.Offline):
        p.notes()


def test_claim_release_apply_files_attach(out):
    p, t = project(out, {("POST", "/api/claim"): (200, {"rev": 4, "screen": "home", "file": "screens/home.html"}),
                         ("POST", "/api/release"): (200, {"rev": 5, "released": True}),
                         ("POST", "/api/apply"): lambda b: (200, {"applied": [e["id"] for e in b["edits"]], "failed": [], "stamp": None}),
                         ("GET", "/api/files?since=3"): (200, {"seq": 4, "changed": ["home"]}),
                         ("POST", "/api/attach"): lambda b: (200, {"agent": b["agent"]})})
    with pytest.raises(S.Invalid):
        p.claim("home", by="a b")
    with pytest.raises(S.NotFound, match="없는 화면이에요: ghost — 있는 화면: home, list"):
        p.claim("ghost")
    with pytest.raises(S.NotFound):
        p.release("ghost")
    assert not t.calls, "검사에 걸리면 서버에 가지 않는다"
    assert p.claim("home", by="me", note="고치는 중")["file"] == "screens/home.html"
    assert t.calls[-1] == ("POST", "/api/claim", {"screen": "home", "by": "me", "note": "고치는 중"})
    p.claim("home")
    assert t.calls[-1][2] == {"screen": "home"}
    assert p.release("home") == {"rev": 5, "released": True}
    assert p.apply([{"id": "e1", "screen": "home", "edit": "text", "path": "h1", "value": "x"}], **{"async": True})["applied"] == ["e1"]
    assert t.calls[-1][2]["async"] is True
    assert p.files(3) == {"seq": 4, "changed": ["home"]}
    assert p.attach("ag-1") == "ag-1" and p.agent == "ag-1"
    with pytest.raises(S.Invalid):
        p.attach("a b")


def test_events_without_a_stream_is_not_yet(out):   # 47-4b — events 는 test_hd_sdk_events.py. 흐름을 못 여는 transport = NotYet(바로)
    p, _ = project(out, {})
    with pytest.raises(S.NotYet) as ei:
        p.events()
    assert "이벤트" in str(ei.value) and ei.value.next


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_wait_returns_working_notes_or_times_out(out):
    p, t = project(out, {})
    st, ns = p.wait(10, clock=Clock(), sleep=Clock().sleep)
    assert st["rev"] == 3 and [n.ref for n in ns] == ["home#1", "home#2", "list#1"]
    quiet, _ = project(out, {("GET", "/api/state"): (200, {"rev": 3, "state": {"notes": []}})})
    c = Clock()
    with pytest.raises(S.TimedOut) as ei:
        quiet.wait(5, poll=2, clock=c, sleep=c.sleep)
    assert ei.value.code == 2 and "5초 동안 보낸 메모가 없어요" in str(ei.value) and c.t == 5


def test_wait_follows_a_restarted_server(out, capsys):
    """서버가 다시 떠 토큰이 바뀌면 finder 가 찾은 새 표지로 이어 간다([hd] 경고 한 줄)."""
    t = FakeTransport({})
    st = state_of(out)
    m = {"pid": 1, "project": "proj-a", "out": str(out), "url": "u", "token": "old", "port": 1}
    new = dict(m, token="new")
    p = S.Project(m, transport=t, finder=lambda o: new)
    calls = {"n": 0}

    def flaky(body):
        calls["n"] += 1
        if calls["n"] == 1:
            raise S.Offline("닿지 않아요")
        return 200, {"rev": 9, "state": st["state"]}
    t.script[("GET", "/api/state")] = flaky
    c = Clock()
    got, ns = p.wait(10, clock=c, sleep=c.sleep)
    assert got["rev"] == 9 and p.marker["token"] == "new" and ns
    assert capsys.readouterr().err.count("[hd]") == 1


# ---------------------------------------------------------------- Hub
def test_hub_hello_new_and_refusals():
    t = FakeTransport({("GET", "/v1/sessions"): (200, {"sessions": [{"project": "a"}, {"project": "b"}]}),
                       ("POST", "/api/new"): lambda b: (200, {"name": "x", "title": b.get("title"), "url": "u"})})
    hub = S.Hub(record={"url": "http://h/", "port": 5, "pid": 2, "token": "k"}, transport=t)
    assert hub.running and hub.hello() == {"url": "http://h/", "port": 5, "pid": 2, "sessions": 2}
    assert hub.new("새 것")["title"] == "새 것" and t.calls[-1] == ("POST", "/api/new", {"title": "새 것"})
    bad = S.Hub(record={"url": "u", "port": 5, "pid": 2, "token": "k"}, transport=FakeTransport({("GET", "/v1/sessions"): (403, {"error": "토큰"})}))
    with pytest.raises(S.Unauthorized, match="홈 서버가 거절했어요"):
        bad.hello()


def test_hub_offline_says_how_to_start(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_HOME", str(tmp_path / "home"))
    hub = S.Hub()
    assert not hub.running and hub.url is None
    with pytest.raises(S.Offline) as ei:
        hub.hello()
    assert ei.value.next == "hd home --no-browser 로 띄우세요"


def test_hub_picks_with_typed_errors(tmp_path, monkeypatch, out):
    monkeypatch.setenv("HD_HOME", str(tmp_path / "home"))
    hub = S.Hub()
    assert hub.canvases() == [] and hub.projects() == []
    with pytest.raises(S.NotFound, match="떠 있는 캔버스가 없어요 — 떠 있는 것: 없음"):
        hub.project()
    with pytest.raises(S.NotFound):
        hub.pick()
    assert hub.project(out=str(out)).online is False
    with pytest.raises(S.Offline, match="도우미가 없어요"):
        hub.project(out=str(out), need_helper=True)
    e, added, old = hub.save(out=str(out), name="my-run")
    assert added and old is None and e["name"] == "my-run" and [r["name"] for r in hub.projects()] == ["my-run"]
    with pytest.raises(S.NotFound, match="저장한 프로젝트에 'zz' 이 없어요"):
        hub.forget("zz")
    assert hub.forget("my-run")["name"] == "my-run"
    with pytest.raises(S.NotFound, match="모르는 프로젝트예요"):
        hub.open("zz")
