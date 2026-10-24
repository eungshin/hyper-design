"""한 번 보내기가 말하는 것(task 17 · A2b, tracking R5·R6·R7) — modules/edits.js request 단위 테스트(node). 브라우저 없음.

R5 빈 레이아웃 = 항목 하나: 레이아웃 줄 + 그 화면 메모 본문(번호 차례, '- ' 들여 쓴 줄), 메모는 따로 나가지 않는다.
   목적도 메모 본문도 없으면 emptyLayouts 가 그 화면 id 를 돌려준다(셸이 한 번 알림).
R6 같은 화면 · 같은 글(공백 정리) · 같은 의도 · 같은 범위 메모 = 항목 하나: 첫 경로가 path=, 나머지는 '   다른 곳: …'.
   여러 요소 메모도 같은 규칙(항목 하나).
R7 범위 n.scope = element|screen|all(없음 = element): screen·all 이면 '   범위: …' 줄. annotation.SCOPES = 고르기 말.
옛 메모(범위 없음·겹침 없음·빈 레이아웃 없음)는 예전 출력 그대로 — 아래 OLD 로 고정. 항목 머리 끝 ' · no=…'(#279) = 그 항목 메모 번호(번호 없는 메모 = 줄 없음, 4번 항목).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'annotation.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const E = globalThis.HD.edits, A = globalThis.HD.annotation, out = {};
const m = (id, no, screen, path, text, note, x) => Object.assign({id, no, screen, targets: [{path, text, rect: null}], path, text, rect: null, note, intent: 'change', sent: false}, x || {});
// 옛 메모 — 지금 출력 고정
out.old = E.request([
  m('a', 1, 'home', 'h1.title', '  안녕   하세요 ', '제목을 크게'),
  m('b', 2, 'home', 'p.lead', '설명', '첫 줄\n둘째 줄'),
  m('c', 1, 'pay', 'body', '결제', '왜 이 화면?', {intent: 'question'}),
  Object.assign(E.note('home', {path: 'a.go', text: '다음', rect: null}, E.say.link('pay'), 'link', 'pay'), {id: 'd'})
], 'C:/o');
// R5 — 빈 레이아웃 + 메모 둘(번호 거꾸로 들어옴) + 다른 화면 메모 하나
const lay = {id: 'L', no: 1, screen: 'new-ab', targets: [{path: '(새 화면)', text: '빈 레이아웃', rect: null}], path: '(새 화면)', text: '빈 레이아웃', rect: null,
             intent: 'change', sent: false, edit: 'new-screen', value: '결제', purpose: '카드로 결제한다', op: 'new', to: ''};
lay.note = E.say.layout(lay.value, lay.screen, lay.purpose);
const m3 = m('m3', 3, 'new-ab', 'body', '결제', '쿠폰 칸\n선택으로'), m2 = m('m2', 2, 'new-ab', 'body', '결제', '카드 목록 위에 합계');
out.r5list = [lay, m3, m2, m('h', 1, 'home', 'h1', '홈', '홈 메모')];
out.r5 = E.request(out.r5list, 'C:/o');
out.r5ids = E.items(out.r5list).map(it => it.notes.map(n => n.id));
const bare = Object.assign({}, lay, {id: 'L2', screen: 'new-cd', purpose: ''}); bare.note = E.say.layout('빈 레이아웃', 'new-cd', '');
out.empty = E.emptyLayouts([lay, m3, bare, m('q', 1, 'new-cd', 'body', '빈', '   '), Object.assign({}, lay, {id: 'L3', screen: 'new-ef'})]);
out.emptyCopy = E.emptyLayouts([Object.assign({}, bare, {copyOf: 'home'})]);
out.emptySay = E.say.emptyLayout;
// R6 — 같은 글 두 요소(공백만 다름) + 다른 글 하나 + 다른 의도 하나 + 여러 요소 메모 하나
out.r6 = E.request([
  m('x1', 1, 'home', 'a.one', '하나', '굵게  해 주세요'),
  m('x2', 2, 'home', 'p.lead', '설명', '다른 요청'),
  m('x3', 3, 'home', 'a.two', '둘', ' 굵게 해 주세요\n'),
  m('x4', 4, 'home', 'a.three', '셋', '굵게 해 주세요', {intent: 'question'}),
  m('x5', 1, 'pay', 'a.p1', '가', '두 곳 모두', {targets: [{path: 'a.p1', text: '가'}, {path: 'button.long', text: '아주 긴 버튼 글자가 여기에 들어갑니다 정말로'}]})
], 'C:/o');
// R7 — 범위
out.r7 = E.request([m('s1', 1, 'home', 'body', '홈', '배경을 움직이는 그라데이션으로', {scope: 'all'}),
                    m('s2', 2, 'home', 'h1', '홈', '여백 넓게', {scope: 'screen'}),
                    m('s3', 3, 'home', 'h2', '부제', '여백 넓게', {scope: 'element'})], 'C:/o');
out.scopes = A.SCOPES; out.scopeOf = [A.scopeOf({}), A.scopeOf({scope: 'all'}), A.scopeOf({scope: 'bogus'}), A.scopeOf({scope: 'screen'})];
out.scopeWord = [A.scopeWord({}), A.scopeWord({scope: 'screen'}), A.scopeWord({scope: 'all'})];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-send-js-"))
    try:
        (tmp / "s.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "s.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


OLD = """[hyper-design 수정 요청] out=C:/o · 4건
1. screen=home · path=h1.title · no=1
   text=" 안녕 하세요 " · intent=change
   요청: 제목을 크게
