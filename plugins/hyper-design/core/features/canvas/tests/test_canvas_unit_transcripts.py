"""S3b — 터미널 대화 기록(transcript_parse · transcripts · transcript_pump). 줄은 손으로 쓴 가짜(실제 세션 기록을 담지 않는다),
paseo 는 가짜 실행기 — 실제 paseo·claude 를 띄우지 않는다."""
import json, pathlib, subprocess, sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import transcript_parse as TP  # noqa: E402
import transcript_pump as PU  # noqa: E402
import transcripts as TS  # noqa: E402


def line(d):
    return (json.dumps(d, ensure_ascii=False) + "\n").encode("utf-8")


def user(uuid, text, **kw):
    return line(dict({"type": "user", "uuid": uuid, "timestamp": "2026-10-25T01:00:00.000Z", "isSidechain": False,
                      "message": {"role": "user", "content": text}}, **kw))


def asst(uuid, blocks, **kw):
    return line(dict({"type": "assistant", "uuid": uuid, "timestamp": "2026-10-25T01:00:01.000Z", "isSidechain": False,
                      "message": {"role": "assistant", "content": blocks}}, **kw))


TEXT = lambda t: {"type": "text", "text": t}                                        # noqa: E731
TOOL = lambda n, i: {"type": "tool_use", "id": "toolu_x", "name": n, "input": i}    # noqa: E731


# ---------------------------------------------------------------- 파서(순수)
def test_claude_parser_keeps_user_assistant_tool_only():
    data = b"".join([
        user("u1", "홈 화면 버튼을 키워줘"),
        asst("a1", [{"type": "thinking", "thinking": "속생각"}]),
        asst("a2", [TEXT("고칠게요.")]),
        asst("a3", [TOOL("Edit", {"file_path": "C:\\p\\out\\screens\\home.html", "old_string": "x"})]),
        user("u2", [{"type": "tool_result", "tool_use_id": "toolu_x", "content": "ok"}]),
        line({"type": "system", "uuid": "s1", "subtype": "hook"}),
        line({"type": "attachment", "uuid": "t1", "attachment": {}}),
        line({"type": "last-prompt", "lastPrompt": "x"}),
        user("u3", [TEXT("<system-reminder>숨김</system-reminder>")]),
        user("u4", "<task-notification>일꾼 끝</task-notification>"),
        user("u5", "메타", isMeta=True),
        user("u6", "곁가지", isSidechain=True),
        user("u7", "일꾼 알림", turnOrigin="task_notification"),
        user("u8", "<command-message>hd</command-message>\n<command-name>/hd</command-name>\n<command-args>list</command-args>"),
    ])
    got, used = TP.parse_claude(data)
    assert used == len(data)
    assert [(e["role"], e["text"]) for e in got] == [
        ("user", "홈 화면 버튼을 키워줘"), ("assistant", "고칠게요."), ("tool", "Edit screens/home.html"), ("user", "/hd list")]
    assert got[0] == {"id": "u1:0", "role": "user", "text": "홈 화면 버튼을 키워줘", "at": "2026-10-25T01:00:00.000Z"}


def test_claude_parser_skips_malformed_and_keeps_partial_last_line():
    good, partial = user("u1", "하나"), user("u2", "둘")[:-5]
    data = b"{not json\n" + b"\xff\xfe\n" + good + partial
    got, used = TP.parse_claude(data)
    assert [e["text"] for e in got] == ["하나"]
    assert used == len(data) - len(partial)          # 덜 쓴 줄은 먹지 않는다


def test_cap_text_and_entries_per_call():
    big = "가" * (TP.TEXT_MAX + 50)
    got, _ = TP.parse_claude(user("u1", big))
    assert len(got[0]["text"]) == TP.TEXT_MAX and got[0]["text"].endswith("…")
    data = b"".join(user("u%d" % i, "말 %d" % i) for i in range(5))
    got, used = TP.parse_claude(data, max_entries=3)
    assert [e["text"] for e in got] == ["말 0", "말 1", "말 2"]
    got2, _ = TP.parse_claude(data[used:], max_entries=3, start=used)
    assert [e["text"] for e in got2] == ["말 3", "말 4"]


