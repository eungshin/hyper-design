"""메모 창(view-memo-pop, 셸 C7) — 메모 모양 HD.annotation.make·makeId(Model)와 View 의 추가·고치기·지우기 되돌리기를 node 로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
globalThis.window = globalThis; globalThis.addEventListener = () => {}; globalThis.document = {activeElement: null}; globalThis.innerWidth = 1200; globalThis.innerHeight = 800;
for (const f of ['annotation.js', 'attach.js', 'notes.js', 'memo-batch.js', 'view-memo-pop.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, A = HD.annotation, out = {};
out.id = A.makeId(1700000000000, 0.123456789); out.idWant = (1700000000000).toString(36) + (0.123456789).toString(36).slice(2, 6);
const tg = [{path: 'a > b', text: '버튼', rect: {x: 1, y: 2, w: 3, h: 4}}, {path: 'c', text: 'C', rect: null}];
out.memo = A.make({id: 'x1', screen: 's', targets: tg, note: '고쳐', intent: 'question'});
out.scoped = A.make({id: 'x2', screen: 's', targets: tg, note: '', intent: 'change', scope: 'screen'});
out.element = A.make({id: 'x3', screen: 's', targets: tg, note: '', intent: 'change', scope: 'element'});
out.copied = out.memo.targets !== tg;
// View: 화면 전체 메모 추가 → 고치기 → 지우기(되돌리기 = 제자리)
const els = {}, el = id => els[id] || (els[id] = {id, value: '', textContent: '', hidden: true, innerHTML: '', style: {}, dataset: {}, on: {},
  addEventListener(t, f) { this.on[t] = f; }, focus() {}, contains: () => false, setAttribute() {}, getBoundingClientRect: () => ({left: 0, top: 0})});
const $ = s => /[ \[]/.test(s) ? null : el(s.replace(/^#/, '')), $$ = () => [];
const NS = HD.notes.store([]), rows = [], toasts = [];
const MP = HD.viewMemoPop.mount({$, $$, esc: x => x, notes: NS, save: () => {}, record: op => rows.push(op), toast: m => toasts.push(m), title: id => 'T' + id,
  modal: () => ({open: false, screen: null, scale: 1, box: null, picking: false, frame: null}), setScreen: () => {}, frame: () => null, cardEl: () => null,
  pins: () => {}, focusPin: () => {}});
MP.card('home');
out.open = MP.isOpen(); out.scopeDefault = MP.draft().screen;
els.pnote.value = '색 바꿔'; els.padd.on.click();
const n = NS.list()[0];
out.added = {screen: n.screen, path: n.path, note: n.note, intent: n.intent, sent: n.sent, closed: !MP.isOpen()};
MP.edit(n.id); els.pnote.value = '색 더 진하게'; els.padd.on.click();
out.edited = NS.list()[0].note;
MP.del(n.id); out.deleted = NS.list().length; rows[rows.length - 1].undo(); out.undone = NS.list().length;
MP.edit('none'); out.missing = toasts[toasts.length - 1];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-mpop-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_make_id_is_time_plus_four_random(js):
    assert js["id"] == js["idWant"]


def test_make_memo_shape(js):
    assert js["memo"] == {"id": "x1", "screen": "s", "targets": [{"path": "a > b", "text": "버튼", "rect": {"x": 1, "y": 2, "w": 3, "h": 4}}, {"path": "c", "text": "C", "rect": None}],
                          "path": "a > b", "text": "버튼", "rect": {"x": 1, "y": 2, "w": 3, "h": 4}, "note": "고쳐", "intent": "question", "sent": False}
    assert js["copied"], "targets 는 사본"


def test_make_scope_only_when_not_element(js):
    assert js["scoped"]["scope"] == "screen" and "scope" not in js["element"]


def test_pop_add_edit_delete_undo(js):
    assert js["open"] and js["scopeDefault"] == "home"
    assert js["added"] == {"screen": "home", "path": "body", "note": "색 바꿔", "intent": "change", "sent": False, "closed": True}
    assert js["edited"] == "색 더 진하게"
    assert js["deleted"] == 0 and js["undone"] == 1
    assert js["missing"] == "그 메모가 없어요 — 이미 지워졌어요"
