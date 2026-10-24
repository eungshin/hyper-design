"""Home Model(home_model) + 프로젝트 목록 새 칸(hd_projects: title·starred·trashed) — 순수 규칙. 서버·브라우저 없음."""
import ast, sys
from pathlib import Path

import pytest

HOME = Path(__file__).resolve().parents[1]
HD = HOME.parent / "hd"
sys.path[:0] = [str(HOME), str(HD)]
import hd_projects as P  # noqa: E402
import home_model as M  # noqa: E402


A, B, C = "C:/p/a/out", "C:/p/b/out", "C:/p/c/out"


def _reg():
    r, _, _ = P.save(P.empty(), A, "2026-10-01T10:00:00+09:00", default_name="alpha")
    r, _, _ = P.save(r, B, "2026-10-02T10:00:00+09:00", default_name="beta")
    r, _, _ = P.save(r, C, "2026-10-03T10:00:00+09:00", default_name="gamma")
    return r


# ---------------------------------------------------------------- hd_projects 새 칸
def test_parse_keeps_new_fields_and_drops_bad_ones_only():
    doc = {"version": 1, "projects": [
        {"name": "a", "out": A, "title": " 세탁 앱 ", "starred": True, "trashed": "2026-10-20T00:00:00+09:00"},
        {"name": "b", "out": B, "title": "", "starred": "yes", "trashed": 5},
        {"name": "c", "out": C}]}
    reg, why, broken = P.parse(doc)
    assert not broken and why is None
    a, b, c = reg["projects"]
    assert a["title"] == "세탁 앱" and a["starred"] is True and a["trashed"].startswith("2026-10-20")
    assert "title" not in b and "starred" not in b and "trashed" not in b, "틀린 새 칸은 그 칸만 버린다(항목은 살린다)"
    assert set(c) == {"name", "out", "kind", "created", "last_opened"}, "옛 모양 그대로"


def test_update_title_star_trash_and_untrash():
    r0 = _reg()
    r1, e = P.update(r0, "alpha", "T1", title="  새 이름 ")
    assert e["title"] == "새 이름" and "title" not in P.find(r0, "alpha"), "원래 목록은 그대로"
    r2, e = P.update(r1, "alpha", "T2", starred=True, trashed=True)
    assert e["starred"] is True and e["trashed"] == "T2"
    r3, e = P.update(r2, "alpha", "T3", trashed=True)
    assert e["trashed"] == "T2", "이미 휴지통이면 시각을 바꾸지 않는다"
    r4, e = P.update(r3, "alpha", "T4", trashed=False)
    assert "trashed" not in e and e["title"] == "새 이름"
    for bad in ({"title": ""}, {"title": "x" * 81}, {"title": "a\nb"}, {"title": 3}, {"starred": "y"}, {"trashed": "now"}):
        with pytest.raises(P.ProjectError):
            P.update(r0, "alpha", "T", **bad)
    with pytest.raises(P.ProjectError, match="모르는"):
        P.update(r0, "nope", "T", starred=True)


def test_forget_only_trashed():
    r = _reg()
    with pytest.raises(P.ProjectError, match="휴지통"):
        P.forget_trashed(r, "alpha")
    r, _ = P.update(r, "alpha", "T", trashed=True)
    r2, hit = P.forget_trashed(r, "alpha")
    assert hit["name"] == "alpha" and [e["name"] for e in r2["projects"]] == ["beta", "gamma"]
    with pytest.raises(P.ProjectError, match="모르는"):
        P.forget_trashed(r2, "alpha")


def test_rows_carry_title_star_trash_with_manifest_fallback():
    r, _ = P.update(_reg(), "alpha", "T", title="알파", starred=True)
    r, _ = P.update(r, "gamma", "T9", trashed=True)
    rs = {x["name"]: x for x in P.rows(r, [], {P.key(A): True, P.key(B): True, P.key(C): True}, {P.key(B): "베타 매니페스트"})}
    assert rs["alpha"]["title"] == "알파" and rs["alpha"]["starred"] is True and rs["alpha"]["trashed"] is None
    assert rs["beta"]["title"] == "베타 매니페스트", "제목이 없으면 screens.json 의 title"
    assert rs["gamma"]["title"] == "gamma" and rs["gamma"]["trashed"] == "T9", "그것도 없으면 이름"
    assert rs["alpha"]["created"] == "2026-10-01T10:00:00+09:00"


# ---------------------------------------------------------------- 구역 · 검색
def _rows():
    r, _ = P.update(_reg(), "alpha", "T", starred=True, title="Zeta 세탁")
    r, _ = P.update(r, "gamma", "2026-10-09", trashed=True)
    return P.rows(r, [], {})


