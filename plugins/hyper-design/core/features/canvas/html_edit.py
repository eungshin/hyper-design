"""Model — 화면 HTML 원문 고치기(task 47-2 에서 helper.py 에서 떼어 냄): 원문 위치를 아는 작은 트리 · palette.js 경로 고르기 ·
편집 패치(글자·지우기·복제·옮기기·속성·넣기·바꾸기·잇기·끊기). 글 → 글 — 파일·네트워크를 쓰지 않는다(쓰기는 history.History · screen_edits).
"""
import html, re
from html.parser import HTMLParser

import links

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

# ---------------------------------------------------------------- HTML: 원문 위치를 아는 작은 트리
class Node:
    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag, self.attrs, self.start, self.open_end, self.parent = tag, dict(attrs), start, open_end, parent
        self.children, self.texts = [], []          # texts: (원문 위치, 길이, 글) — 이 요소 바로 아래 글
        self.close = None                           # 닫는 태그 (시작, 끝) — void·self-closing 은 없음(끝 = open_end), 닫히지 않은 요소도 없음
        self.void = False
        self.order = []                             # 아이·글을 문서 순서대로: ('el', Node) | ('tx', (pos, len, data))


class Tree(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src, self.lines = src, [0]
        for m in re.finditer("\n", src):
            self.lines.append(m.end())
        self.root = Node("#root", [], 0, 0, None)
        self.stack = [self.root]
        self.feed(src); self.close()

    def _pos(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        pos = self._pos(); raw = self.get_starttag_text() or ""
        n = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        self.stack[-1].children.append(n); self.stack[-1].order.append(("el", n))
        if tag not in VOID and not raw.rstrip().endswith("/>"):
            self.stack.append(n)
        else:
            n.void = True

    def handle_startendtag(self, tag, attrs):
        pos = self._pos(); raw = self.get_starttag_text() or ""
        n = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        n.void = True
        self.stack[-1].children.append(n); self.stack[-1].order.append(("el", n))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                pos = self._pos(); gt = self.src.find(">", pos)
                self.stack[i].close = (pos, gt + 1 if gt >= 0 else len(self.src))
                del self.stack[i:]
                return

    def _text(self, data):
        if self.stack[-1].tag in ("script", "style"):
            return
        t = (self._pos(), len(data), data)
        self.stack[-1].texts.append(t); self.stack[-1].order.append(("tx", t))

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        self._text("&" + name + ";")

    def handle_charref(self, name):
        self._text("&#" + name + ";")

    def walk(self, n=None):
        n = n or self.root
        for c in n.children:
            yield c
            yield from self.walk(c)


def _unesc(s):                                       # CSS.escape 되돌리기(\31 · \: 등)
    s = re.sub(r"\\([0-9a-fA-F]{1,6}) ?", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"\\(.)", r"\1", s)


SEG = re.compile(r'^(?:#(?P<id>.+)|(?P<tag>[a-zA-Z][\w-]*)(?:\[data-region="(?P<reg>(?:[^"\\]|\\.)*)"\]|(?:\.(?P<cls>(?:[^:\\]|\\.)+))?(?::nth-of-type\((?P<nth>\d+)\))?))$')


def _seg_ok(n, seg):
    m = SEG.match(seg)
    if not m:
        raise ValueError("모르는 경로 조각: " + seg)
    if m.group("id") is not None:
        return n.attrs.get("id") == _unesc(m.group("id"))
    if n.tag != m.group("tag").lower():
        return False
    if m.group("reg") is not None:
        return n.attrs.get("data-region") == m.group("reg").replace('\\"', '"')
    if m.group("cls") is not None and ((n.attrs.get("class") or "").split() or [""])[0] != _unesc(m.group("cls")):
        return False
    if m.group("nth") is not None:
        sib = [c for c in (n.parent.children if n.parent else []) if c.tag == n.tag]
        if sib.index(n) + 1 != int(m.group("nth")):
            return False
    return True


def select(tree, path):
    """palette.js pathOf 가 만든 경로(조각 ' > ' 조각, 자식 관계) → 요소 하나. 없거나 여럿이면 ValueError."""
    segs = [s.strip() for s in path.split(" > ") if s.strip()]
    if not segs:
        raise ValueError("빈 경로")
    hits = []
    for n in tree.walk():
        cur, ok = n, True
        for seg in reversed(segs):
            if cur is None or cur.tag == "#root":
                ok = False; break
            if seg == "body" and cur.tag != "body" or seg != "body" and not _seg_ok(cur, seg):
                ok = False; break
            cur = cur.parent
        if ok:
            hits.append(n)
    if len(hits) != 1:
        raise ValueError(f"경로에 맞는 요소 {len(hits)}개: {path}")
    return hits[0]


def _set_attr(tag_src, name, value):                # 시작 태그 원문에서 속성 하나 바꾸기(없으면 더하기 · None 이면 지우기)
    rx = re.compile(r'(\s' + re.escape(name) + r')(\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?', re.I)
    if value is None:
        return rx.sub("", tag_src, count=1)
    new = ' %s="%s"' % (name, html.escape(value, quote=True))
    if rx.search(tag_src):
        return rx.sub(lambda m: new, tag_src, count=1)
    end = len(tag_src) - (2 if tag_src.endswith("/>") else 1)
    return tag_src[:end].rstrip() + new + tag_src[end:]


# 글자 고치기(task 30): 요소 안 내용 전부(글 + 인라인 자식)를 새 글로 — 이 태그들(글이 든 것, br·wbr)만 안에 있어도 된다.
# 그 밖(블록·그림·입력·링크 a)이 안에 있으면 거절 — 일부만 바꾸지 않는다. palette.js 미리보기(pending)와 같은 규칙.
# 예외(R15 아이콘 + 글): 자식 요소가 글이 없거나(svg·img·빈 i/span = 아이콘) 글 든 인라인만으로 된 것이면 글 조각만 바꾸고 아이콘은 원문 그대로
# (_icon_text · _icon_text_patch — 바뀐 곳이 글 마디 하나 안이면 그 마디만, 아니면 꾸밈 없이 통째로).
INLINE = {"b", "strong", "i", "em", "span", "small", "u", "s", "mark", "sub", "sup", "code", "abbr", "cite", "q", "kbd", "var", "time",
          "font", "del", "ins", "br", "wbr"}
BLOCK_REASON = "안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요"


def _has_text(n):
    return any(x[2].strip() for x in n.texts) or any(_has_text(c) for c in n.children if c.tag not in ("script", "style"))


def _inline_only(n):
    for c in n.children:
        if c.tag not in INLINE or (c.tag not in ("br", "wbr") and not _has_text(c)) or not _inline_only(c):
            return False
    return True


def _is_root(el):                                    # html·head·body · 화면 뿌리(body 또는 조각 맨 위의 유일한 요소)
    if el.tag in ("html", "head", "body"):
        return True
    p = el.parent
    if p is None or p.tag not in ("body", "#root"):
        return False
    return [c for c in p.children if c.tag not in ("script", "style", "link", "meta")] == [el]


def _icon_text(n):                                   # R15 아이콘 + 글: 글이 있고, 자식 요소는 글이 없거나(아이콘 — svg·img·빈 i/span) 글 든 인라인만으로 된 것(b·span…)
    return _has_text(n) and all(not _has_text(c) or (c.tag in INLINE and _inline_only(c)) for c in n.children)


def _text_runs(el):                                  # 글 묶음 [(시작, 끝, [항목])] — 바로 아래 글·br·글 든 인라인 요소가 이어진 것(글 없는 요소 = 아이콘에서 끊김)
    runs, cur = [], None
    for kind, x in el.order:
        if kind == "tx":
            cur = cur or [x[0], 0, []]
            cur[1] = x[0] + x[1]; cur[2].append((kind, x))
        elif x.tag in ("br", "wbr"):
            if cur is not None:
                cur[1] = x.open_end; cur[2].append((kind, x))
        elif _has_text(x):
            if x.close is None:
                raise ValueError(BLOCK_REASON)
            cur = cur or [x.start, 0, []]
            cur[1] = x.close[1]; cur[2].append((kind, x))
        elif cur is not None:
            runs.append(tuple(cur)); cur = None
    if cur is not None:
        runs.append(tuple(cur))
    return runs


def _run_chars(items):
    """글 묶음 → (마디들, 보이는 글자들). 마디 = 같은 부모 아래 이어진 글 항목 [원문 시작, 끝, 풀어 쓴 글].
    글자 = [글자, 마디 번호(br = -1)] — palette.js plainOf 와 같은 정리(공백 하나로 · br = 줄바꿈 · 줄바꿈 둘레 공백 없앰 · 앞뒤 자름)."""
    leaves, order = [], []

    def walk(its):
        last = None
        for kind, x in its:
            if kind == "tx":
                if last is None:
                    leaves.append([x[0], 0, ""]); last = len(leaves) - 1; order.append(last)
                leaves[last][1] = x[0] + x[1]; leaves[last][2] += html.unescape(x[2])
                continue
            last = None
            if x.tag == "br":
                order.append(-1)
            elif x.tag != "wbr":
                walk(x.order)
    walk(items)
    chars = []
    for i in order:
        chars += [["\n", -1]] if i < 0 else [[ch, i] for ch in re.sub(r"\s+", " ", leaves[i][2])]
    out, k = [], 0                                     # .replace(/ *\n */g,'\n').replace(/ {2,}/g,' ').trim() — 글자마다 주인 마디를 지닌 채
    while k < len(chars):
        if chars[k][0] != " ":
            out.append(chars[k]); k += 1; continue
        j = k
        while j < len(chars) and chars[j][0] == " ":
            j += 1
        if not (k > 0 and chars[k - 1][0] == "\n" or j < len(chars) and chars[j][0] == "\n"):
            out.append(chars[k])
        k = j
    while out and out[0][0] in " \n":
        out.pop(0)
    while out and out[-1][0] in " \n":
        out.pop()
    return leaves, out


def _one_leaf(chars, value):
    """바뀐 곳이 글 마디 하나 안이면 (마디 번호, 그 마디의 새 글 — 앞뒤 공백 뺌) · 바뀐 것 없으면 'same' · 아니면 None.
    바뀐 곳 = 앞뒤 같은 글자를 뺀 가운데. 넣기만이면 앞 글자의 마디(앞이 br·없으면 뒤 글자의 마디).
    마디가 비게 되거나 마디 가장자리 공백이 바뀌면 None(꾸밈 없이 통째로 — 빈 b 가 아이콘으로 읽히지 않게)."""
    old = "".join(c[0] for c in chars)
    if old == value:
        return "same"
    p = 0
    while p < min(len(old), len(value)) and old[p] == value[p]:
        p += 1
    s = 0
    while s < min(len(old), len(value)) - p and old[-1 - s] == value[-1 - s]:
        s += 1
    q, chunk = len(old) - s, value[p:len(value) - s]
    own = {chars[k][1] for k in range(p, q)}
    if not own:
        own = {chars[p - 1][1]} if p > 0 and chars[p - 1][1] >= 0 else ({chars[p][1]} if p < len(chars) else set())
    if len(own) != 1 or -1 in own:
        return None
    leaf = own.pop()
    at = [k for k in range(len(chars)) if chars[k][1] == leaf]
    was, now = old[at[0]:at[-1] + 1], old[at[0]:p] + chunk + old[q:at[-1] + 1]
    if not now.strip() or (was[:1] == " ") != (now[:1] == " ") or (was[-1:] == " ") != (now[-1:] == " "):
        return None
    return leaf, now.strip()


def _icon_text_patch(src, el, value):
    """아이콘 + 글(R15): 아이콘(글 없는 자식 요소)은 원문 그대로.
    글 묶음이 하나이고 바뀐 곳이 글 마디 하나 안이면 그 마디만(마디 앞뒤 공백 · b·span 꾸밈 그대로 — 마디 안 공백은 하나로, 엔티티는 글자로 풀려 다시 escape).
    아니면 첫 글 묶음 = 앞뒤 공백 + 새 글(\\n = br, 묶음 안 꾸밈은 없어짐), 그 뒤 글 묶음은 비움."""
    full = [r for r in _text_runs(el) if _run_chars(r[2])[1]]
    if len(full) == 1:
        leaves, chars = _run_chars(full[0][2])
        hit = _one_leaf(chars, value)
        if hit == "same":
            return full[0][0], full[0][0], ""
        if hit:
            x, y, dec = leaves[hit[0]]
            lead, trail = dec[: len(dec) - len(dec.lstrip())], dec[len(dec.rstrip()):]
            return x, y, lead + html.escape(hit[1], quote=False).replace("\n", "<br>") + trail
    a, b = full[0][0], full[-1][1]
    out, at = [], a
    for i, (x, y, _) in enumerate(full):
        out.append(src[at:x])                          # 사이 원문(아이콘·공백) 그대로
        if i == 0:
            raw = src[x:y]
            lead, trail = raw[: len(raw) - len(raw.lstrip())], raw[len(raw.rstrip()):]
            out.append(lead + html.escape(value, quote=False).replace("\n", "<br>") + trail)
        at = y
    return a, b, "".join(out)


def _text_patch(src, el, value, path):
    if el.void or el.close is None:
        raise ValueError("글자를 넣을 수 없는 요소예요(닫는 태그 없음): " + path)
    if not _inline_only(el):
        if _icon_text(el):
            return _icon_text_patch(src, el, value)
        raise ValueError(BLOCK_REASON)
    a, b = el.open_end, el.close[0]
    inner = src[a:b]
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):] if inner.strip() else ""
    return a, b, lead + html.escape(value, quote=False).replace("\n", "<br>") + trail


