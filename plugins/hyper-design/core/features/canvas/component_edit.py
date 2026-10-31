"""Model — Components 부품 고치기(R55 phase C): out/components.css 규칙에서 고른 요소를 겨누는 규칙·바꿀 칸 찾기 · 검사 · 그 var(--토큰) 하나만 바꿔 쓰기. I/O 없음.

사용자 결정(10-30): 부품 속성은 Foundation 토큰 가운데 **같은 묶음(family)** 안에서만 고른다 — 자유 값 없음(값은 Foundation 탭에서만 바뀐다).
family(이름) → 'color'|'radius'|'space'|'font-size'|'box'|'weight'|'line'|'shadow'|None   (token_edit.kind 위에 — 크기는 글자 크기 --fs-* 와 높이·너비 --h-*/--w-* 로 나눔)
same(가, 나) → 같은 묶음인가(묶음 없음 = 아니다) — JS HD.dsEdit.family·same 과 같은 표(tests/fixtures/component-families.json)
rules(css) → [{selector(정리한 글), parts:[…], decls:[{prop, slots:[{index, token, at:(시작, 끝)}]}]}] — 맨 위 규칙만(@media·@keyframes 안은 건너뜀), 주석·글 따옴표 안은 구조로 보지 않음
slots(css, classes, tag, titles) → 그 요소를 겨누는 규칙들 [{selector, state('' = 바탕·변형, 아니면 '누를 때'…), shared:[부품 이름](목록이 다른 부품도 이름 부르면), slots:[{prop, label, index, token, family}]}]
  겨눔 = 선택자 목록의 한 조각이 겹 선택자 하나(띄어쓰기·> + ~ 없음)이고 그 클래스가 모두 요소에 있다(태그가 있으면 같다). 바꿀 칸 = 묶음이 있는 var(--토큰)만.
  차례: 바탕·변형(클래스 적은 것부터) 다음 상태 규칙(파일 차례). 같은 선택자가 여러 번 = 하나로(뒤 선언이 이김).
check(css, 있는 토큰 이름들, selector, prop, index, from, to) → 까닭(한국어) | None
rewrite(css, selector, prop, index, from, to) → 그 선택자의 마지막 규칙·그 속성 마지막 선언·index 번째 var( 의 이름만 바꾼 css(다른 글자 그대로) | ComponentError
titles(components.html) → {data-key: data-title} — 함께 바뀌는 부품 이름
부르는 곳: screen_edits.apply_component · component_slots(Edge) · 테스트.
"""
import re

import token_edit as TE  # 토큰 종류·이름·쉬운 이름(같은 Model 층)

PROP_LABELS = (("background", "배경"), ("color", "글자 색"), ("border-radius", "모서리"), ("border-top-left-radius", "모서리"),
               ("border-top-right-radius", "모서리"), ("border-bottom-left-radius", "모서리"), ("border-bottom-right-radius", "모서리"),
               ("box-shadow", "그림자"), ("font-size", "글자 크기"), ("font-weight", "굵기"), ("line-height", "줄 높이"),
               ("gap", "간격"), ("row-gap", "간격"), ("column-gap", "간격"), ("outline", "윤곽선"), ("outline-color", "윤곽선"),
               ("fill", "채움"), ("stroke", "선 색"))
PREFIX_LABELS = (("background", "배경"), ("border", "테두리"), ("padding", "안쪽 여백"), ("margin", "바깥 여백"),
                 ("min-height", "높이"), ("max-height", "높이"), ("height", "높이"), ("min-width", "너비"), ("max-width", "너비"), ("width", "너비"))
STATES = ((":active", "누를 때"), (":disabled", "못 누를 때"), ("[aria-disabled=\"true\"]", "못 누를 때"), ("[disabled]", "못 누를 때"),
          (":hover", "올렸을 때"), (":focus-visible", "초점"), (":focus-within", "초점"), (":focus", "초점"),
          ("[aria-checked=\"true\"]", "켰을 때"), ("[aria-selected=\"true\"]", "고른 것"), ("[aria-current=\"page\"]", "지금 위치"),
          ("::before", "앞 꾸밈"), ("::after", "뒤 꾸밈"))
VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
BIT = re.compile(r"\.[A-Za-z0-9_-]+|\[[^\]]*\]|::?[A-Za-z-]+(\([^)]*\))?")


class ComponentError(ValueError):
    pass


