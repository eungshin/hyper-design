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
out.read = [S.read({notes: [1, 2]}, 'notes'), S.read({}, 'notes'), S.read({notes: null}, 'notes')];
const st0 = {notes: [], future: 7};
const w = S.write(st0, 'notes', '[{"id":"a"}]');
out.write = {ok: w.ok, state: w.state, same: w.state === st0, untouched: st0.notes.length};
const wb = S.write(st0, 'notes', '{nope');
out.writeBad = {ok: wb.ok, same: wb.state === st0};
out.drop = [S.drop({notes: 1, busy: 2}, 'busy')];
out.body = S.body(4, {notes: [1], hidden: ['a'], future: 7, locked: ['b']}, ['notes', 'busy']);
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
