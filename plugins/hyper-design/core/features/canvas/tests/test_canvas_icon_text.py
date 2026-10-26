"""R15 아이콘 옆 글자 고치기 — 브라우저(도우미 있음, 크게 보기).

아이콘(svg·img·글 없는 i/span)과 글자가 한 요소에 섞인 곳(job 화면의 `a.wizard-back` = `<svg…/> 이전`)도 글자 고치기가 된다:
요소 막대 '글자'가 켜져 있고, 글자 도구로 누르면 글자 조각만 그 자리에서 고치며(아이콘은 그대로), 파일에도 글자 조각만 바뀌어 써진다(기록 한 줄).
규칙은 test_canvas_unit_text_remove.py(helper edit_html — 아이콘 + 글).
"""
import os, re, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_text_remove import _open, _serve, out  # noqa: F401
from test_canvas_instant import _hist, _job, _modal, _pick, _wait_file

SHOTS = Path(os.environ.get("HD_SHOTS_R15", Path(tempfile.gettempdir()) / "claude" / "r15r16"))
BACK = "a.wizard-back"
SVG_JS = "(s) => { const e = document.querySelector(s); return e.querySelectorAll('svg').length + '|' + e.textContent.trim(); }"


@pytest.mark.area("helper", "modal", "tools")
def test_text_next_to_an_icon_is_editable_and_keeps_the_icon(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        assert mf.evaluate(SVG_JS, BACK) == "1|이전"
        _pick(pg, mf, BACK)
        assert pg.get_attribute('#elbar button[data-act="text"]', "aria-disabled") is None, "아이콘 + 글 요소도 막대 '글자'가 켜져 있다"
        h0 = _hist(out)
        pg.click('#tools [data-tool="text"]')
        mf.click(BACK)
        mf.wait_for_function("(s) => !!document.querySelector(s + ' [contenteditable]') || document.querySelector(s).isContentEditable", arg=BACK, timeout=3000)
        assert mf.evaluate("(s) => document.activeElement && document.querySelector(s).contains(document.activeElement)", BACK), "고치는 칸에 초점"
        assert mf.evaluate("(s) => !document.querySelector(s + ' svg').closest('[contenteditable]')", BACK), "아이콘은 고치는 칸 밖"
        pg.keyboard.type("뒤로")
        pg.keyboard.press("Enter")
        mf.wait_for_function("(s) => !document.querySelector(s + ' [contenteditable]') && !document.querySelector(s).isContentEditable", arg=BACK, timeout=3000)
        assert mf.evaluate(SVG_JS, BACK) == "1|뒤로", "화면은 바로 — 아이콘 그대로, 글자만"
        _wait_file(pg, out, lambda s: re.search(r'<a class="wizard-back" href="login--done.html"><svg[^>]*><path[^>]*/></svg> 뒤로</a>', s),
                   "파일에 글자 조각만 바뀌어 써지지 않았다")
        pg.wait_for_timeout(500)
        assert _hist(out) == h0 + 1, "기록 한 줄"
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "r15-icon-text-after.png"))
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
