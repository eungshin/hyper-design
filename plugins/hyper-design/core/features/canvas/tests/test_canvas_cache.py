"""캐시 머리글(보드 전환 S2) — 도우미(helper.make_server)와 허브(home_server.make_hub, /v1/p/<이름>/)가 같은 규칙(cache_policy.py)으로 답한다.
같은 정적 파일 두 번째 요청 = 304(ETag) · 같은 초 안에 다시 쓴 파일은 304 가 아니다 · 페이지·/api 는 여전히 no-store(머리글 하나) ·
?v= 셸 파일 = immutable · 오류 답 = no-store. 브라우저 없음(HTTP 만) — 이 프로세스 안 서버, 임시 HD_HOME, 작업 트리 빌드."""
import http.client, json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "home")]
import helper  # noqa: E402
import hd_client as C  # noqa: E402
import home_server  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.area("helper")

SCREEN = "<!doctype html><html><head><meta charset='utf-8'></head><body><main><h1>{t}</h1></main></body></html>"
SHELL = "/* 셸 흉내 */"


def make_out(root, name):
    out = root / name / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "home.html").write_text(SCREEN.format(t="AAAA"), encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"title": name, "groups": ["g"], "screens": [
        {"id": "home", "file": "screens/home.html", "title": name, "group": "g", "purpose": "", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = write_record.run_build(out)
    assert r.returncode == 0, r.stderr
    (out / "hd-shell.js").write_text(SHELL, encoding="utf-8")   # S3 가 쓰는 셸 파일 자리 — 여기서는 머리글만 본다
    return out


def get(port, path, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        c.request("GET", path, headers=dict({"Host": "127.0.0.1:%d" % port}, **(headers or {})))
        r = c.getresponse()
        return r.status, r.headers, r.read()
    finally:
        c.close()


def check_static(port, base, out):
    """정적 파일: 첫 답 200 + no-cache + ETag · 같은 판으로 다시 물으면 304(몸통 없음) · 같은 초 안에 다시 쓰면 200 새 내용."""
    st, h, body = get(port, base + "/screens/home.html")
    assert st == 200 and h.get_all("Cache-Control") == ["no-cache"], (st, h.get_all("Cache-Control"))
    tag, lm = h["ETag"], h["Last-Modified"]
    assert tag and b"AAAA" in body
    st, h, body = get(port, base + "/screens/home.html", {"If-None-Match": tag, "If-Modified-Since": lm})
    assert st == 304 and body == b"" and h.get_all("Cache-Control") == ["no-cache"] and h["ETag"] == tag, (st, dict(h))
    f = out / "screens" / "home.html"
    ns = f.stat().st_mtime_ns
    f.write_text(SCREEN.format(t="BBBB"), encoding="utf-8")       # 같은 크기 · 같은 초(Last-Modified 로는 못 가림)
    os.utime(f, ns=(ns, ns - ns % 1_000_000_000 + (ns % 1_000_000_000 + 400_000_000) % 1_000_000_000))
    st, h, body = get(port, base + "/screens/home.html", {"If-None-Match": tag, "If-Modified-Since": lm})
    assert st == 200 and b"BBBB" in body, "같은 초 안에 다시 쓴 화면 파일은 304 로 옛것을 보이지 않는다"
    assert h["ETag"] != tag
    st, h, _ = get(port, base + "/screens/home.html", {"If-Modified-Since": h["Last-Modified"]})
    assert st == 200, "판 표(ETag) 없이 시각만 오면 견주지 않고 새로 준다(초 단위 비교를 믿지 않음)"


def check_rest(port, base, token):
    for p in (base + "/", base + "/index.html?hd=" + token):
        st, h, body = get(port, p)
        assert st == 200 and b"hd-data" in body and h.get_all("Cache-Control") == ["no-store"], (p, st, h.get_all("Cache-Control"))
        assert h["ETag"] is None
    st, h, _ = get(port, base + "/api/state", {"X-HD-Token": token})
    assert st == 200 and h.get_all("Cache-Control") == ["no-store"]
    st, h, _ = get(port, base + "/hd-shell.js?v=abc")
    assert st == 200 and h.get_all("Cache-Control") == ["max-age=31536000, immutable"]
    st, h, _ = get(port, base + "/hd-shell.css?v=abc")              # 아직 없는 셸 파일 — 404 가 1년 남지 않게
    assert st == 404 and h.get_all("Cache-Control") == ["no-store"]
    st, h, _ = get(port, base + "/palette.js")
    assert st == 200 and h.get_all("Cache-Control") == ["no-cache"]


@pytest.fixture
def tmp():
    d = Path(tempfile.mkdtemp(prefix="hd-cache-"))
    old = os.environ.get("HD_HOME")
    os.environ["HD_HOME"] = str(d / "hd-home")
    yield d
    if old is None:
        os.environ.pop("HD_HOME", None)
    else:
        os.environ["HD_HOME"] = old
    shutil.rmtree(d, ignore_errors=True)


def test_helper_revalidates_static_and_keeps_page_fresh(tmp):
    out = make_out(tmp, "alpha")
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        check_static(port, "", out)
        check_rest(port, "", srv.token)
    finally:
        srv.shutdown(); srv.server_close()


def test_hub_session_uses_the_same_rule(tmp):
    out = make_out(tmp, "alpha")
    old_build = C.build
    C.build = lambda o: (write_record.run_build(o).returncode, "")
    C.register(C.abs_out(out))
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=lambda o: write_record.run_build(o), restarter=lambda p: None)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        r = urllib.request.Request("http://127.0.0.1:%d/api/open" % port, data=b'{"name": "alpha"}', method="POST",
                                   headers={"X-HD-Token": srv.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=120) as res:
            assert res.status == 200
        sess = srv.registry.get("alpha")
        check_static(port, "/v1/p/alpha", out)
        check_rest(port, "/v1/p/alpha", sess.token)
        st, h, _ = get(port, "/")                                    # 홈 화면 · 허브 API = no-store, 홈 정적 파일 = no-cache
        assert st == 200 and h.get_all("Cache-Control") == ["no-store"]
        st, h, _ = get(port, "/api/projects", {"X-HD-Token": srv.token})
        assert st == 200 and h.get_all("Cache-Control") == ["no-store"]
        st, h, _ = get(port, "/home.js")
        assert st == 200 and h.get_all("Cache-Control") == ["no-cache"]
        st, h, _ = get(port, "/v1/p/nobody/screens/home.html")
        assert st == 404 and h.get_all("Cache-Control") == ["no-store"]
    finally:
        srv.shutdown(); srv.server_close()
        C.build = old_build
