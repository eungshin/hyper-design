"""받는 곳 고르기 · 에이전트 상태 · 진행 줄 · 새 터미널 · 되돌리기 답(task 47-5b) — 순수 모듈(node). 브라우저 없음.

agents.menu: 접속한 에이전트(here 먼저) + Paseo 줄(같은 id 는 한 번) + 목록에 없는 지금 받는 곳(orphan) + 아무것도 없음(empty).
presence: /api/presence 답 + agent.hello/away/progress → 칩 상태(접속 중 · 진행 글 · 자리 비움).
chat.progress/line: request.sent(via) → agent.progress 글 → agent.reply, 이 요청의 메모만. 예전 claim 줄은 그대로(test_canvas_unit_chat_progress.py).
spawn: 묻는 글에 폴더 · 403 disabled = 꺼짐 설명(HD_ALLOW_SPAWN=1), 오류 덤프 아님.
undo-answer: restore 답 reverted:true = 이미 되돌림.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'agents.js', 'presence.js', 'spawn.js', 'undo-answer.js', 'live.js'])
  vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, out = {};

// ---- agents.menu
const body = {
  agents: [{id: 'pa-1', name: 'Paseo 하나', status: 'running', cwd: '/r'}, {id: 'ag-b', name: '같은 id', status: 'idle', cwd: '/r'}],
  current: 'ag-b', repo: '/r',
  connected: [
    {id: 'ag-a', name: '자리 비운 코덱스', kind: 'codex', state: 'away', listen: true, progress: null},
    {id: 'ag-b', name: '클로드', kind: 'claude', state: 'here', listen: true, progress: {text: '홈   버튼 고치는 중', screen: 'home'}},
    {id: 'ag-c', kind: 'robot', state: 'here', listen: false, progress: null},
    {name: 'id 없음'}
  ]
};
const m = HD.agents.menu(body);
out.menu = {conn: m.connected.map(c => [c.id, c.state, c.kindSay, c.current, c.progress, c.listen]), rows: m.rows.map(r => r.id),
            orphan: m.orphan, bad: m.bad, empty: m.empty};
out.orphan = HD.agents.menu({agents: [], connected: [], current: 'old-paseo'});
out.empty = HD.agents.menu({agents: [], connected: [], current: null});
out.noConnected = HD.agents.menu({agents: body.agents, current: null}).rows.map(r => r.id);

out.delivery = [['paseo', 2], ['event', 1], ['claude', 1], ['queue', 1], [null, 1]].map(([v, n]) => HD.agents.delivery(v ? {via: v} : null, n));

// ---- presence
const P = HD.presence;
let s = P.load(P.initial(), {agents: [{id: 'ag-b', name: '클로드', kind: 'claude', state: 'here', progress: null}, {bad: 1}]});
out.loadBad = s.bad; s = s.s;
out.chip0 = P.chip(s, 'ag-b');
const s1 = P.apply(s, {type: 'agent.progress', agent: 'ag-b', text: '홈 고치는 중', screen: 'home'});
out.chip1 = P.chip(s1, 'ag-b');
const s2 = P.apply(s1, {type: 'agent.away', agent: 'ag-b', name: '클로드', reason: 'lease'});
out.chip2 = P.chip(s2, 'ag-b');
const s3 = P.apply(s2, {type: 'agent.hello', agent: {id: 'ag-b', name: '클로드', kind: 'claude', state: 'here'}});
out.chip3 = P.chip(s3, 'ag-b');
out.sameOnOther = P.apply(s3, {type: 'claim', screen: 'x'}) === s3 && P.apply(s3, {type: 'agent.progress', agent: 'nobody', text: 'x'}) === s3;
out.awayUnknown = P.chip(P.apply(s3, {type: 'agent.away', agent: 'ag-z', name: '새 이름', reason: 'bye'}), 'ag-z');
out.noCurrent = P.chip(s3, null);
out.notListed = P.chip(s3, 'paseo-only');

// ---- chat progress (47-5b)
const C = HD.chat, ids = ['m1'];
const ev = (type, o) => Object.assign({id: 1, type: type, ts: 1, project: 'p'}, o);
let p = null; const seq = [];
const go = e => { p = C.progress(p, e, ['pay'], ids); seq.push(p); };
go(ev('request.sent', {to: 'ag-b', via: 'event', notes: ['zz'], text: 'x', path: 'q'}));   // 다른 요청
go(ev('request.sent', {to: 'ag-b', via: 'event', notes: ['m1'], text: 'x', path: 'q'}));
go(ev('agent.progress', {agent: 'ag-other', text: '남의 일', screen: null}));
go(ev('agent.progress', {agent: 'ag-b', text: '  홈 버튼 고치는 중 ', screen: 'pay'}));
go(ev('request.sent', {to: 'ag-b', via: 'event', notes: ['m1'], text: 'x', path: 'q'}));   // 뒤로 가지 않음
go(ev('agent.reply', {note: 'zz', kind: '반영됨', status: 'done', agent: 'ag-b', screen: 'pay'}));
go(ev('agent.reply', {note: 'm1', kind: '반영됨', status: 'done', agent: 'ag-b', screen: 'pay'}));
out.pseq = seq;
out.queued = C.progress(null, ev('request.sent', {to: null, via: 'queue', notes: ['m1'], text: 'x', path: 'q'}), [], ids);
const last = {text: '버튼 키우기', ids: ['m1'], at: 1};
const n = o => Object.assign({id: 'm1', screen: 'pay', sent: true, replies: []}, o);
const L = (note, pr) => C.line(last, () => note, () => null, false, {progress: pr, titleOf: id => id, agentName: id => ({'ag-b': '클로드'})[id] || null});
out.lines = {
  sentEvent: L(n({}), seq[1]),
  sentPaseoUnknownName: L(n({}), {step: 'sent', via: 'paseo', to: 'pa-9'}),
  sentQueue: L(n({}), out.queued),
  progress: L(n({}), seq[3]),
  replied: L(n({replies: [{kind: '반영됨', what: '버튼을 키웠어요'}]}), seq[6]),
  repliedNoText: L(n({replies: []}), {step: 'replied', kind: '일부', status: 'partial'}),
  unsentBeats: L(n({sent: false}), seq[1]),
  claimStill: L(n({}), {step: 'working', screen: 'pay'})
};

// ---- spawn
const S = HD.spawn;
out.folder = [S.folder('C:/r', 'C:/r/out'), S.folder(null, 'C:/r/out'), S.folder(null, null)];
out.ask = S.ask('codex', 'C:/r', '결제');
out.off = S.answer({status: 403, body: {error: '새 에이전트 열기는 꺼져 있어요(...)', reason: 'disabled'}});
out.token = S.answer({status: 403, body: {error: 'token'}});
out.ok = S.answer({status: 200, body: {spawned: true, via: 'paseo', agent: 'ag-new'}});
out.fail = S.answer({status: 503, body: {error: 'Paseo 를 찾을 수 없어요'}});

// ---- undo-answer
const U = HD.undoAnswer;
out.undo = [U.read({reverted: true, restored: [], changed: [], status: 200}), U.read({restored: ['pay'], changed: ['pay'], status: 200}),
            U.read({error: 'x', reason: 'changed-since'}), U.read({error: '없음'}), U.read(null)].map(r => [r.kind, r.note]);
// ---- live: 새 이벤트도 흐름에서 받는다(EventSource 는 TYPES 만 듣는다)
const LV = HD.live, r5 = LV.plan(LV.initial(), {id: 5, type: 'agent.progress', agent: 'ag-b', text: 'x'}, {});
out.live = {types: ['agent.hello', 'agent.away', 'agent.progress', 'agent.reply', 'request.sent'].every(t => LV.TYPES.indexOf(t) >= 0), last: r5.s.last, acts: r5.acts};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-recv-js-"))
    try:
        (tmp / "r.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "r.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_menu_lists_connected_first_then_paseo_without_duplicates(out):
    m = out["menu"]
    assert [c[0] for c in m["conn"]] == ["ag-c", "ag-b", "ag-a"], "접속 중(here) 먼저, 그다음 이름(없으면 id) — 자리 비움은 뒤"
    assert m["conn"][1] == ["ag-b", "here", "Claude", True, "홈 버튼 고치는 중", True]
    assert m["conn"][0][2] == "에이전트" and m["conn"][0][5] is False, "모르는 kind = 에이전트, listen 그대로"
    assert m["conn"][2][1] == "away"
    assert m["rows"] == ["pa-1"], "접속 목록에 같은 id 가 있으면 Paseo 줄에서 뺀다"
    assert m["orphan"] is None and m["bad"] == 1 and m["empty"] is False


def test_menu_keeps_old_attached_target_and_says_empty(out):
    assert out["orphan"]["orphan"] == {"id": "old-paseo", "label": "old-paseo"}, "목록에 없는 지금 받는 곳도 보인다"
    assert out["orphan"]["empty"] is False
    assert out["empty"]["empty"] is True and out["empty"]["orphan"] is None
    assert out["noConnected"] == ["pa-1", "ag-b"], "옛 도우미(connected 없음) = Paseo 줄 그대로"


def test_presence_chip_follows_hello_progress_away(out):
    assert out["loadBad"] == 1
    assert out["chip0"]["state"] == "here" and out["chip0"]["text"] == "접속 중"
    assert out["chip1"]["text"] == "홈 고치는 중"
    assert out["chip2"]["state"] == "away" and out["chip2"]["text"] == "자리 비움"
    assert out["chip3"]["state"] == "here" and out["chip3"]["text"] == "홈 고치는 중", "돌아오면 접속 중(진행 글은 남음)"
    assert out["sameOnOther"] is True, "상관없는 이벤트·모르는 id 진행 = 같은 상태"
    assert out["awayUnknown"]["name"] == "새 이름" and out["awayUnknown"]["state"] == "away"
    assert out["noCurrent"] is None and out["notListed"] is None, "받는 곳 없음·표에 없음 = 상태 모름(칩 그대로)"


def test_progress_follows_request_sent_progress_reply_of_this_request(out):
    s = out["pseq"]
    assert s[0] is None, "다른 요청의 request.sent = 무시"
    assert s[1] == {"step": "sent", "via": "event", "to": "ag-b"}
    assert s[2] == s[1], "받는 곳이 아닌 에이전트의 진행 = 무시"
    assert s[3] == {"step": "progress", "text": "홈 버튼 고치는 중", "screen": "pay", "via": "event", "to": "ag-b"}
    assert s[4] == s[3], "request.sent 가 다시 와도 뒤로 가지 않는다"
    assert s[5] == s[4], "다른 메모의 답 = 무시"
    assert s[6] == {"step": "replied", "kind": "반영됨", "status": "done", "to": "ag-b"}
    assert out["queued"] == {"step": "sent", "via": "queue", "to": None}


def test_line_words_for_via_progress_reply(out):
    L = out["lines"]
    assert L["sentEvent"] == {"stage": "sent", "text": "보냄 · 클로드 (실시간)", "req": "버튼 키우기"}
    assert L["sentPaseoUnknownName"]["text"] == "보냄 · pa-9 (Paseo)"
    assert L["sentQueue"]["stage"] == "queued" and L["sentQueue"]["text"].startswith("보냄 · 대기열")
    assert L["progress"] == {"stage": "working", "text": "AI 작업 중 · 홈 버튼 고치는 중", "req": "버튼 키우기"}
    assert L["replied"]["stage"] == "applied" and L["replied"]["text"] == "답 옴 · 버튼을 키웠어요"
    assert L["repliedNoText"]["stage"] == "partial" and L["repliedNoText"]["text"] == "답 옴 · 일부"
    assert L["unsentBeats"]["stage"] == "unsent", "보내지 못함은 이벤트보다 앞선다"
    assert L["claimStill"]["text"] == "AI 작업 중 · pay", "claim 줄(47-4b)은 그대로"


def test_spawn_asks_with_folder_and_explains_disabled(out):
    assert out["folder"] == ["C:/r", "C:/r/out", ""]
    a = out["ask"]
    assert a["title"] == "새 터미널 에이전트 열기" and a["ok"] == "열기"
    assert "Codex" in a["lines"][0] and "Paseo" in a["lines"][0] and a["lines"][1] == "일하는 폴더: C:/r"
    off = out["off"]
    assert off["ok"] is False and off["off"] is True and off["title"] == "새 터미널 열기가 꺼져 있어요"
    assert any("HD_ALLOW_SPAWN=1" in x for x in off["lines"]) and not any("(...)" in x for x in off["lines"]), "서버 오류 글을 덤프하지 않고 설명"
    assert out["token"].get("off") is None and out["token"]["ok"] is False, "다른 403(토큰) = 꺼짐 설명이 아님"
    assert out["ok"]["ok"] is True and "ag-new" in out["ok"]["msg"]
    assert out["fail"]["msg"] == "새 터미널을 열지 못했어요 — Paseo 를 찾을 수 없어요"


def test_undo_answer_reverted_is_already_undone(out):
    assert out["undo"] == [["already", "빌드 실패로 이미 되돌림"], ["done", ""], ["changed", ""], ["error", ""], ["done", ""]]


def test_live_stream_listens_to_agent_events(out):
    assert out["live"] == {"types": True, "last": 5, "acts": []}, "agent.*·request.sent 를 들어야 칩·진행 줄에 온다 — 할 일은 없고 기준 id 만"


def test_delivery_counts_event_and_claude_as_received(out):
    d = out["delivery"]
    assert [x["ok"] for x in d] == [True, True, True, False, False], "접속한 에이전트(event)·claude 도 받은 것 — 대기열이라고 하지 않는다"
    assert d[0]["text"] == "AI 에이전트에게 2건 보냈어요 — 카드에 “AI 수정 중”", "Paseo 글은 그대로"
    assert "실시간" in d[1]["text"] and d[3]["text"] is None
