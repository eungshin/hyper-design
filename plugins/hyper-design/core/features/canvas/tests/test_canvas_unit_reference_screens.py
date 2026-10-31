"""보관(reference) 화면은 원본만(R56, 2026-10-31) — 빌드가 덧붙인 설명 표시를 찾아 경고 한 줄. 브라우저 없음.

kind "reference" 화면 파일에 구현 메모(`data-impl-note` · `class="impl-note"`) · 캡션 줄(`class="cap"`) · 실제 창 끝 점선(`id="fold"`)이
있으면 화면마다 `경고:` 한 줄(빌드는 계속). 설명·출처는 screens.json 의 policies 로. 보관이 아닌 화면의 구현 메모는 경고하지 않는다.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_canvas as B  # noqa: E402

PURE = "<!doctype html><title>t</title><div class=\"frame\"><iframe src=\"x.html\"></iframe></div>"
NOTE = PURE + "<details class=\"impl-note\" data-impl-note open><summary>구현 메모</summary></details>"
CAP = "<div class=\"cap\"><b>제목</b></div>" + PURE
FOLD = PURE.replace("</div>", "<div class=\"fold\" id=\"fold\" hidden></div></div>")


def _out(tmp_path, screens):
    out = tmp_path / "out"
    (out / "screens").mkdir(parents=True)
    rows = []
    for sid, kind, html in screens:
        (out / "screens" / f"{sid}.html").write_text(html, encoding="utf-8")
        rows.append(dict({"id": sid, "file": f"screens/{sid}.html", "title": sid}, **({"kind": kind} if kind else {})))
    m = {"screens": rows}
    (out / "screens.json").write_text(json.dumps(m), encoding="utf-8")
    return out, m


def test_reference_screen_with_added_notes_is_named_once_per_screen(tmp_path):
    out, m = _out(tmp_path, [("old-a", "reference", NOTE), ("old-b", "reference", CAP), ("old-c", "reference", FOLD),
                             ("old-ok", "reference", PURE), ("design", None, NOTE)])
    got = B.reference_extras(out, m)
    assert [g[0] for g in got] == ["old-a", "old-b", "old-c"], got
    assert got[0][1] == ["구현 메모"] and got[1][1] == ["캡션 줄"] and got[2][1] == ["창 끝 점선"], got


def test_missing_reference_file_is_skipped(tmp_path):
    out, m = _out(tmp_path, [("old-a", "reference", NOTE)])
    (out / "screens" / "old-a.html").unlink()
    assert B.reference_extras(out, m) == []


def test_warning_line_names_screen_and_where_notes_belong(tmp_path, capsys):
    out, m = _out(tmp_path, [("old-a", "reference", NOTE + CAP)])
    B.warn_reference_extras(out, m)
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith("경고:") and "old-a" in err[0] and "구현 메모" in err[0] and "캡션 줄" in err[0] and "policies" in err[0], err
