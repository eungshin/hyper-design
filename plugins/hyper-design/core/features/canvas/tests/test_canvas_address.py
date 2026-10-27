"""주소 복사(R30, Figma '선택 링크 복사') — 브라우저. 같은 프로세스 도우미 · 임시 HD_HOME(프로젝트 '결제-시안' 등록) · 실제 Paseo 없음.

카드 오른쪽 클릭 → '주소 복사' = 클립보드에 'hd://결제-시안/pay  <out>/screens/pay.html · "결제"' + 토스트 "주소를 복사했어요".
요소를 고른 뒤 오른쪽 클릭 → '주소 복사' = 'hd://결제-시안/pay#<요소 경로>  … · "지금 결제하기"'(경로 = 고른 요소의 palette 경로).
Shift 로 요소 둘 → Ctrl+L = 두 줄(고른 차례) + "주소 2개를 복사했어요". 줄 규칙은 test_canvas_unit_address.py(unit), hd 쪽 읽기는 hd/tests/test_hd_address.py.
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, zoom_to  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parent / "hd"))
import helper  # noqa: E402
import hd_address  # noqa: E402

pytestmark = pytest.mark.area("tools")
SHOTS = Path(os.environ.get("HD_SHOTS_R30", Path(tempfile.gettempdir()) / "claude" / "r30-addr"))
NAME = "결제-시안"


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


@pytest.fixture()
def live(ctx, monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-addr-"))
    out = tmp / "결제 시안" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다"},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝"}]}, ensure_ascii=False), encoding="utf-8")
    home = tmp / "hd-home"; home.mkdir()
    (home / "projects.json").write_text(json.dumps({"version": 1, "projects": [
        {"name": NAME, "out": str(out), "kind": "run", "created": "2026-10-27T00:00:00", "last_opened": "2026-10-27T00:00:00"}]},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("HD_HOME", str(home))          # 진짜 ~/.hyper-design 을 읽지 않는다
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    origin = "/".join(srv.url.split("/")[:3])
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out = out
    yield pg
    pg.close()
    srv.shutdown(); srv.server_close()
    ctx.clear_permissions()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def _frame(pg, sid):
    for _ in range(100):
        f = pg.query_selector(f'.card[data-id="{sid}"] .phone iframe')
        fr = f and f.content_frame()
        if fr and fr.url.split("?")[0].endswith(f"/{sid}.html"):
            return fr
        pg.wait_for_timeout(100)
    raise AssertionError("카드 화면이 실리지 않았어요")


def _xy(pg, ph, fr, sel):
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }", sel)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    return ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc


def _clip(pg, before=None):
    """진짜 클립보드 글(권한은 fixture 가 줌 — 못 읽으면 CLIPERR 로 실패) — 바뀔 때까지 잠깐 기다림."""
    for _ in range(30):
        t = pg.evaluate("navigator.clipboard.readText().catch((e) => 'CLIPERR ' + e)")
        if t and t != before:
            return t
        pg.wait_for_timeout(100)
    return t


def _toast(pg, text):
    pg.wait_for_function("(t) => { const e = document.getElementById('toast'); return e && !e.hidden && e.textContent.includes(t); }", arg=text, timeout=3000)


def test_copy_address_from_card_and_element_menus_and_ctrl_l(live):
    pg = live
    out = pg.evaluate("window.__hdOut")
    assert Path(out) == pg.out
    ph = zoom_to(pg, "pay", 420)
    fr = _frame(pg, "pay")
    fr.wait_for_selector("button.pay", state="attached", timeout=5000)
    a, b = _xy(pg, ph, fr, "button.pay"), _xy(pg, ph, fr, "p.lead")

    # 카드 범위 — 카드 메뉴의 주소 복사(10개 이하 그대로)
    pg.mouse.click(a[0], a[1], button="right")
    pg.wait_for_selector('#cmenu:not([hidden]) button[data-act="card-addr"]', timeout=3000)
    acts = pg.evaluate("[...document.querySelectorAll('#cmenu button')].map(b => b.dataset.act)")
    assert len(acts) <= 10, acts
    assert pg.locator('#cmenu button[data-act="card-addr"] kbd').inner_text() == "Ctrl+L"
    shot(pg, "card-menu.png")
    pg.click('#cmenu button[data-act="card-addr"]')
    _toast(pg, "주소를 복사했어요")
    card = _clip(pg)
    assert card == 'hd://%s/pay  %s/screens/pay.html · "결제"' % (NAME, out), card
    assert "?hd=" not in card

    # 요소 범위 — 요소를 고른 뒤 오른쪽 클릭 → 요소 메뉴의 주소 복사
    pg.keyboard.press("Escape")
    pg.keyboard.press("v")
    pg.mouse.click(*a)
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*a)
    pg.wait_for_selector(".elbox.sel", timeout=8000)
    path = pg.evaluate("document.querySelector('.elbox.sel').dataset.key.split(':').slice(1).join(':')")
    pg.mouse.click(a[0], a[1], button="right")
    pg.wait_for_selector('#cmenu:not([hidden]) button[data-act="addr"]', timeout=3000)
    acts = pg.evaluate("[...document.querySelectorAll('#cmenu button')].map(b => b.dataset.act)")
    assert len(acts) <= 10 and not [x for x in acts if x.startswith("card-")], acts
    shot(pg, "element-menu.png")
    pg.click('#cmenu button[data-act="addr"]')
    _toast(pg, "주소를 복사했어요")
    shot(pg, "toast.png")
    el = _clip(pg, card)
    assert el.startswith("hd://%s/pay#" % NAME) and "\n" not in el, el
    got = hd_address.parse(el)
    assert got == {"project": NAME, "screen": "pay", "path": path, "file": "%s/screens/pay.html" % out, "text": "지금 결제하기"}, got

    # 여러 요소(R19 Shift) → Ctrl+L = 고른 차례로 한 줄씩
    pg.keyboard.down("Shift"); pg.mouse.click(*b); pg.keyboard.up("Shift")
    pg.wait_for_function("document.querySelectorAll('.elbox.sel').length === 2", timeout=8000)
    pg.mouse.move(10, 500)
    pg.evaluate("document.activeElement && document.activeElement.blur && document.activeElement.blur()")
    pg.keyboard.press("Control+l")
    _toast(pg, "주소 2개를 복사했어요")
    shot(pg, "toast-two.png")
    two = _clip(pg, el).splitlines()
    assert [hd_address.parse(x)["path"] for x in two][0] == path and len(two) == 2, two
    assert "p.lead" in hd_address.parse(two[1])["path"] or hd_address.parse(two[1])["text"], two
