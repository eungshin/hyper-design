"""#272 앱 카드 덮개 걷기 — HD.busy.shouldLift(item, event) 와 reduce 'here'(node, 브라우저 없음).

앱 카드(file = 개발 서버 주소)는 mtime 이 없어 파일 규칙으로는 걷히지 않는다. 대신:
- 그 카드 화면이 덮개 뒤에 HMR 로 바뀜(hd-here {hmr:true}) → 걷힘
- 그 카드가 덮개 뒤에 새로 실림(hd-here 로드) → 걷힘. 단 이 판에서 그 카드의 첫 로드(판을 새로 고침·처음 보임)는 걷지 않는다
- 정적 카드(파일)는 이 길로 걷지 않는다(mtime 규칙 그대로) · 덮개보다 이른 신호는 무시
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/busy.js', 'utf8'), {filename: 'busy.js'});
const B = globalThis.HD.busy, out = {};
const app = {via: 'paseo', since: 100, file: 'http://127.0.0.1:5199/hd-stage/word-header.html', mtime: null};
const stat = {via: 'paseo', since: 100, file: 'screens/a.html', mtime: 5};
out.cases = [
  B.shouldLift(app, {kind: 'hmr', at: 150}),
  B.shouldLift(app, {kind: 'load', at: 150}),
  B.shouldLift(app, {kind: 'load', at: 150, first: true}),
  B.shouldLift(app, {kind: 'hmr', at: 90}),
  B.shouldLift(app, {kind: 'load', at: 100}),
  B.shouldLift(stat, {kind: 'hmr', at: 150}),
  B.shouldLift(stat, {kind: 'load', at: 150}),
  B.shouldLift(null, {kind: 'hmr', at: 150}),
  B.shouldLift(app, null),
  B.shouldLift(app, {kind: 'nope', at: 150}),
  B.shouldLift(app, {kind: 'hmr'}),
  B.shouldLift(Object.assign({}, app, {file: 'https://localhost/x.html'}), {kind: 'hmr', at: 150})
];
out.isApp = ['http://127.0.0.1:1/a.html', 'HTTPS://x/y', 'screens/a.html', '', null].map(B.isApp);
let s = B.reduce(B.initial(), {type: 'mark', screens: [{id: 'w', file: app.file}, {id: 'a', file: 'screens/a.html'}], via: 'cli', now: 100});
const keep = B.reduce(s, {type: 'here', id: 'w', kind: 'load', at: 200, first: true});
out.firstKeeps = keep === s;
const early = B.reduce(s, {type: 'here', id: 'w', kind: 'hmr', at: 50});
out.earlyKeeps = early === s;
const gone = B.reduce(s, {type: 'here', id: 'w', kind: 'hmr', at: 200});
out.hmrLifts = Object.keys(gone.items);
out.staticKeeps = B.reduce(s, {type: 'here', id: 'a', kind: 'hmr', at: 200}) === s;
out.missingKeeps = B.reduce(s, {type: 'here', id: 'zz', kind: 'hmr', at: 200}) === s;
// 앱 카드 실패 알림(hd-here {error}, W3 #280) — 카드마다 같은 글은 한 번, 다시 잘 실리면 걷기
const E = (seen, d) => B.hereError(seen, d);
const e1 = E({}, {type: 'hd-here', screen: 'w', error: '  /src/twin/stages.js:\n  boom  '});
const e2 = E(e1.seen, {type: 'hd-here', screen: 'w', error: '/src/twin/stages.js: boom'});
const e3 = E(e2.seen, {type: 'hd-here', screen: 'w', error: '/src/settings/store.js: nope'});
const e4 = E(e3.seen, {type: 'hd-here', screen: 'w'});
const e5 = E(e4.seen, {type: 'hd-here', screen: 'w', hmr: true});
const long = E({}, {type: 'hd-here', screen: 'x', error: 'a'.repeat(400)});
out.err = {e1, e2, e3, e4, e5, longLen: Array.from(long.show).length, longEnd: long.show.slice(-1),
  bad: [E({}, null), E({}, {type: 'other', screen: 'w', error: 'x'}), E({}, {type: 'hd-here', error: 'x'}), E({}, {type: 'hd-here', screen: 'w', error: '   '}), E(null, {type: 'hd-here', screen: 'w', error: 3})]};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-busy-lift-"))
    try:
        (tmp / "s.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "s.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_should_lift_rule(out):
    assert out["cases"] == [
        True,    # HMR 뒤 = 바뀜
        True,    # 덮개 뒤 다시 실림
        False,   # 이 판에서 그 카드 첫 로드(새로 고침·처음 보임)는 AI 수정이 아님
        False,   # 덮개보다 이른 신호
        False,   # 같은 시각 = 뒤가 아님
        False,   # 정적 카드는 mtime 규칙만
        False,
        False,   # 항목 없음
        False,   # 신호 없음
        False,   # 모르는 종류
        False,   # 시각 없음
        True,    # https·localhost 도 앱 카드
    ]
    assert out["isApp"] == [True, True, False, False, False]


def test_reduce_here_lifts_only_by_rule(out):
    assert out["firstKeeps"] and out["earlyKeeps"]
    assert out["hmrLifts"] == ["a"], "앱 카드만 걷히고 정적 카드 덮개는 그대로"
    assert out["staticKeeps"] and out["missingKeeps"]


def test_here_error_once_per_card_and_text(out):
    e = out["err"]
    assert e["e1"]["show"] == "/src/twin/stages.js: boom" and e["e1"]["seen"] == {"w": "/src/twin/stages.js: boom"}, "공백 정리"
    assert e["e2"]["show"] is None and not e["e2"]["clear"], "같은 카드·같은 글 = 다시 띄우지 않음"
    assert e["e3"]["show"] == "/src/settings/store.js: nope", "글이 바뀌면 다시"
    assert e["e4"]["clear"] and e["e4"]["seen"] == {} and e["e4"]["show"] is None, "다시 잘 실리면 걷기"
    assert not e["e5"]["clear"], "없는 것은 다시 걷지 않음"
    assert e["longLen"] == 200 and e["longEnd"] == "…"
    assert all(b["show"] is None and not b["clear"] for b in e["bad"]), e["bad"]
