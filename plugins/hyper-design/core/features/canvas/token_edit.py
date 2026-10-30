"""Model — Foundation 토큰 하나 고치기(R55): tokens.css 첫 :root{…} 의 선언 읽기 · 값 검사 · 그 선언 하나만 바꿔 쓰기. I/O 없음.

kind(이름) → 'color'|'size'|'weight'|'line'|'radius'|'space'|'shadow'|'other' (이름 앞부분으로 — modules/ds-edit.js kindOf 와 같은 표)
decls(css) → {이름: 값} — 첫 :root 블록만, 주석은 건너뜀, 같은 이름은 뒤 것(CSS 처럼)
check(이름, 값, 있는 이름들) → (정리한 값, None) | (None, 까닭 한국어) — 모르는 이름·자유 CSS(; { } < > \\ url( expression 주석) 거절, 종류마다 모양
rewrite(css, 이름, 값) → 그 선언(뒤 것) 값만 바꾼 css — 다른 글자는 그대로. 없는 이름 = TokenError
값 규칙은 JS(modules/ds-edit.js check)와 같은 표(tests/fixtures/token-values.json)로 견준다.
부르는 곳: screen_edits.apply_token(쓰기 한 번) · 테스트.
"""
import re

NAME = re.compile(r"^--[A-Za-z0-9-]+$")
MAX = 200
BAD = re.compile(r"[;{}<>\\\x00-\x1f]")
BAD_WORDS = ("url(", "expression", "/*", "*/", "javascript:", "@import")
SPACE_EXACT = ("--page-x", "--block-pad", "--block-gap", "--row-py")
KINDS = (("--c-", "color"), ("--fs-", "size"), ("--fw-", "weight"), ("--lh-", "line"), ("--r-", "radius"),
         ("--shadow-", "shadow"), ("--stack-", "space"), ("--space-", "space"), ("--gap-", "space"), ("--h-", "size"), ("--w-", "size"))
HEX = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")
FUNC = re.compile(r"^(rgb|rgba|hsl|hsla)\(\s*[0-9.,%\s/+-]+\)$", re.I)
LEN = re.compile(r"^(\d+(\.\d+)?|\.\d+)(px|rem|em|%|vw|vh)$")
NUM = re.compile(r"^(\d+(\.\d+)?|\.\d+)$")
SHADOW = re.compile(r"^[#\w\s.,()%/-]+$")


class TokenError(ValueError):
    pass


def kind(name):
    n = str(name or "")
    if n in SPACE_EXACT:
        return "space"
    for pre, k in KINDS:
        if n.startswith(pre):
            return k
    return "other"


def _mask(css):
    """주석을 같은 길이의 빈칸으로 — 자리(index)는 그대로 두고 선언만 찾게."""
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


def _root(css):
    """첫 :root{…} 몸통 [시작, 끝) — 없거나 안에 { 가 또 있으면(모양이 다름) None."""
    m = _mask(css)
    hit = re.search(r"(^|[\s,}])\:root\s*\{", m)
    if not hit:
        return None
    s = hit.end()
    e = m.find("}", s)
    if e < 0 or "{" in m[s:e]:
        return None
    return s, e


def _spans(css, name):
    """첫 :root 안 그 이름 선언의 값 자리들 [(값 시작, 값 끝)] — 값 = ':' 뒤 빈칸 다음부터 ';' 또는 '}' 앞 빈칸 전까지."""
    r = _root(css)
    if not r:
        return []
    m = _mask(css)
    s, e = r
    out = []
    for hit in re.finditer(r"(?<![\w-])" + re.escape(name) + r"\s*:", m[s:e]):
        vs = s + hit.end()
        ve = vs
        while ve < e and m[ve] != ";":
            ve += 1
        while vs < ve and m[vs].isspace():
            vs += 1
        end = ve
        while end > vs and m[end - 1].isspace():
            end -= 1
        out.append((vs, end))
    return out


def decls(css):
    r = _root(css or "")
    if not r:
        return {}
    m = _mask(css)
    res = {}
    for hit in re.finditer(r"(?<![\w-])(--[A-Za-z0-9-]+)\s*:", m[r[0]:r[1]]):
        sp = _spans(css, hit.group(1))
        if sp:
            vs, ve = sp[-1]
            res[hit.group(1)] = css[vs:ve]
    return res


def check(name, value, names):
    if not isinstance(name, str) or not NAME.match(name):
        return None, "토큰 이름이 아니에요: %r" % (name,)
    if name not in set(names or ()):
        return None, "없는 토큰: %s" % name
    if not isinstance(value, str):
        return None, "값이 글이 아니에요"
    v = value.strip()
    if not v:
        return None, "값이 비었어요"
    if len(v) > MAX:
        return None, "값이 %d자를 넘어요" % MAX
    b = BAD.search(v)
    if b:
        return None, "쓸 수 없는 글자가 있어요: %r (; { } < > \\ 는 안 돼요)" % b.group(0)
    low = v.lower()
    for w in BAD_WORDS:
        if w in low:
            return None, "쓸 수 없는 값이에요: %s" % w
    k = kind(name)
    if k == "color":
        if HEX.match(v):
            return v.upper(), None
        if FUNC.match(v):
            return v, None
        return None, "색은 #RRGGBB 처럼 써요"
    if k in ("size", "space", "radius"):
        if v == "0" or LEN.match(v):
            return v, None
        return None, "숫자와 단위(px·rem·em·%)로 써요"
    if k == "weight":
        if NUM.match(v) and "." not in v and 100 <= int(v) <= 900:
            return v, None
        return None, "굵기는 100~900 사이 숫자예요"
    if k == "line":
        if NUM.match(v) and 0.5 <= float(v) <= 5:
            return v, None
        if LEN.match(v):
            return v, None
        return None, "줄 높이는 0.5~5 사이 숫자예요"
    if k == "shadow":
        if SHADOW.match(v):
            return v, None
        return None, "그림자 값에 쓸 수 없는 글자가 있어요"
    return v, None


def rewrite(css, name, value):
    sp = _spans(css, name)
    if not sp:
        raise TokenError("없는 토큰: %s" % name)
    vs, ve = sp[-1]
    return css[:vs] + value + css[ve:]