def _remove_patch(el, path):
    if _is_root(el):
        raise ValueError("화면 뿌리(html·body·맨 바깥 요소)는 지울 수 없어요 — 화면을 지우려면 카드 메뉴의 삭제: " + path)
    if el.void:
        return el.start, el.open_end, ""
    if el.close is None:
        raise ValueError("닫는 태그를 찾지 못해 지울 수 없어요: " + path)
    return el.start, el.close[1], ""


# 블록 편집(task 49a): 복제·위/아래로 옮기기 — 원문 조각 그대로(요소 [시작, 닫는 태그 끝)), 형제 = 이 태그들은 건너뛴다(palette.js SIB_SKIP 과 같은 규칙)
SIB_SKIP = {"script", "style", "template", "link", "meta"}


def _end(el, path, what):                            # 요소 원문 끝(void·/> = 시작 태그 끝) — 닫는 태그가 없으면 거절
    if el.void:
        return el.open_end
    if el.close is None:
        raise ValueError("닫는 태그를 찾지 못해 %s 수 없어요: %s" % (what, path))
    return el.close[1]


def _block_ok(el, path, what):
    if _is_root(el):
        raise ValueError("화면 뿌리(html·body·맨 바깥 요소)는 %s 수 없어요: %s" % (what, path))


def _strip_ids(src, el, a, b):
    """원문 [a, b) = 요소 el 조각 → id·data-region 을 모두 뺀 복사본(그 안 자손 포함) — 복사본 경로가 원본과 겹치지 않게."""
    nodes, stack = [], [el]
    while stack:
        n = stack.pop(); nodes.append(n); stack.extend(n.children)
    patches = []
    for n in nodes:
        tag = src[n.start:n.open_end]
        new = _set_attr(_set_attr(tag, "id", None), "data-region", None) if ("id" in n.attrs or "data-region" in n.attrs) else tag
        if new != tag:
            patches.append((n.start - a, n.open_end - a, new))
    return _patch(src[a:b], patches)


