"""공용 셸(보드 전환 1단계 P1a) — 진짜 `build_canvas.py --shell`(작업 트리, 하위 프로세스) · 허브 공용 주소 `/v1/shell/<도장>/<파일>`(이 프로세스 안 허브).
브라우저 없음. 셸 뿌리·나무 뿌리는 임시 폴더(작업 트리를 나무 사본처럼 넘김)."""
import http.client, subprocess, sys, threading
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "home")]
import build_canvas as B  # noqa: E402
import code_stamp as CS  # noqa: E402
import home_server  # noqa: E402
import shell_store as SS  # noqa: E402

pytestmark = pytest.mark.area("helper")

HEX = "0123456789abcdef"
STAMP = "g:" + HEX
SHA = HEX + "0" * 24


def test_shell_mode_writes_shell_and_skeleton_without_data(tmp_path):
    dest = tmp_path / "shell"
    env = dict(__import__("os").environ, HD_CODE_STAMP=STAMP)
    r = subprocess.run([sys.executable, str(CANVAS / "build_canvas.py"), "--shell", str(dest)], env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    assert r.returncode == 0, r.stderr
    js, css = (dest / "hd-shell.js").read_text(encoding="utf-8"), (dest / "hd-shell.css").read_text(encoding="utf-8")
    sk = (dest / "skeleton.html").read_text(encoding="utf-8")
    assert all("/* hd-module: %s */" % n in js for n in B.modules()) and "/* hd-shell: canvas_template.html 본 스크립트 */" in js
    tpl, main = B.split_shell(B.TEMPLATE.read_text(encoding="utf-8"))
    assert js == B.shell_js([(n, (B.MODULES_DIR / ("%s.js" % n)).read_text(encoding="utf-8")) for n in B.modules()], main), "out 셸과 같은 내용"
    assert css == B.shell_css([f.read_text(encoding="utf-8") for f in B.CSS_FILES])
    assert CS.page_stamp(sk) == STAMP, "뼈대는 그 도장을 품는다"
    assert sk == CS.stamp_page(tpl, STAMP), "뼈대 = split_shell 첫 값 + hd-code meta 만(P1b 가 끼우는 모양)"
    assert CS.page_inputs(sk) is None, "hd-inputs 는 줄 때 끼운다"
    assert B.CSS_MARKER in sk and B.MODULES_MARKER in sk, "셸 참조 자리는 끼우는 쪽(P1b)이 채운다"
    assert '<script id="hd-data" type="application/json">{}</script>' in sk and '<noscript id="hd-links"></noscript>' in sk, "데이터 없음"
    assert main.strip()[:40] not in sk, "본 스크립트는 셸 파일에만"
    assert not (dest / "index.html").exists() and not (dest / "palette.js").exists()


def test_store_builds_with_the_real_shell_mode(tmp_path):
    """작업 트리를 그 도장의 나무 사본으로 넘겨 진짜 하위 프로세스로 만든다 — get 이 이음매 모양."""
    s = SS.ShellStore(root=tmp_path / "shell", trees=tmp_path / "none", head=lambda: (SHA, CANVAS / "build_canvas.py"))
    hit = s.ensure(STAMP)
    assert hit is not None and hit["dir"] == tmp_path / "shell" / SHA
    assert CS.page_stamp(hit["skeleton"]) == STAMP and (hit["dir"] / "hd-shell.js").stat().st_size > 100_000


def get(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.headers, r.read()
    finally:
        c.close()


def test_hub_serves_shared_shell_immutable_and_404_no_store(tmp_path):
    class Run:
        def __call__(self, script, dest, stamp):
            (dest / "hd-shell.js").write_text("/* 공용 js */", encoding="utf-8")
            (dest / "hd-shell.css").write_text("/* 공용 css */", encoding="utf-8")
            (dest / "skeleton.html").write_text(CS.stamp_page("<html><head></head></html>", stamp), encoding="utf-8")
            return 0, ""
    trees = tmp_path / "trees"
    (trees / SHA / "features" / "canvas").mkdir(parents=True)
    (trees / SHA / "features" / "canvas" / "build_canvas.py").write_text('"--shell"', encoding="utf-8")
    (trees / SHA / ".hd-ok").write_text("", encoding="utf-8")
    store = SS.ShellStore(root=trees / "shell", trees=trees, run=Run(), head=lambda: None)
    assert store.ensure(STAMP)
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=lambda o: None, restarter=lambda p: None,
                               shells=store, prebuild=SS.Prebuilder(store))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        st, h, body = get(port, "/v1/shell/%s/hd-shell.js" % STAMP)
        assert st == 200 and body == "/* 공용 js */".encode("utf-8")
        assert h.get_all("Cache-Control") == ["max-age=31536000, immutable"] and h["Content-Type"].startswith("text/javascript")
        st, h, body = get(port, "/v1/shell/g%%3A%s/hd-shell.css" % HEX)
        assert st == 200 and h["Content-Type"].startswith("text/css") and h.get_all("Cache-Control") == ["max-age=31536000, immutable"]
        for bad in ("/v1/shell/g:%s/hd-shell.js" % ("f" * 16), "/v1/shell/%s/skeleton.html" % STAMP, "/v1/shell/%s/.hd-ok" % STAMP,
                    "/v1/shell/%s/..%%2F..%%2Fhome.json" % STAMP, "/v1/shell/w:%s/hd-shell.js" % HEX, "/v1/shell/"):
            st, h, _ = get(port, bad)
            assert st == 404 and h.get_all("Cache-Control") == ["no-store"], bad
    finally:
        srv.shutdown(); srv.server_close()


def test_hub_prebuilds_with_the_shared_prebuilder(monkeypatch):
    seen = []
    monkeypatch.setattr(SS.PREBUILD, "want", lambda stamp: seen.append(stamp))
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=lambda o: None, restarter=lambda p: None)
    try:
        assert srv.registry.prebuild is SS.PREBUILD and seen == [srv.registry.code], "허브가 뜰 때 잰 도장의 셸을 미리 만든다"
    finally:
        srv.server_close()


