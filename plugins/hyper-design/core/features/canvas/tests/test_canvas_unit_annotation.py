"""메모 주석(task 11) Model — modules/annotation.js 순수 함수 단위 테스트(node). 브라우저 없음.

번호: 화면마다 지금까지 쓴 가장 큰 번호 + 1, 지워도 다시 쓰지 않음, 옛 메모는 화면마다 목록 차례대로.
상태: 답에서 계산(저장하지 않음). 답 검사: 종류마다 꼭 있어야 하는 칸 · 질문 고르기 2–4개 · 모르는 종류(보류) 거절.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
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
const R = k => Object.assign({kind: k}, {what: 'w', screens: [], captured: true, done: 'd', left: 'l', where: 'x', text: 't', question: 'q', choices: ['a', 'b']});
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
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-annotation-js-"))
    try:
        (tmp / "a.js").write_text(AN_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "a.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
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