def family(name):
    if not isinstance(name, str) or not TE.NAME.match(name):
        return None
    k = TE.kind(name)
    if k == "size":
        return "font-size" if name.startswith("--fs-") else "box"
    return None if k == "other" else k


def same(a, b):
    fa = family(a)
    return fa is not None and fa == family(b)


def prop_label(prop):
    p = prop.lower()
    for k, v in PROP_LABELS:
        if p == k:
            return v
    for k, v in PREFIX_LABELS:
        if p.startswith(k):
            return v
    return p


def _mask(css):
    """주석·따옴표 글을 같은 길이 빈칸으로 — 자리는 그대로, 구조(중괄호·쌍반점)만 보게."""
    m = re.sub(r"/\*.*?\*/", lambda x: " " * len(x.group(0)), css, flags=re.S)
    return re.sub(r"\"[^\"\n]*\"|'[^'\n]*'", lambda x: x.group(0)[0] + " " * (len(x.group(0)) - 2) + x.group(0)[-1], m)


def _split(s, sep):
    """괄호·대괄호 밖의 sep 로 나눈 [(시작, 끝)]."""
    out, d, st = [], 0, 0
    for i, ch in enumerate(s):
        if ch in "([":
            d += 1
        elif ch in ")]":
            d -= 1
        elif ch == sep and d == 0:
            out.append((st, i)); st = i + 1
    out.append((st, len(s)))
    return out


def norm(selector):
    s = " ".join(str(selector or "").split())
    return ", ".join(s[a:b].strip() for a, b in _split(s, ",") if s[a:b].strip())


def rules(css):
    m, res, pos = _mask(css), [], 0
    while True:
        j = m.find("{", pos)
        if j < 0:
            break
        st = max(m.rfind(";", pos, j) + 1, m.rfind("}", pos, j) + 1, pos)
        d, k = 1, j + 1
        while k < len(m) and d:
            d += 1 if m[k] == "{" else -1 if m[k] == "}" else 0
            k += 1
        pre = css[st:j].strip()
        pos = k
        if not pre or pre.startswith("@") or "{" in m[j + 1:k - 1]:
            continue                                  # @media·@keyframes 안은 건너뜀
        bs, decls = j + 1, []
        for a, b in _split(m[bs:k - 1], ";"):
            seg = m[bs + a:bs + b]
            c = seg.find(":")
            if c < 0:
                continue
            prop = seg[:c].strip().lower()
            if not re.match(r"^-?[a-z][a-z-]*$", prop):
                continue
            vs = bs + a + c + 1
            slots = [{"index": i, "token": v.group(1), "at": (vs + v.start(1), vs + v.end(1))}
                     for i, v in enumerate(VAR.finditer(m[vs:bs + b]))]
            decls.append({"prop": prop, "slots": slots})
        sel = norm(pre)
        res.append({"selector": sel, "parts": [sel[a:b].strip() for a, b in _split(sel, ",")], "decls": decls})
    return res


def _compound(part):
    """겹 선택자 하나 → (태그, [클래스], [상태 글]) | None(띄어쓰기·> + ~ 가 있음·모르는 모양)."""
    p = part.strip()
    if len(_split(p, " ")) > 1:
        return None
    if re.search(r"[>+~]", re.sub(r"\[[^\]]*\]|\([^)]*\)", "", p)):
        return None
    t = re.match(r"^([A-Za-z][A-Za-z0-9-]*|\*)?", p)
    tag, rest, classes, states = (t.group(1) or "").lower(), p[t.end():], [], []
    while rest:
        b = BIT.match(rest)
        if not b:
            return None
        x = b.group(0)
        if x.startswith("."):
            classes.append(x[1:])
        elif b.group(1) and not x.startswith("::"):
            return None                               # :not(…)·:has(…) 같은 함수 = 겨눔을 셈하지 않는다
        else:
            states.append(x)
        rest = rest[b.end():]
    return tag, classes, states


def _state(bits):
    out = []
    for x in bits:
        lab = next((v for k, v in STATES if k == x.replace("'", '"')), x)
        if lab not in out:
            out.append(lab)
    return " · ".join(out)


def _first_class(part):
    c = re.findall(r"\.([A-Za-z0-9_-]+)", re.split(r"[\s>+~]+", part.strip())[-1])
    return c[0] if c else None


