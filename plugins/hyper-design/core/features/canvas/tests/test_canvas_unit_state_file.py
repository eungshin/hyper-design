"""프로젝트 상태 파일(#228) Model — modules/state-file.js 순수 함수 단위 테스트(node). 브라우저 없음.

프로젝트별 키만 파일로(전역 설정 키는 아님) · 깨진 스냅숏 = 브라우저 저장소만(View 가 [hd] 경고) · 파일이 있으면 파일이 이기고 캐시를 덮음 ·
파일이 없고 브라우저에 값이 있으면 한 번 올리기 · 보낼 본문은 바뀐 키만 · 모르는 키는 그대로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

SF_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/state-file.js', 'utf8'), {filename: 'state-file.js'});
const S = globalThis.HD.stateFile, out = {}, H = 'abc';
const mk = o => k => (k in o ? o[k] : null);
out.names = S.NAMES;
out.key = S.keyOf('card-pos', H);
out.nameOf = ['hd-notes:abc', 'hd-card-pos:abc', 'hd-busy:abc', 'hd-notes:zzz', 'hd-dock', 'hd-pop', 'hd-canvas-prefs', 'hd-other:abc', null].map(k => S.nameOf(k, H));
out.snapBad = [undefined, null, 5, [], {rev: 'x', state: {}}, {rev: -1, state: {}}, {rev: 1.5, state: {}}, {rev: 1, state: []}, {rev: 1}].map(r => S.snapshot(r).ok);
out.snapGood = S.snapshot({rev: 3, state: {notes: [1], future: {x: 1}}});
const local = S.fromLocal(mk({'hd-notes:abc': '[{"id":"n1"}]', 'hd-hidden:abc': '{bad', 'hd-locked:abc': '["a"]', 'hd-dock': '{"x":1}', 'hd-notes:zzz': '[9]'}), H);
out.local = local;
out.fromLocalThrows = S.fromLocal(() => { throw new Error('blocked'); }, H);
const empty = S.snapshot({rev: 0, state: {}}), file = S.snapshot({rev: 4, state: {notes: [{id: 'f1'}], future: 7}}), broken = S.snapshot('nope');
out.decide = {
  broken: S.decide(broken, local.values), none: S.decide(null, local.values),
  migrate: S.decide(empty, local.values), emptyBoth: S.decide(empty, {}), fileWins: S.decide(file, local.values)};
out.bootMigrate = S.boot(empty, local.values);
out.bootFile = S.boot(file, local.values);
out.bootLocal = S.boot(broken, local.values);
// 새로고침이 쓰기 모음(300ms)보다 빠를 때: 브라우저 캐시에는 아직 보내지 못한 메모, 페이지에 끼운 스냅숏은 그 전 rev
const stale = S.snapshot({rev: 4, state: {notes: [{id: 'f1'}], 'note-seq': {home: 1}}});
const unsent = S.fromLocal(mk({'hd-notes:abc': '[{"id":"f1"},{"id":"unsent"}]', 'hd-note-seq:abc': '{"home":2}'}), H);
// 보내지 못한 이름은 쓰기 대기 표시(hd-unsent:<hash> = {base: 그때 rev, names})로 남는다
out.unsentKey = S.unsentKey(H);
out.unsentParse = ['{"base":4,"names":["notes","note-seq","dock"]}', '{bad', '{"base":-1,"names":[]}', '{"base":2}', null].map(S.unsent);
const mark = S.unsent('{"base":4,"names":["notes","note-seq"]}');
out.bootStale = S.boot(stale, unsent.values, mark);                     // 파일이 그대로(rev 4) = 보내지 못한 값이 새것
out.bootStaleNoMark = S.boot(stale, unsent.values, null);              // 표시 없음 = 지금처럼 파일이 이김
const landed = S.snapshot({rev: 5, state: {notes: [{id: 'f1'}, {id: 'unsent'}], 'note-seq': {home: 2}}});
out.bootLanded = S.boot(landed, unsent.values, mark);                   // 닫을 때 보낸 것이 먼저 닿음 = 올릴 것 없음
const moved = S.snapshot({rev: 5, state: {notes: [{id: 'other'}], 'note-seq': {home: 2}}});
out.bootMoved = S.boot(moved, unsent.values, mark);                     // 그 사이 다른 곳이 씀 = 파일이 이김(409 규칙), 잃은 이름을 알림
const removed = S.fromLocal(mk({}), H);
out.bootRemoved = S.boot(stale, removed.values, S.unsent('{"base":4,"names":["notes"]}'));   // 보내지 못한 지우기
out.read = [S.read({notes: [1, 2]}, 'notes'), S.read({}, 'notes'), S.read({notes: null}, 'notes')];
const st0 = {notes: [], future: 7};
const w = S.write(st0, 'notes', '[{"id":"a"}]');
out.write = {ok: w.ok, state: w.state, same: w.state === st0, untouched: st0.notes.length};
const wb = S.write(st0, 'notes', '{nope');
out.writeBad = {ok: wb.ok, same: wb.state === st0};
out.drop = [S.drop({notes: 1, busy: 2}, 'busy')];
out.body = S.body(4, {notes: [1], hidden: ['a'], future: 7, locked: ['b']}, ['notes', 'busy']);
// 두 탭(#274): 새 탭이 알리고(hello) 쓰는 탭이 답(here)하면 새 탭은 읽기만 · 답이 없으면(timeout) 쓰는 탭이 되어 알림 · 누르면(click) 가져옴(take)
const T = (s, ev) => S.tab(s, ev);
const A0 = S.tabStart('a', 100), B0 = S.tabStart('b', 200);
const a1 = T(A0, {type: 'timeout'});                                   // 혼자 = 쓰는 탭, 알림
const b1 = T(B0, {type: 'hello', id: 'x', t: 50});                     // 아직 정하지 않음 — 남의 hello 에 답하지 않음
const aHello = T(a1.s, {type: 'hello', id: 'b', t: 200});              // 쓰는 탭은 새 탭에 답
const b2 = T(B0, {type: 'here', id: 'a', t: 100});                     // 답을 받은 새 탭 = 읽기만
const b2t = T(b2.s, {type: 'timeout'});                                // 늦은 timeout 은 그대로
const bClick = T(b2.s, {type: 'click'});                               // 여기서 편집하기
const aTake = T(a1.s, {type: 'take', id: 'b', t: 200});                // 다른 탭이 가져감 = 읽기만
const aHello2 = T(aTake.s, {type: 'hello', id: 'c', t: 300});          // 읽기만인 탭은 답하지 않음
// 동시에 시작해 둘 다 쓰는 탭이 됨 → 서로의 here 로 더 새 탭이 물러남(시각이 같으면 id)
const bW = T(B0, {type: 'timeout'});
const bSeesOld = T(bW.s, {type: 'here', id: 'a', t: 100});
const aSeesNew = T(a1.s, {type: 'here', id: 'b', t: 200});
const tie = T(T(S.tabStart('b', 100), {type: 'timeout'}).s, {type: 'here', id: 'a', t: 100});
const own = T(a1.s, {type: 'take', id: 'a', t: 100});                  // 제 메시지는 무시
out.tab = {
  start: A0, a1: a1, b1: b1, aHello: aHello.send, b2: b2.s.role, b2send: b2.send, b2t: b2t.s.role, bClick: bClick, aTake: [aTake.s.role, aTake.send],
  aHello2: aHello2.send, bSeesOld: bSeesOld.s.role, aSeesNew: [aSeesNew.s.role, aSeesNew.send], tie: tie.s.role, own: own.s.role,
  junk: [T(a1.s, null).s.role, T(a1.s, {type: 'nope', id: 'z'}).s.role]};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-sf-js-"))
    try:
        (tmp / "sf.js").write_text(SF_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "sf.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_only_per_project_keys_map_to_names(out):
    assert out["names"] == ["notes", "card-pos", "edit-log", "link-names", "hidden", "locked", "folders", "busy", "note-seq"]
    assert out["key"] == "hd-card-pos:abc"
    assert out["nameOf"] == ["notes", "card-pos", "busy", None, None, None, None, None, None], "다른 프로젝트·전역 설정·모르는 키는 파일로 가지 않는다"


def test_broken_snapshot_is_rejected(out):
    assert out["snapBad"] == [False] * 9
    assert out["snapGood"] == {"ok": True, "rev": 3, "state": {"notes": [1], "future": {"x": 1}}}, "모르는 키도 그대로"


def test_local_values_parsed_and_broken_flagged(out):
    assert out["local"] == {"values": {"notes": [{"id": "n1"}], "locked": ["a"]}, "bad": ["hidden"]}, "이 프로젝트 키만 · 깨진 JSON 은 bad"
    assert out["fromLocalThrows"] == {"values": {}, "bad": []}, "저장소가 막혀도 던지지 않는다"


def test_decide_migrate_file_wins_local_only(out):
    assert out["decide"] == {"broken": "local", "none": "local", "migrate": "migrate", "emptyBoth": "file", "fileWins": "file"}


def test_boot_migrate_uploads_local_once(out):
    b = out["bootMigrate"]
    assert b["mode"] == "migrate" and b["rev"] == 0 and b["cache"] == {}
    assert b["state"] == {"notes": [{"id": "n1"}], "locked": ["a"]} and b["upload"] == ["notes", "locked"]


def test_boot_file_wins_and_overwrites_cache(out):
    b = out["bootFile"]
    assert b["mode"] == "file" and b["rev"] == 4 and b["upload"] == []
    assert b["state"] == {"notes": [{"id": "f1"}], "future": 7}, "파일 값 그대로(모르는 키 포함)"
    assert b["cache"]["notes"] == '[{"id":"f1"}]' and b["cache"]["locked"] is None and b["cache"]["hidden"] is None, "캐시는 파일로 덮고 파일에 없는 키는 지운다"
    assert set(b["cache"]) == set(out["names"]), "캐시는 이 프로젝트 키만"


def test_boot_local_only_when_snapshot_broken(out):
    b = out["bootLocal"]
    assert b["mode"] == "local" and b["upload"] == [] and b["cache"] == {} and b["state"] == {"notes": [{"id": "n1"}], "locked": ["a"]}


def test_read_write_drop(out):
    assert out["read"] == ["[1,2]", None, None]
    assert out["write"] == {"ok": True, "state": {"notes": [{"id": "a"}], "future": 7}, "same": False, "untouched": 0}, "새 객체 · 원래 상태 안 바뀜"
    assert out["writeBad"] == {"ok": False, "same": True}, "JSON 이 아니면 파일로 보내지 않는다"
    assert out["drop"] == [{"notes": 1}]


def test_body_has_only_changed_keys(out):
    assert out["body"] == {"rev": 4, "state": {"notes": [1], "busy": None}}, "바뀐 키만 · 없는 값은 null(지움)"


def test_unsent_mark_key_and_parse(out):
    assert out["unsentKey"] == "hd-unsent:abc", "NAMES 가 아니라 파일로 가지 않는다"
    assert out["unsentParse"] == [{"base": 4, "names": ["notes", "note-seq"]}, None, None, None, None], "모르는 이름은 빼고 · 깨지면 null"


def test_boot_with_stale_snapshot_keeps_unsent_local_change(out):
    """300ms 안에 새로고침: 스냅숏(rev 4)이 쓰기 대기 표시의 base 와 같으면 보내지 못한 브라우저 값이 이기고 다시 올린다."""
    b = out["bootStale"]
    assert b["mode"] == "file" and b["rev"] == 4 and b["upload"] == ["notes", "note-seq"] and b["lost"] == []
    assert b["state"] == {"notes": [{"id": "f1"}, {"id": "unsent"}], "note-seq": {"home": 2}}
    assert b["cache"]["notes"] == '[{"id":"f1"},{"id":"unsent"}]' and b["cache"]["note-seq"] == '{"home":2}', "캐시도 보내지 못한 값 그대로"
    n = out["bootStaleNoMark"]
    assert n["upload"] == [] and n["cache"]["notes"] == '[{"id":"f1"}]', "표시가 없으면 파일이 이긴다"


def test_boot_unsent_mark_after_file_moved(out):
    l = out["bootLanded"]
    assert l["rev"] == 5 and l["upload"] == [] and l["lost"] == [], "닫을 때 보낸 것이 이미 닿았으면 올릴 것도 잃은 것도 없다"
    m = out["bootMoved"]
    assert m["rev"] == 5 and m["upload"] == [] and m["lost"] == ["notes"] and m["state"]["notes"] == [{"id": "other"}], "다른 곳이 썼으면 파일이 이기고 잃은 이름을 알린다"
    r = out["bootRemoved"]
    assert r["upload"] == ["notes"] and "notes" not in r["state"] and r["cache"]["notes"] is None, "보내지 못한 지우기도 다시 올린다"


def test_tab_writer_rule(out):
    """#274 — 같은 out 을 연 두 탭: 먼저 연 탭이 계속 쓰고, 새 탭은 읽기만(PUT 없음) — '여기서 편집하기'를 누르면 바뀐다."""
    t = out["tab"]
    assert t["start"] == {"id": "a", "t": 100, "role": "pending"}
    assert t["a1"] == {"s": {"id": "a", "t": 100, "role": "writer"}, "send": {"type": "here", "id": "a", "t": 100}}, "답이 없으면 쓰는 탭 + 알림"
    assert t["b1"]["send"] is None and t["b1"]["s"]["role"] == "pending"
    assert t["aHello"] == {"type": "here", "id": "a", "t": 100}, "쓰는 탭은 새 탭의 hello 에 답한다"
    assert t["b2"] == "reader" and t["b2send"] is None and t["b2t"] == "reader", "답을 받은 새 탭은 읽기만, 늦은 timeout 도 그대로"
    assert t["bClick"] == {"s": {"id": "b", "t": 200, "role": "writer"}, "send": {"type": "take", "id": "b", "t": 200}}
    assert t["aTake"] == ["reader", None], "가져가면 다른 탭은 읽기만"
    assert t["aHello2"] is None, "읽기만인 탭은 hello 에 답하지 않는다(쓰는 탭이 새로고침해도 다시 쓰는 탭)"
    assert t["bSeesOld"] == "reader" and t["aSeesNew"] == ["writer", {"type": "here", "id": "a", "t": 100}] and t["tie"] == "reader", "동시에 시작 = 먼저 연 탭(같으면 id 작은 쪽)이 이긴다"
    assert t["own"] == "writer" and t["junk"] == ["writer", "writer"], "제 메시지·모르는 메시지는 무시"