def test_hub_project_page_uses_the_shared_shell_and_fresh_data_without_a_build(tmp_path):
    """합치기(P1a + P1b): 허브가 세션에 shell=저장소.get 을 넘긴다 — 프로젝트 페이지 = 공용 셸 주소 + 지금 데이터, 화면을 고친 뒤에도 빌드 0번."""
    import json, test_canvas_cache as TC
    s = SS.ShellStore(root=tmp_path / "shell", trees=tmp_path / "none", head=lambda: (SHA, CANVAS / "build_canvas.py"))
    assert s.ensure(STAMP)
    out = TC.make_out(tmp_path, "alpha")
    builds = []
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=lambda o: builds.append(o), restarter=lambda p: None,
                               shells=s, prebuild=SS.Prebuilder(s))
    srv.registry.current_code = lambda *a, **k: STAMP
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        sess = srv.registry._start("alpha", out, None)
        srv.registry.sessions["alpha"] = sess
        (out / "screens" / "home.html").write_text(TC.SCREEN.format(t="ZZZZ-새글"), encoding="utf-8")
        data = json.loads((out / "screens.json").read_text(encoding="utf-8")); data["screens"][0]["title"] = "바뀐 제목"
        (out / "screens.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        st, h, body = get(port, "/v1/p/alpha/")
        html = body.decode("utf-8")
        assert st == 200 and "/v1/shell/%s/hd-shell.js" % STAMP in html and "/v1/shell/%s/hd-shell.css" % STAMP in html, html[:400]
        assert "바뀐 제목" in html and builds == [], "지금 데이터를 끼우고 빌드는 하지 않는다"
    finally:
        srv.shutdown(); srv.server_close()
