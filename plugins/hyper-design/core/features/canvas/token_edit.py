"""Model — Foundation 토큰 하나 고치기(R55): tokens.css 첫 :root{…} 의 선언 읽기 · 값 검사 · 그 선언 하나만 바꿔 쓰기. I/O 없음.

kind(이름) → 'color'|'size'|'weight'|'line'|'radius'|'space'|'shadow'|'other' (이름 앞부분으로 — modules/ds-edit.js kindOf 와 같은 표)
decls(css) → {이름: 값} — 첫 :root 블록만, 주석은 건너뜀, 같은 이름은 뒤 것(CSS 처럼)
check(이름, 값, 있는 이름들) → (정리한 값, None) | (None, 까닭 한국어) — 모르는 이름·자유 CSS(; { } < > \\ url( expression 주석) 거절, 종류마다 모양
rewrite(css, 이름, 값) → 그 선언(뒤 것) 값만 바꾼 css — 다른 글자는 그대로. 없는 이름 = TokenError
label(이름) → 쉬운 이름(Foundation 탭 표 COLOR_NAMES·FS_NAMES… — 빌드와 부품 고치기 창이 같이 쓴다)
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


# 쉬운 이름(Foundation 탭 · 부품 고치기 창, build_canvas 가 가져다 쓴다)
COLOR_GROUPS = [("bg", "배경"), ("text", "글자"), ("brand", "브랜드"), ("sem", "의미색 — 성공 · 주의 · 정보 · 오류"), ("etc", "선 · 그림자 · 기타")]
COLOR_NAMES = {   # 토큰 → (묶음, 쉬운 이름). 표에 없는 변수는 변수 이름 그대로 '기타'에.
    "--c-bg": ("bg", "화면 바탕"), "--c-surface": ("bg", "블록 바탕"), "--c-surface-2": ("bg", "한 단계 깊은 바탕"),
    "--c-disabled-bg": ("bg", "못 누르는 칸 바탕"), "--c-overlay": ("bg", "뒤를 가리는 막"),
    "--c-text": ("text", "본문 글자"), "--c-text-1": ("text", "제목·본문 글자"), "--c-text-2": ("text", "보조 글자"),
    "--c-text-3": ("text", "흐린 설명 글자"), "--c-text-disabled": ("text", "못 누르는 글자"),
    "--c-brand": ("brand", "버튼·강조 색"), "--c-on-brand": ("brand", "버튼 위 글자"), "--c-brand-text": ("brand", "강조 글자"),
    "--c-brand-tint": ("brand", "연한 강조 바탕"), "--c-brand-tint-text": ("brand", "연한 강조 위 글자"),
    "--c-brand-pressed": ("brand", "눌렀을 때 버튼 색"), "--c-focus": ("brand", "고른 칸 테두리"),
    "--c-accent": ("brand", "포인트 색"), "--c-accent-text": ("brand", "포인트 글자"),
    "--c-success": ("sem", "성공 색"), "--c-success-tint": ("sem", "성공 연한 바탕"), "--c-success-tint-text": ("sem", "성공 바탕 위 글자"),
    "--c-warning": ("sem", "주의 색"), "--c-warning-tint": ("sem", "주의 연한 바탕"), "--c-warning-tint-text": ("sem", "주의 바탕 위 글자"),
    "--c-info": ("sem", "정보 색"), "--c-info-tint": ("sem", "정보 연한 바탕"), "--c-info-tint-text": ("sem", "정보 바탕 위 글자"),
    "--c-danger": ("sem", "오류 색"), "--c-danger-tint": ("sem", "오류 연한 바탕"), "--c-danger-tint-text": ("sem", "오류 바탕 위 글자"),
    "--c-line": ("etc", "구분선"), "--c-line-strong": ("etc", "진한 테두리"), "--c-shadow": ("etc", "그림자 색"),
}
FS_NAMES = {"title": "큰 제목", "h2": "블록 제목", "body": "본문", "strong": "강조 본문", "sub": "보조 글", "caption": "작은 글"}
SPACE_NAMES = {"--stack-s": "작은 간격", "--stack-m": "보통 간격", "--stack-l": "큰 간격", "--page-x": "화면 좌우 여백",
               "--block-pad": "블록 안쪽 여백", "--block-gap": "블록 사이", "--row-py": "줄 위아래 여백"}
R_NAMES = {"--r-s": "작은 모서리", "--r-m": "보통 모서리", "--r-l": "큰 모서리", "--r-pill": "알약 모양"}
SH_NAMES = {"--shadow-1": "약한 그림자", "--shadow-2": "뜬 그림자", "--shadow-3": "가장 뜬 그림자"}
H_NAMES = {"--h-appbar": "앱바 높이", "--h-btn": "버튼 높이", "--h-btn-s": "작은 버튼 높이", "--h-tab": "탭바 높이", "--h-row": "목록 행 높이"}


class TokenError(ValueError):
    pass


def label(name):
    """토큰의 쉬운 이름(Foundation 탭이 보이는 이름과 같은 표) — 표에 없으면 이름 그대로."""
    n = str(name or "")
    if n in COLOR_NAMES:
        return COLOR_NAMES[n][1]
    for pre, table in (("--fs-", FS_NAMES), ("--fw-", FS_NAMES), ("--lh-", FS_NAMES)):
        if n.startswith(pre) and n[len(pre):] in table:
            return table[n[len(pre):]] + {"--fs-": "", "--fw-": " 굵기", "--lh-": " 줄 높이"}[pre]
    return SPACE_NAMES.get(n) or R_NAMES.get(n) or SH_NAMES.get(n) or H_NAMES.get(n) or n


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
