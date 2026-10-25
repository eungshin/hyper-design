"""48c AI 되돌리기 — 순수 규칙(node, 브라우저 없음). HD.aiUndo(ai-undo.js, Model): 기록에 올릴 새 줄 · 기준만 잡을 때 · 되살리기 본문 · 답 풀이."""
import json, shutil, subprocess
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parents[1] / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/ai-undo.js', 'utf8'), {filename: 'ai-undo.js'});
const A = globalThis.HD.aiUndo, w = (s, l) => ({seq: 1, stamp: s, screen: 'home', label: l});
console.log(JSON.stringify({
  every: A.EVERY,
  fresh: A.fresh({s1: 1}, [w('s1', 'a'), w('s2', 'AI 반영 · 홈'), {stamp: 5, label: 'x'}, null, w('', 'y'), {stamp: 's3'}]).map(x => x.stamp),
  freshBad: [A.fresh(null, [w('s1', 'a')]).length, A.fresh({}, 'x').length, A.fresh({}, null).length],
  first: [A.first(null, 3), A.first(3, 3), A.first(3, 5), A.first(5, 2), A.first(2, 'x')],
  body: A.body('s1'),
  again: [A.again('screens/home.html?hd-mode=board', 7), A.again('screens/home.html?v=w1&hd-mode=board#x', 8), A.again('a.html', 9), A.again('', 1), A.again(null, 1)],
  out: [A.outcome({status: 200, body: {restored: ['a'], redo: 'r1'}}), A.outcome({status: 409, body: {reason: 'changed-since', error: 'x'}}),
        A.outcome({status: 404, body: {reason: 'missing'}}), A.outcome({status: 500, body: {error: '빌드 실패'}}), A.outcome({status: 200, body: {}}), A.outcome(null)]
}));
"""


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 없음")
    r = subprocess.run([NODE, "-e", JS, str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_fresh_rows_skip_seen_and_broken(res):
    assert res["fresh"] == ["s2"], "본 stamp · 글이 아닌 stamp/label · 빈 stamp 는 빼고 차례 그대로"
    assert res["freshBad"] == [1, 0, 0], "seen 이 없으면 모두 새것 · 목록이 아니면 없음"
    assert res["every"] == 2000


def test_first_means_baseline_only(res):
    assert res["first"] == [True, False, False, True, True], "처음 · 도우미가 다시 떠 seq 가 줄었음 · 깨진 seq = 기준만"


def test_restore_body_and_outcome(res):
    assert res["body"] == {"stamp": "s1", "keep": True, "notify": True}
    ok, changed, missing, err, noredo, broken = res["out"]
    assert ok == {"ok": True, "next": "r1"}, "되살린 뒤 다음 되살리기 stamp(다시 하기)"
    assert changed == {"ok": False, "msg": "그 뒤에 파일이 바뀌어 되돌릴 수 없어요"}, "직접 쓰기와 같은 409 글"
    assert missing["msg"] == "되돌릴 기록이 없어요" and err["msg"] == "되돌리지 못했어요: 빌드 실패"
    assert noredo["ok"] is False and broken["ok"] is False, "redo 없는 200 · 깨진 답 = 실패로 알림(조용히 넘기지 않음)"


def test_card_reload_url_keeps_mode_and_renews_v(res):
    assert res["again"] == ["screens/home.html?hd-mode=board&v=ai7", "screens/home.html?hd-mode=board&v=ai8#x", "a.html?v=ai9", None, None],         "카드 모드(hd-mode)는 그대로, 옛 v 는 빼고 새 v · 깨진 src = null"
