"""Q2b "AI 수정 중" 덮개 — HD.busy(Model, node) 와 도우미 /api/watch(파일 mtime 보기). 브라우저 없음."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

import pytest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
REPO = SCRIPTS.parents[4]
NODE = shutil.which("node")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402


BUSY_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/busy.js', 'utf8'), {filename: 'busy.js'});
const B = globalThis.HD.busy, out = {};
let s = B.initial();
s = B.reduce(s, {type: 'mark', screens: [{id: 'a', file: 'screens/a.html'}, {id: 'b', file: 'screens/b.html'}], via: 'paseo', now: 5});
out.marked = s;
out.files = B.files(s);
s = B.reduce(s, {type: 'baseline', mtimes: {'screens/a.html': 10, 'screens/b.html': 20}});
out.base = {a: s.items.a.mtime, b: s.items.b.mtime};
const s2 = B.reduce(s, {type: 'baseline', mtimes: {'screens/a.html': 99}});
out.baselineKeeps = s2 === s;
const eq = B.reduce(s, {type: 'seen', mtimes: {'screens/a.html': 10, 'screens/b.html': 20}});
out.equalSame = eq === s;
const one = B.reduce(s, {type: 'seen', mtimes: {'screens/a.html': 11, 'screens/b.html': 20}});
out.seenOne = Object.keys(one.items);
let n = B.reduce(B.initial(), {type: 'mark', screens: [{id: 'c', file: 'screens/c.html'}], via: 'queue', now: 1});
n = B.reduce(n, {type: 'baseline', mtimes: {'screens/c.html': null}});
const n2 = B.reduce(n, {type: 'seen', mtimes: {'screens/c.html': 1e12}});
out.nullNever = {same: n2 === n, ids: Object.keys(n2.items), mtime: n2.items.c.mtime};
const l = B.reduce(one, {type: 'lift', id: 'b'});
out.lift = Object.keys(l.items);
out.liftMissing = B.reduce(l, {type: 'lift', id: 'zz'}) === l;
out.unknown = B.reduce(l, {type: 'nope'}) === l;
const store = {};
B.save(s, (k, v) => { store[k] = v; }, 'K');
out.roundtrip = B.load(k => store[k], 'K');
out.garbage = [B.load(() => '{not json', 'K'), B.load(() => JSON.stringify({v: 2, items: {}}), 'K'),
  B.load(() => null, 'K'), B.load(() => { throw new Error('blocked'); }, 'K'), B.load(() => '[1]', 'K')];
B.save(s, () => { throw new Error('quota'); }, 'K');
out.saveNoThrow = true;
console.log(JSON.stringify(out));
"""


def test_busy_model_lifts_only_newer_files():
    """덮개 상태: 두 화면 표시 → 기준 → 한 파일만 새 mtime 이면 그 하나만 걷힘 · 같은 mtime 은 그대로 ·
    기준이 null 이면 걷히지 않음 · 걷기 · 깨진 저장값은 처음 상태 · 바뀐 게 없으면 같은 객체."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-busy-js-"))
    try:
        (tmp / "b.js").write_text(BUSY_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "b.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert out["marked"] == {"v": 1, "items": {
        "a": {"via": "paseo", "since": 5, "file": "screens/a.html", "mtime": None},
        "b": {"via": "paseo", "since": 5, "file": "screens/b.html", "mtime": None}}}
    assert out["files"] == ["screens/a.html", "screens/b.html"]
    assert out["base"] == {"a": 10, "b": 20}
    assert out["baselineKeeps"], "이미 잡은 기준은 바꾸지 않는다"
    assert out["equalSame"], "같은 mtime 이면 아무것도 걷지 않고 같은 객체"
    assert out["seenOne"] == ["b"], "새 mtime 인 a 만 걷힘"
    assert out["nullNever"] == {"same": True, "ids": ["c"], "mtime": None}, "기준이 null 이면 걷히지 않는다"
    assert out["lift"] == []
    assert out["liftMissing"] and out["unknown"]
    assert out["roundtrip"]["items"]["a"]["mtime"] == 10 and set(out["roundtrip"]["items"]) == {"a", "b"}
    assert all(g == {"v": 1, "items": {}} for g in out["garbage"]), out["garbage"]
    assert out["saveNoThrow"]


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-helper-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _post(url, body, token=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    if token:
        req.add_header("X-HD-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def test_helper_watch_reports_mtimes(out):
    """/api/watch: 있는 파일 → float mtime, 없는 파일 · out 밖 → null, 토큰 없으면 403, 잘못된 몸 → 200 {mtimes:{}}."""
    real = next(p for p in sorted((out / "screens").glob("*.html")))
    rel = real.relative_to(out).as_posix()
    (out.parent / "outside.txt").write_text("x", encoding="utf-8")
    files = [rel, "screens/nope.html", "../outside.txt"]
    res = helper.watch(out, files)["mtimes"]
    assert isinstance(res[rel], float) and res[rel] == real.stat().st_mtime
    assert res["screens/nope.html"] is None and res["../outside.txt"] is None, "없는 파일 · out 밖은 null"
    assert helper.watch(out, "nope") == {"mtimes": {}}

    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = srv.url.split("/index.html")[0]
    try:
        assert _post(base + "/api/watch", {"files": files})[0] == 403, "토큰 없으면 거절"
        code, body = _post(base + "/api/watch", {"files": files}, srv.token)
        assert code == 200 and body["mtimes"][rel] == res[rel], body
        assert body["mtimes"]["screens/nope.html"] is None and body["mtimes"]["../outside.txt"] is None
        assert _post(base + "/api/watch", {"files": "screens/x.html"}, srv.token) == (200, {"mtimes": {}})
        assert _post(base + "/api/watch", [1, 2], srv.token) == (200, {"mtimes": {}})
        assert _post(base + "/api/watch", {}, srv.token) == (200, {"mtimes": {}})
    finally:
        srv.shutdown(); srv.server_close()
