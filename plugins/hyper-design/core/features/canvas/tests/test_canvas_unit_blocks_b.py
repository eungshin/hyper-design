"""블록 조립(task 49b) — 속성 칸(attr)·부품 넣기/바꾸기(insert·replace)·쓴 뒤 고른 요소의 새 경로(도우미) · 견본 뼈대 뽑기(specimen_parts) ·
요소 막대 규칙(blocks.js: [상위]·[ 키·상위 고르기·막대 자리·속성 칸·부품 요청 글) · edits.js(attr·insert·replace 바로 쓰기·미리보기·글귀).

도우미(I/O 없음, edit_html·edit_one·apply_edits·restore 직접): 실제 화면(fixtures/blocks-job.html — dayfine job.html 사본)에서.
attr = 허용 목록(img src·alt · a href · input·textarea placeholder)만, on*·style 은 절대 · javascript:·data:(링크) 주소 거절.
insert = 요소 바로 뒤에 견본 뼈대(앞 공백 그대로) · replace = 요소 자리에 뼈대 · 화면 뿌리 거절 · 경로는 정확히 하나에 맞을 때만(task 41).
뼈대는 도우미가 out/components.html 에서 key 로 뽑는다(캔버스가 보낸 마크업을 쓰지 않음) — 견본 글은 중립 글로.
"""
import json, re, shutil, subprocess, sys, tempfile, types
from html.parser import HTMLParser
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")
JOB = (HERE / "fixtures" / "blocks-job.html").read_text(encoding="utf-8")
SPECIMENS = (SCRIPTS.parents[1] / "foundation" / "specimens.html").read_text(encoding="utf-8")

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402
import specimen_parts as SP  # noqa: E402


def edit(src, *ops):
    return helper.edit_html(src, list(ops))


IMG = "div.art-card > img"
BACK = "a.wizard-back"
LEAD = "p.lead"
TILE2 = "div.tile-grid > button:nth-of-type(2)"


# ---------------------------------------------------------------- attr (허용 목록)
def test_attr_sets_img_src_and_alt_and_link_href_on_the_real_screen():
    out = edit(JOB, (IMG, "attr", {"name": "alt", "value": "현미경 그림"}))
    assert '<img src="../assets/fluent/microscope.svg" alt="현미경 그림">' in out, out
    out = edit(JOB, (IMG, "attr", {"name": "src", "value": "../assets/fluent/books.svg"}))
    assert '<img src="../assets/fluent/books.svg" alt="">' in out
    out = edit(JOB, (BACK, "attr", {"name": "href", "value": "start.html"}))
    assert '<a class="wizard-back" href="start.html">' in out
    assert out.replace('href="start.html"', 'href="login--done.html"', 1) == JOB, "그 속성 하나만 바뀐다"


def test_attr_sets_input_placeholder_and_escapes_quotes():
    src = '<main><div class="field"><input class="input" placeholder="이름"></div></main>'
    out = edit(src, ("input.input", "attr", {"name": "placeholder", "value": '예: "지은"'}))
    assert out == '<main><div class="field"><input class="input" placeholder="예: &quot;지은&quot;"></div></main>', out
    out = edit('<main><textarea class="t"></textarea></main>', ("textarea.t", "attr", {"name": "placeholder", "value": "메모"}))
    assert 'placeholder="메모"' in out


@pytest.mark.parametrize("sel,name", [(IMG, "onclick"), (IMG, "onerror"), (BACK, "style"), (IMG, "href"), (BACK, "src"),
                                      (LEAD, "title"), (TILE2, "aria-checked"), (BACK, "ONCLICK")])
def test_attr_refuses_names_outside_the_allow_list(sel, name):
    with pytest.raises(ValueError, match="바꿀 수 없는 속성"):
        edit(JOB, (sel, "attr", {"name": name, "value": "x"}))


