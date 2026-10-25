"""Model — 화면 안 링크 규칙: 링크 주소(href · data-href · onclick 안 .html) → 같은 폴더 화면 id. 파일·네트워크를 쓰지 않는다(글 → 값).

build_canvas(판의 선 미리 뽑기)와 html_edit(끊기·잇기)가 같은 규칙 하나를 쓴다 — foundation/palette.js links()·linkTo 와 같은 규칙,
공유 fixture tests/fixtures/links.json(tests/test_canvas_unit_shared_rules.py). 이상한 주소는 오류 대신 None(링크 아님)으로 거른다.
"""
import posixpath
import re
import urllib.parse
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
GO_ONCLICK = re.compile(r"""['"]([^'"]+\.html?)(?:[?#][^'"]*)?['"]""", re.I)


class Links(HTMLParser):
    """화면 HTML → 같은 폴더 다른 화면으로 가는 링크 [(to, 글)] — foundation/palette.js 의 links()(href · data-href · onclick 안 .html)와 같은 규칙."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.open = [], []                   # open = [태그, 깊이, 도착, 글 조각]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        h = a.get("href") or a.get("data-href")
        if not h and a.get("onclick"):
            m = GO_ONCLICK.search(a["onclick"]); h = m and m.group(1)
        for o in self.open:
            if o[0] == tag: o[1] += 1
        if h and tag not in VOID:
            self.open.append([tag, 1, h, []])
        elif h:
            self.out.append((h, ""))

    def handle_endtag(self, tag):
        for o in reversed(self.open):
            if o[0] == tag:
                o[1] -= 1
                if o[1] == 0:
                    self.open.remove(o); self.out.append((o[2], re.sub(r"\s+", " ", "".join(o[3])).strip()[:40]))
                break

    def handle_data(self, d):
        for o in self.open: o[3].append(d)


def link_target(h):
    """링크 주소(href · data-href · onclick 안 .html) → 같은 폴더 화면 id | None — 브라우저가 실제로 가는 곳(palette.js linkTo 와 같은 규칙).
    화면 폴더 기준으로 풀어(./ · sub/.. · %xx) 같은 폴더의 .html/.htm 이면 파일 이름. ../ 로 나가거나 다른 폴더·주소·스킴이면 None.
    자기 자신은 거르지 않는다(부르는 쪽 몫). 공유 규칙 tests/fixtures/links.json(task 41)."""
    h = (h or "").strip().replace("\\", "/")
    if not h or re.match(r"^[a-z][a-z0-9+.-]*:", h, re.I) or h.startswith(("/", "#")):   # 스킴(javascript:·https:…)·절대 경로·같은 쪽 안
        return None
    h = re.split(r"[?#]", h, maxsplit=1)[0]
    if h.endswith("/") or re.search(r"%(?![0-9a-fA-F]{2})", h):   # 폴더 주소 · 깨진 %xx — 브라우저 쪽(new URL · decodeURIComponent)도 버린다
        return None
    rel = posixpath.normpath(urllib.parse.unquote(h)) if h else ""
    if not rel or "/" in rel or not re.search(r"\.html?$", rel, re.I):
        return None
    return re.sub(r"\.html?$", "", rel, flags=re.I) or None
