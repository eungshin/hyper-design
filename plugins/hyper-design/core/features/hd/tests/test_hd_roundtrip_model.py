"""hd 왕복 Model — pending(기다릴 메모) · agent_error(attach 검사) · choose(stop/attach/wait 대상 고르기). 순수, 브라우저 없음."""
import sys
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
import hd_model as M  # noqa: E402


def test_pending_is_sent_without_reply():
    notes = [{"id": "a", "screen": "s", "sent": True, "intent": "change", "note": "x"},                       # working
             {"id": "b", "screen": "s", "sent": False, "intent": "change", "note": "y"},                      # draft
             {"id": "c", "screen": "s", "sent": True, "intent": "change", "note": "z",
              "replies": [{"kind": "질문", "question": "q", "choices": ["1", "2"]}]},                         # decide
             {"id": "d", "screen": "s", "sent": True, "intent": "change", "note": "w",
              "replies": [{"kind": "반영됨", "what": "w", "screens": ["s"], "captured": True}]}]              # done
    rs = M.pending({"notes": notes, "note-seq": {"s": 4}})
    assert [(r["id"], r["no"], r["status"]) for r in rs] == [("a", 5, "working")], "번호는 note-seq 다음부터(notes 와 같은 규칙)"
    assert M.pending({}) == [] and M.pending({"notes": "broken"}) == [] and M.pending(None) == []


def test_agent_error():
    assert M.agent_error(None) is None and M.agent_error("ag-1_x") is None and M.agent_error("a" * 128) is None
    assert "128" in M.agent_error("a" * 129)
    for bad in ("", "a b", "a\tb", "a\n", 5, ["x"]):
        assert M.agent_error(bad), bad


A = {"project": "proj-a", "out": "C:/w/proj-a/out"}
B = {"project": "proj-b", "out": "C:/w/proj-b/out"}
DEAD = {"project": "proj-c", "out": "C:/w/proj-c/out"}


def test_choose_default_needs_exactly_one_running():
    assert M.choose([A]) == (A, None)
    m, err = M.choose([])
    assert m is None and "떠 있는 캔버스가 없어요" in err
    m, err = M.choose([A, B])
    assert m is None and "여럿" in err and "proj-a" in err and "proj-b" in err


def test_choose_by_name_or_out_key_and_stale_only_when_none_alive():
    assert M.choose([A, B], "proj-b") == (B, None)
    assert M.choose([A, B], "x", keys={"c:/w/proj-a/out"}, key=str.casefold) == (A, None), "경로(정규화한 key)로도"
    m, err = M.choose([A], "proj-c")
    assert m is None and "'proj-c' 캔버스가 떠 있지 않아요" in err and "proj-a" in err
    assert M.choose([A], "proj-c", stale=[DEAD]) == (DEAD, None), "살아 있는 것이 없으면 응답 없는 표지에서(hd stop)"
    a2 = dict(A, pid=2)
    assert M.choose([A], "proj-a", stale=[a2]) == (A, None), "살아 있는 것이 먼저"
