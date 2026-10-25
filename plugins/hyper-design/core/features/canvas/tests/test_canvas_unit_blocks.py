"""블록 기본(task 49a) — 요소 복제·위/아래로 옮기기(도우미) · 요소 막대 규칙(blocks.js) · 글자 바로 쓰기(edits.js).

도우미(I/O 없음, edit_html·apply_edits·restore 직접): duplicate = 요소 원문 바로 뒤에 복사본(앞 공백 그대로 한 번, 복사본 안 id·data-region 은 뺌),
move up|down = 앞·뒤 형제 요소와 원문 조각을 맞바꿈(사이 글·공백은 제자리). 경로가 정확히 하나에 맞을 때만(task 41) · 화면 뿌리 거절.
Model(node): blocks.bar(막대 단추 켜짐·AI 요청) · keyAct(Alt+↑↓·Ctrl+D) · isApp · place(막대 자리) · edits.instantOf(글자 = 바로) · preview(복제·옮기기 미리보기).
"""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402


def edit(src, *ops):
    return helper.edit_html(src, list(ops))


LIST = """<main>
  <ul>
    <li id="a" data-region="r1">첫째</li>
    <li class="it">둘째</li>
    <li class="it">셋째</li>
  </ul>
</main>"""


# ---------------------------------------------------------------- duplicate
def test_duplicate_inserts_copy_after_with_the_same_indent():
    out = edit(LIST, ("ul > li:nth-of-type(2)", "duplicate", None))
    assert out == LIST.replace('<li class="it">둘째</li>', '<li class="it">둘째</li>\n    <li class="it">둘째</li>', 1), out


def test_duplicate_strips_id_and_data_region_in_the_copy_only():
    out = edit(LIST, ("#a", "duplicate", None))
    assert out.count('id="a"') == 1 and out.count('data-region="r1"') == 1, out
    assert '<li id="a" data-region="r1">첫째</li>\n    <li>첫째</li>' in out, out


def test_duplicate_nested_block_strips_every_id_inside_and_keeps_inner_whitespace():
    src = '<body>\n<main>\n  <section class="card">\n    <h2 id="t">제목</h2>\n    <p data-region="d">본문</p>\n  </section>\n  <footer>끝</footer>\n</main>\n</body>'
    out = edit(src, ("section.card", "duplicate", None))
    copy = '  <section class="card">\n    <h2>제목</h2>\n    <p>본문</p>\n  </section>'
    assert out == src.replace('  </section>\n', '  </section>\n' + copy + '\n', 1), out
    assert out.count('id="t"') == 1 and out.count('data-region="d"') == 1


def test_duplicate_inline_siblings_without_whitespace_and_void_elements():
    assert edit("<p><b>a</b><i>b</i></p>", ("p > b", "duplicate", None)) == "<p><b>a</b><b>a</b><i>b</i></p>"
    assert edit('<div><img id="x" src="a.png"><span>t</span></div>', ("#x", "duplicate", None)) == '<div><img id="x" src="a.png"><img src="a.png"><span>t</span></div>'


def test_duplicate_refuses_root_and_ambiguous_paths():
    with pytest.raises(ValueError, match="뿌리"):
        edit("<html><body><main><p>x</p></main></body></html>", ("body > main", "duplicate", None))
    with pytest.raises(ValueError, match="2개"):
        edit('<div><p class="x">1</p></div><div><p class="x">2</p></div>', ("div > p.x", "duplicate", None))   # 둘 다 맞음 → 모호(task 41)


# ---------------------------------------------------------------- move
def test_move_up_swaps_with_the_previous_sibling_and_keeps_whitespace():
    out = edit(LIST, ("ul > li:nth-of-type(3)", "move", "up"))
    assert out == LIST.replace('<li class="it">둘째</li>\n    <li class="it">셋째</li>', '<li class="it">셋째</li>\n    <li class="it">둘째</li>'), out


def test_move_down_swaps_with_the_next_sibling():
    out = edit(LIST, ("#a", "move", "down"))
    assert out == LIST.replace('<li id="a" data-region="r1">첫째</li>\n    <li class="it">둘째</li>', '<li class="it">둘째</li>\n    <li id="a" data-region="r1">첫째</li>'), out


def test_move_refuses_first_up_and_last_down():
    with pytest.raises(ValueError, match="맨 위"):
        edit(LIST, ("#a", "move", "up"))
    with pytest.raises(ValueError, match="맨 아래"):
        edit(LIST, ("ul > li:nth-of-type(3)", "move", "down"))


def test_move_multiline_nested_block_and_skips_script_siblings():
    src = ('<main>\n  <section class="a">\n    <h2>A</h2>\n  </section>\n  <script>var x = 1;</script>\n'
           '  <section class="b">\n    <h2>B</h2>\n  </section>\n</main>')
    out = edit(src, ("section.b", "move", "up"))
    assert out == ('<main>\n  <section class="b">\n    <h2>B</h2>\n  </section>\n  <script>var x = 1;</script>\n'
                   '  <section class="a">\n    <h2>A</h2>\n  </section>\n</main>'), out


