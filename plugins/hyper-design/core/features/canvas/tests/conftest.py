"""캔버스 테스트 영역 표시(marker) — 고친 곳에 맞는 테스트만 골라 돌리려고(contract.md '테스트 층').

test_canvas_modules.py 와 test_canvas_unit_*.py 는 통째로 unit(브라우저 없음, 수 초) — 단 `@pytest.mark.slow`(git·하위 프로세스 빌드 같은 I/O)는 unit 에서 빠진다.
브라우저 테스트는 테스트 파일 안에서 영역을 받는다 — 테스트마다 `@pytest.mark.area("tools", "notes")`(파일 전체면 `pytestmark = pytest.mark.area(...)`).
여기서는 그 표시를 `-m` 으로 고를 수 있는 영역 표시(`tools`·`notes`…)로 바꿔 단다. 영역 표시가 없거나 AREAS 에 없는 영역을 쓴
브라우저 테스트는 수집 단계에서 실패한다. 여기를 고칠 일은 새 영역(AREAS 한 줄)뿐이다.
SERIAL 의 테스트는 -n(xdist) 실행에서 빠지고 따로 `-m serial`(-n 없이)로 돈다.
"""
import json, time
from pathlib import Path

import pytest

AREAS = {
    "input": "이동·확대·끌기·클릭·단축키(판 조작)",
    "modal": "크게 보기·주석 달기(P)",
    "notes": "메모 패널·저장·보내기",
    "tools": "도구 막대·카드 옮기기·우클릭 메뉴·숨기기·되돌리기",
    "flow": "판에 늘 그리는 선(쌍마다 하나·줄 색·보이기/굵기/투명도)",
    "links": "연결 보기(Shift+클릭): 길·태그·색·범례·태그 이름",
    "motion": "카메라·움직임 줄이기",
    "helper": "로컬 도우미(helper.py): 바로 반영·out 안만·원본 남김·토큰·대기열",
    "layers": "레이어 패널: 줄·화면·판 글 나무, 숨김(눈)·잠금·검색·거르기·아래 막대",
    "theme": "테마 패널: 테마 고르기·복제·색 네 칸·대비 경고·이름/삭제(hd-themes)",
    "menu": "위쪽 보기 메뉴(배율 칩)·창 메뉴·Tab 패널 모두 숨기기",
    "dock": "오른쪽 패널 도크: 묶음·탭 합치기/떼기·떠 있는 창·크기·접기·저장",
}


# 격리(fable #4): -n 4 에서만 가끔 깨지는 테스트 — -n 실행은 고르지 않고, 끝에 `pytest tests -m serial`(-n 없이)로 따로 돌린다. 원인을 찾으면 여기서 뺀다.
SERIAL = ("test_v2_no_vertical_through_cards", "test_line_click_shows_end_handles_and_drag_retargets")


def _xdist_on(config):                              # 주 프로세스(-n N, N>0) 또는 일꾼
    return getattr(config, "workerinput", None) is not None or bool(getattr(config.option, "numprocesses", 0))


# 모듈 하나를 차례로 이어 쓰는 페이지(앞 테스트가 남긴 메모·펼침·옮긴 카드를 뒤 테스트가 전제) — -n 에서도 한 일꾼에서 차례대로.
# dpage(편집 테스트 대부분)·gpage 는 나눠 돌린다 — gpage 를 묶으면 -m 으로 고른 일부만 차례로 돌 때 test_v3_main_flow_dashed 가 앞 테스트의 카메라 자리를 이어받아 깨진다
SHARED = ("page", "epage")


@pytest.hookimpl(tryfirst=True)                     # xdist 가 나눌 방식을 정하기 전에
def pytest_configure(config):
    if getattr(config, "workerinput", None) is not None:   # 일꾼은 인자를 다시 읽어 묶음 방식을 모른다 — 묶음 이름을 테스트 id 에 붙이게
        config.option.loadgroup = True
    elif getattr(config.option, "dist", "no") == "load":   # -n 4: 묶음(xdist_group)만 한 일꾼으로, 나머지는 지금처럼 나눠 돌린다
        config.option.dist = "loadgroup"
    config.addinivalue_line("markers", "unit: 순수 함수(node) — 늘 같이 돌린다")
    config.addinivalue_line("markers", "slow: unit 파일 안의 I/O 테스트(git·빌드 하위 프로세스) — unit 에 들지 않는다")
    config.addinivalue_line("markers", "area(*names): 브라우저 테스트의 영역(AREAS) — conftest 가 같은 이름의 표시로 바꿔 단다")
    config.addinivalue_line("markers", "serial: -n 에서 가끔 깨지는 격리 테스트 — -n 실행에서 빠지고 `-m serial`(-n 없이)로 따로")
    for name, what in AREAS.items():
        config.addinivalue_line("markers", f"{name}: {what}")