def test_tool_summary_is_one_short_line():
    assert TP.tool_summary("Bash", {"command": "pytest -q\nsecond", "description": "테스트 돌리기"}) == "Bash 테스트 돌리기"
    assert TP.tool_summary("Grep", {"pattern": "foo"}) == "Grep foo"
    assert TP.tool_summary("Mystery", None) == "Mystery"
    assert len(TP.tool_summary("Bash", {"command": "x" * 500})) == TP.TOOL_MAX


def test_line_without_uuid_gets_stable_offset_id():
    d = line({"type": "user", "message": {"role": "user", "content": "id 없음"}})
    got, _ = TP.parse_claude(b"\n" + d, start=100)
    assert got[0]["id"] == "c101:0"


def test_paseo_parser_tolerates_shapes():
    items = [{"type": "user_message", "text": "안녕", "timestamp": "2026-10-25T01:00:00Z", "id": "e1"},
             {"type": "assistant_message", "content": [{"type": "thinking", "text": "x"}, {"type": "text", "text": "네"}], "timestamp": "2026-10-25T01:00:01Z", "id": "e2"},
             {"type": "tool_call", "name": "Edit", "input": {"file_path": "a/b/c.html"}, "timestamp": "2026-10-25T01:00:02Z", "id": "e3"},
             {"type": "reasoning", "text": "숨김"}, {"type": "error", "message": "x"}, "junk"]
    want = [("user", "안녕"), ("assistant", "네"), ("tool", "Edit b/c.html")]
    assert [(e["role"], e["text"]) for e in TP.parse_paseo(json.dumps(items))] == want
    assert [(e["role"], e["text"]) for e in TP.parse_paseo(json.dumps({"entries": items}))] == want
    jl = "\n".join(json.dumps(i) for i in items) + "\n{broken"
    assert [(e["role"], e["text"]) for e in TP.parse_paseo(jl)] == want
    no_id = TP.parse_paseo(json.dumps([{"role": "user", "text": "같은 말", "at": 1761354000000}]))
    assert no_id == TP.parse_paseo(json.dumps([{"role": "user", "text": "같은 말", "at": 1761354000000}]))   # 해시 id 가 같다
    assert no_id[0]["at"].endswith("Z")


def test_cursors_reject_foreign_strings():
    assert TP.claude_cursor(None) == 0 and TP.claude_cursor("c1:42") == 42 and TP.claude_cursor(TP.END) == TP.END
    for bad in ("p1:x\t", "c1:-1", "42", "c1:"):
        with pytest.raises(ValueError):
            TP.claude_cursor(bad)
    with pytest.raises(ValueError):
        TP.paseo_cursor("c1:3")


# ---------------------------------------------------------------- ClaudeTranscript(파일, 커서)
def claude_home(tmp_path, cwd="C:\\Code\\proj", session="s-1", data=b""):
    folder = tmp_path / "projects" / TS.encode_cwd(cwd)
    folder.mkdir(parents=True)
    (folder / (session + ".jsonl")).write_bytes(data)
    return folder / (session + ".jsonl")


def test_encode_cwd_matches_claude_folder_names():
    assert TS.encode_cwd("C:\\Code\\hyper-design") == "C--Code-hyper-design"


def test_claude_reads_incrementally_from_cursor(tmp_path):
    f = claude_home(tmp_path, data=user("u1", "하나") + asst("a1", [TEXT("둘")]))
    src = TS.ClaudeTranscript("s-1", tmp_path, ["C:\\Code\\proj"])
    got, cur = src.read(None)
    assert [e["text"] for e in got] == ["하나", "둘"]
    assert src.read(cur) == ([], cur)                # 같은 커서 = 새 줄 없음
    half = user("u2", "셋")
    with open(f, "ab") as fh:
        fh.write(half[:10])
    assert src.read(cur) == ([], cur)                # 덜 쓴 줄은 아직
    with open(f, "ab") as fh:
        fh.write(half[10:])
    got, cur2 = src.read(cur)
    assert [e["text"] for e in got] == ["셋"] and cur2 != cur
    assert src.read(TP.END) == ([], cur2)            # END = 지금 끝