def test_move_refuses_root_unknown_direction_and_ambiguous_paths():
    with pytest.raises(ValueError, match="뿌리"):
        edit("<html><body><main><p>x</p></main></body></html>", ("body > main", "move", "up"))
    with pytest.raises(ValueError):
        edit(LIST, ("#a", "move", "left"))
    with pytest.raises(ValueError, match="2개"):
        edit('<div><p class="x">1</p><i>s</i></div><div><p class="x">2</p><i>s</i></div>', ("div > p.x", "move", "down"))


def test_move_and_an_edit_inside_the_moved_element_overlap_is_refused():
    with pytest.raises(ValueError, match="겹치는"):
        edit(LIST, ("ul > li:nth-of-type(3)", "move", "up"), ("ul > li:nth-of-type(2)", "text", "x"))


# ---------------------------------------------------------------- apply_edits + restore (I/O 는 임시 폴더, 빌드는 가짜)
@pytest.fixture()
def out(tmp_path, monkeypatch):
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"screens": [{"id": "job", "file": "screens/job.html"},
                                                            {"id": "app", "file": "http://127.0.0.1:5173/hd-stage/app.html"}]}), encoding="utf-8")
    (o / "screens" / "job.html").write_text("<html><body>" + LIST + "</body></html>", encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return o


def _job(o):
    return (o / "screens" / "job.html").read_text(encoding="utf-8")


def test_apply_duplicate_and_move_then_restore_brings_the_file_back(out):
    before = _job(out)
    res = helper.apply_edits(out, [{"id": "d", "screen": "job", "edit": "duplicate", "path": "#a"}], stamp="s1")
    assert res["applied"] == ["d"] and res["changed"] == ["job"], res
    assert _job(out).count("첫째") == 2
    res2 = helper.apply_edits(out, [{"id": "m", "screen": "job", "edit": "move", "op": "down", "path": "ul > li:nth-of-type(3)"}], stamp="s2")
    assert res2["applied"] == ["m"], res2
    assert _job(out).index("셋째") < _job(out).index("둘째")
    assert helper.restore(out, "s2").get("restored"), "되돌리기 = 그 쓰기 전으로"
    assert helper.restore(out, "s1").get("restored")
    assert _job(out) == before


def test_apply_refuses_move_without_direction_and_app_cards(out):
    res = helper.apply_edits(out, [{"id": "m", "screen": "job", "edit": "move", "path": "#a"},
                                   {"id": "a", "screen": "app", "edit": "duplicate", "path": "div"}], stamp="s3")
    assert not res["applied"] and {f["id"] for f in res["failed"]} == {"m", "a"}, res
    assert "out 밖이거나 없는 파일" in [f for f in res["failed"] if f["id"] == "a"][0]["reason"]


# ---------------------------------------------------------------- blocks.js · edits.js (node)
JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'blocks.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const B = globalThis.HD.blocks, E = globalThis.HD.edits, out = {};
const on = (bar) => Object.fromEntries(bar.map(b => [b.act, b.on]));
const h = {path: 'p', text: '설명', textOk: true, prev: true, next: true, root: false};
out.acts = B.bar(h, {}).map(b => b.act);
out.labels = B.bar(h, {}).map(b => b.label);
out.all = on(B.bar(h, {}));
out.first = on(B.bar(Object.assign({}, h, {prev: false}), {}));
out.last = on(B.bar(Object.assign({}, h, {next: false}), {}));
out.block = B.bar(Object.assign({}, h, {textOk: false}), {}).find(b => b.act === 'text');
out.root = on(B.bar(Object.assign({}, h, {root: true}), {}));
out.app = B.bar(h, {app: true}).map(b => [b.act, b.on, !!b.ask]);
out.appTitle = B.bar(h, {app: true}).find(b => b.act === 'dup').title;
out.srcIsApp = B.bar(Object.assign({}, h, {src: {file: 'A.svelte', line: 3}}), {}).every(b => b.act === 'memo' || b.act === 'parent' || b.ask);
out.isApp = [B.isApp('http://127.0.0.1:5173/hd-stage/x.html'), B.isApp('https://localhost/x'), B.isApp('screens/a.html'), B.isApp(null)];
out.keys = [B.keyAct({key: 'ArrowUp', alt: true}), B.keyAct({key: 'ArrowDown', alt: true}), B.keyAct({key: 'd', ctrl: true}),
            B.keyAct({key: 'D', meta: true}), B.keyAct({key: 'ArrowUp'}), B.keyAct({key: 'ArrowUp', alt: true, shift: true}), B.keyAct({key: 'd', ctrl: true, shift: true}), B.keyAct({key: 'Delete'}), B.keyAct({key: 'Backspace'})];
out.ask = ['text', 'remove', 'dup', 'up', 'down'].map(a => B.askText(a));
out.placeAbove = B.place({x: 100, y: 300, w: 80, h: 20}, {w: 200, h: 36}, {w: 1000, h: 800}, null);
out.placeBelow = B.place({x: 100, y: 40, w: 80, h: 20}, {w: 200, h: 36}, {w: 1000, h: 800}, null);
out.placeAvoid = B.place({x: 100, y: 300, w: 80, h: 20}, {w: 200, h: 36}, {w: 1000, h: 800}, {x: 50, y: 250, w: 300, h: 40});
out.placeClamp = B.place({x: 950, y: 300, w: 80, h: 20}, {w: 200, h: 36}, {w: 1000, h: 800}, null);
const mk = (edit, op) => Object.assign(E.note('job', {path: 'li', text: 't', rect: null}, ''), {edit: edit, op: op || ''});
const tx = Object.assign(mk('text'), {value: 'x'});
out.instant = [E.instantOf(tx), E.instantOf(mk('duplicate')), E.instantOf(mk('move', 'up'))];
out.direct = [E.directOf(mk('duplicate')), E.directOf(mk('move', 'down'))];
out.preview = E.preview([mk('duplicate'), mk('move', 'down'), tx], 'job');
out.say = [E.say.duplicate(), E.say.move('up'), E.say.move('down')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blocks-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bar_has_six_actions_in_order(js):   # 49b 가 [상위]·[바꾸기]·[아래에 넣기]를 더함 — 49a 여섯 단추는 그 차례 그대로(test_canvas_unit_blocks_b)
    six = ["text", "remove", "dup", "up", "down", "memo"]
    assert [a for a in js["acts"] if a in six] == six, js["acts"]
    assert [l for a, l in zip(js["acts"], js["labels"]) if a in six] == ["글자", "지우기", "복제", "↑", "↓", "메모"]
    assert all(js["all"].values()), js["all"]


def test_bar_disables_what_does_not_apply(js):
    assert js["first"]["up"] is False and js["first"]["down"] is True
    assert js["last"]["down"] is False and js["last"]["up"] is True
    assert js["block"]["on"] is False and "글자만 바꿀 수 없어요" in js["block"]["title"], js["block"]
    assert {k: js["root"][k] for k in ("text", "remove", "dup", "up", "down", "memo")} == {"text": True, "remove": False, "dup": False, "up": False, "down": False, "memo": True}, js["root"]


def test_app_cards_turn_every_edit_into_an_ai_request(js):
    app = {a: (o, k) for a, o, k in js["app"]}   # 49b: [상위]는 고르기라 요청이 아님 · [바꾸기]·[아래에 넣기]도 요청
    assert all(app[a] == (True, True) for a in ("text", "remove", "dup", "up", "down")) and app["memo"] == (True, False), js["app"]
    assert js["appTitle"].startswith("AI에게 요청"), js["appTitle"]
    assert js["srcIsApp"], "소스 위치(src)가 있는 요소 = 앱 카드"
    assert js["isApp"] == [True, True, False, False]


def test_keys_alt_arrows_move_ctrl_d_duplicates_delete_removes(js):
    assert js["keys"] == ["up", "down", "dup", "dup", None, None, None, "remove", "remove"]


def test_ask_texts_are_requests(js):
    assert js["ask"][1].startswith("요소 지우기") and js["ask"][2].startswith("요소 복제") and "위로" in js["ask"][3] and "아래로" in js["ask"][4], js["ask"]
    assert js["ask"][0].startswith("글자"), js["ask"]


def test_place_bar_above_else_below_and_clamped(js):
    assert {k: js["placeAbove"][k] for k in ("x", "y", "below")} == {"x": 100, "y": 300 - 36 - 6, "below": False}, js["placeAbove"]
    assert {k: js["placeBelow"][k] for k in ("x", "y", "below")} == {"x": 100, "y": 40 + 20 + 6, "below": True}, js["placeBelow"]
    assert js["placeAvoid"]["below"] is True, "카드 선택 막대와 겹치면 아래로"
    assert js["placeClamp"]["x"] == 1000 - 200 - 8, js["placeClamp"]


def test_text_duplicate_move_are_instant_and_direct(js):
    assert js["instant"] == [True, True, True], "도우미가 있으면 글자·복제·옮기기도 바로 파일에"
    assert js["direct"] == [True, True]


def test_preview_items_for_duplicate_and_move(js):
    assert js["preview"] == [{"path": "li", "dup": True}, {"path": "li", "move": "down"}, {"path": "li", "text": "x"}]


def test_say_duplicate_and_move(js):
    assert js["say"][0].startswith("요소 복제") and "위로" in js["say"][1] and "아래로" in js["say"][2], js["say"]
