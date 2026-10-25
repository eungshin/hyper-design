"""대화창 진행 줄(S2, task 47-4b) — modules/chat.js progress · line 의 이벤트 합치기(node). 브라우저 없음.

보낸 뒤 줄은 서버 이벤트를 따라간다: 보냄 → (claim) AI 작업 중 · <화면> → (screen.written ai · ai.write) 반영됨 · <화면> → (release) 끝.
요청과 상관없는 화면의 이벤트는 무시, 답(reply)이 있으면 짧게 붙인다. 손이 필요한 단계(보내지 못함 · 결정 필요)는 이벤트보다 앞선다. 한 줄, 마지막 상태.
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
const C = globalThis.HD.chat, out = {};
const title = id => ({pay: '결제', done: '완료'})[id] || id;
const ev = (type, o) => Object.assign({id: 1, type: type, ts: 1, project: 'p'}, o);
const sc = ['pay'];
let p = null; const seq = [];
const go = e => { p = C.progress(p, e, sc); seq.push(p); };
go(ev('claim', {screen: 'other', rev: 2}));
go(ev('claim', {screen: 'pay', rev: 3, by: 'a'}));
go(ev('notes.changed', {rev: 4}));
go(ev('screen.written', {screens: ['other', 'pay'], by: 'ai', rev: 1, stamp: null}));
go(ev('screen.written', {screens: ['pay'], by: 'human', rev: 1, stamp: 'S'}));
go(ev('release', {screen: 'pay', rev: 5}));
out.seq = seq;
out.aiWrite = C.progress({step: 'working', screen: 'pay'}, ev('ai.write', {screen: 'pay', seq: 1, stamp: 's', label: 'x', act: 'record'}), sc);
out.anyScreen = C.progress(null, ev('claim', {screen: 'zzz', rev: 1}), []);
out.bad = C.progress(null, null, sc);
const n = (o) => Object.assign({id: 'a', screen: 'pay', sent: true, replies: []}, o);
const last = {text: '버튼 키우기', ids: ['a'], at: 1};
const L = (note, pr, extra) => C.line(last, () => note, () => null, false, Object.assign({progress: pr, titleOf: title}, extra || {}));
out.line = {
  none: L(n({}), null),
  working: L(n({}), {step: 'working', screen: 'pay'}),
  landed: L(n({}), {step: 'landed', screen: 'pay'}),
  done: L(n({}), {step: 'done', screen: 'pay'}),
  doneReply: L(n({replies: [{kind: '반영됨', what: '버튼을 키웠어요'}]}), {step: 'done', screen: 'pay'}),
  doneAnswer: L(n({replies: [{kind: '답변', text: '네 그렇게 했어요'}]}), {step: 'done', screen: 'pay'}),
  decide: L(n({replies: [{kind: '질문', question: '어느 쪽?', choices: ['a', 'b']}]}), {step: 'done', screen: 'pay'}),
  unsent: L(n({sent: false}), {step: 'working', screen: 'pay'}),
  landedReplied: L(n({replies: [{kind: '반영됨', what: '버튼을 키웠어요'}]}), {step: 'landed', screen: 'pay'}),
  workingReplied: L(n({replies: [{kind: '반영됨', what: '버튼을 키웠어요'}]}), {step: 'working', screen: 'pay'}),
  old: C.line(last, () => n({}), () => null, false)
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chatp-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_progress_follows_events_of_the_request_screens(out):
    s = out["seq"]
    assert s[0] is None, "요청 화면이 아닌 claim = 무시"
    assert s[1] == {"step": "working", "screen": "pay"}
    assert s[2] == s[1], "notes.changed 는 단계를 바꾸지 않는다(답은 메모가 말한다)"
    assert s[3] == {"step": "landed", "screen": "pay"}, "AI 쓰기(요청 화면)"
    assert s[4] == s[3], "사람 쓰기는 AI 진행이 아니다"
    assert s[5] == {"step": "done", "screen": "pay"}
    assert out["aiWrite"] == {"step": "landed", "screen": "pay"}
    assert out["anyScreen"] == {"step": "working", "screen": "zzz"}, "화면을 모르는 요청(모든 화면) = 아무 화면"
    assert out["bad"] is None


def test_line_text_per_step(out):
    L = out["line"]
    assert L["none"]["text"].startswith("보냄")
    assert L["working"] == {"stage": "working", "text": "AI 작업 중 · 결제", "req": "버튼 키우기"}
    assert L["landed"]["stage"] == "applied" and L["landed"]["text"] == "반영됨 · 결제"
    assert L["done"]["stage"] == "done" and L["done"]["text"] == "끝"
    assert L["doneReply"]["text"] == "끝 · 버튼을 키웠어요"
    assert L["doneAnswer"]["text"] == "끝 · 답: 네 그렇게 했어요"
    assert L["landedReplied"]["text"] == "끝 · 버튼을 키웠어요", "AI 가 쓰고 모든 메모에 답했으면 끝(덮개는 캔버스가 이미 걷어 release 가 안 올 수 있다)"
    assert L["workingReplied"]["text"] == "AI 작업 중 · 결제", "아직 덮개 중이면 작업 중"


def test_hands_needed_beats_events_and_old_callers_unchanged(out):
    L = out["line"]
    assert L["decide"]["stage"] == "decide", "결정 필요는 이벤트보다 앞선다"
    assert L["unsent"]["stage"] == "unsent"
    assert L["old"]["stage"] == "sent", "progress 없이 부르면 예전 그대로"
