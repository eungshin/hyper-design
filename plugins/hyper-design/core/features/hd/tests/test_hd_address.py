"""hd_address(Model) + hd locate(R30 '주소 복사') — 공유 fixture 줄 읽기 · 순수성 · CLI(도우미 없음 · 임시 HD_HOME). 브라우저 없음."""
import ast, json, subprocess, sys
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_address as A  # noqa: E402
import hdfix  # noqa: E402

FIX = json.loads((HD.parent / "canvas" / "tests" / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
HD_PY = HD / "hd.py"


def hd(home, *args, stdin=None):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=hdfix.env(home),
                       input=stdin, timeout=60)
    return r.returncode, r.stdout, r.stderr


def test_model_is_pure():
    tree = ast.parse((HD / "hd_address.py").read_text(encoding="utf-8"))
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
           {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"re"}, mods


def test_parse_reads_the_same_lines_the_canvas_builds():
    assert [A.parse(c["line"]) for c in FIX["lines"]] == [c["x"] for c in FIX["lines"]]


def test_unreadable_lines_are_none():
    assert [A.parse(x) for x in FIX["bad"]] == [None] * len(FIX["bad"])


def test_lines_picks_address_lines_from_pasted_text():
    t = "고쳐 줘:\n  hd://p/a#h1  /o/a.html · \"A\"\n\nhd://p/b  /o/b.html · \"B\"\n끝"
    assert A.lines(t) == ['hd://p/a#h1  /o/a.html · "A"', 'hd://p/b  /o/b.html · "B"']


def _line(project, screen, path, file, text):
    enc = lambda s, extra: "".join("%%%02X" % b if (c in "% #\"" + extra) else c for c in s for b in ([ord(c)] if c in "% #\"" + extra else [0]))
    return "hd://%s/%s%s  %s · \"%s\"" % (enc(project, "/?"), enc(screen, "/?"), "#" + enc(path, "") if path else "", file, text)


def test_locate_prints_file_path_and_current_outer_html(tmp_path):
    out = hdfix.make_out(tmp_path)                    # proj-a/out · home·list
    f = (out / "screens" / "home.html").as_posix()
    code, so, se = hd(tmp_path / "home", "locate", _line("proj-a", "home", "body > button:nth-of-type(1)", f, "다음"), "--json")
    assert code == 0, se
    r = json.loads(so)["items"][0]
    assert (r["project"], r["screen"], r["path"], r["tag"]) == ("proj-a", "home", "body > button:nth-of-type(1)", "button")
    assert Path(r["file"]) == Path(f) and r["html"] == "<button>다음</button>"
    code, so, se = hd(tmp_path / "home", "locate", _line("proj-a", "home", "body > button:nth-of-type(1)", f, "다음"))
    assert code == 0 and so.splitlines()[0].startswith("proj-a · home · ") and "경로: body > button:nth-of-type(1)" in so and "<button>다음</button>" in so, so


def test_locate_card_and_many_lines_from_stdin_and_project_fallback(tmp_path):
    out = hdfix.make_out(tmp_path)
    gone = (tmp_path / "moved" / "list.html").as_posix()        # 적힌 파일이 없음 → 프로젝트(out 경로) → screens.json
    lines = "\n".join([_line("proj-a", "home", None, (out / "screens" / "home.html").as_posix(), "Home"),
                       _line(out.as_posix(), "list", "h1", gone, "list")])
    code, so, se = hd(tmp_path / "home", "locate", "-", "--json", stdin="이거 고쳐 줘\n" + lines + "\n")
    assert code == 0, se
    a, b = json.loads(so)["items"]
    assert a["path"] is None and a["html"].startswith("<body><h1>home</h1>"), a
    assert Path(b["file"]) == out / "screens" / "list.html" and b["html"] == "<h1>list</h1>", b
    assert "[hd] 적힌 화면 파일이 없어" in se


def test_locate_errors_are_one_line(tmp_path):
    out = hdfix.make_out(tmp_path)
    f = (out / "screens" / "home.html").as_posix()
    for args, part in [(["locate", "http://nope"], "hd:// 주소"),
                       (["locate", _line("proj-a", "home", "body > p:nth-of-type(9)", f, "")], "0개"),
                       (["locate", _line(out.as_posix(), "nope", None, "", "")], "nope")]:
        code, so, se = hd(tmp_path / "home", *args)
        assert code == 1 and se.startswith("hd: ") and part in se and len(se.strip().splitlines()) == 1, (args, se)


def test_locate_is_read_only(tmp_path):
    out = hdfix.make_out(tmp_path)
    before = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    hd(tmp_path / "home", "locate", _line("proj-a", "home", "h1", (out / "screens" / "home.html").as_posix(), "home"))
    assert {p: p.read_bytes() for p in out.rglob("*") if p.is_file()} == before
