"""테스트 브라우저의 바깥 글꼴 막기(R33, hd_testrun.block_external_fonts) — 브라우저 하나로 두 약속.

1) 막은 글꼴 요청이 Python 을 기다리지 않는다: 테스트가 time.sleep 으로 기다리는 동안에도(Playwright 가 이벤트를 처리하지 않는 동안) 글꼴 요청이 바로 끝나
   그 뒤를 잇는 페이지 요청이 서버에 닿는다. 회귀(전체 실행 4904741): 맥락 route 로 막았더니 새 글자의 글꼴 조각 요청이 Python 처리를 기다려,
   줄 이름 바꾸기 뒤 연결선 저장(PUT /api/state)이 40초 넘게 멈췄다(time.sleep 대신 pg.wait_for_timeout 이면 0.5초).
2) 바깥 글꼴 주소(cdn.jsdelivr.net 등)는 망에 나가지 않고 바로 끝난다(실패든 빈 응답이든 — 대체 글꼴로 그린다)."""
import http.server, threading, time

import pytest

from test_canvas_v2 import browser  # noqa: F401
import hd_testrun


class _Hits(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        _Hits.hits.append(self.path)
        b = b"<!doctype html><title>t</title>" if self.path == "/" else b"ok"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


@pytest.mark.area("tools")
def test_font_block_does_not_hold_page_requests_while_the_test_sleeps(browser):
    if not hd_testrun.block_external_fonts():
        pytest.skip("바깥 글꼴 막기 꺼짐(HD_TEST_ALLOW_NET=1)")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Hits)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ctx = browser.new_context()
    pg = ctx.new_page()
    try:
        _Hits.hits.clear()
        pg.goto("http://127.0.0.1:%d/" % srv.server_address[1])
        pg.evaluate("setTimeout(() => fetch('https://cdn.jsdelivr.net/gh/hd-test/none.woff2', {mode: 'no-cors'}).catch(() => 0).finally(() => fetch('/ping')), 50)")
        time.sleep(2.0)                                   # Playwright 를 부르지 않는 기다림
        assert "/ping" in _Hits.hits, ("Python 이 쉬는 동안 글꼴 요청이 끝나지 않아 뒤 요청이 서버에 닿지 않았다(막기가 Python 을 기다림)", _Hits.hits)
        took = pg.evaluate("""async () => { const t = performance.now();
          try { await fetch('https://cdn.jsdelivr.net/gh/hd-test/none.css', {mode: 'no-cors'}); } catch (e) {}
          return performance.now() - t; }""")
        assert took < 1500, ("바깥 글꼴 주소는 바로 끝난다", took)
    finally:
        ctx.close()
        srv.shutdown(); srv.server_close()