def test_sections():
    rs = _rows()
    assert [x["name"] for x in M.section(rs, "recent")] == ["beta", "alpha"], "휴지통 빼고 최근 연 것부터"
    assert [x["name"] for x in M.section(rs, "all")] == ["beta", "alpha"], "제목 casefold 순(beta < zeta 세탁)"
    assert [x["name"] for x in M.section(rs, "starred")] == ["alpha"]
    assert [x["name"] for x in M.section(rs, "trash")] == ["gamma"]
    with pytest.raises(ValueError):
        M.section(rs, "cloud")


def test_search_casefold_title_or_name():
    rs = _rows()
    assert [x["name"] for x in M.search(rs, "ZETA")] == ["alpha"]
    assert [x["name"] for x in M.search(rs, "세탁")] == ["alpha"]
    assert [x["name"] for x in M.search(rs, "bet")] == ["beta"]
    assert len(M.search(rs, "  ")) == 3


def test_rel_time():
    now = "2026-10-25T15:00:00+09:00"
    assert M.rel_time("2026-10-25T14:59:30+09:00", now) == "방금 전"
    assert M.rel_time("2026-10-25T14:15:00+09:00", now) == "45분 전"
    assert M.rel_time("2026-10-25T12:00:00+09:00", now) == "3시간 전"
    assert M.rel_time("2026-10-24T23:00:00+09:00", now) == "어제"
    assert M.rel_time("2026-10-21T09:00:00+09:00", now) == "10-21"
    assert M.rel_time("2025-12-31T09:00:00+09:00", now) == "2025-12-31"
    assert M.rel_time("2026-10-25T03:00:00+00:00", now) == "3시간 전", "다른 시간대는 지금 시간대로 바꿔 본다"
    assert M.rel_time(None, now) == "" and M.rel_time("garbage", now) == ""


# ---------------------------------------------------------------- 탭
def test_tabs_parse_set_add_drop():
    known = {"a", "b", "c"}
    assert M.tabs_parse({"version": 1, "tabs": ["a", "zz", "b", "a", 3]}, known) == (["a", "b"], None)
    for bad in (None, [], {"version": 2, "tabs": []}, {"version": 1, "tabs": "a"}):
        tabs, why = M.tabs_parse(bad, known)
        assert tabs == [] and why
    assert M.tabs_set(["c", "x", "a", "c"], known) == ["c", "a"]
    with pytest.raises(ValueError):
        M.tabs_set("a", known)
    with pytest.raises(ValueError):
        M.tabs_set(["a", 1], known)
    assert M.tabs_add(["a"], "b") == ["a", "b"] and M.tabs_add(["a", "b"], "a") == ["a", "b"]
    assert M.tabs_drop(["a", "b"], "a") == ["b"]
    assert M.tabs_doc(["a"]) == {"version": 1, "tabs": ["a"]}


# ---------------------------------------------------------------- 새 프로젝트 · 썸네일
def test_new_project_names():
    assert M.default_title([]) == "새 프로젝트 1"
    assert M.default_title(["새 프로젝트 1", "새 프로젝트 3"]) == "새 프로젝트 2"
    assert M.new_name("새 프로젝트 1", set()) == "새-프로젝트-1"
    assert M.new_name("My App", {"my-app", "my-app-2"}) == "my-app-3"
    assert M.new_name("!!!", set()) == "project"
    assert M.empty_manifest("X") == {"title": "X", "groups": [], "screens": []}


def test_thumb_rules():
    assert M.thumb_stale(None, [10, None]) is True
    assert M.thumb_stale(5, [10, 3]) is True
    assert M.thumb_stale(12, [10, 3]) is False
    assert M.thumb_stale(None, [None, None]) is False, "원본이 없으면 그리지 않는다"
    assert M.thumb_url(12270, "a", 99.7) == "http://127.0.0.1:12270/thumb/a.png?t=99"
    assert M.thumb_url(None, "a", 1) is None and M.thumb_url(1, "a", None) is None
    assert M.thumb_name("a.png", {"a"}) == "a"
    assert M.thumb_name("../x.png", {"a"}) is None and M.thumb_name("a.jpg", {"a"}) is None and M.thumb_name("b.png", {"a"}) is None


def test_model_is_pure():
    tree = ast.parse((HOME / "home_model.py").read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bad += [a.name for a in node.names if a.name not in ("datetime", "hd_projects")]
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "print", "input", "read_text", "write_text", "urlopen", "remove", "unlink", "listdir", "stat", "now",
                        "today", "time", "utcnow"):
                bad.append(name)
    assert bad == [], "home_model.py 는 I/O·시계를 쓰지 않는다: %s" % bad