def test_claude_finds_file_by_exact_name_only(tmp_path):
    claude_home(tmp_path, cwd="D:\\elsewhere", session="s-2", data=user("u1", "여기"))
    claude_home(tmp_path, cwd="D:\\other", session="s-3", data=user("u1", "다른 세션"))
    got, _ = TS.ClaudeTranscript("s-2", tmp_path, ["C:\\nope"]).read(None)
    assert [e["text"] for e in got] == ["여기"]
    with pytest.raises(TS.TranscriptUnavailable):
        TS.ClaudeTranscript("s-9", tmp_path).read(None)
    with pytest.raises(ValueError):
        TS.ClaudeTranscript("../s-3", tmp_path)       # 경로 글자는 세션 id 가 아니다


def test_claude_long_line_is_read_whole(tmp_path, monkeypatch):
    monkeypatch.setattr(TS, "CHUNK", 64)
    claude_home(tmp_path, data=user("u1", "긴 말 " * 40) + user("u2", "짧은 말"))
    src = TS.ClaudeTranscript("s-1", tmp_path, ["C:\\Code\\proj"])
    got, cur = src.read(None)
    assert got[0]["text"].startswith("긴 말")
    got, _ = src.read(cur)
    assert [e["text"] for e in got] == ["짧은 말"]


# ---------------------------------------------------------------- PaseoTranscript(가짜 실행기)
class FakePaseo:
    def __init__(self, items, code=0):
        self.items, self.code, self.calls = items, code, []

    def __call__(self, args, **kw):
        self.calls.append((args, kw.get("creationflags")))
        assert "send" not in args and "run" not in args   # 읽기만
        items = self.items
        if "--since" in args:
            at = args[args.index("--since") + 1]
            items = [i for i in items if i["timestamp"] >= at]
        if "--tail" in args:
            items = items[-int(args[args.index("--tail") + 1]):]
        return subprocess.CompletedProcess(args, self.code, json.dumps(items), "")


def pitem(i, at, text):
    return {"id": "e%d" % i, "type": "assistant_message", "text": text, "timestamp": at}


def test_paseo_reads_new_entries_with_cursor_and_no_window():
    fake = FakePaseo([pitem(1, "T1", "하나"), pitem(2, "T2", "둘"), pitem(3, "T2", "셋")])
    src = TS.PaseoTranscript("ag-1", lambda: "paseo.exe", fake)
    got, cur = src.read(None)
    assert [e["text"] for e in got] == ["하나", "둘", "셋"]
    assert src.read(cur)[0] == []                    # 같은 시각(T2) 줄도 다시 내지 않는다
    fake.items.append(pitem(4, "T2", "넷"))
    fake.items.append(pitem(5, "T3", "다섯"))
    got, cur = src.read(cur)
    assert [e["text"] for e in got] == ["넷", "다섯"]
    assert src.read(TP.END)[1] == TP.paseo_cursor_str("T3", ["e5"])
    assert all(flags == TS.AD.NO_WINDOW for _, flags in fake.calls)
    assert fake.calls[0][0][:3] == ["paseo.exe", "logs", "ag-1"]


def test_paseo_failure_is_reported_not_hidden():
    with pytest.raises(TS.TranscriptUnavailable):
        TS.PaseoTranscript("ag-1", lambda: "paseo.exe", FakePaseo([], code=1)).read(None)
    with pytest.raises(TS.TranscriptUnavailable):
        TS.PaseoTranscript("ag-1", lambda: None, FakePaseo([])).read(None)