@pytest.mark.parametrize("sel,name,value", [(BACK, "href", "javascript:alert(1)"), (BACK, "href", " JavaScript:alert(1)"),
                                            (BACK, "href", "data:text/html,x"), (IMG, "src", "javascript:x"), (BACK, "href", "vbscript:x")])
def test_attr_refuses_script_addresses(sel, name, value):
    with pytest.raises(ValueError, match="주소"):
        edit(JOB, (sel, "attr", {"name": name, "value": value}))


def test_attr_allows_data_image_src_and_refuses_line_breaks_and_ambiguous_paths():
    assert 'src="data:image/svg+xml,x"' in edit(JOB, (IMG, "attr", {"name": "src", "value": "data:image/svg+xml,x"}))
    with pytest.raises(ValueError, match="줄바꿈"):
        edit(JOB, (IMG, "attr", {"name": "alt", "value": "a\nb"}))
    with pytest.raises(ValueError, match="개"):
        edit(JOB, ("button.tile > img", "attr", {"name": "alt", "value": "x"}))   # 타일 9개 모두 맞음 → 모호(task 41)


# ---------------------------------------------------------------- insert · replace (뼈대 마크업은 도우미가 key 로 뽑아 넘긴다)
SK = '<button class="btn primary">텍스트</button>'


def test_insert_puts_markup_right_after_the_element_with_its_indent():
    out = edit(JOB, (LEAD, "insert", SK))
    lead = '<p class="lead">하는 일에 맞는 사전을 다음 단계에서 골라 드릴게요.</p>'
    assert out == JOB.replace(lead, lead + "\n        " + SK, 1), out


def test_replace_puts_markup_in_the_element_place():
    tile = re.search(r'<button class="tile" role="radio" aria-checked="true">.*?</button>', JOB).group(0)
    out = edit(JOB, (TILE2, "replace", SK))
    assert out == JOB.replace(tile, SK, 1), out


def test_insert_and_replace_refuse_root_ambiguous_and_unclosed():
    for op in ("insert", "replace"):
        with pytest.raises(ValueError, match="뿌리"):
            edit("<html><body><main><p>x</p></main></body></html>", ("body > main", op, SK))
        with pytest.raises(ValueError, match="개"):
            edit(JOB, ("button.tile", op, SK))
        with pytest.raises(ValueError, match="빈 부품"):
            edit(JOB, (LEAD, op, "  "))


# ---------------------------------------------------------------- 쓴 뒤 그 요소의 새 경로(고른 요소 따라가기)
def _sel_text(src, path):
    t = helper.Tree(src)
    el = helper.select(t, path)
    return src[el.start:helper._end(el, path, "")]


def test_edit_one_returns_the_path_of_the_element_after_the_write():
    new, p = helper.edit_one(JOB, TILE2, "move", "up")
    assert "대학원생·연구원" in _sel_text(new, p) and _sel_text(new, p).startswith('<button class="tile" role="radio" aria-checked="true">'), p
    new, p = helper.edit_one(JOB, TILE2, "move", "down")
    assert "대학원생·연구원" in _sel_text(new, p), p
    new, p = helper.edit_one(JOB, TILE2, "duplicate", None)
    assert _sel_text(new, p) == _sel_text(JOB, TILE2), "복제 = 원본에 그대로"
    new, p = helper.edit_one(JOB, LEAD, "text", "새 설명")
    assert _sel_text(new, p) == '<p class="lead">새 설명</p>'
    new, p = helper.edit_one(JOB, LEAD, "insert", SK)
    assert _sel_text(new, p) == SK, "넣기 = 새 부품"
    new, p = helper.edit_one(JOB, TILE2, "replace", SK)
    assert _sel_text(new, p) == SK, "바꾸기 = 새 부품"
    new, p = helper.edit_one(JOB, IMG, "attr", {"name": "alt", "value": "그림"})
    assert _sel_text(new, p) == '<img src="../assets/fluent/microscope.svg" alt="그림">'