2. screen=home · path=p.lead · no=2
   text="설명" · intent=change
   요청: 첫 줄
       둘째 줄
3. screen=pay · path=body · no=1
   text="결제" · intent=question
   요청: 왜 이 화면?
4. screen=home · path=a.go
   text="다음" · intent=change
   요청: 이 요소를 누르면 pay 화면으로 가게 연결"""


def test_old_notes_send_exactly_as_before(out):
    assert out["old"] == OLD


def test_blank_layout_and_its_memos_are_one_item(out):
    lines = out["r5"].split("\n")
    assert lines[0] == "[hyper-design 수정 요청] out=C:/o · 2건", "레이아웃 + 메모 둘 = 한 건, 다른 화면 메모 한 건"
    assert lines[1] == "1. screen=new-ab · path=(새 화면) · no=1,2,3"
    assert lines[3] == '   요청: 새 화면 "결제"(new-ab)을 빈 레이아웃으로 만들기 — 목적: 카드로 결제한다 · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기'
    assert lines[4:7] == ["       - 카드 목록 위에 합계", "       - 쿠폰 칸", "         선택으로"], "메모 본문은 번호 차례, 여러 줄은 더 들여 써서"
    assert lines[7] == "2. screen=home · path=h1 · no=1" and len(lines) == 10
    assert out["r5ids"] == [["L", "m2", "m3"], ["h"]], "메모는 레이아웃 항목에 한 번만 — 보낼 때 함께 '보냄'"


def test_blank_layout_without_purpose_or_memo_body_is_flagged(out):
    assert out["empty"] == ["new-cd"], "목적·메모 있음 = 괜찮음 · 목적만 있음 = 괜찮음 · 목적 없고 빈 메모뿐 = 알림"
    assert out["emptyCopy"] == [], "복제는 내용이 있다"
    assert out["emptySay"] == "빈 레이아웃에 목적이나 메모가 없어요 — AI가 채울 내용을 모를 수 있어요"


def test_same_text_on_several_elements_is_one_item(out):
    lines = out["r6"].split("\n")
    assert lines[0] == "[hyper-design 수정 요청] out=C:/o · 4건"
    assert lines[1] == "1. screen=home · path=a.one · no=1,3" and lines[3] == "   요청: 굵게  해 주세요"
    assert lines[4] == '   다른 곳: a.two ("둘")', "같은 글(공백 정리) = 한 건, 짧은 글은 함께"
    assert lines[5] == "2. screen=home · path=p.lead · no=2"
    assert lines[8] == "3. screen=home · path=a.three · no=4", "의도가 다르면 따로"
    assert lines[11] == "4. screen=pay · path=a.p1 · no=1" and lines[14] == "   다른 곳: button.long", "여러 요소 메모도 한 건 · 긴 글은 경로만"
    assert len(lines) == 15


def test_scope_lines_and_labels(out):
    lines = out["r7"].split("\n")
    assert lines[0].endswith(" · 3건"), "범위가 다르면 같은 글이라도 따로"
    assert lines[3:5] == ["   요청: 배경을 움직이는 그라데이션으로", "   범위: 모든 화면"]
    assert lines[7:9] == ["   요청: 여백 넓게", "   범위: 이 화면 전체"]
    assert lines[11] == "   요청: 여백 넓게" and len(lines) == 12, "이 요소 = 줄 없음"
    assert out["scopes"] == [["element", "이 요소"], ["screen", "이 화면"], ["all", "모든 화면"]]
    assert out["scopeOf"] == ["element", "all", "element", "screen"]
    assert out["scopeWord"] == ["", "이 화면", "모든 화면"]
