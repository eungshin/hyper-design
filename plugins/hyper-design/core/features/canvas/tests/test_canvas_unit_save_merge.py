"""저장 충돌(409) 합치기(#269) Model — modules/save-merge.js 순수 함수 단위 테스트(node) + 이름 목록 지킴(#277).

AI 답(hd reply)·덮개(hd claim)가 파일 rev 를 올려 캔버스의 보내지 못한 변경이 409 를 받을 때:
보낸 이름이 서버에서 바뀌지 않았으면 서버의 다른 이름을 받고 내 값을 지켜 다시 보낸다 · 메모는 id 마다 칸끼리 합친다 ·
둘 다 바꾼 이름만 잃고, 잃은 것을 사람 말로 알린다.
"""
import json, re, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CANVAS = HERE.parent
MOD = CANVAS / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
['state-file.js', 'history.js', 'save-merge.js'].forEach(f => vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f}));
const M = globalThis.HD.saveMerge, out = {};
out.NAMES = HD.stateFile.NAMES; out.LIVE = Object.keys(HD.stateFile.LIVE); out.TRACK = HD.history.TRACK;
const note = (id, extra) => Object.assign({id: id, note: 'n-' + id, sent: true, replies: []}, extra || {});
const R1 = {kind: '반영됨', what: 'x'};

// 1. 카드를 옮기는 중(card-pos·edit-log)에 AI 답이 옴(notes 만 바뀜) → 다시 보냄, notes 는 받음
const base1 = {notes: [note('a')], 'card-pos': {}, 'edit-log': {rows: []}};
const local1 = {notes: [note('a')], 'card-pos': {pay: {dx: 20, dy: 0}}, 'edit-log': {rows: [1]}};
const server1 = {notes: [note('a', {replies: [R1]})], 'card-pos': {}, 'edit-log': {rows: []}, busy: {pay: {via: 'cli'}}};
out.move = M.resolve(['card-pos', 'edit-log'], base1, local1, server1);

// 2. 같은 이름을 둘 다 바꿈(자리) → 잃음 + 사람 말
out.both = M.resolve(['card-pos'], {'card-pos': {}}, {'card-pos': {pay: {dx: 1}}}, {'card-pos': {pay: {dx: 9}}});
out.bothText = M.lostText(out.both.lost || []);
// 2b. 둘이 같은 값으로 바꿈 = 잃지 않음
out.sameChange = M.resolve(['hidden'], {hidden: []}, {hidden: ['x']}, {hidden: ['x']});

// 3. 메모 글을 고치는 중에 그 메모에 AI 답 → 칸끼리 합침(내 글 + 서버 답)
const base3 = {notes: [note('a'), note('b')]};
const local3 = {notes: [note('a', {note: '고친 글'}), note('b'), note('c', {sent: false})]};          // a 고침 · c 새 메모
const server3 = {notes: [note('a', {replies: [R1]}), note('b', {replies: [R1]})]};
out.notesMerge = M.resolve(['notes'], base3, local3, server3);

// 4. 둘 다 replies 를 늘림(사람 답 + AI 답) → 앞이 같으면 이어 붙임
const base4 = {notes: [note('a', {replies: [R1]})]};
out.repliesBoth = M.resolve(['notes'], base4, {notes: [note('a', {replies: [R1, {kind: '사람', what: 'me'}]})]}, {notes: [note('a', {replies: [R1, {kind: 'AI', what: 'ai'}]})]});