# ---------------------------------------------------------------- 견본 뼈대 뽑기 (specimen_parts — 순수)
class _Texts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.texts, self.attrs, self.tags = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag); self.attrs += attrs

    def handle_data(self, d):
        if d.strip():
            self.texts.append(d.strip())


def _scan(s):
    p = _Texts(); p.feed(s); p.close(); return p


def test_sections_list_every_spec_with_key_and_title():
    secs = SP.sections(SPECIMENS)
    keys = [s["key"] for s in secs]
    assert keys[:3] == ["btn", "cta", "chip"] and "wizard" in keys and len(keys) == len(set(keys)) == SPECIMENS.count('<section class="spec"'), keys
    assert secs[0]["title"] == "버튼"


def test_skeleton_takes_the_first_component_of_the_first_stage_with_neutral_text():
    assert SP.markup(SPECIMENS, "btn") == '<button class="btn primary">텍스트</button>'
    f = SP.markup(SPECIMENS, "field")
    assert f == '<div class="field"><label class="label">텍스트</label><input class="input"></div>', f
    s = SP.markup(SPECIMENS, "search")
    assert 'placeholder="입력"' in s and "이름으로 찾기" not in s and "<svg" in s, s


def test_no_specimen_demo_text_survives_in_any_skeleton():
    demo = set(_scan(SPECIMENS).texts)
    for p in SP.parts(SPECIMENS):
        if not p["ok"]:
            continue
        sk = _scan(SP.markup(SPECIMENS, p["key"]))
        assert set(sk.texts) <= {SP.PLACEHOLDER}, (p["key"], sk.texts)
        bad = [(k, v) for k, v in sk.attrs if k in ("id", "for", "value", "title") or k.startswith("on") or
               (k in ("alt", "placeholder", "aria-label") and v not in ("", SP.HINT, SP.LABEL))]
        assert not bad, (p["key"], bad)
        assert not (set(sk.texts) & demo - {SP.PLACEHOLDER}), p["key"]


def test_parts_flag_unclean_specimens_and_markup_refuses_them():
    html = ('<section class="spec" data-key="ok" data-title="좋음"><div class="spec-cell"><div class="spec-stage"><span class="badge">확정</span></div></div></section>'
            '<section class="spec" data-key="js" data-title="스크립트"><div class="spec-cell"><div class="spec-stage"><div onclick="x()">a</div></div></div></section>'
            '<section class="spec" data-key="empty" data-title="빈"><div class="spec-cell"><div class="spec-stage">글만</div></div></section>'
            '<section class="spec" data-key="scr" data-title="속 스크립트"><div class="spec-cell"><div class="spec-stage"><div><script>x</script></div></div></div></section>')
    assert SP.parts(html) == [{"key": "ok", "title": "좋음", "ok": True}, {"key": "js", "title": "스크립트", "ok": False},
                              {"key": "empty", "title": "빈", "ok": False}, {"key": "scr", "title": "속 스크립트", "ok": False}]
    assert SP.markup(html, "ok") == '<span class="badge">텍스트</span>'
    for k in ("js", "empty", "scr", "nope"):
        with pytest.raises(ValueError):
            SP.markup(html, k)


def test_every_real_specimen_is_clean():
    bad = [p["key"] for p in SP.parts(SPECIMENS) if not p["ok"]]
    assert not bad, bad


