"""화면 경험 작은 것들(U3, 10-31) — 브라우저 없이 보는 글·마크업.

F9 손(H) 꼬리말 = 실제 동작(한 번 = 고르기 · 두 번 누르기 = 크게 보기) · F8 Foundation 문서 첫 문장에 없는 '위의 색 점' 안내 없음 ·
F11 위 막대 모니터 아이콘(#vbtn) 없음 — 보기 메뉴는 배율 칩(#zoom) 하나.
"""
import re, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANVAS = HERE.parent
TPL = (CANVAS / "canvas_template.html").read_text(encoding="utf-8")


def tip_of(tool):
    m = re.search(r'data-tool="%s"[^>]*data-tip="([^"]*)"' % tool, TPL)
    assert m, tool
    return m.group(1)


def test_hand_tip_says_double_click_opens_large_view():
    """F9: 손 도구로 카드를 한 번 누르면 고르기, 두 번 누르면 크게 보기(셸 클릭 처리 e.detail) — 꼬리말이 '누르면 크게 보기'라고 하지 않는다."""
    tip = tip_of("hand")
    assert "두 번 누르면 크게 보기" in tip, tip
    assert not re.search(r"(^|[^번] )누르면 크게 보기", tip), tip


def test_foundation_lead_has_no_color_dot_hint():
    """F8: Foundation 첫 문장의 '위의 색 점을 누르면…' — 그 문서 위에는 색 점이 없다(빼고 나머지 문장은 그대로)."""
    sys.path.insert(0, str(CANVAS))
    import build_canvas
    tmp = Path(tempfile.mkdtemp(prefix="hd-found-"))
    try:
        (tmp / "tokens.css").write_text(":root{--c-brand:#2563eb;--space-2:8px}", encoding="utf-8")
        build_canvas.build_foundation(tmp)
        html = (tmp / "foundation.html").read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    lead = re.search(r'<p class="lead">([^<]*)</p>', html).group(1)
    assert "색 점" not in lead and "바로 바뀌어요" not in lead, lead
    assert lead.startswith("이 앱의 모든 화면이 쓰는 색·글자·여백"), lead


def test_top_bar_has_one_view_menu_button():
    """F11: 모니터 아이콘 #vbtn 은 배율 칩 #zoom 과 같은 #vmenu 를 열던 겹친 단추 — 없앤다(배율 칩 하나)."""
    assert 'id="vbtn"' not in TPL and "#vbtn" not in TPL
    assert re.search(r'id="zoom"[^>]*aria-controls="vmenu"', TPL)
    for f in ("view-menu.js", "view-show-pop.js"):
        src = (CANVAS / "modules" / f).read_text(encoding="utf-8")
        assert "#vbtn" not in src and "'vbtn'" not in src, f   # 클래스 .vbtn(위 막대 단추 모양)은 그대로
