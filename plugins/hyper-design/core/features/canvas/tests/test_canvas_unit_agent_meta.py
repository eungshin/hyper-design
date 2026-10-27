"""받는 터미널 정보 · 진짜 이미지 보내기(R28) — 서버 쪽.

unit(순수): agent_meta(usage 합 · 모델별 최대 + 기본 · % 반올림 · 빠진 칸 · 선택지 · 답 모양 · paseo 인자) ·
  attach_rules.paths_in/pick_images(요청 글의 '첨부 이미지:' 경로 · .hd-attach 안만) · PaseoAdapter(가짜 run 으로 argv) ·
  Queue.send(가짜 어댑터 — paseo 면 --image, 대기열이면 없음) · AgentInfo(가짜 Queue·어댑터 · 임시 Paseo/Claude 폴더).
slow: 같은 프로세스 도우미 GET /api/agents/info · POST /api/agents/effort · /api/forward images(가짜 paseo 실행기 — 실제 Paseo 에 아무것도 보내지 않는다).
"""
import json, os, sys, threading, types, urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import adapters as AD  # noqa: E402
import agent_info as AI  # noqa: E402
import agent_meta as AM  # noqa: E402
import attach_rules as AR  # noqa: E402

USAGE = {"input_tokens": 10, "cache_creation_input_tokens": 30000, "cache_read_input_tokens": 300000, "output_tokens": 9990}


# ---------------------------------------------------------------- agent_meta(순수)
def test_usage_sum_and_missing_fields():
    assert AM.usage_sum(USAGE) == 340000, "input + cache_creation + cache_read + output"
    assert AM.usage_sum({"input_tokens": 5}) == 5, "빠진 칸 = 0"
    assert AM.usage_sum({"input_tokens": "5", "output_tokens": -3, "cache_read_input_tokens": 7}) == 7, "글·음수는 버림"
    assert AM.usage_sum({}) is None and AM.usage_sum(None) is None and AM.usage_sum({"service_tier": "x"}) is None


def test_context_max_table_and_safe_default():
    assert AM.context_max("claude-opus-5-5") == 1000000
    assert AM.context_max("claude-opus-4-8") == 200000 and AM.context_max("claude-opus-4-8[1m]") == 1000000
    assert AM.context_max("claude-new-9[1m]") == 1000000, "모르는 [1m] = 1M"
    assert AM.context_max("claude-new-9") == AM.DEFAULT_MAX == 200000 and AM.context_max(None) == 200000
    assert AM.model_label("claude-opus-5-5") == "Opus 5.5" and AM.model_label("gpt-x") == "gpt-x" and AM.model_label(None) is None


def test_context_pct_rounding_and_clamp():
    assert AM.context(340000, 1000000) == {"used": 340000, "max": 1000000, "pct": 34}
    assert AM.context(345000, 1000000)["pct"] == 35 and AM.context(344999, 1000000)["pct"] == 34, "반올림"
    assert AM.context(0, 1000000)["pct"] == 0
    assert AM.context(250000, 200000)["pct"] == 100, "최대를 작게 잡아 넘치면 100"
    assert AM.context(None, 1000000) is None and AM.context(5, 0) is None and AM.context(-1, 10) is None


def _line(**kw):
    return json.dumps(kw).encode("utf-8")


def test_last_usage_takes_last_main_assistant():
    data = b"\n".join([
        _line(type="assistant", message={"model": "claude-opus-5-5", "usage": {"input_tokens": 1}}),
        _line(type="user", message={"content": "hi"}),
        _line(type="assistant", message={"model": "claude-opus-5-5", "usage": USAGE}),
        _line(type="assistant", isSidechain=True, message={"model": "claude-opus-5-5", "usage": {"input_tokens": 9}}),
        _line(type="assistant", message={"model": "<synthetic>", "usage": {"input_tokens": 0}}),
        b'{"type":"assistant","message":{"usage":{"input_tok',         # 덜 쓴 마지막 줄
    ])
    assert AM.last_usage(data) == USAGE
    cut = _line(type="assistant", message={"model": "m", "usage": {"input_tokens": 77}})
    assert AM.last_usage(b'"usage":{"input_tokens":5}}}\n' + cut, whole=False) == {"input_tokens": 77}
    assert AM.last_usage(b'{"type":"assistant","message":{"usage":{"input_tokens":5}}}', whole=False) is None, "잘린 첫 줄은 버린다"
    assert AM.last_usage(b"") is None and AM.last_usage(b"not json\n") is None and AM.last_usage(None) is None


