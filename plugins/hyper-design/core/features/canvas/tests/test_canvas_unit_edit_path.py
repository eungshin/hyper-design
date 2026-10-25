"""편집 쌓는 길(view-edit-path, 셸 C5) — DOM 없는 View 를 node 로: 반영 대기 put/take 대칭(되돌리기·다시 하기),
도우미 바로 쓰기가 거절되면(Promise reject) 같은 편집이 반영 대기로 쌓이는지, 선 자르기가 반영 대기 연결은 끊기 대신 취소하는지.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'notes.js', 'view-edit-path.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, out = {};
function setup(vs, links) {
  const NS = HD.notes.store([]), log = {rows: [], toasts: [], saves: 0};
  const ED = HD.viewEditPath.mount({notes: NS, save: () => { log.saves++; }, record: op => log.rows.push(op), toast: (m, u) => log.toasts.push([m, !!u]),
                                    title: id => 'T' + id, sync: () => vs, linksOf: (from, cb) => cb(links ? links[from] || [] : null)});
  return {NS, ED, log};
}
const ids = NS => NS.list().map(n => n.id).sort();
(async () => {
  // 반영 대기(도우미 없음): put → undo(take) → redo(put) 가 같은 목록
  let {NS, ED, log} = setup(null);
  ED.linkTo('a', [{path: 'p1', text: 'go'}], 'b');
  out.queued = NS.list().map(n => [n.screen, n.op, n.to, n.note]);
  out.row = {label: log.rows[0].label, status: log.rows[0].status};
  const after = ids(NS); log.rows[0].undo(); out.undone = ids(NS).length; log.rows[0].redo(); out.redoSame = JSON.stringify(ids(NS)) === JSON.stringify(after);
  out.toast = log.toasts[0];
  ED.linkTo('a', [{path: 'p1', text: 'go', to: 'b'}], 'b'); out.same = log.toasts[1][0];
  // drops: 같이 취소한 편집은 undo 로 돌아오고 redo 로 다시 빠진다
  ({NS, ED, log} = setup(null));
  const keepNote = HD.edits.note('a', {path: 'p9', text: 'x'}, 'old', 'link', 'c'); NS.add(keepNote);
  ED.add('cancel', [], 'm', [keepNote]);
  out.dropGone = NS.list().length; log.rows[0].undo(); out.dropBack = NS.list().map(n => n.id)[0] === keepNote.id; log.rows[0].redo(); out.dropAgain = NS.list().length;
  // 바로 쓰기: 켜져 있으면 VS.write, 기록 없음 · 거절되면 같은 편집이 반영 대기로(keep) 쌓인다
  let wrote = [];
  ({NS, ED, log} = setup({on: true, write: (l, list) => { wrote.push(l); return Promise.resolve({}); }}));
  ED.linkTo('a', [{path: 'p1', text: 'go'}], 'b'); await new Promise(r => setTimeout(r, 0));
  out.instant = {wrote, queued: NS.list().length, rows: log.rows.length};
  ({NS, ED, log} = setup({on: true, write: () => Promise.reject(new Error('down'))}));
  ED.linkTo('a', [{path: 'p1', text: 'go'}], 'b'); await new Promise(r => setTimeout(r, 0));
  out.fallback = {queued: NS.list().length, rows: log.rows.map(r => r.label + ':' + r.status)};
  ({NS, ED, log} = setup({on: true, write: () => Promise.resolve({failed: [{reason: '없는 요소'}]})}));
  ED.linkTo('a', [{path: 'p1', text: 'go'}], 'b'); await new Promise(r => setTimeout(r, 0));
  out.refused = log.toasts[0][0];
  // 선 자르기: 양쪽 방향, 반영 대기 연결은 끊기 대신 취소
  ({NS, ED, log} = setup(null, {a: [{path: 'pa', text: 'A', to: 'b'}], b: [{path: 'pb', text: 'B', to: 'a'}]}));
  const pend = HD.edits.note('b', {path: 'pb', text: 'B'}, 'x', 'link', 'a'); NS.add(pend);
  ED.cutPairs([['a', 'b']]);
  out.cut = {ops: NS.list().map(n => n.screen + ':' + n.op), label: log.rows[0].label, toast: log.toasts[0][0]};
  ({NS, ED, log} = setup(null));
  ED.cutPairs([['a', 'b']], true); out.noLinks = log.toasts.map(t => t[0]);
  console.log(JSON.stringify(out));
})();
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-edit-path-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pending_edit_undo_redo_is_symmetric(out):
    assert len(out["queued"]) == 1 and out["queued"][0][:3] == ["a", "link", "b"]
    assert '"Tb"(b)' in out["queued"][0][3], "편집 문구에 도착 화면 이름(id)"
    assert out["row"] == {"label": "트리거 연결", "status": "pending"}
    assert out["undone"] == 0 and out["redoSame"], "되돌리기 = 뺌, 다시 하기 = 같은 편집 그대로"
    assert out["toast"] == ["Tb(으)로 이었어요 — 반영 대기", True]
    assert out["same"] == "이미 그 화면으로 가요"
    assert out["dropGone"] == 0 and out["dropBack"] and out["dropAgain"] == 0, "같이 취소한 편집은 되돌리면 돌아온다"


def test_instant_write_and_refused_write_falls_back_to_pending(out):
    assert out["instant"] == {"wrote": ["트리거 연결"], "queued": 0, "rows": 0}, "바로 쓰기는 반영 대기·기록 없이 VS.write"
    assert out["fallback"] == {"queued": 1, "rows": ["트리거 연결:pending"]}, "도우미가 못 받으면 같은 편집을 반영 대기로"
    assert "파일에 쓰지 못해 반영 대기로 남겼어요: 없는 요소" in out["refused"]


def test_cut_pairs_cancels_pending_link_instead_of_cutting(out):
    assert out["cut"]["ops"] == ["a:cut"], "a→b 는 끊기 메모, 반영 대기였던 b→a 는 취소(목록에서 빠짐)"
    assert out["cut"]["label"] == "선 자르기" and out["cut"]["toast"] == "1개 연결을 끊었어요 · 반영 대기 1개를 취소했어요"
    assert out["noLinks"] == ["이 화면은 연결을 알려 주지 않아요(palette.js 없음)", "끊을 연결을 찾지 못했어요"], "링크를 모르는 화면 = 알리고 빈 목록"
