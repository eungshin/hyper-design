"""하단 대화창 Model — modules/chat.js 순수 함수 단위 테스트(node). 브라우저 없음 (S1).

칩: 고른 카드마다 [화면 이름], 고른 요소 하나면 [버튼 · 기록 남기기](R27 F13)(그 화면 칩도) — 지운 칩(×)은 빠지고, 고르기가 바뀌면 다시 보인다.
범위: 칩 없음 = 모든 화면 · 카드 칩 = 그 화면들 · 요소 칩 = 그 요소.
build: 메모 초안 — 지금 메모와 같은 모양(memo-batch.build 재사용), 요청문(edits.request)은 /hyper-design:fix 가 읽는 형식 그대로.
line: 마지막 요청의 상태 한 줄(메모 상태 + AI 수정 중 덮개) — 보내는 중 → 보냄 → AI 작업 중 → 반영됨 / 답.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const C = globalThis.HD.chat, E = globalThis.HD.edits, out = {};
const title = id => ({pay: '결제', done: '완료', home: '홈'})[id] || id;
let k = 0; const mk = () => 'm' + (++k);
const BTN = {path: 'main.wrap:nth-of-type(1) > button.cta:nth-of-type(1)', text: 'edit_note 기록 남기기', kind: 'button',
             quote: {exact: '기록 남기기', prefix: '', suffix: ''}, rect: {x: 1, y: 2, w: 3, h: 4}};
out.tag = [C.tagOf(BTN.path), C.tagOf('#hero'), C.tagOf('section[data-region="top"]'), C.tagOf(''), C.tagOf(null)];
out.label = [C.elLabel(BTN), C.elLabel({path: '#hero', kind: 'box', text: ''}),
             C.elLabel({path: 'p.x:nth-of-type(1)', text: '아주 긴 문장이 여기에 들어가서 스무 글자를 넘기면 잘린다'})];
out.types = [C.elType(BTN), C.elType({path: '#hero', kind: 'box'}), C.elType({path: 'p.x:nth-of-type(1)'}), C.elType({path: 'div > img.hero', kind: 'box'}),
             C.elType({path: 'img'}), C.elType({path: 'aside.side', kind: 'box'}), C.elType({path: ''})];
out.none = C.chips({ids: [], titleOf: title, el: null});
out.cards = C.chips({ids: ['pay', 'done', 'pay', ''], titleOf: title, el: null});
out.elem = C.chips({ids: ['pay'], titleOf: title, el: {screen: 'pay', h: BTN, app: false}});
out.elemOther = C.chips({ids: [], titleOf: title, el: {screen: 'done', h: BTN}});
out.badEl = C.chips({ids: ['pay'], titleOf: title, el: {screen: 'pay', h: {path: null}}});
const dis = {'screen:done': 1, 'el:pay:old': 1};
out.visible = C.visible(out.cards, dis).map(c => c.key);
out.prune = C.prune(dis, out.cards);
out.scope = [C.scope([]), C.scope(out.cards), C.scope(out.elem)];
out.scopeLabel = [C.scopeLabel([]), C.scopeLabel(out.cards), C.scopeLabel(out.elem)];
k = 0; out.empty = C.build(out.cards, '   ', {first: 'pay', titleOf: title}, mk);
k = 0; out.noScreen = C.build([], '배경 바꾸기', {first: null, titleOf: title}, mk);
k = 0; out.all = C.build([], '  전체 글꼴 키우기 ', {first: 'home', titleOf: title}, mk);
k = 0; out.one = C.build(C.visible(out.cards, {'screen:done': 1}), '여백 줄이기', {first: 'home', titleOf: title}, mk);
k = 0; out.many = C.build(out.cards, '여백 줄이기', {first: 'home', titleOf: title}, mk);
k = 0; out.el = C.build(out.elem, "이 버튼 문구를 '기록 시작'으로", {first: 'home', titleOf: title}, mk);
k = 0; out.elDismissed = C.build(C.visible(out.elem, {[out.elem[1].key]: 1}), '버튼 키우기', {first: 'home', titleOf: title}, mk);
const SRC = {path: 'button.go:nth-of-type(1)', text: '가입', kind: 'button', src: {file: 'src/App.svelte', line: 12, column: 3}};
k = 0; out.app = C.build(C.chips({ids: ['pay'], titleOf: title, el: {screen: 'pay', h: SRC, app: true}}), '색 바꾸기', {first: 'pay', titleOf: title}, mk);
k = 0; out.mixed = C.build(C.chips({ids: ['pay', 'done'], titleOf: title, el: {screen: 'pay', h: BTN}}), '같이 고치기', {first: 'pay', titleOf: title}, mk);
out.req = {all: E.request(out.all.memos, '/o'), one: E.request(out.one.memos, '/o'), el: E.request(out.el.memos, '/o'), app: E.request(out.app.memos, '/o')};
// 상태 줄
const n = (o) => Object.assign({id: 'x', screen: 'pay', sent: true, replies: []}, o);
out.stage = [
  C.stage(n({sent: false}), null, true), C.stage(n({sent: false}), null, false), C.stage(n({}), null), C.stage(n({}), {via: 'queue'}),
  C.stage(n({}), {via: 'paseo'}), C.stage(n({}), {via: 'cli'}), C.stage(n({replies: [{kind: '질문', question: '어느 쪽?', choices: ['a', 'b']}]}), null),
  C.stage(n({replies: [{kind: '일부', done: 'a', left: 'b'}]}), null), C.stage(n({replies: [{kind: '반영됨', what: '바꿈'}]}), null),
  C.stage(n({replies: [{kind: '답변', text: '그건 이렇게요'}]}), null), C.stage(null, null)];
const notes = {a: n({id: 'a'}), b: n({id: 'b', screen: 'done', replies: [{kind: '반영됨', what: 'ok'}]}), c: n({id: 'c', replies: [{kind: '답변', text: '네 바꿨어요'}]})};
const find = id => notes[id] || null;
out.line = [
  C.line(null, find, () => null, false),
  C.line({text: '여백 줄이기', ids: ['a'], at: 1}, find, () => null, false),
  C.line({text: '여백 줄이기', ids: ['a'], at: 1}, find, s => (s === 'pay' ? {via: 'paseo'} : null), false),
  C.line({text: '여백', ids: ['a', 'b'], at: 1}, find, () => null, false),
  C.line({text: '여백', ids: ['b', 'gone'], at: 1}, find, () => null, false),
  C.line({text: '질문', ids: ['c'], at: 1}, find, () => null, false)];
out.parse = [C.parseLast(null), C.parseLast('{"text":"a","ids":["x"],"at":5}'), C.parseLast('{깨짐'), C.parseLast('{"text":"a","ids":"x"}'), C.parseLast('[]')];
out.record = C.record('  여백 줄이기\n두 줄 ', [{id: 'a'}, {id: 'b'}], 9);
// 칩 줄 접기(S1c) · placeholder 로 범위
const many = C.chips({ids: ['a', 'b', 'c', 'd', 'e'], titleOf: title, el: null});
const keys = f => ({shown: f.shown.map(c => c.key), more: f.more});
out.fold = {five: keys(C.fold(many)), fiveOpen: keys(C.fold(many, true)), three: keys(C.fold(many.slice(0, 3))), four: keys(C.fold(many.slice(0, 4))),
            none: keys(C.fold([])), bad: keys(C.fold(null)),
            withEl: keys(C.fold(C.chips({ids: ['a', 'b', 'c', 'd'], titleOf: title, el: {screen: 'd', h: BTN}})))};
out.ph = [C.placeholder([]), C.placeholder(out.cards), C.placeholder(out.elem), C.placeholder(null)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chat-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_element_chip_label_is_kind_word_and_short_quote(out):
    assert out["tag"] == ["BUTTON", "", "SECTION", "", ""]
    a, b, c = out["label"]
    assert a == "버튼 · 기록 남기기", "R27 F13: 태그 대신 사람 말(종류) · 글은 quote.exact(아이콘 글자 없이)"
    assert b == "영역", "글이 없으면 종류만"
    assert c.startswith("글자 · ") and c.endswith("…") and len(c) <= 2 + 3 + 20 + 1, ("종류가 없으면 태그로 짐작(P = 글자), 20자에서 자름", c)
    assert out["types"] == ["button", "box", "text", "image", "image", "box", ""], out["types"]


def test_chips_from_selection(out):
    assert out["none"] == [], "아무것도 안 고름 = 칩 없음(범위 모든 화면)"
    assert [(c["kind"], c["screen"], c["label"]) for c in out["cards"]] == [("screen", "pay", "결제"), ("screen", "done", "완료")], "겹침·빈 값 빼고 고른 차례"
    assert [c["key"] for c in out["cards"]] == ["screen:pay", "screen:done"]
    e = out["elem"]
    assert [c["kind"] for c in e] == ["screen", "el"] and e[1]["label"] == "버튼 · 기록 남기기" and e[1]["type"] == "button" and e[1]["screen"] == "pay"
    assert e[1]["key"] == "el:pay:" + "main.wrap:nth-of-type(1) > button.cta:nth-of-type(1)"
    assert [(c["kind"], c["screen"]) for c in out["elemOther"]] == [("screen", "done"), ("el", "done")], "요소의 화면 칩이 없으면 앞에 더한다"
    assert [c["kind"] for c in out["badEl"]] == ["screen"], "경로 없는 요소는 칩 없음"


def test_dismissed_chips_and_prune(out):
    assert out["visible"] == ["screen:pay"]
    assert out["prune"] == {"screen:done": 1}, "지금 칩에 없는 지운 표시는 버린다(다시 고르면 다시 보임)"


def test_scope(out):
    assert out["scope"] == ["all", "screen", "element"]
    assert out["scopeLabel"] == ["모든 화면", "화면 2개", "요소"]


def test_build_refuses_empty_text_and_no_screen(out):
    assert out["empty"]["memos"] == [] and out["empty"]["why"]
    assert out["noScreen"]["memos"] == [] and out["noScreen"]["why"]


def test_build_all_screens(out):
    m = out["all"]["memos"]
    assert len(m) == 1 and m[0]["screen"] == "home" and m[0]["scope"] == "all" and m[0]["path"] == "body"
    assert m[0]["note"] == "전체 글꼴 키우기" and m[0]["intent"] == "chat" and m[0]["sent"] is False   # 대화창 글 = 받는 AI 가 질문인지 바꾸기인지 정한다
    assert "intent=chat" in out["req"]["all"]
    assert "범위: 모든 화면" in out["req"]["all"] and "screen=home · path=body" in out["req"]["all"]


def test_build_cards_reuses_memo_batch(out):
    one = out["one"]["memos"]
    assert len(one) == 1 and one[0]["screen"] == "pay" and one[0]["scope"] == "screen" and "batch" not in one[0]
    assert "1. screen=pay · path=body" in out["req"]["one"] and "범위: 이 화면 전체" in out["req"]["one"] and "요청: 여백 줄이기" in out["req"]["one"]
    many = out["many"]["memos"]
    assert [x["screen"] for x in many] == ["pay", "done"] and len({x["batch"] for x in many}) == 1 and all(x["scope"] == "screen" for x in many)


def test_build_element_memo(out):
    m = out["el"]["memos"]
    assert len(m) == 1, "요소 칩이 있으면 그 화면의 화면 메모는 따로 나가지 않는다"
    x = m[0]
    assert x["screen"] == "pay" and x["path"] == "main.wrap:nth-of-type(1) > button.cta:nth-of-type(1)" and "scope" not in x
    assert x["targets"][0]["quote"]["exact"] == "기록 남기기" and x["targets"][0]["path"] == x["path"]
    assert "screen=pay · path=main.wrap:nth-of-type(1) > button.cta:nth-of-type(1)" in out["req"]["el"]
    assert "요청: 이 버튼 문구를 '기록 시작'으로" in out["req"]["el"] and "범위:" not in out["req"]["el"]
    d = out["elDismissed"]["memos"]
    assert len(d) == 1 and d[0]["path"] == "body" and d[0]["scope"] == "screen", "요소 칩을 지우면 화면 전체로 넓어진다"


def test_build_app_card_keeps_source_line(out):
    m = out["app"]["memos"][0]
    assert m["targets"][0]["src"]["file"] == "src/App.svelte"
    assert "소스: src/App.svelte:12" in out["req"]["app"]


def test_build_mixed_element_and_other_card(out):
    m = out["mixed"]["memos"]
    assert [(x["screen"], x["path"]) for x in m] == [("pay", "main.wrap:nth-of-type(1) > button.cta:nth-of-type(1)"), ("done", "body")]
    assert m[1]["scope"] == "screen"


def test_stage_of_one_memo(out):
    assert out["stage"] == ["sending", "unsent", "sent", "queued", "working", "working", "decide", "partial", "applied", "answered", "applied"]


def test_status_line(out):
    a, b, c, d, e, f = out["line"]
    assert a is None
    assert b["stage"] == "sent" and b["text"].startswith("보냄") and b["req"] == "여백 줄이기"
    assert c["stage"] == "working" and "AI 작업 중" in c["text"]
    assert d["stage"] == "sent" and "1/2" in d["text"], "여러 메모면 끝난 수"
    assert e["stage"] == "applied" and "반영됨" in e["text"], "없어진 메모 = 바로 반영돼 목록에서 빠짐"
    assert f["stage"] == "answered" and "네 바꿨어요" in f["text"]


def test_parse_and_record(out):
    p = out["parse"]
    assert p[0] == {"last": None, "bad": False}
    assert p[1] == {"last": {"text": "a", "ids": ["x"], "at": 5}, "bad": False}
    assert p[2] == {"last": None, "bad": True} and p[3] == {"last": None, "bad": True} and p[4] == {"last": None, "bad": True}
    assert out["record"] == {"text": "여백 줄이기 두 줄", "ids": ["a", "b"], "at": 9}


def test_chip_row_folds_after_three(out):
    f = out["fold"]
    assert f["five"] == {"shown": ["screen:a", "screen:b"], "more": 3}, "5개 = 앞 2개 + 외 3개"
    assert f["fiveOpen"] == {"shown": ["screen:a", "screen:b", "screen:c", "screen:d", "screen:e"], "more": 0}, "외 N개를 누르면 펼침"
    assert f["three"]["more"] == 0 and len(f["three"]["shown"]) == 3, "3개까지는 다 보인다(외 1개는 자리를 아끼지 않는다)"
    assert f["four"] == {"shown": ["screen:a", "screen:b"], "more": 2}
    assert f["none"] == {"shown": [], "more": 0} and f["bad"] == {"shown": [], "more": 0}
    assert f["withEl"]["shown"][-1].startswith("el:d:") and f["withEl"]["more"] == 2, "고른 요소 칩은 접지 않는다"


def test_placeholder_carries_scope(out):
    assert out["ph"] == ["모든 화면에 대해 무엇을 바꾸거나 만들까요?", "무엇을 바꿀까요?", "무엇을 바꿀까요?",
                         "모든 화면에 대해 무엇을 바꾸거나 만들까요?"], "모든 화면 칩 대신 placeholder 가 범위를 말한다"


def test_every_chat_memo_lets_the_receiver_decide(out):
    """대화창이 만든 메모는 칩(모든 화면 · 화면 · 요소)과 상관없이 intent=chat — 사용자가 바꾸기/질문을 고르지 않는다."""
    for k in ("all", "one", "el"):
        assert out[k]["memos"] and all(m["intent"] == "chat" for m in out[k]["memos"]), (k, out[k]["memos"])