// 5. 같은 칸을 둘 다 다르게 → 메모 잃음
out.noteClash = M.resolve(['notes'], {notes: [note('a')]}, {notes: [note('a', {note: '내 글'})]}, {notes: [note('a', {note: '다른 글'})]});
// 6. 내가 지운 메모에 AI 답 → 잃음(지우기와 답이 부딪침) · 서버가 지운 메모를 내가 안 건드림 = 지워짐
out.delVsReply = M.resolve(['notes'], {notes: [note('a')]}, {notes: []}, {notes: [note('a', {replies: [R1]})]});
out.serverDel = M.resolve(['notes'], {notes: [note('a'), note('b')]}, {notes: [note('a', {note: 'x'}), note('b')]}, {notes: [note('a')]});
// 7. 서버에만 새 메모 → 뒤에 붙음 · id 없는 메모 = 합치지 않음(잃음)
out.serverNew = M.resolve(['notes'], {notes: [note('a')]}, {notes: [note('a', {note: 'x'})]}, {notes: [note('a'), note('z')]});
out.noId = M.resolve(['notes'], {notes: [{note: 'x'}]}, {notes: [{note: 'y'}]}, {notes: [{note: 'z'}]});
// 8. 지운 이름(내 쪽 없음) — 서버가 그대로면 지움 유지
out.dropped = M.resolve(['hidden'], {hidden: ['x']}, {}, {hidden: ['x'], notes: []});
// 9. 순수 — 넣은 값을 건드리지 않는다
const frozen = JSON.stringify([base3, local3, server3]);
M.resolve(['notes'], base3, local3, server3);
out.pure = JSON.stringify([base3, local3, server3]) === frozen;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-sm-js-"))
    try:
        (tmp / "sm.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "sm.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pending_move_survives_ai_reply(out):
    m = out["move"]
    assert m["ok"], m
    assert m["state"]["card-pos"] == {"pay": {"dx": 20, "dy": 0}} and m["state"]["edit-log"] == {"rows": [1]}, "내 값은 지킨다"
    assert m["state"]["notes"][0]["replies"] == [{"kind": "반영됨", "what": "x"}], "서버의 답은 받는다"
    assert m["state"]["busy"] == {"pay": {"via": "cli"}}
    assert sorted(m["adopt"]) == ["busy", "notes"], "화면이 다시 읽을 이름 = 내 상태와 달라진 이름"


def test_same_name_changed_on_both_sides_is_lost_and_named(out):
    assert out["both"] == {"ok": False, "lost": ["card-pos"]}
    assert "카드 자리" in out["bothText"]
    assert out["sameChange"]["ok"] and out["sameChange"]["state"]["hidden"] == ["x"]


def test_notes_merge_per_id(out):
    m = out["notesMerge"]
    assert m["ok"], m
    by = {n["id"]: n for n in m["state"]["notes"]}
    assert [n["id"] for n in m["state"]["notes"]] == ["a", "b", "c"]
    assert by["a"]["note"] == "고친 글" and by["a"]["replies"] == [{"kind": "반영됨", "what": "x"}], "내 글 + 서버 답"
    assert by["b"]["replies"] == [{"kind": "반영됨", "what": "x"}] and by["c"]["sent"] is False
    assert m["adopt"] == ["notes"]


def test_both_appended_replies_join(out):
    m = out["repliesBoth"]
    assert m["ok"], m
    assert [r["what"] for r in m["state"]["notes"][0]["replies"]] == ["x", "me", "ai"]


def test_note_conflicts_are_lost(out):
    assert out["noteClash"] == {"ok": False, "lost": ["notes"]}
    assert out["delVsReply"] == {"ok": False, "lost": ["notes"]}
    assert out["noId"] == {"ok": False, "lost": ["notes"]}
    assert out["serverDel"]["ok"] and [n["id"] for n in out["serverDel"]["state"]["notes"]] == ["a"]
    assert out["serverDel"]["state"]["notes"][0]["note"] == "x"
    assert [n["id"] for n in out["serverNew"]["state"]["notes"]] == ["a", "z"]


def test_removed_name_stays_removed_and_pure(out):
    assert out["dropped"]["ok"] and "hidden" not in out["dropped"]["state"] and out["dropped"]["state"]["notes"] == []
    assert out["pure"]


def test_name_lists_agree(out):   # #277 — 이름 목록 셋이 따로 놀지 않게
    names = set(out["NAMES"])
    assert set(out["TRACK"]) <= names, "history.TRACK ⊆ state-file.NAMES"
    assert set(out["LIVE"]) <= names, "view-state-sync 가 제자리에서 받는 이름 ⊆ NAMES"
    src = (CANVAS / "canvas_template.html").read_text(encoding="utf-8")
    body = re.search(r"function adoptState\(names\) \{(.*?)\n\}", src, re.S)
    assert body, "템플릿의 adoptState 를 찾지 못함"
    handled = set(re.findall(r"has\('([a-z-]+)'\)", body.group(1)))
    assert names - {"edit-log", "busy", "note-seq"} <= handled, "adoptState 가 다루지 않는 이름: %s" % (names - {"edit-log", "busy", "note-seq"} - handled)
