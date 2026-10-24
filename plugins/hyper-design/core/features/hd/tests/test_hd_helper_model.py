"""도우미 순수 규칙(helper_model) — #273 since·413 글·완료 메모 보관 줄 · #281 기록·대기열 정리 고르기 · #282 out 같음/안 규칙(hd_projects). 브라우저·I/O 없음."""
import ast, json, sys
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
import helper_model as H  # noqa: E402
import hd_projects as P  # noqa: E402


# ---------------------------------------------------------------- #273 GET /api/state?since
def test_state_reply_unchanged_only_when_rev_matches():
    snap = {"rev": 4, "state": {"notes": [1]}}
    assert H.state_reply(snap, None) is snap, "since 없음 = 전체"
    assert H.state_reply(snap, 4) == {"rev": 4, "unchanged": True}, "같은 rev = 몸통 없이"
    assert H.state_reply(snap, 3) is snap and H.state_reply(snap, 5) is snap, "다르면 전체"


def test_parse_since():
    assert H.parse_since(None) is None and H.parse_since("") is None
    assert H.parse_since("7") == 7 and H.parse_since("0") == 0
    for bad in ("x", "-1", "1.5", "007a"):
        try:
            H.parse_since(bad)
        except ValueError:
            continue
        raise AssertionError("받으면 안 됨: " + bad)


def test_too_big_names_size_and_fix():
    msg = H.too_big(int(2.5 * 1024 * 1024), 2 * 1024 * 1024)
    assert "2.5 MB" in msg and "2 MB" in msg and "완료 메모를 보관으로 옮기세요" in msg, msg


# ---------------------------------------------------------------- #273 보관
def test_archive_lines_one_json_line_per_note():
    lines, err = H.archive_lines({"notes": [{"id": "a", "note": "줄\n바꿈"}, {"id": "b"}]})
    assert err is None and len(lines) == 2 and all("\n" not in x for x in lines)
    assert json.loads(lines[0]) == {"id": "a", "note": "줄\n바꿈"} and "줄" in lines[0], "한글 그대로, 한 줄"
    assert H.archive_lines({"notes": []}) == ([], None)
    for bad in (None, [], {"notes": "x"}, {"notes": [1]}, {"notes": [{"id": "a"}, "b"]}, {}):
        lines, err = H.archive_lines(bad)
        assert lines is None and err, bad


def test_archive_notes_reads_newest_last_capped_and_skips_broken():
    lines = [json.dumps({"i": i}) for i in range(5)] + ["{broken", "", "[1]"]
    notes, bad = H.archive_notes(lines, cap=4)
    assert notes == [{"i": 3}, {"i": 4}] and bad == 2, "마지막 4줄만(빈 줄은 셈하지 않음), 깨진 줄·객체 아닌 줄은 건너뜀"
    notes, bad = H.archive_notes(lines)
    assert [n["i"] for n in notes] == [0, 1, 2, 3, 4] and bad == 2


# ---------------------------------------------------------------- #281 정리 고르기
def _stamp(day, i=0):
    return "202610%02d-1200%02d-000000" % (day, i)


def test_history_prune_keeps_newest_and_young_and_unknown_names():
    names = [_stamp(d) for d in range(1, 11)] + ["t1", "fix-components.css", "manifest.json"]
    cutoff = _stamp(5)                                   # 이보다 앞(오래됨)만 지울 수 있다
    assert H.history_prune(names, cutoff, keep=200) == [], "200개 이하면 아무것도"
    gone = H.history_prune(names, cutoff, keep=3)
    assert gone == [_stamp(1), _stamp(2), _stamp(3), _stamp(4)], "가장 새 3개 밖이면서 30일보다 오래된 것만"
    assert "t1" not in gone and "fix-components.css" not in gone, "시각 이름이 아닌 것은 손대지 않는다"


def test_queue_prune_only_marked_and_old():
    names = [_stamp(1) + ".txt", _stamp(1) + ".sent",          # 보냄 + 오래됨 → 둘 다
             _stamp(2) + ".txt",                                 # 표시 없음 → 그대로
             _stamp(3) + ".txt", _stamp(3) + ".lifted",          # 걷힘 + 오래됨 → 둘 다
             _stamp(9) + ".txt", _stamp(9) + ".sent",            # 보냄이지만 최근 → 그대로
             _stamp(1) + ".sent.bak", "note.txt", "readme.sent"]
    gone = H.queue_prune(names, cutoff=_stamp(5))
    assert sorted(gone) == sorted([_stamp(1) + ".txt", _stamp(1) + ".sent", _stamp(3) + ".txt", _stamp(3) + ".lifted"]), gone


def test_stamp_cutoff_is_comparable_text():
    assert H.STAMP.match(_stamp(1)) and not H.STAMP.match("t1")


# ---------------------------------------------------------------- #282 out 같음 · 안
def test_same_and_inside_ignore_case_separators_trailing_slash():
    assert P.same("C:\\Runs\\Gym\\out", "c:/runs/gym/out/")
    assert not P.same("C:/runs/gym/out", "C:/runs/gym/out2")
    assert P.inside("C:\\Runs\\out", "c:/runs/OUT/screens/a.html")
    assert P.inside("c:/runs/out/", "C:\\runs\\out"), "자기 자신도 안"
    assert not P.inside("C:/runs/out", "C:/runs/out2/a.html"), "이름이 앞부분만 같은 옆 폴더는 밖"
    assert not P.inside("C:/runs/out", "C:/runs/a.html")
    assert P.inside("C:/", "c:/x/y"), "드라이브 뿌리"
    assert P.inside("/home/u/out", "/home/u/out/a") and not P.inside("/home/u/out", "/home/u/Out/a"), "드라이브 없는 경로는 대소문자를 가린다"


def test_helper_model_is_pure():
    tree = ast.parse((HD / "helper_model.py").read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names]
            if names not in (["json"], ["re"]):
                bad.append("import " + ",".join(names))
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "print", "input", "read_text", "write_text", "urlopen", "remove", "unlink", "listdir", "stat"):
                bad.append(name)
        elif isinstance(node, ast.Name) and node.id in ("os", "urllib", "pathlib", "io", "socket", "subprocess", "datetime", "time"):
            bad.append(node.id)
    assert bad == [], "helper_model.py 는 I/O 를 쓰지 않는다: %s" % bad


def test_archive_lines_skips_notes_already_archived():   # 보관 뒤 저장이 실패해 같은 메모가 다시 와도 한 줄만
    lines, err = H.archive_lines({"notes": [{"id": "a"}, {"id": "b"}, {"note": "id 없음"}]}, have={"a"})
    assert err is None and [json.loads(x).get("id") for x in lines] == ["b", None]