def test_effort_options_from_provider_rows_or_default():
    rows = [{"id": "claude-opus-5", "thinkingOptionIds": ["off", "low"]},
            {"id": "claude-opus-5-5", "thinkingOptionIds": ["low", "medium", "high", "xhigh", "max", 3, ""]}]
    assert AM.effort_options(rows, "claude-opus-5-5") == ["low", "medium", "high", "xhigh", "max"]
    assert AM.effort_options(rows, "nope") == list(AM.DEFAULT_EFFORTS) and AM.effort_options(None, "x") == list(AM.DEFAULT_EFFORTS)
    assert AM.check_effort("high", ["low", "high"]) is None
    assert "고를 수 없어요" in AM.check_effort("ultra", ["low", "high"]) and AM.check_effort("", ["low"]) and AM.check_effort(None, ["low"])


def test_info_shape():
    row = {"id": "a1", "name": "HD2", "provider": "claude/claude-opus-5-5", "thinking": "medium"}
    got = AM.info(row, ["low", "medium"], USAGE)
    assert got == {"agent": "a1", "name": "HD2", "provider": "claude", "model": "claude-opus-5-5", "modelLabel": "Opus 5.5",
                   "effort": "medium", "effortOptions": ["low", "medium"], "context": {"used": 340000, "max": 1000000, "pct": 34}}
    assert AM.info(dict(row, thinking="auto"), [], None)["effort"] is None and AM.info(row, [], None)["context"] is None, "모름 = null(0% 가 아님)"
    codex = AM.info({"id": "c", "provider": "codex", "thinking": "high"}, [], USAGE)
    assert codex["context"] is None and codex["model"] is None and codex["modelLabel"] == "codex", "Claude 기록만 읽는다"
    assert AM.info(None, [], None) is None and AM.info({"name": "x"}, [], None) is None


def test_paseo_argv():
    assert AM.send_argv("a1", "/q/1.txt") == ["send", "a1", "--prompt-file", "/q/1.txt", "--no-wait"]
    assert AM.send_argv("a1", "/q/1.txt", ["/o/.hd-attach/x-1.png", "/o/.hd-attach/x-2.jpg"]) == [
        "send", "a1", "--prompt-file", "/q/1.txt", "--image", "/o/.hd-attach/x-1.png", "--image", "/o/.hd-attach/x-2.jpg", "--no-wait"]
    assert AM.update_argv("a1", "high") == ["agent", "update", "a1", "--thinking", "high"]


# ---------------------------------------------------------------- 첨부 경로(순수)
N1, N2 = "20261027-101112-123456-1.png", "20261027-101112-123456-2.jpg"


def test_paths_in_reads_indented_lines_once():
    text = "요청: 버튼을 키워 주세요\n  첨부 이미지: C:\\o\\.hd-attach\\%s\n첨부 이미지: C:\\o\\.hd-attach\\%s\n첨부 이미지: C:\\o\\.hd-attach\\%s\n" % (N1, N2, N1)
    assert AR.paths_in(text) == ["C:\\o\\.hd-attach\\" + N1, "C:\\o\\.hd-attach\\" + N2]
    assert AR.paths_in("") == [] and AR.paths_in(None) == []


