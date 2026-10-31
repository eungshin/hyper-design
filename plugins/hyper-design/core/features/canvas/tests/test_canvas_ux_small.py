"""화면 경험 작은 것들(U3, 10-31) — 브라우저 한 흐름씩 (Playwright, test_canvas_annotations 의 작은 두 화면 판).

F7 오른쪽 도크 '연결' 칸: 고르기 전·뒤 같은 높이(빈 상태 문구, 넘치면 그 안에서 스크롤) — 메모 칸을 밀지 않는다.
F14 메모 지우기 = '지웠어요 · 되돌리기' 토스트(카드 지우기와 같이).
F15 새로고침 뒤 첫 Ctrl+Z 는 지난 세션의 '메모 지우기'를 되살리지 않는다 — 기록 패널 줄 누르기로만.
"""
import pytest

from test_canvas_v2 import browser, ctx, reload  # noqa: F401
from test_canvas_edit import fit_view, notes_of, wait_notes
from test_canvas_annotations import apage, annotate_button, PIN  # noqa: F401

GROUP = "(id) => { const g = document.getElementById(id).closest('.dk-g'); if (!g) return null; const r = g.getBoundingClientRect(); return {top: r.top, h: r.height}; }"


def links_state(pg):
    return {"links": pg.evaluate(GROUP, "pLinks"), "notes": pg.evaluate(GROUP, "pNotes"),
            "empty": pg.is_visible("#pLinks .dkp-empty"), "legend": pg.is_visible("#legend")}


@pytest.mark.area("dock", "links")
def test_links_panel_keeps_its_height_when_a_card_is_picked(apage):
    pg = apage
    fit_view(pg)
    pg.keyboard.press("v")
    pg.keyboard.press("Escape")
    before = links_state(pg)
    assert before["empty"] and not before["legend"], ("안 고르면 빈 상태 문구가 보인다(빈 탭이 아니라)", before)
    b = pg.locator('.card[data-id="pay"] .cover').bounding_box()
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + 40)
    pg.wait_for_selector("#legend:not([hidden])")
    after = links_state(pg)
    assert not after["empty"], after
    assert abs(after["links"]["h"] - before["links"]["h"]) <= 1, ("연결 칸 높이는 고르기 전과 같다", before, after)
    assert abs(after["notes"]["top"] - before["notes"]["top"]) <= 1, ("메모 칸이 밀려 내려가지 않는다", before, after)
    body = pg.evaluate("getComputedStyle(document.getElementById('pLinks').closest('.dk-body')).overflowY")
    assert body == "auto", "넘치면 연결 칸 안에서 스크롤"
    pg.keyboard.press("Escape")
    pg.keyboard.press("h")


@pytest.mark.area("notes")
def test_memo_delete_offers_undo_toast(apage):
    pg = apage
    fit_view(pg)
    annotate_button(pg, "지울 메모")
    wait_notes(pg, 1)
    pg.wait_for_selector(PIN, state="visible", timeout=4000)
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click('#thread li.focus button[data-act="del"]')
    wait_notes(pg, 0)
    pg.wait_for_function("(() => { const t = document.getElementById('toast'); return !t.hidden && t.textContent.includes('지웠어요'); })()", timeout=3000)
    pg.click("#toast button:has-text('되돌리기')")
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["note"].endswith("지울 메모")
    pg.keyboard.press("Escape")


@pytest.mark.area("notes", "tools")
def test_first_ctrl_z_after_reload_does_not_revive_last_session_memo(apage):
    pg = apage
    pg.evaluate("Object.keys(localStorage).filter(k => /^hd-(notes|edit-log|note-seq):/.test(k)).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    fit_view(pg)
    annotate_button(pg, "지난 세션 메모")
    wait_notes(pg, 1)
    pg.wait_for_selector(PIN, state="visible", timeout=4000)
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click('#thread li.focus button[data-act="del"]')
    wait_notes(pg, 0)
    pg.keyboard.press("Escape")
    reload(pg)
    assert pg.is_disabled("#undo"), "새로고침 뒤 위쪽 ↶ 는 쉰다(이번 세션에 한 일 없음)"
    pg.keyboard.press("Control+z")
    pg.wait_for_function("document.getElementById('toast').textContent.includes('기록 패널')", timeout=3000)
    pg.wait_for_timeout(200)
    assert notes_of(pg) == [], "지난 세션의 메모 지우기는 Ctrl+Z 로 되살아나지 않는다"
    pg.click('#dock .dk-tab[data-p="history"]')
    n = pg.evaluate("[...document.querySelectorAll('#hlist li[data-i]')].find(li => li.textContent.includes('메모 지우기')).dataset.i")
    pg.click(f'#hlist li[data-i="{int(n) - 1}"]')
    wait_notes(pg, 1)
    pg.evaluate("Object.keys(localStorage).filter(k => /^hd-(notes|edit-log|note-seq):/.test(k)).forEach(k => localStorage.removeItem(k))")
    reload(pg)
