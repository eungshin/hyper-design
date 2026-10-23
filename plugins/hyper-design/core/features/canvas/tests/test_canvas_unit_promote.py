"""빈 레이아웃 승격(#241 R2) Model — modules/promote.js 순수 함수 단위 테스트(node). 브라우저 없음.

때(promotable): 빈 레이아웃 메모의 마지막 AI 답이 반영됨(screens[0]) · 대체됨(where 에 든 화면 id) 이고 그 화면이 데이터에 있을 때만 — 화면이 아직 없으면 없음,
  승격한 뒤에는 다시 걸리지 않음(되풀이), 빈 레이아웃 둘 = 승격 둘, 한 화면을 둘이 노리면 먼저 온 것만.
promote: 메모(번호·답 그대로) · 들어오고 나가는 잇기 · 폴더 자리 · 카드 자리(빈 레이아웃 자리가 이김) · 입력은 그대로 · undo = 입력.
#235: 빈 레이아웃 메모 본문이 보내기 요청문에 실리고(task 17 R5) 상태 파일 본문에 이름·목적이 실린다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['promote.js', 'edits.js', 'state-file.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const P = globalThis.HD.promote, E = globalThis.HD.edits, S = globalThis.HD.stateFile, out = {};
const lay = (id, screen, value, replies, x) => Object.assign({id, no: 1, screen, targets: [{path: '(새 화면)', text: '빈 레이아웃', rect: null}], path: '(새 화면)', text: '빈 레이아웃',
  rect: null, intent: 'change', sent: true, edit: 'new-screen', op: 'new', to: '', value, purpose: value + ' 목적', x: 900, y: 40, note: 'L', replies}, x || {});
const memo = (id, no, screen, note, replies) => ({id, no, screen, targets: [{path: 'body', text: '', rect: null}], path: 'body', text: '', rect: null, note, intent: 'change', sent: true, replies: replies || []});
const link = (id, from, to) => Object.assign(E.note(from, {path: 'a.go', text: '가기', rect: null}, '이 요소를 누르면 "빈"(' + to + ') 화면으로 가게 연결', 'link', to), {id, no: 9, replies: []});
const done = (screens) => [{kind: '반영됨', what: '만듦', screens, captured: true, by: 'agent'}];
const ids = ['home', 'pay', 'guide'];

// 때
out.none = P.promotable([lay('L', 'new-a', '안내', [])], ids);                                   // 답 없음
out.notYet = P.promotable([lay('L', 'new-a', '안내', done(['guide-x']))], ids);                  // 그 화면이 아직 데이터에 없음
out.one = P.promotable([lay('L', 'new-a', '안내', done(['guide', 'home']))], ids);
out.replaced = P.promotable([lay('L', 'new-a', '안내', [{kind: '대체됨', where: '기존 화면 pay(결제)에 합침', by: 'agent'}])], ids);
out.replacedWhole = P.target(lay('L', 'new-a', 'x', [{kind: '대체됨', where: ' home '}]), ids);
out.replacedPart = [P.target(lay('L', 'new-a', 'x', [{kind: '대체됨', where: 'homepage 로'}]), ids), P.target(lay('L', 'new-a', 'x', [{kind: '대체됨', where: 'myhome 으로'}]), ids)];   // home 은 다른 id 의 일부 → 없음
out.confirmed = P.promotable([lay('L', 'new-a', '안내', done(['guide']).concat([{kind: '확인', by: 'user'}]))], ids);   // 사람 완료 뒤에도
out.reopened = P.promotable([lay('L', 'new-a', '안내', done(['guide']).concat([{kind: '다시', by: 'user'}]))], ids);  // 다시 열면 아님
out.question = P.promotable([lay('L', 'new-a', '안내', done(['guide']).concat([{kind: '질문', question: '?', choices: ['a', 'b']}]))], ids);
out.two = P.promotable([lay('L1', 'new-a', '안내', done(['guide'])), lay('L2', 'new-b', '결제2', done(['pay'])), memo('m', 1, 'home', 'x')], ids);
out.clash = P.promotable([lay('L1', 'new-a', '안내', done(['guide'])), lay('L2', 'new-b', '안내2', done(['guide']))], ids);
out.realId = P.promotable([lay('L', 'pay', '안내', done(['guide']))], ids);                     // new-screen 인데 id 가 이미 화면
out.mapIds = P.promotable([lay('L', 'new-a', '안내', done(['guide']))], {guide: 1});

// promote
const st = {
  notes: [lay('L', 'new-a', '안내', done(['guide'])), memo('m2', 2, 'new-a', '목록 위에 검색', [{kind: '일부', done: 'a', left: 'b'}]), memo('m3', 3, 'new-a', '버튼 둘'),
          link('in', 'home', 'new-a'), link('outg', 'new-a', 'pay'), memo('h1', 1, 'home', '홈 메모')],
  cardPos: {'new-a': {dx: 30, dy: -10}, home: {dx: 5, dy: 5, g: 'G'}},
  folders: {v: 1, folders: [{id: 'f1', name: '온보딩', ids: ['home', 'new-a', 'pay'], open: true}, {id: 'f2', name: '기타', ids: ['guide'], open: false}]}
};
const before = JSON.stringify(st);
const r = P.promote(st, 'new-a', 'guide', {draft: {x: 930, y: 30}, screen: {x: 400, y: 600}, g: '안내'});
out.r = r;
out.inputSame = JSON.stringify(st) === before;
out.undoIsInput = JSON.stringify(Object.assign({}, r.undo, {notes: r.undo.notes.map(n => { const c = Object.assign({}, n); delete c.stay; return c; })})) === before;
out.undoStay = r.undo.notes.map(n => n.stay || null);
out.afterUndo = P.promotable(r.undo.notes, ids);
out.afterUndoOther = P.promotable(r.undo.notes.map(n => n.id === 'L' ? Object.assign({}, n, {replies: n.replies.concat([{kind: '반영됨', what: 'x', screens: ['pay'], captured: false}])}) : n), ids);
out.again = P.promote(r.state, 'new-a', 'guide', null);                                          // 이미 승격 = null
out.afterPromotable = P.promotable(r.state.notes, ids);
// 화면에 이미 옮긴 자리가 있으면 빈 레이아웃 자리가 이기고 moved
const st2 = {notes: [lay('L', 'new-a', '안내', done(['guide']))], cardPos: {guide: {dx: 100, dy: 50, g: '안내'}}, folders: {v: 1, folders: []}};
out.r2 = P.promote(st2, 'new-a', 'guide', {draft: {x: 930, y: 30}, screen: {x: 500, y: 650}, g: '안내'});
out.r2noPlace = P.promote(st2, 'new-a', 'guide', null);
out.missing = P.promote(st2, 'new-zz', 'guide', null);
out.say = [P.say('안내', '질문창 안내', false), P.say('안내', '질문창 안내', true)];
out.movedSay = [P.movedSay(r.state.notes[1]), P.movedSay(memo('x', 1, 'home', ''))];

// #235 — 빈 레이아웃 메모 본문이 요청문에, 이름·목적이 상태 파일 본문에
const l235 = lay('L', 'new-a', '안내', [], {sent: false});
l235.note = E.say.layout(l235.value, l235.screen, l235.purpose);
const m235 = Object.assign(memo('m', 2, 'new-a', '질문창 위에 안내 문구'), {sent: false});
out.req235 = E.request([l235, m235], 'C:/o');
const got = S.fromLocal(k => k === 'hd-notes:h' ? JSON.stringify([l235, m235]) : null, 'h');
out.body235 = S.body(1, got.values, ['notes']);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-promote-js-"))
    try:
        (tmp / "p.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "p.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_promote_before_reply_or_before_screen_exists(out):
    assert out["none"] == [] and out["notYet"] == [], "답이 없거나 그 화면이 아직 데이터에 없으면 아무것도"
    assert out["realId"] == [], "이미 진짜 화면 id 인 것은 빈 레이아웃이 아니다"


def test_reflected_reply_promotes_to_first_screen(out):
    assert out["one"] == [{"draft": "new-a", "screen": "guide", "name": "안내"}], "반영됨 = screens[0]"
    assert out["mapIds"] == out["one"], "ids 는 {id: 1} 도 된다"


def test_replaced_reply_finds_screen_id_in_where(out):
    assert out["replaced"] == [{"draft": "new-a", "screen": "pay", "name": "안내"}]
    assert out["replacedWhole"] == "home"
    assert out["replacedPart"] == [None, None], "다른 단어의 일부는 화면 id 가 아니다"


def test_last_agent_reply_decides(out):
    assert out["confirmed"] == [{"draft": "new-a", "screen": "guide", "name": "안내"}], "사람이 완료해도 그 앞 반영됨을 본다"
    assert out["reopened"] == [] and out["question"] == [], "다시 열거나 마지막이 질문이면 아직"


def test_two_drafts_two_promotes_and_one_screen_taken_once(out):
    assert [(p["draft"], p["screen"]) for p in out["two"]] == [("new-a", "guide"), ("new-b", "pay")]
    assert [(p["draft"], p["screen"]) for p in out["clash"]] == [("new-a", "guide")], "한 화면은 먼저 온 빈 레이아웃만"


def test_memos_move_and_keep_numbers_and_replies(out):
    ns = {n["id"]: n for n in out["r"]["state"]["notes"]}
    assert ns["m2"]["screen"] == "guide" and ns["m2"]["no"] == 2 and ns["m2"]["replies"] == [{"kind": "일부", "done": "a", "left": "b"}]
    assert ns["m3"]["screen"] == "guide" and ns["m3"]["no"] == 3
    assert ns["m2"]["moved"] == {"from": "new-a", "name": "안내"}
    lay = ns["L"]
    assert "edit" not in lay and lay["screen"] == "guide" and lay["no"] == 1 and lay["replies"][0]["kind"] == "반영됨", "빈 레이아웃 메모는 그 화면의 완료 메모로 남는다"
    assert lay["moved"] == {"from": "new-a", "name": "안내"}
    assert ns["h1"] == {**ns["h1"], "screen": "home"} and "moved" not in ns["h1"], "다른 화면 메모는 그대로"
    assert out["r"]["memos"] == 2 and out["r"]["name"] == "안내"
    assert out["movedSay"] == ["빈 레이아웃 '안내'에서 옮겨 왔어요", ""]


def test_lines_both_directions_follow(out):
    ns = {n["id"]: n for n in out["r"]["state"]["notes"]}
    assert ns["in"]["to"] == "guide" and ns["in"]["screen"] == "home", "들어오는 잇기"
    assert "(guide)" in ns["in"]["note"] and "(new-a)" not in ns["in"]["note"], "요청 글의 도착 id 도"
    assert ns["outg"]["screen"] == "guide" and ns["outg"]["to"] == "pay", "나가는 잇기"
    assert out["r"]["lines"] == 2


def test_folder_place_and_card_position(out):
    fs = out["r"]["state"]["folders"]["folders"]
    assert fs[0]["ids"] == ["home", "guide", "pay"], "빈 레이아웃이 있던 폴더·차례에"
    assert fs[1]["ids"] == [], "화면은 다른 폴더에서 빠진다"
    cp = out["r"]["state"]["cardPos"]
    assert cp["guide"] == {"dx": 530, "dy": -570, "g": "안내"} and "new-a" not in cp, "화면 옮긴 거리 = 빈 레이아웃 - 화면"
    assert cp["home"] == {"dx": 5, "dy": 5, "g": "G"}
    assert out["r"]["moved"] is False


def test_draft_position_wins_over_user_position(out):
    assert out["r2"]["state"]["cardPos"]["guide"] == {"dx": 530, "dy": -570, "g": "안내"}
    assert out["r2"]["moved"] is True
    assert out["say"] == ["빈 레이아웃 '안내' 자리에 질문창 안내이 들어왔어요",
                          "빈 레이아웃 '안내' 자리에 질문창 안내이 들어왔어요 — 따로 옮겨 둔 자리 대신 빈 레이아웃 자리로"]
    assert out["r2noPlace"]["state"]["cardPos"]["guide"] == {"dx": 100, "dy": 50, "g": "안내"} and out["r2noPlace"]["moved"] is False, "자리를 모르면 그대로"


def test_pure_idempotent_and_undo_is_input(out):
    assert out["inputSame"] and out["undoIsInput"]
    assert out["undoStay"] == ["guide", None, None, None, None, None], "되돌리면 빈 레이아웃 메모에 stay = 그 화면"
    assert out["afterUndo"] == [], "되돌린 승격은 다시 걸리지 않는다"
    assert [(p["draft"], p["screen"]) for p in out["afterUndoOther"]] == [("new-a", "pay")], "AI 가 다른 화면으로 답하면 다시 걸린다"
    assert out["again"] is None and out["afterPromotable"] == [], "한 번만"
    assert out["missing"] is None


def test_235_layout_memos_ride_send_and_state_file_has_name_purpose(out):
    """#235 — task 17(R5)로 풀렸는지: 빈 레이아웃 메모 본문이 레이아웃 항목에 실리고, 상태 파일 본문의 메모에 이름·목적이 있다."""
    lines = out["req235"].split("\n")
    assert lines[0].endswith(" · 1건") and lines[1].startswith("1. screen=new-a"), out["req235"]
    assert "목적: 안내 목적" in lines[3] and lines[4] == "       - 질문창 위에 안내 문구", out["req235"]
    lay = out["body235"]["state"]["notes"][0]
    assert lay["edit"] == "new-screen" and lay["value"] == "안내" and lay["purpose"] == "안내 목적"
