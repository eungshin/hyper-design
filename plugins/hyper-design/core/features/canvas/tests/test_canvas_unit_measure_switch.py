"""perf/measure_switch.py 의 순수 부분 — 인자 해석 · 결과 JSON → 요약 줄 → 표(브라우저·허브 없음)."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[6]
_spec = importlib.util.spec_from_file_location("measure_switch", ROOT / "perf" / "measure_switch.py")
MS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MS)


def test_args_default_and_list():
    a = MS.parse_args([])
    assert a.cases == ["normal"] and a.runs == 3 and a.ref == "HEAD"
    a = MS.parse_args(["--cases", "normal, data,code", "--runs", "5", "--ref", "abc123"])
    assert a.cases == ["normal", "data", "code"] and a.runs == 5 and a.ref == "abc123"


def test_args_all_and_dedupe():
    assert MS.parse_args(["--cases", "all"]).cases == ["normal", "data", "code", "first"]
    assert MS.parse_args(["--cases", "data,data,normal"]).cases == ["data", "normal"]


@pytest.mark.parametrize("argv", [["--cases", "fast"], ["--cases", ""], ["--runs", "0"], ["--runs", "x"]])
def test_args_reject_bad(argv, capsys):
    with pytest.raises(SystemExit) as e:
        MS.parse_args(argv)
    assert e.value.code == 2


RES = {
    "normal": [{"to": "laundry", "click_cards": 619, "click_nav": 170, "api_open": 167, "ttfb": 37, "fcp": 528, "frames_done": 622},
               {"to": "dayfine", "click_cards": 401, "click_nav": 150, "api_open": 120, "ttfb": 30, "fcp": 300, "frames_done": None},
               {"to": "laundry", "click_cards": 500, "click_nav": 160, "api_open": 140, "ttfb": 33, "fcp": 400, "frames_done": 700}],
    "first": [{"to": "dayfine", "api_open": 1120, "goto_cards": 1307, "goto_nav": 19, "ttfb": 181, "fcp": 916, "frames_done": 2820}],
}


def test_summarize_ranges_skip_missing():
    rows = MS.summarize(RES)
    by = {(r["case"], r["metric"]): r for r in rows}
    cc = by[("normal", "click_cards")]
    assert (cc["n"], cc["min"], cc["med"], cc["max"]) == (3, 401, 500, 619)
    fd = by[("normal", "frames_done")]
    assert (fd["n"], fd["min"], fd["max"]) == (2, 622, 700)          # None 은 빼고 센다
    assert by[("first", "goto_cards")]["med"] == 1307
    assert ("first", "click_cards") not in by and ("normal", "goto_cards") not in by
    assert [r["metric"] for r in rows if r["case"] == "normal"][0] == "click_cards"   # 첫 줄 = 사용자가 기다린 시간


def test_summarize_empty_case_is_one_row():
    rows = MS.summarize({"code": []})
    assert rows == [{"case": "code", "metric": None, "label": "결과 없음", "n": 0, "min": None, "med": None, "max": None}]


def test_format_table():
    t = MS.format_table(MS.summarize(RES))
    lines = t.splitlines()
    assert lines[0].split() == ["경우", "지표", "n", "최소", "중앙", "최대"]
    row = next(x for x in lines if "클릭→카드 보임" in x)
    assert row.split()[0] == "normal" and row.split()[-4:] == ["3", "401", "500", "619"]
    assert any("first" in x and "열기→카드 보임" in x and x.split()[-1] == "1307" for x in lines)
    assert "(ms)" in lines[-1]
    empty = MS.format_table(MS.summarize({"code": []}))
    assert "결과 없음" in empty and "-" in empty.splitlines()[2]
