"""part_stamp.py(Model) — 앱 부품(parts.json) 도장·낡음 규칙·모양 검사·post 단계. I/O 없음(통합은 test_canvas_unit_parts_file.py · hd/tests/test_hd_parts.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import part_stamp as PS  # noqa: E402

A, B = "a" * 40, "b" * 40
NOW, OLD = "g:" + A[:16], "g:" + B[:16]
REPO = "C:/Code/app"


def part(**kw):
    p = {"file": "screens/mock-a.html", "repo": REPO, "watch": ["ui/src"], "build": ["node", "build.mjs", "{out}"],
         "stamp": NOW, "dirty": False, "built_at": "2026-10-27T10:00:00"}
    p.update(kw)
    return p


def test_tree_of_one_path_is_the_tree_sha_prefix_and_many_paths_mix():
    assert PS.tree_of([("ui/src", A + "\n")]) == NOW, "한 경로 = git 나무 sha 앞 16(code_stamp.tree_stamp 와 같은 모양)"
    two = PS.tree_of([("ui/src", A), ("ui/vite.config.js", B)])
    assert two.startswith("g:") and len(two) == 18 and two not in (NOW, OLD)
    assert two == PS.tree_of([("ui/vite.config.js", B), ("ui/src", A)]), "차례와 상관없이"
    assert two != PS.tree_of([("ui/src", B), ("ui/vite.config.js", A)]), "어느 경로의 sha 인지도 든다"
    assert PS.tree_of([("ui/src", "fatal: bad")]) is None and PS.tree_of([]) is None and PS.tree_of(None) is None, "못 잼 = None"


def test_state_judges_only_when_the_current_stamp_is_known():
    assert PS.state(part(), NOW) == "fresh"
    assert PS.state(part(), OLD) == "stale"
    assert PS.state(part(stamp=None), NOW) == "stale", "도장 없이 빌드한 부품 = 낡음"
    assert PS.state(part(), None) == "unknown", "지금 도장을 모르면 판단하지 않는다(code_stamp.stale 과 같음)"


def test_parse_keeps_good_parts_and_skips_bad_ones_with_one_line_each():
    data = {"version": 1, "parts": [
        part(),
        part(file="../escape.html"),
        part(file="C:/abs.html"),
        part(repo="relative/repo"),
        part(watch=[]),
        part(watch=["../up"]),
        part(build=[]),
        part(build=["node", "build.mjs"]),                 # 결과 경로 {out} 이 없음
        part(post=[{"nope": 1}]),
        "junk",
        part(file="screens\\mock-b.html", build=["node", "b.mjs"], env={"MOCKUP_OUT": "{out}"},
             post=[{"inject_before_body": '<script src="../palette.js"></script>'}]),
    ]}
    parts, warns = PS.parse(data)
    assert [p["file"] for p in parts] == ["screens/mock-a.html", "screens/mock-b.html"], "역슬래시는 / 로"
    assert parts[1]["env"] == {"MOCKUP_OUT": "{out}"} and parts[1]["post"][0]["inject_before_body"].startswith("<script")
    assert len(warns) == 9 and all(w.startswith("[hd] parts.json") for w in warns), warns
    assert parts[0]["dirty"] is False and PS.parse({"version": 1, "parts": [part(dirty=None, stamp=None, built_at=None)]})[0][0]["dirty"] is False


def test_parse_whole_file_errors():
    for bad in (None, [], {"version": 2, "parts": []}, {"version": 1, "parts": {}}):
        parts, warns = PS.parse(bad)
        assert parts == [] and len(warns) == 1 and warns[0].startswith("[hd] parts.json"), bad
    assert PS.parse({"version": 1, "parts": []}) == ([], [])


def test_row_label_shows_stale_and_dirty():
    r = PS.row(part(dirty=True), OLD, dirty_now=False)
    assert r["state"] == "stale" and r["stale"] is True and r["dirty"] is True and r["current"] == OLD
    assert "낡음" in r["label"] and "미커밋 변경 포함" in r["label"]
    assert PS.row(part(), NOW, False)["label"] == "최신"
    assert PS.row(part(), None, None)["state"] == "unknown"


def test_select_by_file_name_or_stem():
    ps = [part(), part(file="screens/mock-b.html")]
    assert PS.select(ps, None) == ps and PS.select(ps, "*") == ps
    assert [p["file"] for p in PS.select(ps, "screens/mock-b.html")] == ["screens/mock-b.html"]
    assert [p["file"] for p in PS.select(ps, "mock-b.html")] == ["screens/mock-b.html"]
    assert [p["file"] for p in PS.select(ps, "mock-a")] == ["screens/mock-a.html"]
    assert [p["file"] for p in PS.select(ps, "screens\\mock-a.html")] == ["screens/mock-a.html"]
    assert PS.select(ps, "zzz") == []


def test_apply_post_injects_once_before_the_last_body_close():
    tag = '<script src="../palette.js"></script>'
    html = "<html><body><p>x</p></BODY></html>"
    once = PS.apply_post(html, [{"inject_before_body": tag}])
    assert once == "<html><body><p>x</p>" + tag + "</BODY></html>"
    assert PS.apply_post(once, [{"inject_before_body": tag}]) == once, "이미 있으면 다시 넣지 않는다"
    assert PS.apply_post("<p>no body</p>", [{"inject_before_body": tag}]) == "<p>no body</p>" + tag
    assert PS.apply_post(html, None) == html and PS.apply_post(html, []) == html


def test_record_updates_only_the_matching_entry_and_keeps_the_rest():
    data = {"version": 1, "parts": [part(), "junk", part(file="screens/mock-b.html", stamp=OLD)], "x": 1}
    new = PS.record(data, "screens/mock-b.html", NOW, True, "2026-10-27T11:00:00")
    assert new["parts"][2]["stamp"] == NOW and new["parts"][2]["dirty"] is True and new["parts"][2]["built_at"] == "2026-10-27T11:00:00"
    assert new["parts"][0] == part() and new["parts"][1] == "junk" and new["x"] == 1, "다른 항목·모르는 키는 그대로"
    assert data["parts"][2]["stamp"] == OLD, "받은 것을 고치지 않는다"


def test_stale_screens_maps_screen_dependencies():
    deps = {"tabs": ["screens/home.html", "screens/mock-a.html"], "home": ["screens/home.html"], "dict": ["screens/mock-b.html"]}
    assert PS.stale_screens(deps, {"screens/mock-a.html"}) == ["tabs"]
    assert PS.stale_screens(deps, {"screens/mock-a.html", "screens/mock-b.html"}) == ["dict", "tabs"]
    assert PS.stale_screens(deps, set()) == [] and PS.stale_screens(None, {"x"}) == []


def test_warn_line_names_the_rebuild_command():
    rows = [PS.row(part(), OLD, False), PS.row(part(file="screens/mock-b.html"), NOW, False)]
    line = PS.warn_line(rows, "proj")
    assert line.startswith("[hd]") and "screens/mock-a.html" in line and "mock-b" not in line and "hd parts --rebuild proj" in line
    assert PS.warn_line([PS.row(part(), NOW, False)], "proj") is None
    assert PS.warn_line([], "proj") is None


def test_model_has_no_io():
    src = Path(PS.__file__).read_text(encoding="utf-8")
    for bad in ("open(", "subprocess", "pathlib", "os.", "urllib", "time.", "print("):
        assert bad not in src, bad