def _dup_patch(src, el, path):
    """복제: 요소 바로 뒤에 복사본 — 요소 앞 공백(줄바꿈·들여쓰기)을 한 번 더 넣고 복사본. 패치 = 요소 자리 전체(안의 다른 편집과 겹치면 거절)."""
    _block_ok(el, path, "복제할")
    a, b = el.start, _end(el, path, "복제할")
    k = a
    while k > 0 and src[k - 1] in " \t\r\n":
        k -= 1
    return a, b, src[a:b] + src[k:a] + _strip_ids(src, el, a, b)


def _move_patch(src, el, path, way):
    """옮기기: up·down = 앞·뒤 형제 요소와 맞바꿈 · 정수 = 형제 요소(script·style 등 빼고) 사이 그 자리로(49c 끌기 — 쓰기·되돌리기 하나).
    둘 사이 글·공백·주석은 제자리 — 요소 원문만 돌아간다."""
    _block_ok(el, path, "옮길")
    sibs = [c for c in el.parent.children if c.tag not in SIB_SKIP]
    i = sibs.index(el)
    if way in ("up", "down"):
        j = i - 1 if way == "up" else i + 1
        if j < 0:
            raise ValueError("맨 위 요소라 더 위로 옮길 수 없어요: " + path)
        if j >= len(sibs):
            raise ValueError("맨 아래 요소라 더 아래로 옮길 수 없어요: " + path)
    elif isinstance(way, int) and not isinstance(way, bool):
        j = way
        if not 0 <= j < len(sibs):
            raise ValueError("옮길 자리가 형제 범위(0~%d) 밖이에요: %d" % (len(sibs) - 1, j))
        if j == i:
            raise ValueError("이미 그 자리예요: " + path)
    else:
        raise ValueError("옮길 방향은 up·down 이나 자리 번호예요: %s" % (way,))
    run = sibs[min(i, j):max(i, j) + 1]
    ends = [_end(c, path, "옮길") for c in run]
    order = [el] + run[:-1] if j < i else run[1:] + [el]
    pieces = {id(c): src[c.start:e] for c, e in zip(run, ends)}
    body = ""
    for k, c in enumerate(order):
        body += pieces[id(c)] + (src[ends[k]:run[k + 1].start] if k + 1 < len(run) else "")
    return run[0].start, ends[-1], body


