"""#254 hd claim + 화면 파일 지켜보기 — HD.busy 의 cli 덮개·덮개 글·다시 실을 카드 규칙(node) · helper.FileWatch(I/O 없음) · VIA drift. 브라우저 없음."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402
import hd_model  # noqa: E402  (helper 가 hd 폴더를 path 에 넣는다)

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/busy.js', 'utf8'), {filename: 'busy.js'});
const B = globalThis.HD.busy, out = {}, warns = [];
out.via = B.VIA;
let s = B.reduce(B.initial(), {type: 'mark', screens: [{id: 'a', file: 'screens/a.html'}], via: 'cli', now: 7});
out.cliMark = s.items.a;
out.badVia = B.reduce(B.initial(), {type: 'mark', screens: [{id: 'a', file: 'f'}], via: 'nope', now: 1}).items;
const old = ['paseo', 'queue'].map(v => B.reduce(B.initial(), {type: 'mark', screens: [{id: 'x', file: 'f'}], via: v, now: 1}).items.x);
out.old = old;
const stored = JSON.stringify({v: 1, items: {
  h: {via: 'cli', since: 1, file: 'screens/h.html', mtime: 10, by: 'agent-7', note: '버튼 고치는 중'},
  q: {via: 'queue', since: 2, file: 'screens/q.html', mtime: null},
  bad: {via: 'zzz', file: 'screens/b.html'}}});
const L = B.load(() => stored, 'K', m => warns.push(m));
out.loaded = L.items;
out.warns = warns.slice();
const based = B.reduce(B.reduce(L, {type: 'mark', screens: [{id: 'n', file: 'screens/n.html'}], via: 'cli', now: 3}), {type: 'baseline', mtimes: {'screens/n.html': 5, 'screens/h.html': 99}});
out.baseKeepsBy = based.items.h;
out.liftCli = Object.keys(B.reduce(L, {type: 'seen', mtimes: {'screens/h.html': 11}}).items);
out.looks = [B.look({via: 'paseo'}), B.look({via: 'queue'}), B.look(L.items.h), B.look({via: 'cli', by: 'a', note: '아주 긴 설명이 들어가서 칩에 다 들어가지 않는 경우를 봅니다'}), B.look({via: 'cli', note: '  두  칸   '}), B.look(null)];
out.max = B.MAX;
out.labels = [B.label(L.items.h), B.label({via: 'cli'}), B.label({via: 'cli', note: '정리'}), B.label({via: 'paseo'}), B.label({via: 'queue'})];
warns.length = 0;
out.brokenWarn = [B.load(() => '{x', 'K', m => warns.push(m)), warns.slice()];
warns.length = 0;
out.noWarnEmpty = [B.load(() => null, 'K', m => warns.push(m)), warns.length];
const busy = {v: 1, items: {c: {via: 'cli', file: 'screens/c.html', mtime: 1}}};
out.r1 = B.refresh(['a', 'b', 'a', 'c', 'zz', 7], {known: ['a', 'b', 'c'], busy: busy, skip: {b: 100}, now: 50, modal: null});
out.r2 = B.refresh(['b'], {known: ['b'], skip: {b: 100}, now: 101, modal: 'b'});
out.r3 = B.refresh(['a'], {known: ['a', 'b'], modal: 'b'});
out.r4 = B.refresh(null, {});
out.r5 = B.refresh(['m'], {known: ['m'], skip: {m: 100}, now: 50, modal: 'm'});
console.log(JSON.stringify(out));
"""


def run_js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-claim-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_busy_accepts_cli_and_keeps_old_vias():
    out = run_js()
    assert out["cliMark"] == {"via": "cli", "since": 7, "file": "screens/a.html", "mtime": None}
    assert out["badVia"] == {}, "모르는 via 는 그대로 거절"
    assert out["old"] == [{"via": "paseo", "since": 1, "file": "f", "mtime": None}, {"via": "queue", "since": 1, "file": "f", "mtime": None}], "paseo·queue 는 전과 같다"
    assert out["loaded"]["h"] == {"via": "cli", "since": 1, "file": "screens/h.html", "mtime": 10, "by": "agent-7", "note": "버튼 고치는 중"}, "by·note 를 읽어 둔다"
    assert out["loaded"]["q"] == {"via": "queue", "since": 2, "file": "screens/q.html", "mtime": None}
    assert "bad" not in out["loaded"] and any(w.startswith("[hd]") and "bad" in w for w in out["warns"]), "깨진 항목은 건너뛰고 [hd] 한 줄"
    assert out["baseKeepsBy"]["by"] == "agent-7" and out["baseKeepsBy"]["mtime"] == 10, "기준 잡기가 by·note 를 지우지 않고, 있는 기준은 그대로"
    assert out["liftCli"] == ["q"], "cli 덮개도 파일 mtime 이 기준보다 새면 걷힌다"


