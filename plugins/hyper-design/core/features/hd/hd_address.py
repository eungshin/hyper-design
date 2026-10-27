"""Model — 주소 줄 읽기(R30 '주소 복사'): 캔버스가 복사한 'hd://<프로젝트>/<화면>[#<요소 경로>]  <화면 파일> · "<글>"' → 칸들. 순수(I/O 없음).

같은 규칙의 만들기·읽기 = canvas modules/address.js(build·parse). 공유 fixture = canvas/tests/fixtures/addresses.json — 두 쪽 테스트가 같은 줄을 읽는다.
글자 되돌리기: 주소 부분만 퍼센트(%XX, UTF-8). 파일 경로는 그대로, 글은 \\ 와 " 앞의 \\ 를 뗀다.
parse(line) → {project, screen, path|None, file|None, text|None} | None(hd:// 로 시작하지 않음 · 프로젝트·화면 없음 · 깨진 %)
lines(text) → 글 안의 주소 줄만(앞뒤 공백 뺌 — 여러 줄을 한꺼번에 붙여도 줄마다)
"""
import re

_TAIL = re.compile(r'^(.*?)\s*· "((?:[^"\\]|\\.)*)"$')
_PCT = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _dec(s):
    """%XX 묶음 → UTF-8 글. 깨진 바이트·홀로 선 % 는 None(읽지 못함 — JS decodeURIComponent 와 같은 판정)."""
    try:
        out = _PCT.sub(lambda m: bytes.fromhex(m.group(0).replace("%", "")).decode("utf-8"), s)
    except UnicodeDecodeError:
        return None
    return None if "%" in _PCT.sub("", s) else out


def parse(line):
    s = str(line if line is not None else "").strip()
    if not s.startswith("hd://"):
        return None
    m = re.search(r"\s", s)
    addr, rest = (s, "") if not m else (s[:m.start()], s[m.start():].strip())
    body = addr[5:]
    head, _, frag = body.partition("#")
    has_frag = "#" in body
    project_raw, sl, screen_raw = head.partition("/")
    screen_raw = screen_raw[:-1] if screen_raw.endswith("/") else screen_raw
    if not sl or not project_raw or not screen_raw:
        return None
    project, screen = _dec(project_raw), _dec(screen_raw)
    path = _dec(frag) if has_frag and frag else None
    if not project or not screen or (has_frag and frag and path is None):
        return None
    file, text = rest or None, None
    t = _TAIL.match(rest)
    if t:
        file = t.group(1).strip() or None
        text = re.sub(r'\\([\\"])', r"\1", t.group(2))
    return {"project": project, "screen": screen, "path": path, "file": file, "text": text}


def lines(text):
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip().startswith("hd://")]