# 블록 조립(task 49b): 속성 칸 — 허용 목록만(on*·style 은 절대), 스크립트 주소 거절. 같은 목록: palette.js ATTR_OK · blocks.js ATTRS
ATTR_OK = {"img": ("src", "alt"), "a": ("href",), "input": ("placeholder",), "textarea": ("placeholder",)}
ATTR_MAX = 2000
BAD_URL = re.compile(r"^\s*(javascript|vbscript|data):", re.I)
DATA_IMG = re.compile(r"^\s*data:image/", re.I)


def _attr_patch(src, el, v, path):
    """속성 하나 바꾸기 — v = {name, value}. 허용 목록(태그마다) 밖·on*·style 거절, href·src 의 javascript:·vbscript:·data:(그림 src 의 data:image/ 만 허용) 거절."""
    v = v if isinstance(v, dict) else {}
    name, value = str(v.get("name") or ""), v.get("value")
    if name not in ATTR_OK.get(el.tag, ()) or name.lower().startswith("on") or name.lower() == "style":
        raise ValueError("바꿀 수 없는 속성이에요(%s %s) — 그림 src·alt · 링크 href · 입력 칸 placeholder 만: %s" % (el.tag, name or "?", path))
    if not isinstance(value, str):
        raise ValueError("속성 값은 글이어야 해요: " + path)
    if "\n" in value or "\r" in value:
        raise ValueError("속성 값에는 줄바꿈을 넣을 수 없어요: " + path)
    if len(value) > ATTR_MAX:
        raise ValueError("속성 값이 %d자를 넘어요: %s" % (ATTR_MAX, path))
    if name in ("href", "src") and BAD_URL.match(value) and not (name == "src" and DATA_IMG.match(value)):
        raise ValueError("이 주소는 쓸 수 없어요(javascript:·data: 등): " + path)
    return el.start, el.open_end, _set_attr(src[el.start:el.open_end], name, value)