def test_pick_images_only_inside_attach_folder():
    f = "C:\\o\\.hd-attach"
    ok, bad = AR.pick_images(f, [f + "\\" + N1, "c:/O/.HD-ATTACH/" + N2, "C:\\o\\screens\\" + N1, f + "\\..\\secret.png",
                                 f + "\\evil.exe", "relative\\" + N1, 5])
    assert ok == ["C:\\o\\.hd-attach\\" + N1, "c:\\O\\.HD-ATTACH\\" + N2], ok
    assert len(bad) == 5
    many = [f + "\\20261027-101112-123456-%d.png" % i for i in range(1, 10)]
    assert len(AR.pick_images(f, many)[0]) == AR.IMAGES_MAX
    assert AR.pick_images("/o/.hd-attach", ["/o/.hd-attach/" + N1, "/o/x/" + N1]) == (["/o/.hd-attach/" + N1], ["/o/x/" + N1])


# ---------------------------------------------------------------- 어댑터(가짜 run)
class Run:
    def __init__(self, code=0, out=b"", err=b""):
        self.calls, self.code, self.out, self.err = [], code, out, err

    def __call__(self, args, **kw):
        self.calls.append(args)
        return types.SimpleNamespace(returncode=self.code, stdout=self.out, stderr=self.err)


def test_paseo_adapter_send_passes_each_image():
    run = Run()
    a = AD.PaseoAdapter(lambda: "/bin/paseo", run=run)
    assert a.send("/q/1.txt", "t", "a1", images=["/o/.hd-attach/" + N1]) == (True, None)
    assert run.calls[-1] == ["/bin/paseo", "send", "a1", "--prompt-file", "/q/1.txt", "--image", "/o/.hd-attach/" + N1, "--no-wait"]
    a.send("/q/2.txt", "t", {"id": "a2"})
    assert "--image" not in run.calls[-1], "이미지 없으면 예전 그대로"
    AD.PaseoAdapter(lambda: "C:\\P\\paseo.cmd", run=run).send("/q/3.txt", "t", "a1", images=["x"])
    assert run.calls[-1][:3] == ["cmd", "/c", "C:\\P\\paseo.cmd"]


def test_paseo_adapter_update_thinking_and_failure_reason():
    run = Run()
    assert AD.PaseoAdapter(lambda: "/bin/paseo", run=run).update_thinking("a1", "high") == (True, None)
    assert run.calls[-1] == ["/bin/paseo", "agent", "update", "a1", "--thinking", "high"]
    bad = Run(code=1, err="Error: thinking option 'max' not supported\n".encode("utf-8"))
    ok, why = AD.PaseoAdapter(lambda: "/bin/paseo", run=bad).update_thinking("a1", "max")
    assert not ok and "not supported" in why
    assert AD.PaseoAdapter(lambda: None, run=run).update_thinking("a1", "high") == (False, AD.NO_PASEO)
    rows, why = AD.PaseoAdapter(lambda: "/bin/paseo", run=Run(out=b'[{"id":"m"}]')).read_json(["provider", "models", "claude", "--thinking", "--json"])
    assert rows == [{"id": "m"}] and why is None
    assert AD.PaseoAdapter(lambda: "/bin/paseo", run=Run(out=b"nope")).read_json(["x"]) == (None, "JSON 이 아니에요")


# ---------------------------------------------------------------- Queue.send(가짜 어댑터)
class FakeAdapter(AD.AgentAdapter):
    def __init__(self, name):
        self.name, self.sent = name, []

    def ready(self):
        return True

    def send(self, path, text, target, images=()):
        self.sent.append({"path": path, "target": target, "images": list(images)})
        return True, None


def _queue(tmp_path, agent="a1"):
    import send_queue
    out = tmp_path / "out"
    (out / ".hd-attach").mkdir(parents=True)
    (out / ".hd-attach" / N1).write_bytes(b"\x89PNG\r\n\x1a\n")
    q = send_queue.Queue(out, threading.Lock(), agent=agent)
    q.adapters["paseo"] = FakeAdapter("paseo")
    return q, (out / ".hd-attach" / N1).resolve()


