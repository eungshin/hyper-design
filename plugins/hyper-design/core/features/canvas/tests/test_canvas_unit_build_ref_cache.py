"""build_ref.py 풀어 둔 ref 캐시 규칙(49d) — I/O 없음.

다시 빌드마다 `git archive` + 풀기(약 1.5~5초)를 하지 않게, 풀어 둔 core 나무를 그 나무 sha 로 임시 폴더에 두고 sha 가 같으면 다시 쓴다.
- prune(entries, keep, now, grace) → 지울 이름 목록: 가장 최근에 쓴 keep 개와 grace 안에 쓴 것은 남긴다(다른 빌드가 쓰는 중일 수 있음).
  sha 모양이 아닌 이름(만드는 중 `.tmp-…` 등)은 grace 가 지난 것만 지운다.
- usable(names) → 그 폴더를 다시 써도 되나: 다 풀었다는 표시(`.hd-ok`)가 있어야 한다(풀다 멈춘 폴더는 쓰지 않음).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_ref  # noqa: E402

A, B, C, D = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
NOW = 10_000.0


def test_keeps_newest_and_recent_prunes_the_rest():
    ents = [(A, NOW - 9000), (B, NOW - 8000), (C, NOW - 7000), (D, NOW - 6000)]
    assert build_ref.prune(ents, keep=2, now=NOW, grace=600) == [A, B]          # 오래된 것부터


def test_recent_entries_survive_even_beyond_keep():
    ents = [(A, NOW - 60), (B, NOW - 30), (C, NOW - 10)]
    assert build_ref.prune(ents, keep=1, now=NOW, grace=600) == []


def test_unfinished_temp_dirs_only_after_grace():
    old_tmp, new_tmp = A + ".tmp-12", B + ".tmp-13"
    ents = [(old_tmp, NOW - 5000), (new_tmp, NOW - 5), (C, NOW - 1)]
    assert build_ref.prune(ents, keep=3, now=NOW, grace=600) == [old_tmp]


def test_foreign_names_are_left_alone():
    assert build_ref.prune([("notes.txt", NOW - 99999), ("README", 0.0)], keep=0, now=NOW, grace=600) == []


def test_usable_needs_done_marker():
    assert build_ref.usable({".hd-ok", "features"}) is True
    assert build_ref.usable({"features"}) is False
    assert build_ref.usable(set()) is False