def _part(markup, path):
    if not isinstance(markup, str) or not markup.strip():
        raise ValueError("빈 부품이에요: " + path)
    return markup.strip()


def _lead(src, a):                                   # 요소 앞 공백(줄바꿈·들여쓰기) — 넣은 부품도 같은 들여쓰기로
    k = a
    while k > 0 and src[k - 1] in " \t\r\n":
        k -= 1
    return src[k:a]


def _insert_patch(src, el, markup, path):
    """넣기: 요소 바로 뒤에 부품(앞 공백 그대로 한 번 + 뼈대). 화면 뿌리 거절."""
    _block_ok(el, path, "옆에 넣을")
    a, b = el.start, _end(el, path, "옆에 넣을")
    return a, b, src[a:b] + _lead(src, a) + _part(markup, path)


def _replace_patch(src, el, markup, path):
    """바꾸기: 요소 자리 [시작, 닫는 태그 끝) 를 부품으로. 화면 뿌리 거절."""
    _block_ok(el, path, "바꿀")
    return el.start, _end(el, path, "바꿀"), _part(markup, path)


SCRIPT_REASON = "이 글은 화면 스크립트가 그려요"
JS_STR = re.compile(r"""'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`""", re.S)


def _squash(s):
    return re.sub(r"\s+", " ", s).strip()