def test_busy_label_says_who_and_what():
    out = run_js()
    assert out["labels"] == ["agent-7 수정 중 · 버튼 고치는 중", "AI 수정 중", "AI 수정 중 · 정리", "AI 수정 중", "대기열에 있음"]


def test_busy_look_is_a_small_chip_per_via():   # task 37 — 화면을 가리지 않는 칩: 바쁨(working) · 대기열(queued)
    paseo, queue, cli, long_, spaced, none = run_js()["looks"]
    mx = run_js()["max"]
    assert paseo["kind"] == "working" and paseo["text"] == "AI 수정 중" and paseo["title"].startswith("AI 수정 중")
    assert queue["kind"] == "queued" and queue["text"] == "대기열" and queue["title"].startswith("대기열에 있음"), "대기열 = 짧은 글 · 전체는 title"
    assert cli == {"kind": "working", "text": "agent-7 수정 중 · 버튼 고치는 중", "title": cli["title"]} and cli["title"].startswith("agent-7 수정 중 · 버튼 고치는 중")
    assert long_["kind"] == "working" and len(long_["text"]) <= mx and long_["text"].endswith("…"), "긴 글은 칩 길이로 줄이고"
    assert "아주 긴 설명이 들어가서 칩에 다 들어가지 않는 경우를 봅니다" in long_["title"], "전체는 title 에"
    assert spaced["text"] == "AI 수정 중 · 두 칸", "칸은 하나로·앞뒤 자름"
    assert none is None


def test_busy_broken_value_warns_and_resets():
    out = run_js()
    assert out["brokenWarn"][0] == {"v": 1, "items": {}} and len(out["brokenWarn"][1]) == 1 and out["brokenWarn"][1][0].startswith("[hd]")
    assert out["noWarnEmpty"] == [{"v": 1, "items": {}}, 0], "값이 없음은 깨짐이 아니다"


def test_refresh_targets_only_changed_known_cards():
    out = run_js()
    assert out["r1"] == {"cards": ["a"], "modal": False}, "판에 있는 카드만 · 한 번씩 · 덮개 카드(c)는 걷는 길이 · 방금 쓴 것(b)은 건너뜀"
    assert out["r2"] == {"cards": ["b"], "modal": True}, "건너뛰기는 시간이 지나면 끝 · 크게 보기가 그 화면이면 그것도"
    assert out["r3"] == {"cards": ["a"], "modal": False}, "다른 화면을 크게 보는 중이면 크게 보기는 그대로"
    assert out["r4"] == {"cards": [], "modal": False}
    assert out["r5"] == {"cards": [], "modal": False}, "방금 쓴 화면은 크게 보기도 다시 싣지 않는다"


def test_via_list_matches_hd_model():
    assert run_js()["via"] == list(hd_model.BUSY_VIA), "canvas HD.busy.VIA 와 hd_model.BUSY_VIA 는 같다"


def test_file_watch_seq_and_changes():
    w = helper.FileWatch()
    assert w.tick({"a": 1.0, "b": 2.0}) == [] and w.changes(-1) == {"seq": 0, "changed": []}, "처음 = 기준만"
    assert w.tick({"a": 1.0, "b": 2.0}) == [] and w.seq == 0, "그대로면 seq 그대로"
    assert w.tick({"a": 1.5, "b": 2.0}) == ["a"] and w.seq == 1
    assert w.changes(0) == {"seq": 1, "changed": ["a"]} and w.changes(1) == {"seq": 1, "changed": []}
    assert w.tick({"a": 1.5, "b": None, "c": 3.0}) == ["b", "c"] and w.seq == 2, "없어짐·생김도 바뀜"
    assert w.changes(0) == {"seq": 2, "changed": ["a", "b", "c"]} and w.changes(1) == {"seq": 2, "changed": ["b", "c"]}
    assert w.tick({"a": 1.5}) == [] and w.seq == 2, "screens.json 에서 빠진 화면은 알리지 않는다"
    assert w.changes(-1) == {"seq": 2, "changed": []}


def test_file_watch_absorbs_own_writes():
    w = helper.FileWatch()
    w.tick({"a": 1.0})
    w.absorb({"a": 2.0})                              # 도우미가 스스로 쓴 뒤
    assert w.tick({"a": 2.0}) == [] and w.seq == 0, "스스로 쓴 것은 알리지 않는다"
    assert w.tick({"a": 3.0}) == ["a"] and w.seq == 1, "그 뒤 바깥에서 바뀐 것은 알린다"