def test_queue_send_hands_images_to_paseo(tmp_path):
    q, img = _queue(tmp_path)
    missing = img.parent / "20261027-101112-123456-9.png"
    text = "요청: 이 화면처럼\n  첨부 이미지: %s\n  첨부 이미지: %s" % (img, missing)
    code, res = q.send({"text": text})
    assert code == 200 and res["via"] == "paseo", res
    assert q.adapters["paseo"].sent[-1]["images"] == [str(img)], "글 줄에서 읽고 없는 파일은 뺀다"
    assert "첨부 이미지: %s" % img in Path(res["path"]).read_text(encoding="utf-8"), "경로 줄은 대기열 글에 그대로"
    code, res = q.send({"text": "x", "images": [str(img), str(tmp_path / "elsewhere.png")]})
    assert code == 200 and q.adapters["paseo"].sent[-1]["images"] == [str(img)], "본문 images 도 .hd-attach 안만"
    assert q.send({"text": "x", "images": "nope"})[0] == 400 and q.send({"text": "x", "images": [""]})[0] == 400


def test_queue_without_receiver_sends_nothing(tmp_path):
    q, img = _queue(tmp_path, agent=None)
    code, res = q.send({"text": "첨부 이미지: %s" % img})
    assert code == 200 and res["via"] == "queue" and q.adapters["paseo"].sent == []


# ---------------------------------------------------------------- AgentInfo(가짜 Queue·어댑터, 임시 폴더)
class FakeQueue:
    def __init__(self, agent, rows):
        self.agent, self.rows, self.calls = agent, rows, 0
        self.agents_cache, self.agents_lock = ("x", None), threading.Lock()

    def agents(self, auto=False):
        self.calls += 1
        return {"agents": self.rows}


class InfoAdapter:
    def __init__(self, update=(True, None), models=None):
        self.updates, self.update, self.reads = [], update, 0
        self.models = models if models is not None else [{"id": "claude-opus-5-5", "thinkingOptionIds": ["low", "medium", "high", "xhigh", "max"]}]

    def update_thinking(self, aid, opt):
        self.updates.append((aid, opt))
        return self.update

    def read_json(self, rest, timeout=20):
        self.reads += 1
        return (self.models, None) if self.models is not False else (None, "boom")


ROW = {"id": "a1", "name": "HD2", "provider": "claude/claude-opus-5-5", "thinking": "medium", "cwd": "C:\\Code\\hyper-design"}
SID = "10126343-2536-4ecd-b559-e4e376e82267"