def _plain(src, el):                                 # 요소 원문 안 글(태그 빼고 · br = 줄 · 엔티티 풀고 · 공백 하나로) — palette.js plainOf 와 견줄 글
    if el.close is None:
        return ""
    inner = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", src[el.open_end:el.close[0]], flags=re.S | re.I)
    return _squash(html.unescape(re.sub(r"<[^>]*>", "", re.sub(r"<br\s*/?>", "\n", inner, flags=re.I))))


def _script_text_patch(src, old, value, path):
    """화면에 보인 글(old)이 파일의 그 요소 글과 다름 = 스크립트가 그린 글 → <script> 안 문자열에서 old 한 곳을 새 글로."""
    if "\n" in value:
        raise ValueError(SCRIPT_REASON + " — 줄바꿈은 바로 쓸 수 없어요(AI에게 맡겨 주세요): " + path)
    hits = []
    for n in Tree(src).walk():
        if n.tag != "script" or n.close is None or n.attrs.get("src"):
            continue
        for m in JS_STR.finditer(src, n.open_end, n.close[0]):
            body, at = m.group(0)[1:-1], m.start() + 1
            i = body.find(old)
            while i >= 0:
                hits.append((at + i, m.group(0)[0])); i = body.find(old, i + 1)
    if not hits:                                     # 글 사이에 <b> 같은 서식이 끼면 문자열에 그대로 없다 — 스크립트 안 HTML 조각에서 그 글의 요소를 찾는다
        mk = _script_markup_patch(src, old, value)
        if mk:
            return mk
    if len(hits) != 1:
        raise ValueError(SCRIPT_REASON + " — 스크립트에서 그 글을 %s 찾아 파일에 쓰지 않았어요(AI에게 맡겨 주세요): %s"
                         % ("못" if not hits else "%d곳에서" % len(hits), path))
    a, q = hits[0]
    v = value.replace("\\", "\\\\").replace(q, "\\" + q)
    if q == "`":
        v = v.replace("${", "\\${")
    return a, a + len(old), v


TAG_RX = re.compile(r"<[^>]*>")


def _segments(frag):                                 # 조각 원문 → 글 조각 [(원문 시작, 원문 끝, 풀린 글)] — 태그 사이 글만(엔티티 풀고)
    out, at = [], 0
    for m in list(TAG_RX.finditer(frag)) + [None]:
        end = m.start() if m else len(frag)
        if end > at:
            out.append((at, end, html.unescape(frag[at:end])))
        if m:
            at = m.end()
    return out


def _js_quote(v, q):                                 # 새 글 → 그 문자열 따옴표(q) 안에 넣을 원문
    v = v.replace("\\", "\\\\").replace(q, "\\" + q)
    return v.replace("${", "\\${") if q == "`" else v


def _markup_edit(frag, old, value):
    """서식 낀 조각 원문(frag) 안 글을 old → value 로 — 바뀐 부분이 글 조각 하나 안이면 그 조각만(굵게 등 서식 그대로),
    여러 조각에 걸치면 조각 전체를 그냥 글로. (조각 안 상대 시작, 끝, 새 원문)."""
    segs = _segments(frag)
    plain = "".join(t for _, _, t in segs)
    if _squash(plain) != old:
        return None
    i = 0
    while i < min(len(plain), len(value)) and plain[i] == value[i]:
        i += 1
    j = 0
    while j < min(len(plain), len(value)) - i and plain[-1 - j] == value[-1 - j]:
        j += 1
    a, b, mid = i, len(plain) - j, value[i:len(value) - j]
    pos = 0
    for s0, s1, t in segs:                           # 바뀐 [a, b) 를 다 품는 글 조각 하나
        if pos <= a and b <= pos + len(t):
            nt = t[:a - pos] + mid + t[b - pos:]
            return s0, s1, html.escape(nt, quote=False)
        pos += len(t)
    return 0, len(frag), html.escape(value, quote=False)


