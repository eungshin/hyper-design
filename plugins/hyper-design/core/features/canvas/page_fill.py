"""Model — 페이지 끼우기: 템플릿·뼈대 글의 자리에 hd-data · noscript 링크 · 셸 참조 · 데이터 도장 · inject 를 끼운다. 파일·프로세스 없음(tests/test_canvas_unit_page_fill.py).

부르는 곳: build_canvas.build_index(디스크 index.html — data_json · put_links · put_data) · session.ProjectSession.page(줄 때 — page_html, 보드 전환 1단계 P1b).
hd-data 이스케이프 규칙은 여기 하나(data_json): `</` → `<\\/` · `<!--` → `<\\u0021--`(JSON 값은 같고 HTML 파서가 <script> 를 닫지 않는다).
  예전 build_index 의 `<\\!--` 는 JSON 이 아니었다 — 데이터에 `<!--` 가 들면 브라우저 JSON.parse 가 'Bad escaped character' 로 판이 안 열렸다.

뼈대(shell_store.get(도장)["skeleton"], P1a 의 build_canvas.py --shell 이 쓴다)에 기대하는 모양 — 이 함수들이 고르는 자리:
- canvas_template.html 그대로에서 <!-- hd-modules --> 바로 뒤 본 <script> 만 뺀 것(build_canvas.split_shell 의 첫 값) + 코드 도장 meta(code_stamp.stamp_page)
- 비어 있는 자리 네 개: DATA_SLOT(`{}` 그대로) · LINKS_SLOT(빈 noscript) · CSS_SLOT · JS_SLOT(표시 주석 그대로 — 참조는 줄 때 공용 주소로 끼운다)
- 데이터 도장 meta(hd-inputs)는 없음(줄 때 끼움) · `<head>` 는 하나(inject 자리)
오류 탐지: 자리가 없으면 SlotMissing(ValueError, 어느 자리인지 글에) — 부르는 쪽이 [hd] 한 줄 뒤 예전 길.
"""
import html
import json

import code_stamp as CS  # 데이터 도장 meta(stamp_inputs)

DATA_SLOT = '<script id="hd-data" type="application/json">{}</script>'
LINKS_SLOT = '<noscript id="hd-links"></noscript>'
CSS_SLOT = "<!-- hd-shell-css -->"                  # → <link rel="stylesheet" href="…">
JS_SLOT = "<!-- hd-modules -->"                     # → <script src="…"></script>(hd-data 뒤 — 실행 차례)
HEAD = "<head>"


class SlotMissing(ValueError):
    """뼈대·템플릿에 끼울 자리가 없다(다른 판의 뼈대 · 깨진 파일)."""


def _esc(x):
    return html.escape(str(x if x is not None else ""))


def _need(text, slot, what="자리"):
    if slot not in text:
        raise SlotMissing("페이지에 %s %s 가 없어요" % (what, slot))


def need(text, *slots):
    """자리 검사만 — 하나라도 없으면 SlotMissing(끼우기 전에, 파일을 쓰기 전에)."""
    for slot in slots:
        _need(text, slot)


def data_json(data):
    """hd-data 객체 → <script> 안에 그대로 넣을 JSON 글(build_index 와 줄 때가 같은 규칙)."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\u0021--")


def links_html(rows):
    """hd-data rows → 스크립트 없이도(그리고 도달성 검사가) 따라갈 수 있는 화면 링크 목록 <noscript id="hd-links">."""
    lis = "".join('<li><a href="%s">%s</a></li>' % (_esc(c["file"]), _esc(c["title"])) for r in rows for c in r["screens"])
    return ('<noscript id="hd-links"><ul>%s<li><a href="foundation.html">Foundation</a></li>'
            '<li><a href="components.html">Components</a></li></ul></noscript>' % lis)


def put_links(text, rows):
    _need(text, LINKS_SLOT)
    return text.replace(LINKS_SLOT, links_html(rows))


def put_data(text, data):
    _need(text, DATA_SLOT)
    return text.replace(DATA_SLOT, DATA_SLOT.replace("{}", data_json(data)))


def shell_tags(refs):
    """{"js": 주소, "css": 주소} → (CSS 자리 글, 스크립트 자리 글). 주소는 속성 안이라 이스케이프."""
    if not isinstance(refs, dict) or not refs.get("js") or not refs.get("css"):
        raise SlotMissing("셸 참조(js·css 주소)가 없어요: %r" % (refs,))
    return '<link rel="stylesheet" href="%s">' % _esc(refs["css"]), '<script src="%s"></script>' % _esc(refs["js"])


def put_shell(text, refs):
    _need(text, CSS_SLOT)
    _need(text, JS_SLOT)
    link, script = shell_tags(refs)
    return text.replace(CSS_SLOT, link, 1).replace(JS_SLOT, script, 1)


def put_head(text, inject):
    """inject(window.__hd… · __hdState)를 첫 <head> 바로 뒤에 — 도장 meta 보다 앞(디스크 길과 같은 자리)."""
    if not inject:
        return text
    _need(text, HEAD, "머리")
    return text.replace(HEAD, HEAD + inject, 1)


def page_html(skeleton, data, refs, inject="", inputs=None):
    """뼈대 + hd-data(data) + noscript 링크 + 셸 참조(refs = 공용 주소) + 데이터 도장(inputs) + inject → 줄 페이지 글.
    자리 하나라도 없으면 SlotMissing(아무것도 끼우지 않은 채 — 반쯤 채운 페이지를 주지 않는다)."""
    need(skeleton, DATA_SLOT, LINKS_SLOT, CSS_SLOT, JS_SLOT)
    text = put_shell(put_links(skeleton, data["rows"]), refs)
    text = CS.stamp_inputs(text, inputs)
    return put_head(put_data(text, data), inject)
