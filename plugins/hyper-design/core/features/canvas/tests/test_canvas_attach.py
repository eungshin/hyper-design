"""첨부 이미지(R22) — 브라우저. 도우미로 연 캔버스(받는 곳 없음 = 대기열 .hd-queue, 실제 Paseo·에이전트 없음 — paseo 는 없는 경로).

(a) 판 아래 대화창: 붙여넣기(합성 ClipboardEvent) → 썸네일 칩 → Enter → out/.hd-attach 에 파일, 보낸 요청문에 '첨부 이미지: <절대 경로>' · 앞 바이트가 이미지가 아니면 칩이 빠지고 토스트
(b) 대화 패널 안 입력창(docked): 끌어 놓기(합성 drop) → 칩 · × = 빼기
(c) 메모 창: 붙여넣기 → 칩 → 추가 = 메모 글에 경로 줄 + attach 칸 → 다시 열면 칩(썸네일은 도우미에서) → 위쪽 [보내기] 요청문에 경로
(d) 도우미 없이(file://): 붙여넣기 = '도우미로 열었을 때만' 토스트, 칩 없음
규칙(종류·크기·칩 목록·글 줄)은 test_canvas_unit_attach.py, 서버는 test_canvas_unit_attach_py.py.
"""
import json, os, re, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx, zoom_to  # noqa: F401
from test_canvas_chat import _serve, queued
from test_canvas_chat_log import served, open_page  # noqa: F401
from test_canvas_edit import notes_of, wait_notes, el_point, frame_of

pytestmark = pytest.mark.area("chat", "notes")
SHOTS = Path(os.environ.get("HD_SHOTS_R22", Path(tempfile.gettempdir()) / "claude" / "r22-impl"))
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

# 합성 붙여넣기·끌어 놓기 — 진짜 클립보드 대신 같은 DataTransfer 를 실은 이벤트(브라우저가 사람 붙여넣기에 주는 모양)
GIVE = """([sel, how, b64, name, type]) => {
  const bin = atob(b64), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  const dt = new DataTransfer(); dt.items.add(new File([u], name, {type}));
  const el = document.querySelector(sel); el.focus();
  if (how === 'paste') return el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  el.dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true}));
  return el.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
}"""


def give(pg, sel, how="paste", b64=PNG, name="shot.png", type_="image/png"):
    pg.evaluate(GIVE, [sel, how, b64, name, type_])


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def saved_chip(pg, scope, n=1):
    pg.wait_for_function(f"document.querySelectorAll('{scope} .hd-att-chip:not(.up) img').length === {n}", timeout=8000)


def attach_files(out):
    d = out / ".hd-attach"
    return sorted(p for p in d.iterdir() if not p.name.endswith(".tmp")) if d.is_dir() else []


@pytest.fixture()
def live(ctx):
    pg, errors, done = _serve(ctx)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    yield pg
    done()
    assert not errors, errors


@pytest.mark.area("chat")
def test_chat_paste_image_sends_its_path(live):
    pg = live
    pg.wait_for_selector("#hdchat .ch-box[data-hd-attach]")
    assert pg.is_visible("#hdchat .ch-clip"), "📎 단추"
    give(pg, "#hdchat textarea")
    saved_chip(pg, "#hdchat")
    files = attach_files(pg.out)
    assert len(files) == 1 and files[0].suffix == ".png" and re.match(r"^\d{8}-\d{6}-\d{6}-1\.png$", files[0].name), files
    pg.click("#hdchat textarea")
    pg.keyboard.type("이 화면처럼 맞춰 주세요")
    shot(pg, "r22-chat-bottom.png")
    # 앞 바이트가 이미지가 아니면(이름·종류는 png 라도) 서버가 거절 → 그 칩만 빠지고 토스트, 붙인 것은 그대로
    give(pg, "#hdchat textarea", b64="aGVsbG8gd29ybGQ=", name="fake.png")
    pg.wait_for_function("document.querySelector('#toast') && /PNG·JPEG·WebP·GIF/.test(document.querySelector('#toast').textContent)", timeout=8000)
    saved_chip(pg, "#hdchat")
    assert len(attach_files(pg.out)) == 1, "거절된 것은 쓰지 않았다"
    pg.keyboard.press("Enter")
    text = queued(pg)
    want = "첨부 이미지: " + str(files[0].resolve())
    assert want in text and "이 화면처럼 맞춰 주세요" in text, text
    assert pg.locator("#hdchat .hd-att-chip").count() == 0 and pg.is_hidden("#hdchat .ch-att"), "보낸 뒤 칩을 비운다"
    st = pg.evaluate("JSON.parse(JSON.stringify(window.__hdLastHelper || {}))")
    assert st, "보냄"