def _script_markup_patch(src, old, value):
    """<script> 문자열이 HTML 조각이면(템플릿 등) 그 안에서 보인 글(old)이 맞는 가장 안쪽 요소 하나 → 그 안 글만 고친 패치 | None."""
    hits = []
    for n in Tree(src).walk():
        if n.tag != "script" or n.close is None or n.attrs.get("src"):
            continue
        for m in JS_STR.finditer(src, n.open_end, n.close[0]):
            body, at, q = m.group(0)[1:-1], m.start() + 1, m.group(0)[0]
            if "<" not in body or "\\" in body:
                continue
            try:
                els = list(Tree(body).walk())
            except Exception:
                continue
            match = [e for e in els if e.tag not in ("#root", "script", "style") and e.close is not None
                     and _squash(_plain(body, e)) == old]
            match = [e for e in match if not any(o is not e and _inside(o, e) for o in match)]   # 가장 안쪽만
            hits += [(at, body, e, q) for e in match]
    if len(hits) != 1:
        return None
    at, body, e, q = hits[0]
    frag = body[e.open_end:e.close[0]]
    r = _markup_edit(frag, old, value)
    if r is None:
        return None
    a = at + e.open_end
    return a + r[0], a + r[1], _js_quote(r[2], q)


def _inside(inner, outer):
    p = inner.parent
    while p is not None:
        if p is outer:
            return True
        p = p.parent
    return False


def _op_patch(src, el, op, value, path):
    if op == "text":
        if isinstance(value, dict):                  # {value, old} — old = 고치기 전 화면에 보이던 글(캔버스, 단계 넘김 화면)
            old, value = _squash(str(value.get("old") or "")), str(value.get("value", ""))
            if old and old not in _plain(src, el):
                return _script_text_patch(src, old, value, path)
        return _text_patch(src, el, value, path)
    if op == "remove":
        return _remove_patch(el, path)
    if op == "duplicate":
        return _dup_patch(src, el, path)
    if op == "move":
        return _move_patch(src, el, path, value)
    if op == "attr":
        return _attr_patch(src, el, value, path)
    if op == "insert":
        return _insert_patch(src, el, value, path)
    if op == "replace":
        return _replace_patch(src, el, value, path)
    if op in ("link", "cut"):
        return _relink(src, el, op, value, path)
    raise ValueError("모르는 편집: " + op)


def _after(src, el, op, value, p):
    """편집 하나를 쓴 뒤 그 요소(옮긴 것 · 넣은·바꾼 부품)가 새 원문에서 시작하는 자리 | None(지움)."""
    if op == "remove":
        return None
    if op == "insert":
        return p[0] + (_end(el, "", "") - el.start) + len(_lead(src, el.start))
    if op == "move" and (value == "down" or (isinstance(value, int) and not isinstance(value, bool)
                                             and value > [c for c in el.parent.children if c.tag not in SIB_SKIP].index(el))):
        return p[0] + len(p[2]) - (_end(el, "", "") - el.start)   # 뒤로 옮김 = 조각 끝에 그 요소
    return p[0] if op in ("move", "replace") else el.start


def _select_or_script(tree, path, op, value):      # 경로 → 요소 | None(요소 0개인데 글 고치기에 old 가 있음 = 스크립트가 그린 요소 — 10-29 탭 도구 말풍선)
    try:
        return select(tree, path)
    except ValueError as e:
        if op == "text" and isinstance(value, dict) and value.get("old") and str(e).startswith("경로에 맞는 요소 0개"):
            return None
        raise


def _script_only(src, value, path):
    return _script_text_patch(src, _squash(str(value.get("old") or "")), str(value.get("value", "")), path)


