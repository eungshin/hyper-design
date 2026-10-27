"""스크립트가 그리는 글 고치기(html_edit, I/O 없음) — 단계 넘김(SPA 설명) 화면에서 '다음' 뒤 바뀐 글을 글자 도구로 고칠 때.

규칙:
- 캔버스는 고치기 전 화면에 보이던 글(old)을 함께 보낸다. 파일의 그 요소 글이 old 와 같으면(공백 무시) 예전처럼 요소 안을 바꾼다.
- 다르면 그 글은 화면 스크립트가 그린 것 — 요소를 바꾸면 다시 실을 때 스크립트가 덮어써 고친 것이 사라진다.
  그래서 <script> 안 문자열에서 old 를 찾아 정확히 한 곳이면 그 문자열 조각을 새 글로 바꾼다(따옴표는 escape). 요소는 그대로.
- 못 찾거나 여러 곳 · 새 글에 줄바꿈 = 거절(ValueError, 까닭 = SCRIPT_REASON 으로 시작) — 파일은 그대로.
- old 가 없으면(옛 캔버스) 예전 그대로.
"""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import html_edit  # noqa: E402

pytestmark = pytest.mark.unit

TOUR = ('<main><div id="pt-bubble"><strong id="pt-b-head"></strong><span id="pt-b-body"></span></div></main>\n'
        '<script>\nconst BEATS = [\n'
        "  { head: '잠깐 보는 중이에요', body: '다음 단어를 찾으면 첫 번째 사전으로 돌아와요.' },\n"
        "  { head: '1번 탭이에요', body: '2를 누르면 Go, 3을 누르면 그다음 사전이에요.' },\n"
        '];\n</script>')
OLD = '2를 누르면 Go, 3을 누르면 그다음 사전이에요.'


def edit(src, path, value, old=None):
    v = value if old is None else {"value": value, "old": old}
    return html_edit.edit_html(src, [(path, "text", v)])


def test_script_drawn_text_is_changed_in_the_script_not_the_element():
    out = edit(TOUR, "#pt-b-body", "2를 누르면 두 번째 사전이에요.", OLD)
    assert "body: '2를 누르면 두 번째 사전이에요.'" in out
    assert OLD not in out
    assert '<span id="pt-b-body"></span>' in out          # 요소는 그대로 — 다시 실어도 스크립트가 새 글을 그린다


def test_quote_in_new_text_is_escaped_for_the_literal():
    out = edit(TOUR, "#pt-b-body", "it's 2", OLD)
    assert "body: 'it\\'s 2'" in out


def test_text_that_matches_the_file_keeps_the_old_path():
    src = '<main><p>안녕  하세요</p></main>'
    assert edit(src, "p", "반가워요", "안녕 하세요") == '<main><p>반가워요</p></main>'


def test_no_old_keeps_the_old_behaviour():
    assert '<span id="pt-b-body">새 글</span>' in edit(TOUR, "#pt-b-body", "새 글")


@pytest.mark.parametrize("old", ["어디에도 없는 글", "누르면"])   # 없음 · 여러 곳(같은 문자열 안에 두 번)
def test_not_found_once_in_script_is_refused(old):
    with pytest.raises(ValueError, match=html_edit.SCRIPT_REASON):
        edit(TOUR, "#pt-b-body", "새 글", old)


def test_line_break_in_script_drawn_text_is_refused():
    with pytest.raises(ValueError, match=html_edit.SCRIPT_REASON):
        edit(TOUR, "#pt-b-body", "2를 누르면\nGo", OLD)


# ---------------------------------------------------------------- apply_edits: 캔버스가 보낸 old 가 화면 파일까지
@pytest.fixture()
def out(tmp_path, monkeypatch):
    import json, types
    import helper
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"screens": [{"id": "tour", "file": "screens/tour.html", "title": "설명"}]}), encoding="utf-8")
    (o / "screens" / "tour.html").write_text(TOUR, encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return o


def test_apply_with_old_writes_the_script_and_refusal_keeps_the_file(out):
    import helper
    f = out / "screens" / "tour.html"
    res = helper.apply_edits(out, [{"id": "a", "screen": "tour", "edit": "text", "path": "#pt-b-body", "value": "새 설명", "old": OLD}], stamp="s1")
    assert res["applied"] == ["a"] and not res["failed"], res
    assert "body: '새 설명'" in f.read_text(encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    res = helper.apply_edits(out, [{"id": "b", "screen": "tour", "edit": "text", "path": "#pt-b-body", "value": "x", "old": "없는 글"}], stamp="s2")
    assert not res["applied"] and res["failed"][0]["reason"].startswith(html_edit.SCRIPT_REASON), res
    assert f.read_text(encoding="utf-8") == before
