"""Foundation 토큰 고치기(R55) — Python 규칙(token_edit.py, 순수) + 쓰기 한 번(screen_edits.apply_token, .hd-history 원본 → restore).

token_edit: kind(이름) · decls(css) = 첫 :root{…} 의 선언(같은 이름은 뒤 것) · check(이름, 값, 있는 이름들) → (정리한 값, None) | (None, 까닭) ·
rewrite(css, 이름, 값) → 그 선언 하나만 바꾼 css(다른 글자·주석·다른 블록은 그대로).
값 규칙은 JS(modules/ds-edit.js)와 같은 표(fixtures/token-values.json) — test_canvas_unit_ds_edit.py 가 같은 표로 견준다."""
import json, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import token_edit as TE  # noqa: E402
import screen_edits  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit
TABLE = json.loads((HERE / "fixtures" / "token-values.json").read_text(encoding="utf-8"))

CSS = """/* foundation tokens — 생성물 */
@import url('https://cdn.example/x.css');

:root {
  /* 색 — --c-brand: 이 주석은 선언이 아니다 */
  --c-bg: #FAFAFA;
  --c-brand: #1B1B1B;
  --c-brand-text: #737373;
  --fs-title: 28px; --fw-title: 700; --lh-title: 1.36;
  --fs-body: 16px; --fw-body: 400; --lh-body: 1.55;
  --shadow-1: 0 2px 8px rgba(27, 27, 27, .08);
  --r-m: 12px
}

.text-large { --fs-body: 18px; }
[data-theme="dark"] { --c-brand: #FFFFFF; }
"""


def test_kind_follows_the_token_name():
    for name, kind in TABLE["kinds"]:
        assert TE.kind(name) == kind, name


@pytest.mark.parametrize("name,value,want", TABLE["values"], ids=[f"{n}={v!r}" for n, v, _ in TABLE["values"]])
def test_value_rule(name, value, want):
    names = [n for n, _ in TABLE["kinds"]]
    got, why = TE.check(name, value, names)
    if want is None:
        assert got is None and why, f"{name}={value!r} 는 거절이어야 한다"
    else:
        assert (got, why) == (want, None)


def test_semicolon_and_braces_are_refused_with_a_reason():
    got, why = TE.check("--c-brand", "#E11D48; color: red", ["--c-brand"])
    assert got is None and ";" in why


def test_unknown_name_is_refused():
    got, why = TE.check("--c-nope", "#E11D48", ["--c-brand"])
    assert got is None and "--c-nope" in why
    got, why = TE.check("c-brand", "#E11D48", ["c-brand"])
    assert got is None, "이름은 --로 시작"


def test_decls_reads_only_the_first_root_block_and_skips_comments():
    d = TE.decls(CSS)
    assert d["--c-brand"] == "#1B1B1B", "주석 안 '--c-brand:' 도, 아래 [data-theme] 도 아니다"
    assert d["--fw-title"] == "700" and d["--lh-body"] == "1.55"
    assert d["--r-m"] == "12px", "마지막 선언은 ; 없이 } 앞에서 끝나도 읽는다"
    assert "--fs-strong" not in d
    assert TE.decls("body{color:red}") == {} and TE.decls("") == {}


def test_rewrite_changes_one_declaration_and_nothing_else():
    new = TE.rewrite(CSS, "--c-brand", "#E11D48")
    assert TE.decls(new)["--c-brand"] == "#E11D48"
    assert new.replace("--c-brand: #E11D48;", "--c-brand: #1B1B1B;", 1) == CSS, "다른 글자는 바이트 그대로"
    assert '[data-theme="dark"] { --c-brand: #FFFFFF; }' in new, "다른 블록은 그대로"
    assert "--c-brand-text: #737373;" in new, "이름이 앞을 같이 쓰는 토큰은 아니다"


def test_rewrite_on_a_shared_line_and_last_declaration():
    new = TE.rewrite(CSS, "--fw-body", "600")
    assert "--fs-body: 16px; --fw-body: 600; --lh-body: 1.55;" in new
    new = TE.rewrite(CSS, "--r-m", "8px")
    assert "  --r-m: 8px\n}" in new
    assert ".text-large { --fs-body: 18px; }" in TE.rewrite(CSS, "--fs-body", "17px")


def test_rewrite_unknown_name_raises():
    with pytest.raises(TE.TokenError):
        TE.rewrite(CSS, "--c-nope", "#000000")


def _out(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "tokens.css").write_text(CSS, encoding="utf-8", newline="\n")
    return out


def _ok(out):
    return subprocess.CompletedProcess([], 0, "", "")


def test_apply_token_writes_once_with_history_and_restore_brings_bytes_back(tmp_path):
    out = _out(tmp_path)
    before = (out / "tokens.css").read_bytes()
    r = screen_edits.apply_token(out, "--c-brand", "#e11d48", build=_ok)
    assert r.get("error") is None, r
    assert r["value"] == "#E11D48" and r["old"] == "#1B1B1B" and r["stamp"]
    assert TE.decls((out / "tokens.css").read_text(encoding="utf-8"))["--c-brand"] == "#E11D48"
    assert (out / ".hd-history" / r["stamp"] / "tokens.css").read_bytes() == before, "원본을 남긴다"
    back = write_record.restore(out, r["stamp"], build=_ok)
    assert "restored" in back, back
    assert (out / "tokens.css").read_bytes() == before, "되돌리면 바이트 그대로"


def test_apply_token_refuses_bad_values_without_writing(tmp_path):
    out = _out(tmp_path)
    before = (out / "tokens.css").read_bytes()
    for name, value in (("--c-brand", "#E11D48; color: red"), ("--c-nope", "#E11D48"), ("--c-brand", "url(x)")):
        r = screen_edits.apply_token(out, name, value, build=_ok)
        assert r.get("reason") == "invalid" and r["error"], r
    assert (out / "tokens.css").read_bytes() == before
    assert not (out / ".hd-history").exists(), "거절이면 기록도 없다"


def test_apply_token_without_tokens_file(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = screen_edits.apply_token(out, "--c-brand", "#E11D48", build=_ok)
    assert r.get("reason") == "missing" and "tokens.css" in r["error"]


def test_apply_token_build_failure_reverts(tmp_path):
    out = _out(tmp_path)
    before = (out / "tokens.css").read_bytes()
    r = screen_edits.apply_token(out, "--c-brand", "#E11D48", build=lambda o: subprocess.CompletedProcess([], 1, "", "boom"))
    assert r["error"].startswith(write_record.BUILD_FAIL)
    assert (out / "tokens.css").read_bytes() == before


def test_file_watch_reports_tokens_change_as_its_own_entry(tmp_path):
    """/api/files(R55): tokens.css 가 바뀌면 '@tokens' 가 바뀐 목록에 든다 — 다른 탭·AI 가 고친 토큰도 Foundation·DS 카드가 다시 읽게."""
    import os, busy
    out = _out(tmp_path)
    (out / "screens.json").write_text(json.dumps({"screens": []}), encoding="utf-8")
    fw = busy.FileWatch()
    assert fw.tick(busy.scan(out, {})) == []
    f = out / "tokens.css"
    st = f.stat()
    os.utime(f, (st.st_atime, st.st_mtime + 5))
    assert fw.tick(busy.scan(out, {})) == ["@tokens"]
