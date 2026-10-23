"""바뀐 클래스를 쓰는 화면 찾기 — 공용 CSS 한 줄이 다른 화면을 깨도 놓치지 않게(R9, fix 4단계).

python3 class_users.py <out> --classes a,b [--json]
python3 class_users.py <out> --css-old <고치기 전 components.css 사본> --css-new <out>/components.css [--json]

- screens.json 의 화면마다 그 화면 파일(`file`, 없으면 screens/<id>.html)의 class 속성 낱말에 그 클래스가 있으면 그 화면 id.
  글자 속에 클래스 이름이 나오는 것은 세지 않는다. 화면 파일이 없으면 건너뛰고 경고 한 줄(stderr).
- --css-old/--css-new: 두 CSS 에서 선택자·본문이 달라진 규칙의 선택자 클래스를 모아 --classes 에 더한다.
- 출력: 화면 id 한 줄씩(없으면 빈 출력) · --json → {"classes": […], "screens": […], "missing": […]}.
"""
import argparse, json, pathlib, re, sys
from html.parser import HTMLParser


# ── 순수 함수(파일 I/O 없음) ──────────────────────────────────────────────
class _Classes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = set()

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "class" and v:
                self.found.update(v.split())

    handle_startendtag = handle_starttag


def class_tokens(html):
    """HTML 글 → class 속성에 쓰인 클래스 낱말 집합."""
    p = _Classes()
    p.feed(html)
    p.close()
    return p.found


def users(pages, classes):
    """pages: [(id, html)] 순서대로 → classes 중 하나라도 class 속성에 쓰는 화면 id 목록(순서 유지)."""
    want = {c.lstrip(".") for c in classes if c.strip(".")}
    return [sid for sid, html in pages if want & class_tokens(html)]


_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_CLS = re.compile(r"\.(-?[A-Za-z_][\w-]*)")


def _rules(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {(_norm(sel), _norm(body).rstrip(";")) for sel, body in _RULE.findall(css)}


def _norm(s):
    """공백 차이만 있는 규칙은 같은 규칙으로."""
    return re.sub(r"\s*([:;,>+~])\s*", r"\1", " ".join(s.split()))


def changed_classes(old_css, new_css):
    """두 CSS 글 → 더하거나·지우거나·본문이 바뀐 규칙의 선택자에 나오는 클래스 집합."""
    return {c for sel, _ in _rules(old_css) ^ _rules(new_css) for c in _CLS.findall(sel)}


# ── 파일 I/O ─────────────────────────────────────────────────────────────
def load_pages(out):
    """<out>/screens.json → ([(id, html)], [없는 화면 id])."""
    m = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    pages, missing = [], []
    for s in m.get("screens", []):
        f = out / (s.get("file") or f"screens/{s['id']}.html")
        if f.is_file():
            pages.append((s["id"], f.read_text(encoding="utf-8")))
        else:
            missing.append(s["id"])
    return pages, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description="바뀐 클래스를 쓰는 화면 id")
    ap.add_argument("out")
    ap.add_argument("--classes", default="")
    ap.add_argument("--css-old")
    ap.add_argument("--css-new")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if bool(a.css_old) != bool(a.css_new):
        ap.error("--css-old 와 --css-new 는 함께 준다")
    classes = {c.strip().lstrip(".") for c in a.classes.split(",") if c.strip().strip(".")}
    if a.css_old:
        classes |= changed_classes(pathlib.Path(a.css_old).read_text(encoding="utf-8"),
                                   pathlib.Path(a.css_new).read_text(encoding="utf-8"))
    if not classes and not a.css_old:
        ap.error("클래스가 없다 — --classes 나 --css-old/--css-new 를 준다")
    if not classes:
        print("[class_users] 바뀐 규칙에 클래스 선택자가 없음 — 요소·전역 규칙이 바뀌었으면 모든 화면을 본다", file=sys.stderr)
    pages, missing = load_pages(pathlib.Path(a.out))
    for sid in missing:
        print(f"[class_users] 화면 파일 없음, 건너뜀: {sid}", file=sys.stderr)
    ids = users(pages, classes)
    if a.json:
        print(json.dumps({"classes": sorted(classes), "screens": ids, "missing": missing}, ensure_ascii=False))
    else:
        print("\n".join(ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
