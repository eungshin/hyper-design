"""캐시 규칙 하나(보드 전환 S2) — cache_policy.py(순수: 주소·상태 → Cache-Control · 판 표 ETag · 같은 판인지) unit ·
modules/project-list.js(이 페이지의 GET /api/projects 받기 하나 — 같은 답을 나눠 씀) unit(node). 브라우저·서버 없음."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import cache_policy as CP  # noqa: E402

MOD = HERE.parent / "modules"
NODE = shutil.which("node")


@pytest.mark.parametrize("path", ["/", "/index.html", "/?hd=t", "/index.html?hd=t&to=x", "/home.html", ""])
def test_page_is_never_stored(path):
    assert CP.header(path) == CP.NO_STORE, "페이지 = 데이터·도장이 든 판 — 늘 새로"


@pytest.mark.parametrize("path", ["/api/state", "/api/projects", "/api/files?since=3", "/events?hd=t", "/api/events",
                                  "/agents", "/v1/sessions", "/v1/p/alpha/", "/api/x.js"])
def test_api_and_events_are_never_stored(path):
    assert CP.header(path) == CP.NO_STORE


@pytest.mark.parametrize("path", ["/palette.js", "/screens/pay.html", "/screens/a%20b.html", "/assets/logo.png", "/assets/p.JPG",
                                  "/assets/i.svg", "/fonts/x.woff2", "/components.css", "/hd-shell.js", "/hd-shell.css?x=1",
                                  "/hd-shell.js?v=", "/home.js", "/home.css"])
def test_static_files_revalidate(path):
    assert CP.header(path) == CP.REVALIDATE, "정적 파일 = 매번 묻고, 안 바뀌었으면 304"


@pytest.mark.parametrize("path", ["/hd-shell.js?v=abc123", "/hd-shell.css?v=abc123", "/hd-shell.js?hd=t&v=0f"])
def test_versioned_shell_is_immutable(path):
    assert CP.header(path) == CP.IMMUTABLE == "max-age=31536000, immutable"


def test_only_shell_files_get_immutable():
    assert CP.header("/palette.js?v=abc") == CP.REVALIDATE, "?v= 는 셸 파일만 — 다른 파일은 주소가 도장을 따르지 않는다"
    assert CP.header("/screens/hd-shell.js?v=abc") == CP.REVALIDATE, "셸 파일은 out 맨 위에만"


def test_thumbnail_keeps_long_cache():
    assert CP.header("/thumb/alpha.png?t=12") == CP.THUMB == "max-age=31536000", "허브 썸네일 — 주소의 ?t= 가 바뀌면 새로(예전 그대로)"


@pytest.mark.parametrize("path", ["/hd-shell.js?v=abc", "/palette.js", "/thumb/a.png?t=1"])
@pytest.mark.parametrize("status", [301, 403, 404, 500])
def test_errors_are_never_stored(path, status):
    assert CP.header(path, status) == CP.NO_STORE, "없는 셸 파일 404 가 1년 남지 않게"


def test_not_modified_keeps_the_rule():
    assert CP.header("/palette.js", 304) == CP.REVALIDATE
    assert CP.header("/hd-shell.js?v=a", 304) == CP.IMMUTABLE


@pytest.mark.parametrize("path", ["/README", "/x.py", "/screens.json", "/data.bin"])
def test_unknown_kinds_are_not_stored(path):
    assert CP.header(path) == CP.NO_STORE, "모르는 종류(데이터 json 포함) = 예전처럼 no-store"


def test_etag_follows_nanoseconds_and_size():
    a = CP.etag(1_700_000_000_100_000_000, 10)
    assert a == CP.etag(1_700_000_000_100_000_000, 10) and a.startswith('"') and a.endswith('"')
    assert a != CP.etag(1_700_000_000_600_000_000, 10), "같은 초 안 두 번 쓰기도 다른 판(Last-Modified 는 초 단위라 놓친다)"
    assert a != CP.etag(1_700_000_000_100_000_000, 11)


def test_same_version_reads_if_none_match():
    t = CP.etag(5, 6)
    assert CP.same(t, t) and CP.same("W/" + t, t) and CP.same('"x", ' + t, t) and CP.same("*", t)
    assert not CP.same(None, t) and not CP.same("", t) and not CP.same('"x"', t) and not CP.same(t, None)


JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/project-list.js', 'utf8'), {filename: 'project-list.js'});
const L = globalThis.HD.projectList, out = {};
let n = 0, fail = false;
const api = {on: true, call: function (m, p) { n++; out.last = [m, p];
  return fail ? Promise.reject(new Error('끊김')) : Promise.resolve({status: 200, body: [{name: 'p' + n}]}); }};
(async function () {
  const a = L.get(api), b = L.get(api), c = L.get(api);
  out.same = a === b && b === c;
  out.bodies = (await Promise.all([a, b, c])).map(r => r.body[0].name);
  out.afterLoad = n;
  out.again = (await L.get(api)).body[0].name;
  out.calls1 = n;
  out.fresh = (await L.fresh(api)).body[0].name;
  out.afterFresh = (await L.get(api)).body[0].name;
  out.calls2 = n;
  fail = true;
  out.err = await L.fresh(api).then(() => 'ok', e => e.message);
  fail = false;
  out.retry = (await L.get(api)).body[0].name;
  out.calls3 = n;
  console.log(JSON.stringify(out));
})();
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-project-list-js-"))
    try:
        (tmp / "p.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "p.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_page_load_asks_projects_once(js):
    assert js["same"] and js["bodies"] == ["p1", "p1", "p1"] and js["afterLoad"] == 1, "머리 제목·탭 바·주소 복사가 부르면 한 번만 받는다"
    assert js["last"] == ["GET", "/api/projects"]
    assert js["again"] == "p1" and js["calls1"] == 1, "다 받은 뒤 부른 것도 같은 답"


def test_fresh_asks_again_and_becomes_the_shared_answer(js):
    assert js["fresh"] == "p2" and js["afterFresh"] == "p2" and js["calls2"] == 2, "고르기 창 = 열 때마다 새로, 그 답을 나눠 쓴다"


def test_failure_is_not_kept(js):
    assert js["err"] == "끊김", "실패는 부른 쪽에 그대로(쪽마다 [hd] 경고·토스트)"
    assert js["retry"] == "p4" and js["calls3"] == 4, "실패한 답은 남기지 않는다 — 다음 부르기가 다시 받는다"