def edit_one(src, path, op, value):
    """편집 하나 → (새 원문, 그 요소의 새 경로 | None) — 경로 = 태그:nth-of-type 사슬(palette.js find 도 읽음). 쓴 뒤 캔버스가 같은 요소를 다시 고른다."""
    tree = Tree(src)
    el = _select_or_script(tree, path, op, value)
    if el is None:                                   # 파일 HTML 에 없는 요소 = 스크립트가 만든 요소 → 스크립트 안 글만
        return _patch(src, [_script_only(src, value, path)]), path
    p = _op_patch(src, el, op, value, path)
    new = _patch(src, [p])
    at = _after(src, el, op, value, p)
    if at is None:
        return new, None
    hit = [n for n in Tree(new).walk() if n.start == at]
    return new, (_path_of(hit[0]) if hit else None)


def edit_html(src, edits):
    """edits = [(path, op, value)] — op: text(요소 안 내용 전부를 value 로, '' = 비우기) | remove(요소 통째로) | link(value=도착 id) | cut
    | duplicate(바로 뒤에 복사본, 복사본 id·data-region 뺌) | move(value = up|down, 형제와 맞바꿈 | 정수 = 형제 요소 사이 그 자리로, 49c)
    | attr(value = {name, value} — 허용 목록만) | insert·replace(value = 부품 뼈대 마크업 — 도우미가 key 로 뽑은 것만, task 49b).
    원문 위치 기준으로 뒤에서부터 바꾼다. 같은 자리 두 편집 = 나중 것, 겹치는 자리(안팎) = ValueError."""
    tree, spans = Tree(src), {}
    for path, op, value in edits:
        el = _select_or_script(tree, path, op, value)
        p = _script_only(src, value, path) if el is None else _op_patch(src, el, op, value, path)
        spans[(p[0], p[1])] = p                       # 같은 자리 = 나중 것
    patches = sorted(spans.values(), key=lambda p: (p[0], p[1]))
    for x, y in zip(patches, patches[1:]):
        if y[0] < x[1]:
            raise ValueError("한 요소에 겹치는 편집이에요 — 하나씩 반영해 주세요")
    return _patch(src, patches)


def _relink(src, el, op, value, path=""):
    """요소 하나의 시작 태그 → 잇기(value=도착 id)·끊기 한 패치 (start, end, 새 태그)."""
    tag_src = src[el.start:el.open_end]
    href = value + ".html" if op == "link" else None
    onclick = el.attrs.get("onclick") or ""
    if el.tag == "a" or "href" in el.attrs:
        tag_src = _set_attr(tag_src, "href", href)
    elif "data-href" in el.attrs:
        tag_src = _set_attr(tag_src, "data-href", href)
    elif re.search(r"\.html?", onclick):
        tag_src = _set_attr(tag_src, "onclick", "location.href='%s'" % href if href else None)
    elif op == "link":
        tag_src = _set_attr(tag_src, "onclick", "location.href='%s'" % href)
    else:
        raise ValueError("이 요소에는 끊을 연결이 없어요: " + path)
    if op == "cut" and "href" in el.attrs and "data-href" in el.attrs:   # 둘 다 있으면 둘 다 끊는다
        tag_src = _set_attr(tag_src, "data-href", None)
    return el.start, el.open_end, tag_src


def _patch(src, patches):                            # 원문 위치 기준으로 뒤에서부터
    for a, b, new in sorted(patches, key=lambda p: -p[0]):
        src = src[:a] + new + src[b:]
    return src


def _path_of(n):                                     # 요소 → select() 가 다시 찾는 경로(태그:nth-of-type 사슬)
    segs = []
    while n.parent is not None:
        if n.tag == "body":
            segs.append("body"); break
        segs.append("%s:nth-of-type(%d)" % (n.tag, [c for c in n.parent.children if c.tag == n.tag].index(n) + 1))
        n = n.parent
    return " > ".join(reversed(segs))


def _link_to(attrs):
    """요소 속성 → 가는 화면 id | None — links.Links + link_target 과 같은 규칙(href · data-href · onclick 안 .html, 공유 fixture links.json)."""
    h = attrs.get("href") or attrs.get("data-href")
    if not h and attrs.get("onclick"):
        m = links.GO_ONCLICK.search(attrs["onclick"]); h = m and m.group(1)
    return links.link_target(h) if h else None
