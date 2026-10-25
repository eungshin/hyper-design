"""끌어 옮기기 한 번 = 쓰기 하나(49c 요청) — apply 편집 {edit:"move", op:"to", to:<형제 요소 사이 새 자리, 0부터>, path}.
k 칸 끌기를 up|down k 번으로 보내면 쓰기·되돌리기 줄이 k 개 — to 하나면 하나. 형제 = script·style·template·link·meta 를 뺀 요소(up|down 과 같은 셈).
사이 글·공백은 제자리, 요소 원문만 돈다. 쓴 뒤 경로 = 옮긴 요소의 새 자리(캔버스가 다시 고른다). I/O 없음(apply 는 임시 폴더·가짜 빌드)."""
import json, sys, types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helper  # noqa: E402

pytestmark = pytest.mark.unit

LIST = """<main>
  <ul>
    <li id="a">첫째</li>
    <li class="b">둘째</li>
    <script>var s = 1;</script>
    <li class="c">셋째</li>
    <li class="d">넷째</li>
  </ul>
</main>"""


def order(src):
    return sorted(("첫째", "둘째", "셋째", "넷째"), key=src.index)


def test_move_to_later_index_is_one_patch_and_keeps_gaps():
    out = helper.edit_html(LIST, [("#a", "move", 2)])
    assert order(out) == ["둘째", "셋째", "첫째", "넷째"]
    assert out == LIST.replace('<li id="a">첫째</li>\n    <li class="b">둘째</li>\n    <script>var s = 1;</script>\n    <li class="c">셋째</li>',
                               '<li class="b">둘째</li>\n    <li class="c">셋째</li>\n    <script>var s = 1;</script>\n    <li id="a">첫째</li>'), out


def test_move_to_earlier_index_and_ends():
    assert order(helper.edit_html(LIST, [("li.d", "move", 0)])) == ["넷째", "첫째", "둘째", "셋째"]
    assert order(helper.edit_html(LIST, [("#a", "move", 3)])) == ["둘째", "셋째", "넷째", "첫째"]
    assert order(helper.edit_html(LIST, [("li.c", "move", 1)])) == ["첫째", "셋째", "둘째", "넷째"]


def test_move_to_one_step_equals_up_down():
    assert helper.edit_html(LIST, [("li.b", "move", 2)]) == helper.edit_html(LIST, [("li.b", "move", "down")])
    assert helper.edit_html(LIST, [("li.c", "move", 1)]) == helper.edit_html(LIST, [("li.c", "move", "up")])


def test_move_to_refuses_same_place_out_of_range_and_bool():
    with pytest.raises(ValueError, match="이미 그 자리"):
        helper.edit_html(LIST, [("#a", "move", 0)])
    with pytest.raises(ValueError, match="범위"):
        helper.edit_html(LIST, [("#a", "move", 4)])
    with pytest.raises(ValueError, match="범위"):
        helper.edit_html(LIST, [("#a", "move", -1)])
    with pytest.raises(ValueError):
        helper.edit_html(LIST, [("#a", "move", True)])


def test_edit_one_answers_the_moved_element_new_path():
    new, path = helper.edit_one(LIST, "#a", "move", 2)
    assert path and helper.select(helper.Tree(new), path).attrs.get("id") == "a", path
    new, path = helper.edit_one(LIST, "li.d", "move", 0)
    assert path and "d" in helper.select(helper.Tree(new), path).attrs.get("class", ""), path


@pytest.fixture()
def out(tmp_path, monkeypatch):
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"screens": [{"id": "job", "file": "screens/job.html"}]}), encoding="utf-8")
    (o / "screens" / "job.html").write_text("<html><body>" + LIST + "</body></html>", encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return o


def test_apply_move_to_is_one_write_one_restore(out):
    f = out / "screens" / "job.html"
    before = f.read_text(encoding="utf-8")
    res = helper.apply_edits(out, [{"id": "m", "screen": "job", "edit": "move", "op": "to", "to": 3, "path": "#a"}], stamp="s1")
    assert res["applied"] == ["m"] and res["stamp"] == "s1" and res["paths"]["m"], res
    assert order(f.read_text(encoding="utf-8")) == ["둘째", "셋째", "넷째", "첫째"]
    assert helper.restore(out, "s1").get("restored") and f.read_text(encoding="utf-8") == before, "되돌리기 하나로 끌기 전"


def test_apply_move_to_refuses_bad_to_and_keeps_up_down(out):
    res = helper.apply_edits(out, [{"id": "x", "screen": "job", "edit": "move", "op": "to", "to": "2", "path": "#a"},
                                   {"id": "y", "screen": "job", "edit": "move", "op": "to", "path": "#a"},
                                   {"id": "z", "screen": "job", "edit": "move", "op": "to", "to": 9, "path": "#a"}], stamp="s2")
    assert not res["applied"] and {f["id"] for f in res["failed"]} == {"x", "y", "z"}, res
    res = helper.apply_edits(out, [{"id": "u", "screen": "job", "edit": "move", "op": "down", "path": "#a"}], stamp="s3")
    assert res["applied"] == ["u"], "up|down 그대로"
