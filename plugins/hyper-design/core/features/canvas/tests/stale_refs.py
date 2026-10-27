"""낡은 선택자 찾기: `python tests/stale_refs.py [base]` (기본 base = HEAD).

`git diff <base>` 에서 modules/*.js · *.css · canvas_template.html 의 지운 줄에 있던 `.class` · `#id` · `data-x` 가운데
지금 캔버스 코드 어디에도 없는 것을 골라, 아직 tests/ 에 남은 곳을 보인다(의심 목록 — 확인은 사람이).
"""
import re, subprocess, sys
from pathlib import Path

CANVAS = Path(__file__).resolve().parent.parent
TESTS = CANVAS / "tests"

_QUOTED = re.compile(r"""(['"`])(.*?)\1""")
_SEL = re.compile(r"(?<![\w-])([.#])([A-Za-z_][\w-]*)")
_DATA = re.compile(r"\bdata-([a-z][a-z0-9-]*)")
_DATASET = re.compile(r"\bdataset\.([A-Za-z]\w*)")
_CLASSLIST = re.compile(r"classList\.(?:add|remove|toggle|contains)\(([^)]*)\)")
_ATTR = re.compile(r"""\b(id|class|className)\s*[=:]\s*(['"`])([^'"`]*)\2""")


def _kebab(s):
    return re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), s)


def tokens(line, css=False):
    """한 줄에서 ('.', 이름) · ('#', 이름) · ('data-', 이름)."""
    out = set()
    for kind, name in _SEL.findall(line if css else " ".join(q for _, q in _QUOTED.findall(line))):
        if not re.fullmatch(r"[0-9a-fA-F]{3,8}", name) or kind == ".":   # #fff 같은 색은 빼고
            out.add((kind, name))
    out |= {("data-", n) for n in _DATA.findall(line)}
    out |= {("data-", _kebab(n)) for n in _DATASET.findall(line)}
    for args in _CLASSLIST.findall(line):
        out |= {(".", n) for _, n in _QUOTED.findall(args) if re.fullmatch(r"[A-Za-z_][\w-]*", n)}
    for attr, _, val in _ATTR.findall(line):
        k = "#" if attr == "id" else "."
        out |= {(k, n) for n in val.split() if re.fullmatch(r"[A-Za-z_][\w-]*", n)}
    return out


def removed_tokens(diff_text):
    """diff 의 지운 줄(-)에서 나온 토큰 — 파일 머리(---)는 뺀다."""
    out, css = set(), False
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            css = line.endswith(".css")
        elif line.startswith("-") and not line.startswith("---"):
            out |= tokens(line[1:], css)
    return out


def still_used(tok, source):
    kind, name = tok
    pat = (r"data-" + re.escape(name) + r"\b") if kind == "data-" else (r"(?<![\w-])" + re.escape(name) + r"(?![\w-])")
    return re.search(pat, source) is not None


def test_hits(tok, files):
    kind, name = tok
    if kind == "data-":
        pat = re.compile(r"data-" + re.escape(name) + r"(?![\w-])|dataset\." + re.escape(re.sub(r"-(\w)", lambda m: m.group(1).upper(), name)) + r"\b")
    else:
        pat = re.compile(re.escape(kind) + re.escape(name) + r"(?![\w-])")
    hits = []
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pat.search(line):
                hits.append((f.name, i, line.strip()[:120]))
    return hits


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    base = argv[1] if len(argv) > 1 else "HEAD"
    paths = ["modules", "canvas_template.html"] + [str(p.relative_to(CANVAS)) for p in CANVAS.glob("*.css")]
    r = subprocess.run(["git", "-C", str(CANVAS), "diff", base, "--", *paths], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print(r.stderr.strip()); return 2
    diff = "\n".join(b for b in r.stdout.split("\ndiff --git") if re.search(r"\.(js|css|html)\b", b.split("\n", 1)[0]))
    gone = removed_tokens(diff)
    src = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in
                    [*CANVAS.glob("modules/*.js"), *CANVAS.glob("modules/*.css"), *CANVAS.glob("*.css"), CANVAS / "canvas_template.html"] if p.exists())
    gone = sorted(t for t in gone if not still_used(t, src))
    tests = sorted(TESTS.glob("*.py"))
    n = 0
    for tok in gone:
        for name, i, line in test_hits(tok, tests):
            n += 1
            print(f"{tok[0]}{tok[1]}\t{name}:{i}\t{line}")
    print(f"[stale_refs] base {base}: 지운 토큰 {len(gone)} · 테스트에 남은 곳 {n}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
