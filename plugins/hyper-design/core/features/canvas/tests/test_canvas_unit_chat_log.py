"""대화 패널(S3) Model — modules/chat-log.js(node). 브라우저 없음.

서버 기록 → 턴(오래된 것 위) · 보일 줄(보냄 · 진행 · 답 · AI 반영 · 빌드 완료/실패 · 되돌림) · 턴 상태 · 닿은 화면 · 되돌릴 stamp ·
자동 스크롤 · 터미널 대화(S3b 모양) 섞기 · 같은 요청 한 번만.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'chat-log.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const L = globalThis.HD.chatLog, out = {};
const T = 1000000;
let n = 0; const r = (turn, kind, o, at) => Object.assign({seq: ++n, at: at == null ? T + n : at, turn: turn, kind: kind}, o || {});
const recs = [
  r(1, 'ask', {text: '버튼 키워', chips: ['결제'], screens: ['pay'], agent: 'Claude A', notes: ['n1']}),
  r(1, 'sent', {notes: ['n1'], to: 'ag1', via: 'event', text: '# 요청\n버튼'}),
  r(1, 'built', {screens: ['pay']}),                                  // AI 쓰기 전 빌드 = 안 보임
  r(1, 'progress', {text: '파일 읽는 중', screen: 'pay'}),
  r(1, 'write', {screen: 'pay', label: 'AI 반영 · 결제', stamp: 'S1'}),
  r(1, 'built', {screens: ['pay']}),
  r(1, 'write', {screen: 'done', label: 'AI 반영 · 완료', stamp: 'S2'}),
  r(1, 'reply', {note: 'n1', rkind: '반영됨', status: 'done', text: '버튼을 키웠어요', screen: 'pay'}),
  r(6, 'sent', {notes: ['n9'], via: 'queue', text: '# hyper-design 요청\n\n- 제목 바꾸기'}),
];
const ts = L.turns(recs, T + 100);
out.t1 = {ask: ts[0].ask, lines: ts[0].lines.map(l => l.kind + ':' + l.text + ':' + l.tone), state: ts[0].state, screens: ts[0].screens, stamps: ts[0].stamps, undoable: ts[0].undoable};
out.t2 = {ask: ts[1].ask, lines: ts[1].lines.map(l => l.text), state: ts[1].state, undoable: ts[1].undoable};
out.order = ts.map(t => t.id);
const one = (rs, now) => L.turns(rs, now == null ? T + 100 : now).map(t => t.state);
n = 0;
out.states = {
  running: one([r(1, 'ask', {text: 'a'}), r(1, 'sent', {via: 'event'})]),
  queuedProgress: one([r(1, 'sent', {via: 'queue'}), r(1, 'progress', {text: 'x'})]),
  idle: one([r(1, 'sent', {via: 'event'}, T)], T + L.IDLE_MS + 1),
  older: one([r(1, 'sent', {via: 'event'}), r(2, 'sent', {via: 'event'})]),
  failed: one([r(1, 'sent', {via: 'event'}), r(1, 'write', {stamp: 'S'}), r(1, 'failed', {reason: '깨짐'})]),
  fixed: one([r(1, 'sent', {via: 'event'}), r(1, 'failed', {reason: '깨짐'}), r(1, 'write', {stamp: 'S'})]),
  decide: one([r(1, 'sent', {via: 'event'}), r(1, 'reply', {status: 'decide', text: '어느 쪽?'})]),
  undone: one([r(1, 'sent', {via: 'event'}), r(1, 'write', {stamp: 'S'}), r(1, 'reply', {status: 'done'}), r(1, 'undone', {})]),
};
n = 0;
const fl = L.turns([r(1, 'failed', {reason: 'x'.repeat(300)})], T)[0];
out.failLine = [fl.lines[0].tone, fl.lines[0].text.length < 200, fl.ask];
out.undoRunning = L.turns([r(1, 'sent', {via: 'event'}), r(1, 'write', {stamp: 'S'})], T + 50)[0].undoable;
out.parse = [L.parse({seq: 3, records: [{seq: 1, at: 1, turn: 1, kind: 'ask'}, {seq: 'x'}, {seq: 2, at: 1, turn: 1, kind: 'zzz'}]}), L.parse({records: []}), L.parse(null)];
out.merge = L.merge([{seq: 2, at: 1, turn: 1, kind: 'ask'}], [{seq: 1, at: 1, turn: 1, kind: 'sent'}, {seq: 2, at: 1, turn: 1, kind: 'ask', text: 'new'}]).map(x => x.seq + (x.text || ''));
out.stick = [L.stick(500, 1000, 480), L.stick(400, 1000, 480), L.stick(0, 100, 480)];
// 터미널 대화(S3b)
const E = (id, role, text, at) => ({id, role, text, at});
out.pt = [L.parseTranscript({entries: [E('a', 'user', 'hi', 5), E('b', 'bot', 'x', 6), {id: 'c'}], cursor: 'k', source: 'claude'}), L.parseTranscript({}), L.parseTranscript({entries: []}).source];
out.me = L.mergeEntries([E('a', 'user', 'old', 5), E('b', 'assistant', 'b', 3)], [E('a', 'user', 'new', 5), E('c', 'tool', 't', 4)]).map(e => e.id + e.text);
const ents = [E('u1', 'user', '버튼 키워 주세요 — 버튼 키워', T + 1), E('u2', 'user', '# 요청 버튼 그리고 더', T + 2), E('u3', 'user', '다른 질문', T + 3), E('a1', 'assistant', '네', T + 4)];
out.echo = L.echo(ents, ts).map(e => e.id);
out.tl = L.timeline(ts, [E('x', 'assistant', 'early', T - 5), E('y', 'user', 'mid', T + 8), E('z', 'tool', 'late', T + 999)]).map(i => i.type === 'turn' ? 't' + i.turn.id : i.entry.id);
out.ev = [L.entryView(E('t', 'tool', 'Read screens/pay.html\nmore', 1)), L.entryView(E('u', 'user', 'hi', 1)).label, L.entryView(E('a', 'assistant', 'ok', 1)).label];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chatlog-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_turn_lines_in_order(out):
    t = out["t1"]
    assert t["ask"] == {"text": "버튼 키워", "chips": ["결제"], "screens": ["pay"], "agent": "Claude A", "fromRequest": False}
    assert t["lines"] == ["sent:보냄 · Claude A (실시간):muted", "progress:파일 읽는 중:muted", "write:AI 반영 · 결제:ok", "built:빌드 완료:muted",
                          "write:AI 반영 · 완료:ok", "reply:버튼을 키웠어요:"], "AI 쓰기 앞의 빌드 줄은 숨김, 받는 곳 이름은 보낼 때의 알약"
    assert t["state"] == "done" and t["screens"] == ["pay", "done"]
    assert t["stamps"] == ["S2", "S1"] and t["undoable"], "되돌리기 = AI 쓰기 stamp, 새것 먼저"


def test_turn_without_ask_uses_request_first_line(out):
    t = out["t2"]
    assert t["ask"]["text"] == "hyper-design 요청" and t["ask"]["fromRequest"]
    assert t["lines"] == ["보냄 · 대기열 — 읽는 에이전트를 기다려요"] and t["state"] == "queued" and not t["undoable"]
    assert out["order"] == [1, 6], "오래된 턴이 위"


def test_turn_states(out):
    s = out["states"]
    assert s["running"] == ["running"]
    assert s["queuedProgress"] == ["running"], "대기열이어도 진행이 오면 작업 중"
    assert s["idle"] == ["done"], "10분 조용하면 끝"
    assert s["older"] == ["done", "running"], "지난 턴은 끝"
    assert s["failed"] == ["failed"] and s["fixed"] == ["running"], "실패 뒤 다시 쓰면 실패가 아님"
    assert s["decide"] == ["decide"] and s["undone"] == ["undone"]


def test_failed_line_and_undo_rules(out):
    assert out["failLine"] == ["red", True, None], "빨간 줄 · 이유는 짧게 · 요청 없는 시스템 턴"
    assert out["undoRunning"] is False, "작업 중인 턴은 되돌리지 않는다"


def test_parse_merge_stick(out):
    ok, none1, none2 = out["parse"]
    assert ok == {"seq": 3, "records": [{"seq": 1, "at": 1, "turn": 1, "kind": "ask"}], "reset": False} and none1 is None and none2 is None
    assert out["merge"] == ["1", "2new"], "같은 seq 는 뒤의 것 하나"
    assert out["stick"] == [True, False, True], "맨 아래 24px 안이면 따라감, 올려 읽는 중이면 그대로"


def test_transcript_shape_and_merge(out):
    ok, bad, src = out["pt"]
    assert [e["id"] for e in ok["entries"]] == ["a"] and ok["cursor"] == "k" and ok["source"] == "claude"
    assert bad is None and src == "none"
    assert out["me"] == ["bb", "ct", "anew"], "id 하나씩(뒤의 것), at 차례"


def test_transcript_echo_and_timeline(out):
    assert out["echo"] == ["u3", "a1"], "캔버스 요청(글 또는 요청문 앞부분)이 터미널에도 찍힌 줄은 한 번만"
    assert out["tl"] == ["x", "t1", "y", "t6", "z"], "턴과 터미널 줄은 시간 차례"
    tool, user, asst = out["ev"]
    assert tool["role"] == "tool" and tool["label"] == "도구 · Read screens/pay.html" and "more" in tool["text"]
    assert user == "터미널에서" and asst == ""
