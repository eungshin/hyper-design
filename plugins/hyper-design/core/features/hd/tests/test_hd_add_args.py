"""hd add 여러 장(W10 F2) — 위치 인자 풀이(옛 `hd add a.html <캔버스>` 모양 포함) · 여러 장 놓기 계획(차례 배치 · 상태 몸통 하나) ·
SETTLE 이 필요한 때 · argparse 모양. 순수(파일·도우미 없음)."""
import sys
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
sys.path.append(str(HD.parent / "canvas"))
import hd  # noqa: E402
import hd_place as L  # noqa: E402

G = "샘플"
DATA = {"groups": [G], "screens": [{"id": "a", "file": "a.html", "title": "A", "group": G},
                                   {"id": "b", "file": "b.html", "title": "B", "group": G}]}
STATE = {"card-pos": {"a": {"dx": 10, "dy": -5, "g": G}}, "card-size": {"a": {"w": 1440, "h": 1024, "preset": "Desktop"}}}
FILES = {"x.html", "y.html", "z.html", "C:/w/notes.txt"}


def is_file(p):
    return p in FILES


def items(*sids):
    return [{"sid": s, "html_title": s.upper()} for s in sids]


# ---------------------------------------------------------------- 위치 인자
@pytest.mark.parametrize("args,to,want", [
    (["x.html"], None, (["x.html"], None, False)),
    (["x.html", "y.html", "z.html"], None, (["x.html", "y.html", "z.html"], None, False)),
    (["x.html", "proj-a"], None, (["x.html"], "proj-a", True)),                       # 옛 모양: 둘째 = 캔버스 이름
    (["x.html", "C:/w/proj/out"], None, (["x.html"], "C:/w/proj/out", True)),         # 옛 모양: out 경로(폴더)
    (["x.html", "y.html", "proj-a"], None, (["x.html", "y.html"], "proj-a", True)),
    (["x.html", "missing.html"], None, (["x.html", "missing.html"], None, False)),   # .html 이면 파일(없으면 뒤에서 '없는 파일')
    (["x.html", "C:/w/notes.txt"], None, (["x.html", "C:/w/notes.txt"], None, False)),   # 있는 파일이면 파일
    (["x.html", "proj-a"], "proj-b", (["x.html", "proj-a"], "proj-b", False)),         # --to 가 있으면 위치 인자는 모두 파일
])
def test_split_add_args(args, to, want):
    assert L.split_add_args(args, to, is_file) == want


def test_batch_refuses_per_file_options_and_duplicate_ids():
    L.check_batch(["a"], sid="x", title="t")                          # 한 장이면 --id · --title 그대로
    for sid, title in (("x", None), (None, "t")):
        with pytest.raises(L.PlaceError, match="한 장일 때만"):
            L.check_batch(["a", "b"], sid=sid, title=title)
    with pytest.raises(L.PlaceError, match="같은 화면 id"):
        L.plan_many(DATA, STATE, items("c", "c"))


# ---------------------------------------------------------------- 여러 장 계획
def test_plan_many_at_places_first_then_rest_beside_it_in_order():
    r = L.plan_many(DATA, STATE, items("c", "d", "e"), at=(0, 200), size={"w": 390, "h": 844})
    assert [s["id"] for s in r["data"]["screens"]] == ["a", "b", "c", "d", "e"], "차례로 그 줄 끝에"
    assert [pl["pos"] for pl in r["plans"]] == [{"dx": 0, "dy": 200, "g": G}] * 3, "둘째부터 = 앞 화면 옆(--after 규칙: 같은 옮긴 거리)"
    assert [pl["size"] for pl in r["plans"]] == [{"w": 390, "h": 844}] * 3
    assert r["patch"] == {"card-pos": dict(STATE["card-pos"], c={"dx": 0, "dy": 200, "g": G}, d={"dx": 0, "dy": 200, "g": G},
                                           e={"dx": 0, "dy": 200, "g": G}),
                          "card-size": dict(STATE["card-size"], c={"w": 390, "h": 844}, d={"w": 390, "h": 844}, e={"w": 390, "h": 844})}, \
        "상태 몸통 하나(이름마다 통째 값) — 다른 카드 값은 그대로"


def test_plan_many_after_chains_and_default_appends():
    r = L.plan_many(DATA, STATE, items("c", "d"), after="a")
    assert [s["id"] for s in r["data"]["screens"]] == ["a", "c", "d", "b"], "--after a 바로 뒤, 둘째는 첫째 바로 뒤"
    assert [pl["pos"]["dx"] for pl in r["plans"]] == [10, 10]
    r = L.plan_many(DATA, {}, items("c", "d"))
    assert [s["id"] for s in r["data"]["screens"]] == ["a", "b", "c", "d"] and r["patch"] == {}, "자리 없이 = 줄 끝, 상태 쓸 것 없음"


def test_plan_many_single_is_plan():
    one = L.plan(DATA, STATE, "c", at=(1, 2), html_title="C")
    r = L.plan_many(DATA, STATE, [{"sid": "c", "html_title": "C"}], at=(1, 2))
    assert r["plans"][0] == one and r["data"] == one["data"]


def test_plan_many_replace_keeps_existing_screens_in_place():
    r = L.plan_many(DATA, STATE, items("a", "b"), at=(5, 5), replace=True)
    assert [s["id"] for s in r["data"]["screens"]] == ["a", "b"], "바꾸는 화면은 제자리(차례 배치는 새 화면만)"
    assert r["plans"][1]["pos"] == "keep"


def test_settle_needed_only_for_new_screen_with_position():
    new_at = L.plan_many(DATA, STATE, items("c"), at=(1, 1))["plans"]
    new_plain = L.plan_many(DATA, {}, items("c"))["plans"]
    repl_at = L.plan_many(DATA, STATE, items("a"), at=(1, 1), replace=True)["plans"]
    size_only = L.plan_many(DATA, {}, items("c"), size={"w": 390, "h": 844})["plans"]
    assert L.settle_needed(new_at) is True, "캔버스가 새 카드를 알기 전 card-pos 는 cleanPos 가 버리고 되쓴다"
    assert (L.settle_needed(new_plain), L.settle_needed(repl_at), L.settle_needed(size_only)) == (False, False, False)


# ---------------------------------------------------------------- argparse
def test_parser_takes_many_files_and_to():
    a = hd.parser().parse_args(["add", "x.html", "y.html", "z.html", "--to", "proj-a", "--at=0,200"])
    assert (a.files, a.to, a.at) == (["x.html", "y.html", "z.html"], "proj-a", "0,200")
    a = hd.parser().parse_args(["add", "x.html", "proj-a"])
    assert (a.files, a.to) == (["x.html", "proj-a"], None), "옛 모양은 풀이(split_add_args)가 가른다"