# ---------------------------------------------------------------- apply_edits + restore (I/O 는 임시 폴더, 빌드는 가짜)
@pytest.fixture()
def out(tmp_path, monkeypatch):
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"screens": [{"id": "job", "file": "screens/job.html"}]}), encoding="utf-8")
    (o / "screens" / "job.html").write_text(JOB, encoding="utf-8", newline="")
    (o / "components.html").write_text(SPECIMENS, encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return o


def _job(o):
    return (o / "screens" / "job.html").read_text(encoding="utf-8")


def test_apply_attr_insert_replace_then_restore_brings_the_file_back(out):
    res = helper.apply_edits(out, [{"id": "a", "screen": "job", "edit": "attr", "op": "alt", "path": IMG, "value": "그림"}], stamp="s1")
    assert res["applied"] == ["a"] and 'alt="그림"' in _job(out), res
    assert "그림" in _sel_text(_job(out), res["paths"]["a"])
    res = helper.apply_edits(out, [{"id": "i", "screen": "job", "edit": "insert", "path": LEAD, "value": "btn"}], stamp="s2")
    assert res["applied"] == ["i"] and _sel_text(_job(out), res["paths"]["i"]) == SK, res
    res = helper.apply_edits(out, [{"id": "r", "screen": "job", "edit": "replace", "path": TILE2, "value": "chip"}], stamp="s3")
    assert res["applied"] == ["r"] and "대학원생·연구원" not in _job(out).split('class="tile-grid"')[1].split("</div>")[0], res
    assert _sel_text(_job(out), res["paths"]["r"]) == '<div class="chips"><button class="chip">텍스트</button></div>', res
    for s in ("s3", "s2", "s1"):
        assert helper.restore(out, s).get("restored"), s
    assert _job(out) == JOB


def test_apply_refuses_unknown_part_bad_attr_and_never_takes_markup_from_the_canvas(out):
    res = helper.apply_edits(out, [{"id": "u", "screen": "job", "edit": "insert", "path": LEAD, "value": "nope"},
                                   {"id": "m", "screen": "job", "edit": "insert", "path": LEAD, "value": "<script>alert(1)</script>"},
                                   {"id": "o", "screen": "job", "edit": "attr", "op": "onclick", "path": IMG, "value": "x"},
                                   {"id": "s", "screen": "job", "edit": "attr", "op": "style", "path": IMG, "value": "color:red"}], stamp="s4")
    assert not res["applied"] and {f["id"] for f in res["failed"]} == {"u", "m", "o", "s"}, res
    assert _job(out) == JOB
    assert "부품" in [f for f in res["failed"] if f["id"] == "u"][0]["reason"]


def test_apply_returns_the_moved_element_path(out):
    res = helper.apply_edits(out, [{"id": "m", "screen": "job", "edit": "move", "op": "up", "path": TILE2}], stamp="s5")
    assert res["applied"] == ["m"] and "대학원생·연구원" in _sel_text(_job(out), res["paths"]["m"]), res


def test_parts_of_out_reads_components_html(out):
    ps = helper.parts_of(out)
    assert ps["parts"][0] == {"key": "btn", "title": "버튼", "ok": True}, ps
    (out / "components.html").unlink()
    assert helper.parts_of(out) == {"parts": [], "error": "부품 견본(components.html)이 없어요"}


# ---------------------------------------------------------------- blocks.js · edits.js (node)
JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'blocks.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const B = globalThis.HD.blocks, E = globalThis.HD.edits, out = {};
const on = (bar) => Object.fromEntries(bar.map(b => [b.act, b.on]));
const h = {path: 'p', text: '설명', textOk: true, prev: true, next: true, root: false, up: true, tag: 'p', rect: {x: 10, y: 50, w: 100, h: 20}};
out.acts = B.bar(h, {}).map(b => b.act);
out.labels = B.bar(h, {}).map(b => b.label);
out.img = B.bar(Object.assign({}, h, {tag: 'img', attrs: {src: 'a.png', alt: ''}}), {}).map(b => b.act);
out.top = on(B.bar(Object.assign({}, h, {up: false}), {}));
out.root = on(B.bar(Object.assign({}, h, {root: true}), {}));
out.app = B.bar(Object.assign({}, h, {tag: 'img', attrs: {src: 'a'}}), {app: true}).map(b => [b.act, b.on, !!b.ask]);
out.keys = [B.keyAct({key: '[', code: 'BracketLeft'}), B.keyAct({key: '[', code: 'BracketLeft', ctrl: true, shift: true}), B.keyAct({key: 'ㅔ', code: 'BracketLeft'}), B.keyAct({key: 'Escape'})];
const R = (x, y, w, hh) => ({x: x, y: y, w: w, h: hh});
const c0 = Object.assign({}, h, {path: 'c'}), same = {path: 'w', rect: R(10, 50, 100, 20)}, sec = {path: 's', rect: R(0, 40, 300, 200), root: false}, rt = {path: 'r', rect: R(0, 0, 400, 900), root: true};
out.up1 = B.parentPick(c0, [same, sec, rt]).path;
out.up2 = B.parentPick(c0, [same]);
out.up3 = B.parentPick(c0, []);
out.up4 = B.parentPick(c0, null);
const V = R(0, 0, 1000, 800), S = {w: 200, h: 36};
out.above = B.place(R(100, 300, 80, 20), S, V, null);
out.below = B.place(R(100, 30, 80, 20), S, V, null);
out.avoid = B.place(R(100, 300, 80, 20), S, V, R(50, 250, 300, 40));
out.right = B.place(R(950, 300, 40, 20), S, V, null);
out.side = B.place(R(100, 20, 300, 770), S, V, null);
out.left = B.place(R(700, 20, 290, 770), S, V, null);
out.over = B.place(R(0, 0, 1000, 800), S, V, null);
out.clip = B.place(R(300, 120, 80, 20), S, R(200, 100, 500, 600), null);
out.bottom = B.place(R(100, 790, 80, 30), S, V, null);
out.fields = B.attrFields({tag: 'img', attrs: {src: 'a.png', alt: '', onclick: 'x', style: 'y'}});
out.fieldsA = B.attrFields({tag: 'a', attrs: {href: 'b.html', src: 'z'}});
out.fieldsI = B.attrFields({tag: 'input', attrs: {placeholder: '이름', value: 'v'}});
out.fieldsNone = B.attrFields({tag: 'p', attrs: {href: 'x'}});
out.allowed = [B.attrOk('img', 'src'), B.attrOk('img', 'onerror'), B.attrOk('a', 'style'), B.attrOk('textarea', 'placeholder'), B.attrOk('a', 'HREF')];
out.ask = [B.partAsk('insert', '버튼'), B.partAsk('swap', '칩'), B.partAsk('insert', ''), B.askText('attr', {})];
const mk = (edit, op, value) => Object.assign(E.note('job', {path: 'img', text: '', rect: null}, ''), {edit: edit, op: op || '', value: value});
out.instant = ['attr', 'insert', 'replace'].map(k => E.instantOf(mk(k, 'alt', 'x')));
out.direct = ['attr', 'insert', 'replace'].map(k => E.directOf(mk(k, 'alt', 'x')));
out.preview = E.preview([mk('attr', 'alt', '그림'), mk('insert', '', 'btn')], 'job');
out.say = [E.say.attr('alt', '그림'), E.say.attr('href', ''), E.say.insert('버튼'), E.say.replace('칩')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blocks-b-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bar_order_has_parent_first_and_part_buttons(js):
    assert js["acts"] == ["parent", "text", "remove", "dup", "up", "down", "swap", "insert", "memo"], js["acts"]
    assert js["labels"] == ["상위", "글자", "지우기", "복제", "↑", "↓", "바꾸기", "아래에 넣기", "메모"], js["labels"]
    assert js["img"] == ["parent", "text", "attr", "remove", "dup", "up", "down", "swap", "insert", "memo"], "속성 칸은 고칠 속성이 있을 때만"


def test_parent_off_at_the_top_and_root_blocks_part_edits(js):
    assert js["top"]["parent"] is False
    assert js["root"]["swap"] is False and js["root"]["insert"] is False and js["root"]["parent"] is True


def test_app_card_parent_is_selection_not_a_request(js):
    d = {a: (o, ask) for a, o, ask in js["app"]}
    assert d["parent"] == (True, False) and d["attr"] == (True, True) and d["swap"] == (True, True) and d["insert"] == (True, True), js["app"]


def test_bracket_key_walks_up(js):
    assert js["keys"] == ["parent", None, "parent", None], "[ = 상위(한글 자판도 같은 자리) · Ctrl+Shift+[ 는 프로젝트 탭 · Esc 는 풀기"


def test_parent_pick_skips_wrappers_with_the_same_box(js):
    assert js["up1"] == "s" and js["up2"] is None and js["up3"] is None and js["up4"] is None


def test_place_above_else_below_never_over_the_element(js):
    assert js["above"] == {"x": 100, "y": 300 - 36 - 6, "below": False, "side": "", "over": False}, js["above"]
    assert js["below"]["below"] is True and js["below"]["y"] == 30 + 20 + 6
    assert js["avoid"]["below"] is True
    assert js["right"]["x"] == 950 + 40 - 200, "오른쪽 끝 요소 = 막대 오른쪽을 요소 오른쪽에 맞춤"
    assert js["side"]["side"] == "right" and js["side"]["x"] == 100 + 300 + 6, js["side"]
    assert js["left"]["side"] == "left" and js["left"]["x"] == 700 - 200 - 6, js["left"]
    assert js["over"]["over"] is True, "화면을 다 덮는 요소만 겹친다"
    assert js["clip"] == {"x": 300, "y": 120 + 20 + 6, "below": True, "side": "", "over": False}, ("보이는 칸(크게 보기 창) 안에서", js["clip"])
    b = js["bottom"]; el = {"x": 100, "y": 790, "w": 80, "h": 30}
    assert b["y"] + 36 <= el["y"] and not b["below"], b


def test_attr_fields_use_the_allow_list_only(js):
    assert js["fields"] == [{"name": "src", "label": "이미지 주소", "value": "a.png"}, {"name": "alt", "label": "대체 글", "value": ""}], js["fields"]
    assert js["fieldsA"] == [{"name": "href", "label": "링크 주소", "value": "b.html"}]
    assert js["fieldsI"] == [{"name": "placeholder", "label": "안내 글", "value": "이름"}]
    assert js["fieldsNone"] == []
    assert js["allowed"] == [True, False, False, True, False]


def test_part_requests_and_attr_ask(js):
    assert js["ask"][0] == "이 자리에 버튼 넣기 — 데이터는 화면에 맞게", js["ask"]
    assert js["ask"][1] == "이 요소를 칩(으)로 바꾸기 — 데이터는 화면에 맞게"
    assert js["ask"][2] == "이 자리에 부품 넣기 — 데이터는 화면에 맞게"
    assert js["ask"][3].startswith("속성 바꾸기")


def test_attr_insert_replace_are_instant_and_direct(js):
    assert js["instant"] == [True, True, True] and js["direct"] == [True, True, True]
    assert js["preview"] == [{"path": "img", "attr": "alt", "value": "그림"}], js["preview"]
    assert js["say"][0] == '속성 alt 를 "그림"(으)로 바꾸기' and js["say"][1] == "속성 href 비우기", js["say"]
    assert js["say"][2].startswith("부품 넣기: 버튼") and js["say"][3].startswith("부품으로 바꾸기: 칩"), js["say"]


def test_specimen_parts_is_a_pure_model():
    src = (SCRIPTS / "specimen_parts.py").read_text(encoding="utf-8")
    assert src.startswith('"""Model — '), "머리 = 층 — 맡은 일"
    assert not re.search(r"^\s*(import|from)\s+(os|pathlib|socket|subprocess|urllib|http\.server|shutil)\b", src, re.M), "파일·네트워크를 쓰지 않는다"
    assert not re.search(r"(?<![\w.])open\(", src), "open() 없음"
