"""Model — 부품 견본(components.html · foundation/specimens.html 의 section.spec[data-key])에서 화면에 넣을 뼈대만 뽑는다(task 49b). 파일·네트워크를 쓰지 않는다.

뼈대 = 그 견본의 첫 칸(.spec-cell)의 첫 무대(.spec-stage) 안 첫 요소(= '기본' 모습 하나), 다시 써서 만든다(원문을 붙이지 않음):
  - 글은 모두 중립 글 PLACEHOLDER('텍스트') — 견본의 보기 글(이름·날짜·금액…)은 화면에 들어가지 않는다(데이터는 AI 가 화면에 맞게)
  - 속성: id·for·value·title·aria-labelledby·aria-describedby 는 뺌(견본 안 이름이 화면과 겹치지 않게) · placeholder = HINT · alt = '' · aria-label = LABEL
  - 깨끗하지 않으면(on* 속성 · script·style·iframe·object·embed·template · javascript: 주소 · 첫 무대에 요소가 없음) 뼈대 없음 → 캔버스는 AI 요청 메모로
sections(html) → [{key, title, inner}] · skeleton(inner) → 글|None · parts(html) → [{key, title, ok}] · markup(html, key) → 글 (없거나 깨끗하지 않으면 ValueError)
"""
import html as _html
import re
from html.parser import HTMLParser

PLACEHOLDER = "텍스트"
HINT = "입력"
LABEL = "설명"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BAD_TAGS = {"script", "style", "iframe", "object", "embed", "template", "link", "meta", "base", "form"}
DROP = {"id", "for", "value", "title", "aria-labelledby", "aria-describedby", "name", "checked", "selected", "disabled"}
CASE = {"viewbox": "viewBox", "preserveaspectratio": "preserveAspectRatio"}   # 파서가 낮춘 svg 속성 이름 되돌리기
BAD_URL = re.compile(r"^\s*(javascript|vbscript):", re.I)
SEC = re.compile(r"<section\b[^>]*\bclass\s*=\s*[\"'][^\"']*\bspec\b[^\"']*[\"'][^>]*>", re.I)
TAG = re.compile(r"<(/?)section\b[^>]*>", re.I)


def _attr(tag, name):
    m = re.search(r"""\b%s\s*=\s*["']([^"']*)["']""" % re.escape(name), tag)
    return _html.unescape(m.group(1)) if m else ""


def sections(html):
    """section.spec[data-key] 들(문서 차례) — 안의 section 은 깊이로 건너뛴다(build_canvas.spec_sections 와 같은 뜻)."""
    res, i = [], 0
    while True:
        mo = SEC.search(html, i)
        if not mo:
            return res
        depth, j, end = 1, mo.end(), len(html)
        while depth:
            t = TAG.search(html, j)
            if not t:
                j = end; break
            depth += -1 if t.group(1) else 1
            j = t.end()
        key = _attr(mo.group(0), "data-key")
        if key:
            inner = html[mo.end():j]
            inner = inner[: len(inner) - len("</section>")] if inner.lower().endswith("</section>") else inner
            res.append({"key": key, "title": _attr(mo.group(0), "data-title") or key, "inner": inner})
        i = j


class _Unclean(Exception):
    pass


class _Skel(HTMLParser):
    """첫 .spec-stage 의 첫 요소를 다시 쓴다 — 글은 중립 글, 속성은 걸러서."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stage = 0            # .spec-stage 안 깊이(0 = 밖)
        self.depth = 0            # 뽑는 요소 안 깊이
        self.out, self.done, self.bad, self.svg = [], False, False, 0
        self.text = False         # 바로 앞에 중립 글을 썼나(이어진 글 = 하나)

    def _open(self, tag, attrs, void):
        if tag in BAD_TAGS:
            raise _Unclean(tag)
        parts = []
        for k, v in attrs:
            k = k.lower(); v = "" if v is None else v
            if k.startswith("on"):
                raise _Unclean(k)
            if k in ("href", "src", "xlink:href", "action", "formaction") and BAD_URL.match(v):
                raise _Unclean(k)
            if k in DROP and not self.svg:
                continue
            if k == "placeholder":
                v = HINT
            elif k == "alt":
                v = ""
            elif k == "aria-label":
                v = LABEL
            parts.append(' %s="%s"' % (CASE.get(k, k), _html.escape(v, quote=False).replace('"', "&quot;")))
        self.out.append("<" + tag + "".join(parts) + ("/>" if void else ">"))
        self.text = False

    def handle_starttag(self, tag, attrs, selfclose=False):
        if self.done:
            return
        if self.depth == 0 and not self.stage:
            if "spec-stage" in (dict(attrs).get("class") or "").split():
                self.stage = 1
            return
        self.depth += 1                              # 무대 안 첫 요소(depth 1) = 뼈대
        html_void = tag in VOID and not self.svg
        self._open(tag, attrs, selfclose and not html_void)
        if html_void or selfclose:
            self._close(tag, emit=False)
        elif tag == "svg":
            self.svg += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, selfclose=True)

    def _close(self, tag, emit=True):
        if emit:
            self.out.append("</" + tag + ">")
            if tag == "svg" and self.svg:
                self.svg -= 1
        self.depth -= 1
        self.text = False
        if self.depth == 0:
            self.done = True

    def handle_endtag(self, tag):
        if self.done:
            return
        if self.depth == 0:
            if self.stage and tag == "div":          # 무대가 요소 없이 닫힘
                self.done = True
            return
        if tag in VOID:
            return
        self._close(tag)

    def handle_data(self, data):
        if self.done or self.depth == 0:
            return
        if data.strip():
            if self.svg:
                return                               # svg 안 글(title 등)은 버린다
            if not self.text:
                self.out.append(PLACEHOLDER); self.text = True

    def handle_comment(self, data):
        return


def skeleton(inner):
    """견본 하나의 안쪽 → 뼈대 마크업 | None(깨끗하지 않음·요소 없음)."""
    p = _Skel()
    try:
        p.feed(inner); p.close()
    except _Unclean:
        return None
    s = "".join(p.out).strip()
    return s if s.startswith("<") and p.done and p.depth == 0 else None


def parts(html):
    return [{"key": s["key"], "title": s["title"], "ok": skeleton(s["inner"]) is not None} for s in sections(html)]


def markup(html, key):
    for s in sections(html):
        if s["key"] == key:
            sk = skeleton(s["inner"])
            if sk is None:
                raise ValueError("이 부품은 뼈대를 뽑지 못했어요 — AI에게 요청해 주세요: " + key)
            return sk
    raise ValueError("없는 부품: " + str(key))
