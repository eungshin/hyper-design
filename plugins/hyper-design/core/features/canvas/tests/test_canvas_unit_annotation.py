"""메모 주석(task 11) Model — modules/annotation.js 순수 함수 단위 테스트(node). 브라우저 없음.

번호: 화면마다 지금까지 쓴 가장 큰 번호 + 1, 지워도 다시 쓰지 않음, 옛 메모는 화면마다 목록 차례대로.
상태: 답에서 계산(저장하지 않음). 답 검사: 종류마다 꼭 있어야 하는 칸 · 질문 고르기 2–4개 · 모르는 종류(보류) 거절.
답 검사·상태는 hd_model 과 같은 공유 fixture(core/features/hd/tests/fixtures/replies.json)로 묶는다(drift 검사, task 16).
답 글(says)·질문 고르기(question·answer·followUp)·대기열 말(label)·파일에서 온 목록 받기(adopt).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
FIXTURE = HERE.parents[1] / "hd" / "tests" / "fixtures" / "replies.json"
NODE = shutil.which("node")

AN_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/annotation.js', 'utf8'), {filename: 'annotation.js'});
const A = globalThis.HD.annotation, out = {};
// 옛 메모 → 화면마다 목록 차례대로
const old = [{id: 'a', screen: 'home'}, {id: 'b', screen: 'login'}, {id: 'c', screen: 'home'}, {id: 'd', screen: 'home', no: 7}];
const m = A.migrate(old, {});
out.mig = {nos: old.map(n => n.no), seq: m.seq, changed: m.changed, replies: old.every(n => Array.isArray(n.replies))};
out.migAgain = A.migrate(old, m.seq).changed;
// 지운 뒤 더하기 = 다시 쓰지 않음
let seq = m.seq, list = old.slice();
list = list.filter(n => n.id !== 'd');
list.push({id: 'e', screen: 'home'});
seq = A.migrate(list, seq).seq;
out.afterDelete = list.find(n => n.id === 'e').no;
out.lostSeq = (() => { const l = [{id: 'x', screen: 's', no: 4}, {id: 'y', screen: 's'}]; return [A.migrate(l, null).seq, l[1].no]; })();
out.badSeq = A.migrate([{id: 'z', screen: 'q'}], {q: 'nope', r: -3}).seq;
out.nextNo = [A.nextNo({}, 'a'), A.nextNo({a: 3}, 'a'), A.nextNo(null, 'a')];
// 상태
const F = {'반영됨': {what: 'w', screens: ['s'], captured: true}, '일부': {done: 'd', left: 'l'}, '대체됨': {where: 'x'}, '답변': {text: 't'}, '질문': {question: 'q', choices: ['a', 'b']}};
const R = k => Object.assign({kind: k}, F[k] || {});
const st = (sent, ...kinds) => A.status({sent, replies: kinds.map(R)});
out.status = {draft: st(false), working: st(true), decide: st(true, '질문'), partial: st(true, '일부'),
  done1: st(true, '반영됨'), done2: st(true, '대체됨'), done3: st(true, '답변'), lastWins: st(true, '질문', '반영됨'),
  userDone: st(true, '확인'), userDoneDraft: st(false, '확인'), reopened: st(false, '반영됨', '확인', '다시'), reopenedSent: st(true, '확인', '다시'),
  noReplies: A.status({sent: true})};
out.open = [A.isOpen({sent: true, replies: [R('반영됨')]}), A.isOpen({sent: true, replies: [R('질문')]}), A.isOpen({sent: false})];
out.rework = [A.rework({replies: [R('확인'), R('다시'), R('확인'), R('다시')]}), A.rework({})];
// 답 검사
const V = r => A.validReply(r).ok;
out.valid = {
  good: ['반영됨', '일부', '대체됨', '답변', '질문'].map(k => V(R(k))),
  user: [V({kind: '확인'}), V({kind: '다시', by: 'user', at: 'now'})],
  missing: [V({kind: '반영됨', screens: [], captured: true}), V({kind: '반영됨', what: 'w', captured: true}), V({kind: '반영됨', what: 'w', screens: []}),
            V({kind: '반영됨', what: 'w', screens: [], captured: 'yes'}), V({kind: '일부', done: 'd'}), V({kind: '일부', left: 'l'}),
            V({kind: '대체됨'}), V({kind: '답변', text: ''}), V({kind: '질문', choices: ['a', 'b']})],
  choices: [1, 2, 4, 5].map(k => V({kind: '질문', question: 'q', choices: ['a', 'b', 'c', 'd', 'e'].slice(0, k)})),
  unknown: [V({kind: '보류', text: 't'}), V({}), V(null), V([])],
  why: A.validReply({kind: '보류'}).why};
out.reply = A.reply('확인', 't0');
// 공유 fixture(drift): hd_model 과 같은 답 검사·상태
out.fixture = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')).map(c => {
  const errs = [].concat(...c.replies.map(r => A.validReply(r, c.note_intent, c.from === 'agent').errors));
  return {name: c.name, valid: !errs.length, errs, status: A.status({intent: c.note_intent, sent: c.sent, replies: c.replies})};
});
// 답 글 · 질문 고르기 · 대기열 말
out.says = ['반영됨', '일부', '대체됨', '답변', '질문'].map(k => A.says(R(k))).concat([A.says({kind: '확인'}), A.says(A.answer('B', 't')), A.says({kind: '다시'})]);
out.tip = [A.tip(R('반영됨')), A.tip(Object.assign(R('반영됨'), {captured: false, detail: 'd'})), A.tip(R('일부')), A.tip(Object.assign(R('답변'), {detail: '더'}))];
const ask = {sent: true, replies: [R('질문')]};
out.ask = {q: A.question(ask), none: [A.question({sent: true, replies: [R('질문'), R('반영됨')]}), A.question({sent: false, replies: [R('질문')]}), A.question({})],
  answered: (() => { const n = {sent: true, replies: [R('질문'), A.answer('b', 't1')]}; return [A.status(n), A.validReply(n.replies[1]).ok, A.question(n)]; })(),
  answer: A.answer('b', 't1'), follow: A.followUp('어느 색?', '파랑')};
out.label = [A.label({sent: true}, false), A.label({sent: true}, true), A.label({sent: true, replies: [R('질문')]}, true), A.label({sent: false}, true)];
out.decide = A.decideCount([ask, {sent: true}, {sent: true, replies: [R('질문')]}, {sent: true, replies: [R('질문'), {kind: '확인'}]}]);
// 파일에서 온 목록: 같은 id 는 같은 객체(칸만 바뀜), 없어진 칸·메모는 빠짐, 새 것은 그대로
const a = {id: 'a', note: '1', old: 1}, b = {id: 'b'}, cur = [a, b];
const got = A.adopt(cur, [{id: 'c', note: 'new'}, {id: 'a', note: '2', replies: [R('반영됨')]}]);
out.adopt = {same: got[1] === a, ids: got.map(n => n.id), a: a, curLen: cur.length};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-annotation-js-"))
    try:
        (tmp / "a.js").write_text(AN_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "a.js"), str(MOD), str(FIXTURE)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_numbers_per_screen_in_list_order(out):
    assert out["mig"]["nos"] == [8, 1, 9, 7], "번호가 있는 메모(7)보다 크게, 화면마다 목록 차례대로"
    assert out["mig"]["seq"] == {"home": 9, "login": 1} and out["mig"]["changed"] and out["mig"]["replies"]
    assert out["migAgain"] is False, "다시 돌려도 바뀌지 않는다"


def test_numbers_never_reused_after_delete(out):
    assert out["afterDelete"] == 10, "지운 7·9 를 다시 쓰지 않는다(지금까지 가장 큰 번호 + 1)"
    assert out["lostSeq"] == [{"s": 5}, 5], "seq 를 잃어도 목록의 가장 큰 번호 위로"
    assert out["badSeq"] == {"q": 1}, "깨진 seq 값은 버린다"
    assert out["nextNo"] == [1, 4, 1]


def test_status_derived_from_last_reply(out):
    s = out["status"]
    assert (s["draft"], s["working"], s["decide"], s["partial"]) == ("draft", "working", "decide", "partial")
    assert s["done1"] == s["done2"] == s["done3"] == s["lastWins"] == "done"
    assert s["userDone"] == s["userDoneDraft"] == "done", "사람이 완료(확인) = 완료"
    assert s["reopened"] == "draft" and s["reopenedSent"] == "working", "다시 열기 = 다시 보내기 전까지 draft"
    assert s["noReplies"] == "working"
    assert out["open"] == [False, True, True]
    assert out["rework"] == [2, 0]


def test_valid_reply_per_kind(out):
    v = out["valid"]
    assert all(v["good"]) and all(v["user"])
    assert not any(v["missing"]), v["missing"]
    assert v["choices"] == [False, True, True, False], "질문 고르기는 2–4개"
    assert not any(v["unknown"]), "보류 같은 모르는 종류 거절"
    assert "보류" in v["why"]
    assert out["reply"] == {"by": "user", "kind": "확인", "at": "t0"}


def test_shared_fixture_matches_hd_model(out):
    """drift 검사: hd_model 테스트가 읽는 같은 fixture 를 JS 로 — valid·status 가 같아야 한다. from=agent 는 validReply(…, agent=true) 로 그대로 옮긴다(사람 답 거절)."""
    import json as _j
    cases = {c["name"]: c for c in _j.loads(FIXTURE.read_text(encoding="utf-8"))}
    assert len(out["fixture"]) == len(cases) >= 40
    for got in out["fixture"]:
        c = cases[got["name"]]
        assert got["valid"] == c["valid"], (c["name"], got["errs"])
        if c["valid"]:
            assert got["status"] == c["status"], c["name"]
        else:
            assert any(c["reason"] in e for e in got["errs"]), (c["name"], c["reason"], got["errs"])


def test_says_one_line_per_kind(out):
    assert out["says"] == ["반영됨 — w · s", "일부 — d · 남은 것 l", "대체됨 → x", "답변 — t", "질문 — q", "완료함", "완료함 — 고름: B", "다시 엶"]
    assert out["tip"] == ["화면: s · 캡처 확인함", "화면: s · 캡처 안 봄\nd","", "더"], "반영됨 줄에 올리면 화면·캡처"


def test_question_answer_closes_and_follow_up(out):
    a = out["ask"]
    assert a["q"] == {"question": "q", "choices": ["a", "b"]}
    assert a["none"] == [None, None, None], "질문이 마지막 답이고 결정 필요일 때만 고를 것"
    assert a["answered"] == ["done", True, None], "고른 답(확인 + answer) = 완료, 검사 통과"
    assert a["answer"] == {"by": "user", "kind": "확인", "answer": "b", "at": "t1"}
    assert a["follow"] == '질문 "어느 색?" → 파랑'
    assert out["label"] == ["AI 작업 중", "대기열", "결정 필요", "보내기 전"], "받는 곳 없이 보낸 것만 '대기열'"
    assert out["decide"] == 2


def test_adopt_keeps_object_identity(out):
    d = out["adopt"]
    assert d["same"] and d["ids"] == ["c", "a"], "같은 id 는 같은 객체, 새 목록 차례, 없어진 메모는 빠짐"
    assert d["a"] == {"id": "a", "note": "2", "replies": [{"kind": "반영됨", "what": "w", "screens": ["s"], "captured": True}]}, "없어진 칸은 지우고 새 칸은 씀"
    assert d["curLen"] == 2, "지금 목록 배열은 그대로(새 배열을 돌려줌)"