# ---------------------------------------------------------------- source_for(고르기)
def test_source_for_chooses_by_kind(tmp_path):
    env = TS.SourceEnv(tmp_path, (), lambda: "paseo.exe", FakePaseo([]))
    assert isinstance(TS.source_for({"id": "claude-1", "kind": "claude", "session": "abc"}, env), TS.ClaudeTranscript)
    assert isinstance(TS.source_for({"id": "ag-1", "kind": "paseo"}, env), TS.PaseoTranscript)
    assert isinstance(TS.source_for({"id": "ag-1"}, env), TS.PaseoTranscript)        # 붙이기만 한 id = Paseo
    for rec in ({"id": "claude-1", "kind": "claude"}, {"id": "x", "kind": "codex"}, {"id": "x", "kind": "other"},
                {"id": "c", "kind": "claude", "session": "../x"}, None):
        src = TS.source_for(rec, env)
        assert isinstance(src, TS.NoTranscript) and src.read("") == ([], "")


# ---------------------------------------------------------------- 펌프
class FakeSource(TS.TranscriptSource):
    kind = "fake"

    def __init__(self):
        self.lines, self.fail = [], None

    def read(self, since):
        if self.fail:
            raise TS.TranscriptUnavailable(self.fail)
        n = len(self.lines) if since == TP.END else int(since or 0)
        return [dict(id=str(i), role="user", text=t, at="") for i, t in enumerate(self.lines[n:], n)], str(len(self.lines))


def pump(allowed=("a1",)):
    seen, src, t = [], FakeSource(), [0.0]
    p = PU.TranscriptPump(lambda type_, **d: seen.append(dict(d, type=type_)), lambda aid: {"id": aid, "kind": "x"},
                          lambda aid: aid in allowed, factory=lambda r: src, clock=lambda: t[0])
    return p, seen, src, t


def test_pump_publishes_only_new_entries():
    p, seen, src, t = pump()
    src.lines = ["옛 말"]
    assert p.watch("a1")
    p.tick()
    assert seen == []                                # 붙기 전 기록은 이벤트가 아니다(HTTP 로)
    src.lines.append("새 말")
    t[0] += 1
    p.tick()
    t[0] += 1
    p.tick()
    assert seen == [{"type": "agent.transcript", "agent": "a1", "entries": [{"id": "1", "role": "user", "text": "새 말", "at": ""}]}]


def test_pump_refuses_unselected_and_drops_released(capsys):
    allowed = {"a1"}
    p, seen, src, t = pump(allowed)
    assert not p.watch("zz")
    assert p.http_get({"agent": ["zz"]})[0] == 403
    p.watch("a1")
    allowed.discard("a1")
    p.tick()
    assert p.watching() == []


def test_pump_logs_failure_once_and_keeps_going(capsys):
    p, seen, src, t = pump()
    p.watch("a1")
    src.fail = "없어요"
    p.tick()
    t[0] += 1
    p.tick()
    assert capsys.readouterr().err.count("[hd]") == 1


def test_http_get_history_and_bad_cursor():
    p, seen, src, t = pump()
    src.lines = ["하나", "둘"]
    code, res = p.http_get({"agent": ["a1"]})
    assert code == 200 and [e["text"] for e in res["entries"]] == ["하나", "둘"] and res["cursor"] == "2" and res["source"] == "fake"
    assert p.watching() == ["a1"]                     # 읽으면 지켜보기도 시작
    assert p.http_get({})[0] == 400
    assert p.http_get({"agent": ["a1"], "since": ["x"]})[0] == 400


def test_pump_for_wires_presence_and_attach(tmp_path):
    class Pres:
        def get(self, aid):
            return {"id": aid, "kind": "claude", "session": "s1"} if aid == "claude-9" else None

    class Q:
        agent, repo = "ag-7", None

    class Ev:
        def __init__(self):
            self.seen = []

        def publish(self, type_, **d):
            self.seen.append(type_)

    class Sess:
        presence, queue, events, out = Pres(), Q(), Ev(), tmp_path

    p = PU.pump_for(Sess())
    assert p.allowed("claude-9") and p.allowed("ag-7") and not p.allowed("other")
    assert p.resolve("ag-7") == {"id": "ag-7"} and p.resolve("other") is None
