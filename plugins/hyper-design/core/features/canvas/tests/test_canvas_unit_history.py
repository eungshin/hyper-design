"""기록 시간줄(task 33) ViewModel — modules/history.js 순수 함수 단위 테스트(node). 브라우저 없음.

줄은 닫힌 함수가 아니라 상태 차이(d)를 들고 있어 새로고침 뒤에도 줄 누르기로 오간다 · 저장·다시 읽기 뒤에도 go 가 된다 ·
크기 한도는 옛 줄의 d 부터 버리고 그 줄은 잠긴다(old) · 보낸 자리와 그 앞은 잠긴다(sent) · 화면 설정처럼 d 가 없는 지난 줄도 잠긴다(live).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

H_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/history.js', 'utf8'), {filename: 'history.js'});
const H = globalThis.HD.history, out = {};
const clone = v => JSON.parse(JSON.stringify(v));
// 가짜 저장소: 상태 이름 → 값, 줄마다 d = diff(전, 후)
let store = {'card-pos': {}, notes: [{id: 'a', note: 'x'}], hidden: []};
let s = H.initial([]);
const act = (label, f) => { const before = clone(store); f(store); s = H.reduce(s, {type: 'record', row: {label, status: 'canvas', at: '', d: H.diff(before, store)}}); };
act('move 1', st => { st['card-pos'].c1 = {dx: 10, dy: 0}; });
act('move 2', st => { st['card-pos'].c1 = {dx: 10, dy: 40}; });
act('hide', st => { st.hidden.push('c2'); });
act('memo del', st => { st.notes = []; });
act('memo add', st => { st.notes = [{id: 'b', note: 'y'}]; });
out.kinds = Object.fromEntries(s.rows.map(r => [r.label, Object.keys(r.d).map(n => n + ':' + r.d[n].k).join(',')]));
// 줄 사이 오가기 = steps 의 d 를 차례로 patch
function go(st, to, cur) {
  const p = H.steps(st, to);
  p.undo.forEach(r => Object.assign(cur, H.patch(cur, r.d, 'before')));
  p.redo.forEach(r => Object.assign(cur, H.patch(cur, r.d, 'after')));
  return H.reduce(st, {type: 'go', to});
}
let cur = clone(store);
s = go(s, 1, cur); out.at1 = clone(cur);
s = go(s, 0, cur); out.at0 = clone(cur);
s = go(s, 5, cur); out.at5same = JSON.stringify(cur) === JSON.stringify(store);
s = go(s, 3, cur); out.at3 = clone(cur);
// 저장 → 다시 읽기(새로고침): 되돌린 줄은 빠지고, 남은 줄은 잠기지 않는다
const re = H.initial(JSON.parse(JSON.stringify(H.saved(s))));
out.reload = {len: re.rows.length, at: re.at, lock: re.lock, why: H.why(re)};
let cur2 = clone(cur), r2 = go(re, 1, cur2); out.reloadAt1 = clone(cur2);
r2 = go(r2, 3, cur2); out.reloadBack = JSON.stringify(cur2) === JSON.stringify(cur);
// 보냄: 경계 = at, 그 앞은 잠김(새로고침 뒤에도)
let sent = H.reduce(H.reduce(re, {type: 'record', row: {label: 'edit', status: 'pending', at: '', d: {notes: {k: 'ids', e: {z: [null, {id: 'z'}, -1, 0]}}}}}), {type: 'sent'});
out.sent = {lock: sent.lock, at: sent.at, why: H.why(sent), status: sent.rows[3].status, canUndo: H.canUndo(sent)};
const sentRe = H.initial(JSON.parse(JSON.stringify(H.saved(sent))));
out.sentReload = {lock: sentRe.lock, why: H.why(sentRe), go0: H.reduce(sentRe, {type: 'go', to: 0}).at};
// 화면 설정(상태 차이 없음) 줄: 이번 세션은 op 로, 지난 세션이면 잠김(live)
let live = H.reduce(H.initial([]), {type: 'record', row: {label: 'line color', status: 'canvas', at: '', op: {undo() {}, redo() {}}}});
out.liveNow = live.lock;
const liveRe = H.initial(H.saved(live)); out.liveRe = {lock: liveRe.lock, why: H.why(liveRe)};
// 파일에 쓴 줄은 d 가 있어도 지난 세션이면 잠김(file)
const fileRe = H.initial([{label: 'write', status: 'file', at: '', d: {hidden: {k: 'set', e: {q: [false, true, -1, 0, 'q']}}}}]);
out.fileRe = {lock: fileRe.lock, why: H.why(fileRe)};
// 크기 한도: 새것부터 MAX_BYTES 까지만 d, 넘으면 옛 줄의 d 를 버리고 old → 잠김
const big = 'x'.repeat(Math.floor(H.MAX_BYTES / 3) - 200);
let cap = H.initial([]);
for (let i = 0; i < 5; i++) cap = H.reduce(cap, {type: 'record', row: {label: 'big ' + i, status: 'canvas', at: '', d: {notes: {k: 'val', e: {'*': [null, big]}}}}});
const capSaved = H.saved(cap), capRe = H.initial(JSON.parse(JSON.stringify(capSaved)));
out.cap = {withD: capSaved.filter(r => r.d).map(r => r.label), old: capSaved.filter(r => r.old).map(r => r.label), lock: capRe.lock, why: H.why(capRe),
           bytes: JSON.stringify(capSaved).length <= H.MAX_BYTES + 2000};
// 깨진 d 는 버린다(잠김)
const bad = H.initial([{label: 'bad', status: 'canvas', at: '', d: {notes: 'nope'}}, {label: 'ok', status: 'canvas', at: '', d: {hidden: {k: 'set', e: {q: [false, true, -1, 0, 'q']}}}}]);
out.bad = {lock: bad.lock, bad: !!bad.rows[0].bad, hasD: !!bad.rows[0].d};
// 메모 자리: 지운 메모를 되돌리면 제자리로
const nb = [{id: 'a'}, {id: 'b'}, {id: 'c'}], na = [{id: 'a'}, {id: 'c'}], nd = H.diff({notes: nb}, {notes: na});
out.order = H.patch({notes: na}, nd, 'before').notes.map(n => n.id).join('');
out.none = H.diff({hidden: ['a']}, {hidden: ['a'], busy: 1});
console.log(JSON.stringify(out));
"""


