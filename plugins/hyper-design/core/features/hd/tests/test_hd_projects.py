"""hd 프로젝트 목록 Model(hd_projects) — 넣기·고치기·같은 out 은 한 항목·지우기·찾기·순서·이름 규칙·깨진 파일·순수성. 브라우저 없음."""
import ast, sys
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
import hd_projects as P  # noqa: E402

A = "C:\\runs\\laundry\\out"
B = "C:/runs/gym/out"


def test_slug_rules():
    assert P.slug("Laundry V1!") == "laundry-v1"
    assert P.slug("  세탁 앱 ") == "세탁-앱"
    assert P.slug("a__b--c") == "a-b-c"
    assert P.slug("!!!") == "" and P.slug(None) == ""


def test_save_adds_then_same_out_is_same_entry():
    r0 = P.empty()
    r1, e, added = P.save(r0, A, "t1", default_name="laundry")
    assert added and e == {"name": "laundry", "out": A, "kind": "run", "created": "t1", "last_opened": "t1"}
    assert r0["projects"] == [], "원래 목록은 그대로"
    r2, e2, added2 = P.save(r1, "c:/runs/laundry/out/", "t2", default_name="other")
    assert not added2 and e2["name"] == "laundry" and len(r2["projects"]) == 1, "같은 out(대소문자·구분자·끝 '/' 달라도) = 같은 항목"
    r3, e3, _ = P.save(r2, A, "t3", name="Laundry V1")
    assert e3["name"] == "laundry-v1" and e3["created"] == "t1" and len(r3["projects"]) == 1, "이름만 바꿈"


def test_names_are_unique():
    r, _, _ = P.save(P.empty(), A, "t", default_name="app")
    r, e, _ = P.save(r, B, "t", default_name="app")
    assert e["name"] == "app-2", "기본 이름이 겹치면 -2"
    with pytest.raises(P.ProjectError, match="이미 다른 프로젝트"):
        P.save(r, "C:/x/out", "t", name="app")
    with pytest.raises(P.ProjectError, match="글자·숫자"):
        P.save(r, "C:/x/out", "t", name="!!")


def test_find_touch_forget_order():
    r, _, _ = P.save(P.empty(), A, "2026-01-01", default_name="laundry")
    r, _, _ = P.save(r, B, "2026-01-02", default_name="gym")
    r, _, _ = P.save(r, "C:/z/out", "2026-01-02", default_name="alpha")
    assert P.find(r, "gym")["out"] == B
    assert P.find(r, "C:/runs/laundry/out")["name"] == "laundry", "경로로도 찾는다"
    assert P.find(r, "nope") is None
    assert [e["name"] for e in P.ordered(r)] == ["alpha", "gym", "laundry"], "최근 것부터, 같으면 이름 순"
    r = P.touch(r, A, "2026-02-01")
    assert [e["name"] for e in P.ordered(r)][0] == "laundry"
    r2, hit = P.forget(r, "gym")
    assert hit["out"] == B and [e["name"] for e in r2["projects"]] == ["laundry", "alpha"]
    assert P.forget(r2, "gym")[1] is None


def test_rows_state_running_off_missing():
    r, _, _ = P.save(P.empty(), A, "1", default_name="a")
    r, _, _ = P.save(r, B, "2", default_name="b")
    r, _, _ = P.save(r, "C:/gone/out", "0", default_name="c")
    alive = [{"out": "c:/runs/laundry/out", "url": "http://127.0.0.1:5/index.html?hd=x", "pid": 7}]
    rs = P.rows(r, alive, {P.key(A): True, P.key(B): True, P.key("C:/gone/out"): False})
    assert [(x["name"], x["state"], x["pid"]) for x in rs] == [("b", "off", None), ("a", "running", 7), ("c", "missing", None)]
    lines = P.format_rows(rs).splitlines()
    assert lines[0] == "b · %s · 꺼짐 · 2" % B
    assert lines[1].endswith("· http://127.0.0.1:5/index.html?hd=x · 1") and lines[2].endswith("· 없음 · 0")
    assert "hd save" in P.format_rows([])


def test_parse_broken_and_partly_bad():
    for doc in (None, [], {"version": 2, "projects": []}, {"version": 1, "projects": {}}):
        reg, why, broken = P.parse(doc)
        assert reg == P.empty() and why and broken
    good = {"name": "a", "out": A}
    reg, why, broken = P.parse({"version": 1, "projects": [good, {"name": "Bad Name", "out": B}, {"name": "x"}, dict(good, name="b")]})
    assert not broken and "3개" in why and [e["name"] for e in reg["projects"]] == ["a"]
    assert P.parse({"version": 1, "projects": [good]})[1:] == (None, False)


def test_model_is_pure():
    tree = ast.parse((HD / "hd_projects.py").read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bad.append("import " + ",".join(a.name for a in node.names))
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "print", "input", "read_text", "write_text", "urlopen", "remove", "unlink", "listdir", "stat", "now"):
                bad.append(name)
    assert bad == [], "hd_projects.py 는 I/O·시계를 쓰지 않는다: %s" % bad