def slots(css, classes, tag="", titles=None):
    have, tag, titles = set(classes or ()), str(tag or "").lower(), titles or {}
    merged, order = {}, []
    for r in rules(css):
        hits, states, plain = [], [], False
        for p in r["parts"]:
            c = _compound(p)
            if not c or not c[1] or not set(c[1]) <= have or (c[0] and c[0] != "*" and c[0] != tag):
                continue
            hits.append(p)
            if c[2]:
                states.extend(c[2])
            else:
                plain = True
        if not hits:
            continue
        g = merged.get(r["selector"])
        if g is None:
            names = []
            if len(hits) < len(r["parts"]):
                for p in r["parts"]:
                    fc = _first_class(p)
                    n = titles.get(fc, "." + fc) if fc else p
                    if n not in names:
                        names.append(n)
            g = merged[r["selector"]] = {"selector": r["selector"], "state": "" if plain else _state(states), "shared": names,
                                         "decls": {}, "n": min(len(_compound(p)[1]) for p in hits), "at": len(order)}
            order.append(g)
        for d in r["decls"]:
            g["decls"].pop(d["prop"], None)
            g["decls"][d["prop"]] = d                 # 뒤 선언이 이긴다(CSS 처럼)
    out = []
    for g in order:
        sl = []
        for prop, d in g["decls"].items():
            ok = [s for s in d["slots"] if family(s["token"])]
            for n, s in enumerate(ok):
                lab = prop_label(prop) + (" %d" % (n + 1) if len(ok) > 1 else "")
                sl.append({"prop": prop, "label": lab, "index": s["index"], "token": s["token"], "family": family(s["token"])})
        if sl:
            out.append({"selector": g["selector"], "state": g["state"], "shared": g["shared"], "slots": sl, "_k": (1 if g["state"] else 0, 0 if g["state"] else g["n"], g["at"])})
    out.sort(key=lambda g: g["_k"])
    for g in out:
        del g["_k"]
    return out


def _find(css, selector, prop, index):
    """→ (그 slot, None) | (None, 까닭)."""
    sel, last = norm(selector), None
    rs = [r for r in rules(css) if r["selector"] == sel]
    if not rs:
        return None, "그런 규칙이 없어요: %s" % sel
    for r in rs:
        for d in r["decls"]:
            if d["prop"] == str(prop).lower():
                last = d
    if last is None:
        return None, "그 규칙에 그런 속성이 없어요: %s" % prop
    if not 0 <= index < len(last["slots"]):
        return None, "그 자리에 토큰이 없어요: %s %s #%d" % (sel, prop, index)
    return last["slots"][index], None


def check(css, names, selector, prop, index, frm, to):
    if not isinstance(selector, str) or not isinstance(prop, str) or not selector.strip() or not prop.strip():
        return "선택자·속성이 글이 아니에요"
    if not isinstance(index, int) or isinstance(index, bool):
        return "자리(index)는 정수예요"
    for n in (frm, to):
        if not isinstance(n, str) or not TE.NAME.match(n):
            return "토큰 이름이 아니에요: %r" % (n,)
    if family(frm) is None:
        return "바꿀 수 없는 토큰이에요: %s (Foundation 묶음이 아님)" % frm
    if to not in set(names or ()):
        return "없는 토큰: %s" % to
    if not same(frm, to):
        return "같은 묶음의 토큰만 고를 수 있어요: %s(%s) → %s(%s)" % (frm, family(frm), to, family(to) or "묶음 없음")
    s, why = _find(css, selector, prop, index)
    if why:
        return why
    if s["token"] != frm:
        return "그 자리는 %s 예요(%s 가 아님) — 다시 열어 주세요" % (s["token"], frm)
    return None


def rewrite(css, selector, prop, index, frm, to):
    s, why = _find(css, selector, prop, index)
    if why:
        raise ComponentError(why)
    if s["token"] != frm:
        raise ComponentError("그 자리는 %s 예요(%s 가 아님)" % (s["token"], frm))
    a, b = s["at"]
    return css[:a] + to + css[b:]


def titles(html):
    out = {}
    for tag in re.findall(r"<section\b[^>]*>", html or "", flags=re.I):
        k = re.search(r"""\bdata-key\s*=\s*["']([^"']+)["']""", tag)
        t = re.search(r"""\bdata-title\s*=\s*["']([^"']+)["']""", tag)
        if k and t:
            out[k.group(1)] = t.group(1)
    return out
