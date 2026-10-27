"""여러 화면에 같은 메모(modules/memo-batch.js + 셸 선택 막대·메모 창) — 브라우저.

카드 두 장 고르기 → 선택 막대 [메모] → 범위는 '고른 화면 2개'·'모든 화면'만 → [추가] = 화면마다 메모 하나(같은 batch, 화면 전체),
되돌리기 한 번 = 둘 다 빠짐.
"""
import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_edit import dpage, fit_view, visible_cover, notes_of, wait_notes, picked, selbar  # noqa: F401


def pick_two(pg):
    fit_view(pg)
    p = visible_cover(pg)
    q = visible_cover(pg, skip=[p["id"]])
    pg.mouse.click(p["x"], p["y"])
    pg.wait_for_timeout(150)
    pg.keyboard.press("v")
    pg.keyboard.down("Shift"); pg.mouse.click(q["x"], q["y"]); pg.keyboard.up("Shift")
    pg.wait_for_timeout(150)
    assert sorted(picked(pg)) == sorted([p["id"], q["id"]])
    return p["id"], q["id"]


@pytest.mark.area("tools", "notes")
def test_two_cards_one_memo_goes_to_each_screen_and_undoes_together(dpage):
    a, b = pick_two(dpage)
    assert "메모" in selbar(dpage), "여러 장이어도 메모 단추가 보인다"
    n0 = len(notes_of(dpage))
    dpage.click('#selbar [data-act="memo"]')
    dpage.wait_for_selector("#pop:not([hidden])")
    scopes = dpage.evaluate("[...document.querySelectorAll('#pscope button')].filter(b => !b.hidden).map(b => [b.dataset.scope, b.getAttribute('aria-label'), b.getAttribute('aria-pressed')])")   # R27 F09: 범위 = 아이콘, 이름은 aria-label
    assert scopes == [["screen", "고른 화면 2개", "true"], ["all", "모든 화면", "false"]], scopes
    assert "고른 화면 2개" in dpage.locator("#ptitle").text_content()
    dpage.fill("#pnote", "두 화면 여백을 같이 줄이기")
    dpage.click("#padd")
    wait_notes(dpage, n0 + 2)
    new = notes_of(dpage)[-2:]
    assert sorted(n["screen"] for n in new) == sorted([a, b])
    assert {n["note"] for n in new} == {"두 화면 여백을 같이 줄이기"} and {n["scope"] for n in new} == {"screen"}
    assert {n["path"] for n in new} == {"body"} and len({n["batch"] for n in new}) == 1 and new[0]["batch"]
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)


@pytest.mark.area("tools", "notes")
def test_single_card_memo_keeps_three_scopes(dpage):
    fit_view(dpage)
    p = visible_cover(dpage)
    dpage.mouse.click(p["x"], p["y"])
    dpage.wait_for_timeout(150)
    dpage.click('#selbar [data-act="memo"]')
    dpage.wait_for_selector("#pop:not([hidden])")
    scopes = dpage.evaluate("[...document.querySelectorAll('#pscope button')].filter(b => !b.hidden).map(b => b.getAttribute('aria-label'))")
    assert scopes == ["이 요소", "이 화면", "모든 화면"], "한 장이면 지금과 같다"
    dpage.click("#pcancel")
