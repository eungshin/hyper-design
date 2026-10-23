"""hd Model — 답 검사·상태(공유 fixture replies.json)·번호 대신 매기기·줄 만들기·순수성. 브라우저 없음."""
import ast, json, sys
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
import hd_model as M  # noqa: E402

CASES = json.loads((HD / "tests" / "fixtures" / "replies.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture_case(case):
    errs = []
    for r in case["replies"]:
        errs += M.check_reply(r, case["note_intent"], agent=case.get("from") == "agent")
    assert (not errs) == case["valid"], errs
    if not case["valid"]:
        assert any(case["reason"] in e for e in errs), (case["reason"], errs)
    else:
        note = {"intent": case["note_intent"], "sent": case.get("sent", True), "replies": case["replies"]}
        assert M.status(note) == case["status"]


def test_fixture_covers_every_kind_and_status():
    kinds = {r.get("kind") for c in CASES for r in c["replies"] if isinstance(r, dict)}
    assert set(M.KINDS) | {"보류"} <= kinds
    assert {c["status"] for c in CASES if c["valid"]} == set(M.STATUSES)


def test_one_line_reason_per_failed_field():
    errs = M.check_reply({"kind": "반영됨", "what": "", "screens": [], "captured": "no", "x": 1}, "change")
    assert [e.split(":")[0] for e in errs] == ["x", "what", "screens", "captured"]
    assert all("\n" not in e for e in errs)


def test_known_screens_checked():
    r = {"kind": "반영됨", "what": "a", "screens": ["home", "ghost"], "captured": False}
    assert M.check_reply(r, "change", known_screens={"home"}) == ["screens: 없는 화면 ghost"]
    assert M.check_reply(r, "change") == []


def test_stamp_defaults_by_agent_and_sets_at():
    r = {"kind": "대체됨", "where": "x"}
    s = M.stamp(r, "2026-10-23T10:00:00+09:00")
    assert s == {"kind": "대체됨", "where": "x", "by": "agent", "at": "2026-10-23T10:00:00+09:00"} and "by" not in r
    assert M.stamp(dict(r, by="codex"), "t")["by"] == "codex"


def test_numbers_fallback_matches_annotation_migrate():
    notes = [{"screen": "a"}, {"screen": "b", "no": 4}, {"screen": "a"}, {"screen": "b"}, {"id": "x"}, {"screen": "c"}]
    assert M.numbers(notes) == [1, 4, 2, 5, None, 1]
    assert M.numbers(notes, {"a": 7, "c": "bad"}) == [8, 4, 9, 5, None, 1], "note-seq 다음부터"
    assert M.numbers([{"screen": "a", "no": 2}, {"screen": "a", "no": 1}]) == [2, 1], "있는 번호는 그대로"


def test_find_by_ref_and_parse_ref():
    notes = [{"id": "n1", "screen": "home"}, {"id": "n2", "screen": "home", "no": 3}, {"id": "n3", "screen": "x#y"}]
    assert M.parse_ref("home#3") == {"screen": "home", "no": 3}
    assert M.parse_ref("x#y#1") == {"screen": "x#y", "no": 1}
    assert M.parse_ref("n1") == "n1" and M.parse_ref("home#0") == "home#0"
    assert M.find(notes, {"screen": "home", "no": 3}) == 1
    assert M.find(notes, {"screen": "home", "no": 4}) == 0, "번호 없는 메모 = 가장 큰 번호 다음"
    assert M.find(notes, "n3") == 2 and M.find(notes, "nope") is None and M.find(notes, {"screen": "home", "no": 9}) is None


def test_rows_pick_and_format():
    notes = [
        {"id": "n1", "screen": "home", "no": 1, "intent": "change", "sent": True, "note": "버튼 문구\n바꿔줘",
         "targets": [{"path": "body > main > button:nth-of-type(1)", "text": "  다음 "}, {"path": "p", "text": "y"}]},
        {"id": "n2", "screen": "home", "no": 2, "intent": "question", "sent": True, "note": "왜?", "path": "", "text": "",
         "replies": [{"kind": "답변", "text": "규칙", "by": "agent", "at": "t"}]},
        {"id": "n3", "screen": "list", "intent": "change", "sent": False, "note": "draft", "path": "h1", "text": "가" * 70},
    ]
    rs = M.rows(notes)
    assert [(r["no"], r["status"]) for r in rs] == [(1, "working"), (2, "done"), (1, "draft")]
    assert rs[0]["target"] == {"path": "body > main > button:nth-of-type(1)", "quote": "다음", "count": 2}
    assert [r["id"] for r in M.pick(rs)] == ["n1"]
    assert [r["id"] for r in M.pick(rs, "sent")] == ["n1", "n2"]
    assert len(M.pick(rs, "all")) == 3
    text = M.format_rows(rs).splitlines()
    assert text[0] == 'home #1 · working · change · button:nth-of-type(1) "다음" +1 · 버튼 문구 바꿔줘'
    assert text[1] == "home #2 · done · question · (화면 전체) · 왜?"
    assert text[2].startswith("    ↳ 답변 — 규칙")
    assert '"' + "가" * 59 + '…"' in text[3], "인용 60자 이하"
    assert M.format_rows([]) == "(메모 없음)"


def test_project_name():
    assert M.project_name("out", "laundry-v1") == "laundry-v1"
    assert M.project_name("gym-v2", "runs") == "gym-v2"


def test_model_is_pure():
    tree = ast.parse((HD / "hd_model.py").read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bad.append("import " + ",".join(a.name for a in node.names))
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "print", "input", "read_text", "write_text", "urlopen", "remove", "unlink", "listdir", "stat"):
                bad.append(name)
        elif isinstance(node, ast.Name) and node.id in ("os", "urllib", "pathlib", "io", "socket", "subprocess", "datetime", "time"):
            bad.append(node.id)
    assert bad == [], "hd_model.py 는 I/O 를 쓰지 않는다: %s" % bad
