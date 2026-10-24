"""완료 메모 보관(#273) Model — modules/archive.js 순수 함수 단위 테스트(node). 브라우저 없음.

완료(done) 메모 중 끝난 지 30일 넘은 것 + 완료가 200개를 넘으면 오래된 것부터 넘친 것을 고른다.
보내기 전·AI 작업 중·결정 필요·일부 반영은 절대 고르지 않는다. 보관이 끝나면(ok) 보낸 그대로인 메모만 목록에서 뺀다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

AR_JS = r"""
const fs = require('fs'), vm = require('vm');
['annotation.js', 'archive.js'].forEach(f => vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f}));
const A = globalThis.HD.archive, out = {}, DAY = 86400000, NOW = Date.parse('2026-10-25T00:00:00Z');
const iso = d => new Date(NOW - d * DAY).toISOString();
const done = (id, d) => ({id, sent: true, replies: [{kind: '반영됨', at: iso(d)}]});
const list = [
  done('old', 31), done('fresh', 2),
  {id: 'confirmed', replies: [{kind: '확인', at: iso(40)}]},                               // 사람이 닫음 = 완료
  {id: 'draft', replies: [], at: iso(90)},                                                 // 보내기 전
  {id: 'working', sent: true, replies: []},
  {id: 'decide', sent: true, replies: [{kind: '질문', at: iso(90)}]},
  {id: 'partial', sent: true, replies: [{kind: '일부', at: iso(90)}]},
  {id: 'reopened', sent: true, replies: [{kind: '반영됨', at: iso(90)}, {kind: '다시', at: iso(80)}]},
  {sent: true, replies: [{kind: '반영됨', at: iso(90)}]},                                   // id 없음 = 뺄 수 없으니 고르지 않음
  {id: 'notime', sent: true, replies: [{kind: '반영됨'}]},                                 // 끝난 시각 모름 = 나이로는 고르지 않음
];
out.pick = A.pickArchive(list, NOW).map(n => n.id);
const many = []; for (let i = 0; i < 205; i++) many.push(done('d' + i, i % 10)); many.push({id: 'w', sent: true, replies: []});
many.push({id: 'nt', sent: true, replies: [{kind: '답변'}]});                             // 시각 모름 = 넘칠 때 가장 오래된 것으로
out.overflow = A.pickArchive(many, NOW).map(n => n.id);
out.empty = [A.pickArchive(null, NOW), A.pickArchive([], NOW), A.pickArchive('x', NOW)];
out.limits = [A.KEEP_DAYS, A.KEEP_DONE];
const sent = [done('a', 40), done('b', 40)];
const cur = [done('a', 40), {id: 'b', sent: true, replies: sent[1].replies.concat([{kind: '다시', at: iso(0)}])}, done('c', 1)];
out.without = A.without(cur, sent).map(n => n.id);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ar-js-"))
    try:
        (tmp / "ar.js").write_text(AR_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "ar.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_only_done_notes_older_than_30_days(out):
    assert out["pick"] == ["old", "confirmed"], "완료 + 30일 넘음만 · draft·working·decide·partial·다시 열림·id 없음·시각 모름은 남긴다"
    assert out["limits"] == [30, 200]


def test_done_beyond_newest_200_overflow(out):
    o = out["overflow"]
    assert len(o) == 6 and o[0] != "w" and "w" not in o, "완료 206개 중 넘친 6개 — 작업 중 메모는 세지도 고르지도 않는다"
    assert "nt" in o, "끝난 시각을 모르는 완료는 넘칠 때 가장 오래된 것으로"
    assert all(int(i[1:]) % 10 == 9 for i in o if i != "nt"), "가장 오래 전에 끝난 것부터"


def test_bad_input_picks_nothing(out):
    assert out["empty"] == [[], [], []]


def test_without_removes_only_unchanged_archived(out):
    assert out["without"] == ["b", "c"], "보관한 그대로인 것만 뺀다 — 그 사이 다시 연 메모는 남긴다"