def run_js(src):
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-hist-"))
    try:
        (tmp / "h.js").write_text(src, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "h.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def out():
    return run_js(H_JS)


def test_rows_carry_state_deltas(out):
    assert out["kinds"] == {"move 1": "card-pos:obj", "move 2": "card-pos:obj", "hide": "hidden:set", "memo del": "notes:ids", "memo add": "notes:ids"}
    assert out["none"] is None, "되돌릴 이름(TRACK) 밖의 변화는 줄에 넣지 않는다"


def test_go_across_rows(out):
    assert out["at1"] == {"card-pos": {"c1": {"dx": 10, "dy": 0}}, "notes": [{"id": "a", "note": "x"}], "hidden": []}, "줄 1 = 첫 옮기기 바로 뒤"
    assert out["at0"]["card-pos"] == {} and out["at0"]["hidden"] == [], "시작 = 아무것도 안 한 상태"
    assert out["at5same"], "끝까지 다시 = 지금 상태"
    assert out["at3"] == {"card-pos": {"c1": {"dx": 10, "dy": 40}}, "notes": [{"id": "a", "note": "x"}], "hidden": ["c2"]}


def test_persist_reload_keeps_go(out):
    assert out["reload"] == {"len": 3, "at": 3, "lock": 0, "why": None}, "되돌린 줄은 저장하지 않고, 남은 줄은 새로고침 뒤에도 잠기지 않는다"
    assert out["reloadAt1"]["card-pos"] == {"c1": {"dx": 10, "dy": 0}}, "새로고침 뒤 줄 누르기 = 그 상태"
    assert out["reloadBack"], "다시 앞으로"


def test_sent_locks_and_survives_reload(out):
    assert out["sent"] == {"lock": 4, "at": 4, "why": "sent", "status": "sent", "canUndo": False}
    assert out["sentReload"] == {"lock": 4, "why": "sent", "go0": 4}, "보낸 경계는 새로고침 뒤에도"


def test_rows_without_data_lock_after_reload(out):
    assert out["liveNow"] == 0, "이번 세션 줄은 op 로 되돌린다"
    assert out["liveRe"] == {"lock": 1, "why": "live"}
    assert out["fileRe"] == {"lock": 1, "why": "file"}, "파일에 쓴 줄은 지난 세션이면 잠김"
    assert out["bad"] == {"lock": 1, "bad": True, "hasD": False}, "깨진 d 는 버리고 잠근다"


def test_cap_drops_oldest_deltas(out):
    assert out["cap"]["withD"] == ["big 2", "big 3", "big 4"] and out["cap"]["old"] == ["big 0", "big 1"], out["cap"]
    assert out["cap"]["lock"] == 2 and out["cap"]["why"] == "old" and out["cap"]["bytes"]


def test_memo_restored_in_place(out):
    assert out["order"] == "abc"
