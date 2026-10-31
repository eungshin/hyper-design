"""hd_place(Model) — 화면 줄 읽기 · 크기/자리 글 · 놓기 계획 · 상태 몸통 · 순수성. 파일·도우미 없음."""
import ast, sys
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
sys.path.append(str(HD.parent / "canvas"))
import hd_place as L  # noqa: E402

PRESETS = L.parse_presets((HD.parent / "canvas" / "modules" / "artboard.js").read_text(encoding="utf-8"))
G = "샘플"
DATA = {"title": "t", "groups": [G], "screens": [
    {"id": "a", "file": "a.html", "title": "A", "group": G},
    {"id": "a--hover", "file": "a-hover.html", "title": "A hover", "group": G},
    {"id": "b", "file": "b.html", "title": "B", "group": G}]}
STATE = {"card-pos": {"a": {"dx": 10, "dy": -5, "g": G}, "b": {"dx": 1, "dy": 2, "g": "다른 줄"}, "x": [1, 2]},
         "card-size": {"a": {"w": 1440, "h": 1024, "preset": "Desktop"}, "b": {"w": 1440, "h": 1024, "preset": "Desktop"}, "bad": {"w": "x"}}}


def ids(d):
    return [s["id"] for s in d["screens"]]


def test_model_is_pure():
    tree = ast.parse((HD / "hd_place.py").read_text(encoding="utf-8"))
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
           {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"re"}, mods


def test_id_rule_matches_canvas_screen_copy():
    import screen_copy
    assert L.ID_OK.pattern == screen_copy.ID_OK.pattern and L.ID_MAX == screen_copy.ID_MAX


def test_rows_read_pos_and_size_and_drop_broken_or_other_row_values():
    rs = L.rows(DATA, STATE)
    assert [(r["id"], r["pos"], r["size"]) for r in rs] == [
        ("a", {"dx": 10, "dy": -5}, {"w": 1440, "h": 1024, "preset": "Desktop"}),
        ("a--hover", None, None),
        ("b", None, {"w": 1440, "h": 1024, "preset": "Desktop"})], "b 의 자리는 다른 줄 것이라 캔버스도 버린다"
    text = L.format_rows(rs, DATA["groups"])
    assert text.splitlines()[0] == "[샘플]" and "  a · A · a.html · 자리 +10,-5 · 1440×1024(Desktop)" in text
    assert L.rows({"screens": "x"}, {}) == [] and L.format_rows([]) == "(화면 없음)"


def test_size_and_at_text():
    assert PRESETS["desktop"] == ("Desktop", 1440, 1024)
    assert L.parse_size("Desktop", PRESETS) == {"w": 1440, "h": 1024, "preset": "Desktop"}
    assert L.parse_size("iphone 16", PRESETS) == {"w": 393, "h": 852, "preset": "iPhone 16"}
    assert L.parse_size("1440x1024", PRESETS)["preset"] == "Desktop" and L.parse_size("800×600", PRESETS) == {"w": 800, "h": 600}
    assert L.parse_size("320x50", PRESETS) == {"w": 320, "h": 50} and L.parse_size("860x40000", PRESETS) == {"w": 860, "h": 40000}
    for bad in ("15x500", "60001x200", "Nope", ""):
        with pytest.raises(L.PlaceError):
            L.parse_size(bad, PRESETS)
    assert L.parse_at("200,0") == (200, 0) and L.parse_at(" -40 , 12.6 ") == (-40, 13)
    with pytest.raises(L.PlaceError):
        L.parse_at("200")


def test_plan_new_screen_default_goes_to_end_of_last_row_with_row_size():
    p = L.plan(DATA, STATE, "c", html_title=L.html_title("<title>  새\n  화면 </title>"))
    assert ids(p["data"]) == ["a", "a--hover", "b", "c"] and p["entry"] == {"id": "c", "file": "c.html", "title": "새 화면", "group": G}
    assert p["pos"] == "keep" and p["size"] == {"w": 1440, "h": 1024, "preset": "Desktop"} and p["size_from"] == "group"
    assert DATA["screens"][-1]["id"] == "b", "입력은 고치지 않는다"


def test_plan_after_skips_variants_and_copies_pos_and_size():
    p = L.plan(DATA, STATE, "c", title="C", after="a")
    assert ids(p["data"]) == ["a", "a--hover", "c", "b"]
    assert p["pos"] == {"dx": 10, "dy": -5, "g": G} and p["size"]["w"] == 1440 and p["pos_from"] == "after"


def test_plan_new_group_and_at():
    p = L.plan(DATA, STATE, "c", group="새 줄", at=(200, -40), size={"w": 393, "h": 852})
    assert p["data"]["groups"] == [G, "새 줄"] and p["group_added"] and ids(p["data"])[-1] == "c"
    assert p["pos"] == {"dx": 200, "dy": -40, "g": "새 줄"} and p["size"] == {"w": 393, "h": 852}
    assert L.plan({"screens": []}, {}, "c")["data"] == {"screens": [{"id": "c", "file": "c.html", "title": "c"}]}, "줄 없음 = groups 를 만들지 않음"


def test_plan_refuses():
    for kw, why in ((dict(sid="a"), "이미 있는 화면 id"), (dict(sid="c", after="zz"), "없는 화면이에요(--after): zz"),
                    (dict(sid="c", after="a", group="다른"), "--after a 는 '샘플' 줄"), (dict(sid="bad id"), "--id"),
                    (dict(sid="c", files={"c.html"}), "이미 그 파일"), (dict(sid="c", title=" "), "--title")):
        with pytest.raises(L.PlaceError) as e:
            L.plan(DATA, STATE, **kw)
        assert why in str(e.value), (kw, str(e.value))


def test_plan_replace_keeps_place_title_and_file():
    p = L.plan(DATA, STATE, "a", replace=True, purpose="새 목적")
    assert ids(p["data"]) == ids(DATA) and p["replaced"] and p["file"] == "a.html"
    assert p["entry"]["title"] == "A" and p["entry"]["purpose"] == "새 목적" and p["pos"] == "keep" and p["size"] == "keep"


def test_state_patch_only_changed_names_and_keeps_other_cards():
    st = {"card-pos": {"a": {"dx": 1, "dy": 1, "g": G}}}
    assert L.state_patch(st, "c", {"dx": 5, "dy": 0, "g": G}, "keep") == {"card-pos": {"a": {"dx": 1, "dy": 1, "g": G}, "c": {"dx": 5, "dy": 0, "g": G}}}
    assert L.state_patch(st, "a", None, {"w": 800, "h": 600}) == {"card-pos": {}, "card-size": {"a": {"w": 800, "h": 600}}}
    assert L.state_patch(st, "a", {"dx": 1, "dy": 1, "g": G}, "keep") == {} and L.state_patch({}, "z", None, None) == {}


def test_asset_rel_keeps_relative_path_inside_screen_folder():
    assert L.asset_rel(["C:\\", "m"], ["C:\\", "m", "img", "a.png"]) == "img/a.png"
    assert L.asset_rel(["C:\\", "m"], ["C:\\", "other", "a.png"]) == "a.png"
    assert L.default_id("my mock (v2)") == "my-mock-(v2)" and L.html_title("<title>\n X </title>") == "X" and L.html_title("") is None