def _homes(tmp_path, usage=USAGE):
    paseo, claude = tmp_path / "paseo", tmp_path / "claude"
    (paseo / "agents" / "C-Code-hyper-design").mkdir(parents=True)
    (paseo / "agents" / "C-Code-hyper-design" / "a1.json").write_text(json.dumps(
        {"id": "a1", "cwd": ROW["cwd"], "runtimeInfo": {"sessionId": SID}}), encoding="utf-8")
    proj = claude / "projects" / "C--Code-hyper-design"
    proj.mkdir(parents=True)
    lines = [json.dumps({"type": "user", "message": {"content": "x" * 600000}}),
             json.dumps({"type": "assistant", "message": {"model": "claude-opus-5-5", "usage": usage}})]
    (proj / (SID + ".jsonl")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paseo, claude


@pytest.mark.slow
def test_info_reads_model_effort_and_context(tmp_path):
    paseo, claude = _homes(tmp_path)
    ai = AI.AgentInfo(FakeQueue("a1", [ROW]), InfoAdapter(), paseo, claude)
    code, got = ai.get()
    assert code == 200 and got["paseo"] is True and got["modelLabel"] == "Opus 5.5" and got["effort"] == "medium"
    assert got["effortOptions"] == ["low", "medium", "high", "xhigh", "max"]
    assert got["context"] == {"used": 340000, "max": 1000000, "pct": 34}, "긴 파일은 꼬리만 읽어도 마지막 usage"
    ai.get()
    assert ai.adapter.reads == 1, "선택지는 캐시"


@pytest.mark.slow
def test_info_unknown_context_is_null_and_non_paseo_hidden(tmp_path):
    ai = AI.AgentInfo(FakeQueue("a1", [ROW]), InfoAdapter(models=False), tmp_path / "none", tmp_path / "none2")
    code, got = ai.get()
    assert code == 200 and got["context"] is None and got["effortOptions"] == list(AM.DEFAULT_EFFORTS), "기록이 없으면 null · 선택지 실패 = 기본"
    assert AI.AgentInfo(FakeQueue(None, [ROW]), InfoAdapter()).get() == (200, {"agent": None, "paseo": False})
    assert AI.AgentInfo(FakeQueue("hello-agent", [ROW]), InfoAdapter()).get() == (200, {"agent": "hello-agent", "paseo": False})


@pytest.mark.slow
def test_effort_change_validates_and_reports_failure(tmp_path):
    q = FakeQueue("a1", [ROW])
    ad = InfoAdapter()
    ai = AI.AgentInfo(q, ad, tmp_path / "p", tmp_path / "c")
    assert ai.effort({"effort": "ultra"})[0] == 400 and ad.updates == [], "선택지 밖은 paseo 를 부르지 않는다"
    assert ai.effort({})[0] == 400 and ai.effort([1])[0] == 400
    code, got = ai.effort({"effort": "high"})
    assert code == 200 and ad.updates == [("a1", "high")] and q.agents_cache is None, "성공 = ls 캐시를 비우고 새 답"
    ad.update = (False, "not supported")
    code, got = ai.effort({"effort": "max"})
    assert code == 502 and "not supported" in got["error"]
    assert AI.AgentInfo(FakeQueue(None, []), ad).effort({"effort": "high"})[0] == 409


# ---------------------------------------------------------------- 도우미 HTTP(같은 프로세스, 가짜 실행기)
@pytest.mark.slow
def test_http_info_effort_and_forward_images(tmp_path, monkeypatch):
    import helper
    paseo_dir, claude_dir = _homes(tmp_path)
    monkeypatch.setenv("PASEO_HOME", str(paseo_dir))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude_dir))
    out = tmp_path / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens.json").write_text(json.dumps({"groups": [], "screens": []}), encoding="utf-8")
    (out / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
    fake = tmp_path / "paseo.cmd"
    fake.write_text("", encoding="ascii")
    srv = helper.make_server(out, 0, paseo=str(fake))
    sess = srv.session if hasattr(srv, "session") else None
    sess = sess or next(v for v in vars(srv).values() if hasattr(v, "agent_info"))
    run = Run()
    rows = [dict(ROW)]

    def fake_run(args, **kw):
        run.calls.append(args)
        rest = args[3:] if args[:2] == ["cmd", "/c"] else args[1:]
        if rest[:1] == ["ls"]:
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(rows).encode("utf-8"), stderr=b"")
        if rest[:2] == ["provider", "models"]:
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(InfoAdapter().models).encode("utf-8"), stderr=b"")
        if rest[:2] == ["agent", "update"]:
            rows[0]["thinking"] = rest[-1]
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    import send_queue
    monkeypatch.setattr(send_queue.subprocess, "run", fake_run)
    sess.queue.adapters["paseo"].run = fake_run
    sess.queue.agent = "a1"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host = "http://127.0.0.1:%d" % srv.server_address[1]

    def call(method, path, body=None):
        req = urllib.request.Request(host + path, method=method, data=json.dumps(body).encode("utf-8") if body is not None else None,
                                     headers={"X-HD-Token": sess.token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        code, got = call("GET", "/api/agents/info")
        assert code == 200 and got["effort"] == "medium" and got["context"]["pct"] == 34, got
        code, got = call("POST", "/api/agents/effort", {"effort": "high"})
        assert code == 200 and got["effort"] == "high", got
        assert any(a[-5:] == ["agent", "update", "a1", "--thinking", "high"] for a in run.calls)
        assert call("POST", "/api/agents/effort", {"effort": "bogus"})[0] == 400
        img = out.resolve() / ".hd-attach" / N1
        img.parent.mkdir()
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        code, got = call("POST", "/api/forward", {"text": "요청\n첨부 이미지: %s" % img, "notes": [], "images": [str(img)]})
        assert code == 200 and got["via"] == "paseo", got
        sent = [a for a in run.calls if "send" in a][-1]
        assert sent[sent.index("--image") + 1] == str(img) and sent[-1] == "--no-wait", sent
    finally:
        srv.shutdown(); srv.server_close()