@pytest.hookimpl(tryfirst=True)                     # xdist 가 묶음 이름(xdist_group)을 읽기 전에 표시를 단다
def pytest_collection_modifyitems(config, items):
    missing, unknown = [], []
    for it in items:
        if it.fspath.basename == "test_canvas_modules.py" or it.fspath.basename.startswith("test_canvas_unit_"):   # 브라우저 없는 테스트 파일
            if not it.get_closest_marker("slow"):
                it.add_marker(pytest.mark.unit)
            continue
        if not it.fspath.basename.startswith("test_canvas_"):
            continue
        areas = [a for m in it.iter_markers("area") for a in m.args]
        if not areas:
            missing.append(it.nodeid)
            continue
        bad = [a for a in areas if a not in AREAS]
        if bad:
            unknown.append(f"{it.nodeid} {bad}")
            continue
        for a in areas:
            it.add_marker(getattr(pytest.mark, a))
        if (it.originalname or it.name) in SERIAL:
            it.add_marker(pytest.mark.serial)
        shared = [f for f in SHARED if f in getattr(it, "fixturenames", ())]
        if shared:
            it.add_marker(pytest.mark.xdist_group(it.fspath.purebasename + ":" + shared[0]))
    if missing:
        raise pytest.UsageError("영역 표시(@pytest.mark.area(...))가 없는 브라우저 테스트: " + ", ".join(missing))
    if unknown:
        raise pytest.UsageError("AREAS(tests/conftest.py)에 없는 영역: " + ", ".join(unknown))
    if _xdist_on(config):                             # -n: 격리 테스트는 빼고(주·일꾼이 같은 목록을 갖게 둘 다에서)
        out = [it for it in items if it.get_closest_marker("serial")]
        if out:
            items[:] = [it for it in items if not it.get_closest_marker("serial")]
            config.hook.pytest_deselected(items=out)


# ── 검토 과정 기록(tracking/README.md): 테스트를 돌릴 때마다 무엇을·얼마나·결과를 tracking/runs.json 에 한 줄 — review.py 가 과한 검토를 찾는다
RUNS = Path(__file__).resolve().parent / "tracking" / "runs.json"
_RUN = {}


def pytest_sessionstart(session):
    _RUN.update(t0=time.time(), failed=[], passed=0, skipped=0)


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if report.failed:
            _RUN.setdefault("failed", []).append(report.nodeid.split("::")[-1])
        elif report.skipped:
            _RUN["skipped"] = _RUN.get("skipped", 0) + 1
        elif report.when == "call":
            _RUN["passed"] = _RUN.get("passed", 0) + 1


def pytest_sessionfinish(session, exitstatus):
    if "t0" not in _RUN or getattr(session.config.option, "collectonly", False) or hasattr(session.config, "workerinput"):
        return                                     # xdist(-n): 일꾼마다 쓰지 않고 결과를 모두 받는 주 프로세스만 한 줄
    o = session.config.option
    sel = {"m": o.markexpr or "", "k": o.keyword or "", "lf": bool(getattr(o, "lf", False)),
           "files": sorted({Path(str(a)).name for a in session.config.args if str(a).endswith(".py")})}
    scope = "full" if not (sel["m"] or sel["k"] or sel["lf"] or sel["files"]) else ("unit" if sel["m"] == "unit" and not sel["k"] else "part")
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "scope": scope, "sel": sel, "n": session.testscollected,
           "passed": _RUN.get("passed", 0), "failed": _RUN.get("failed", []), "skipped": _RUN.get("skipped", 0),
           "sec": round(time.time() - _RUN["t0"], 1)}
    try:
        runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else []
    except (OSError, ValueError):
        runs = []
    runs.append(rec)
    try:
        RUNS.parent.mkdir(exist_ok=True)
        RUNS.write_text(json.dumps(runs[-500:], ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
