"""보내기 길(view-send, 셸 C6) — 보낸 뒤 말(HD.agents.sentSay, Model)과 View 의 보내기 한 번(보내는 중 막기·보낸 것 빼기·__hdLastHelper)을 node 로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
globalThis.window = globalThis;
for (const f of ['agents.js', 'annotation.js', 'notes.js', 'edits.js', 'view-send.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, A = HD.agents, out = {};
const n = id => ({id, screen: 's', path: 'body', text: 't', note: 'n' + id, intent: 'change', sent: false});
out.queued = A.sentSay({done: [], left: [n(1), n(2)], fw: {via: 'queue'}, res: null}, {agent: null, warn: ''});
out.agentQueued = A.sentSay({done: [], left: [n(1)], fw: {via: 'queue'}, res: null}, {agent: 'a1', warn: ''});
out.paseo = A.sentSay({done: [n(3)], left: [n(1)], fw: {via: 'paseo'}, res: null}, {agent: null, warn: ''});
out.doneOnly = A.sentSay({done: [n(3)], left: [], fw: null, res: {failed: [{reason: '정책 줄이 너무 길어요'}]}}, {agent: null, warn: '빈 레이아웃'});
out.quiet = A.sentSay({done: [n(3)], left: [], fw: null, res: null}, {agent: null, warn: ''});
// View: 보내기 한 번 — 바로 반영된 것은 빼고 남은 것은 sent, 보내는 중엔 다시 못 보냄
const els = {}, el = id => els[id] || (els[id] = {id, textContent: '', disabled: false, hidden: true, on: {}, addEventListener(t, f) { this.on[t] = f; }, dataset: {}});
const NS = HD.notes.store([n('a'), n('b')]), log = {toasts: [], sent: 0, applied: 0, saves: 0, marks: []};
let release;
const VS = {on: true, send: list => new Promise(r => { release = () => r({ok: {a: 1}, left: list.filter(x => x.id !== 'a'), done: [list[0]], fw: {via: 'queue'}, res: null}); })};
const SN = HD.viewSend.mount({$: s => el(s.replace('#', '')), notes: NS, save: () => { log.saves++; }, record: () => {}, toast: (m, u, ms) => log.toasts.push([m, ms]),
  history: {sent: () => { log.sent++; }, applied: () => { log.applied++; }}, sync: () => VS, cover: () => null, cardEl: () => null, sizes: () => null, agent: () => null, out: () => '/o'});
(async () => {
  SN.send(NS.list().slice());
  out.busy = SN.busy(); out.btnOff = els.nsend.disabled; out.msg = els.nmsg.textContent;
  release(); await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  out.after = {busy: SN.busy(), ids: NS.list().map(x => [x.id, x.sent]), sent: log.sent, applied: log.applied, last: !!window.__hdLastHelper, fw: window.__hdLastHelper.forward.via};
  out.toast = log.toasts[log.toasts.length - 1];
  out.request = SN.request([n('z')]).indexOf('/o') >= 0;
  console.log(JSON.stringify(out));
})();
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-send-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_sent_say_queue_without_terminal(js):
    q = js["queued"]
    assert q["text"] == "AI가 연결되지 않아 2건을 대기열에 저장했어요" and q["ms"] == 9000 and q["ok"] is False
    assert q["connect"]["label"] == "연결" and "hd notes" in q["connect"]["tip"] and "--paseo-agent" in q["connect"]["tip"], "알림은 한 줄 · CLI 안내는 [연결] 툴팁(R27 F04)"
    assert "hd-queue" not in q["text"] and "hd notes" not in q["text"]


def test_sent_say_agent_and_paseo(js):
    assert js["agentQueued"]["text"] == "AI 에이전트에게 보내지 못해 1건을 대기열에 저장했어요" and js["agentQueued"]["connect"]["label"] == "연결"
    assert js["paseo"]["ok"] is True and js["paseo"]["text"].startswith("바로 반영 1건 · ") and "connect" not in js["paseo"]


def test_sent_say_refused_and_warn_lead(js):
    assert js["doneOnly"]["text"] == "빈 레이아웃 · 파일에 쓰지 못함: 정책 줄이 너무 길어요 · 바로 반영 1건" and js["doneOnly"]["ms"] == 9000
    assert js["quiet"] == {"text": "바로 반영 1건", "ms": 0, "ok": False}


def test_send_blocks_while_sending_and_settles(js):
    assert js["busy"] is True and js["btnOff"] is True and js["msg"] == "보내는 중…"
    a = js["after"]
    assert a["busy"] is False and a["ids"] == [["b", True]] and a["sent"] == 1 and a["applied"] == 0
    assert a["last"] and a["fw"] == "queue"
    assert js["request"]