@pytest.mark.area("chat", "dock")
def test_docked_composer_drop_and_remove(ctx, served):
    out, srv = served
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    pg.wait_for_selector("#hdchat.docked")
    give(pg, "#hdchat textarea", how="drop")
    saved_chip(pg, "#hdchat.docked")
    shot(pg, "r22-chat-docked.png")
    pg.click("#hdchat .hd-att-chip button")
    assert pg.locator("#hdchat .hd-att-chip").count() == 0 and pg.is_hidden("#hdchat .ch-att")
    assert pg.is_visible("#hdchat.docked"), "× 는 패널·입력창을 닫지 않는다"
    pg.close()
    assert not errors, errors


@pytest.mark.area("notes")
def test_memo_popup_paste_keeps_attachment_and_sends_path(live):
    pg = live
    ph = zoom_to(pg, "pay", 420)
    fr = frame_of(pg, "pay")
    pg.keyboard.press("p")
    x, y = el_point(pg, ph, fr, "button.pay")
    pg.mouse.click(x, y)
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.is_visible("#pop .patt"), "📎 단추"
    give(pg, "#pnote")
    saved_chip(pg, "#pop")
    pg.fill("#pnote", "이 스크린샷처럼 버튼을 키워 주세요")
    shot(pg, "r22-memo-popup.png")
    pg.click("#padd")
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    path = str(attach_files(pg.out)[0].resolve())
    assert n["note"] == "이 스크린샷처럼 버튼을 키워 주세요\n첨부 이미지: " + path, n["note"]
    assert [a["path"] for a in n.get("attach", [])] == [path] and n["attach"][0]["rel"].startswith(".hd-attach/"), n
    assert pg.locator("#pop .hd-att-chip").count() == 0, "닫으면 칩을 비운다"
    # 다시 열면(고치기) 칩이 돌아오고, 글 칸에는 경로 줄 없이
    pg.click('#dock .dk-tab[data-p="notes"]')
    pg.locator("#nlist button[data-act='edit']").first.click(force=True)
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    saved_chip(pg, "#pop")
    assert pg.input_value("#pnote") == "이 스크린샷처럼 버튼을 키워 주세요"
    pg.click("#padd")
    assert notes_of(pg)[0]["note"].count("첨부 이미지: ") == 1, "고쳐 저장해도 줄은 한 번"
    pg.click("#nsend")
    text = queued(pg)
    assert "첨부 이미지: " + path in text, text


@pytest.mark.area("chat")
def test_without_helper_says_so(ctx, tmp_path):
    pg, errors, done = _serve(ctx)
    try:
        pg.goto(Path(pg.out / "index.html").resolve().as_uri())
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector("#hdchat textarea")
        give(pg, "#hdchat textarea")
        pg.wait_for_function("document.querySelector('#toast') && /도우미로 열었을 때만/.test(document.querySelector('#toast').textContent)", timeout=5000)
        assert pg.locator("#hdchat .hd-att-chip").count() == 0 and not attach_files(pg.out)
    finally:
        done()
    assert not errors, errors
