"""캔버스 테스트 영역 표시(marker) — 고친 곳에 맞는 테스트만 골라 돌리려고(contract.md '테스트 층').

test_canvas_modules.py 와 test_canvas_unit_*.py 는 통째로 unit(브라우저 없음, 수 초) — 단 `@pytest.mark.slow`(git·하위 프로세스 빌드 같은 I/O)는 unit 에서 빠진다.
브라우저 테스트는 테스트 파일 안에서 영역을 받는다 — 테스트마다 `@pytest.mark.area("tools", "notes")`(파일 전체면 `pytestmark = pytest.mark.area(...)`).
여기서는 그 표시를 `-m` 으로 고를 수 있는 영역 표시(`tools`·`notes`…)로 바꿔 단다. 영역 표시가 없거나 AREAS 에 없는 영역을 쓴
브라우저 테스트는 수집 단계에서 실패한다. 여기를 고칠 일은 새 영역(AREAS 한 줄)뿐이다.
SERIAL 의 테스트는 -n(xdist) 실행에서 빠지고 따로 `-m serial`(-n 없이)로 돈다.
`--surface frame,board` 는 -m 고른 것에 그 화면 동작(SURFACES)을 함께 쓰는 테스트 파일을 더한다 — 파일은 달라도 같은 동작을 쓰는 이웃 조각을 커밋 전에 같이 본다.
실행 도구(hd_testrun.py): -n 2 이상이면 주 프로세스가 잠금(hd-testrun.lock)을 잡고(다른 실행이 잡고 있으면 기다림, HD_TEST_NOLOCK=1 은 건너뜀),
끝에 깨진 것만 -n 0 으로 한 번 더 돌려 '진짜 실패 · 혼자 통과(부하로 보임)'를 나눈다. chromium 시작 인자로 바깥 글꼴(cdn.jsdelivr.net…) 주소를 바로 실패시킨다.
"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_testrun  # noqa: E402

hd_testrun.block_external_fonts()                   # 주·일꾼 모두 — 이 conftest 를 가져오는 프로세스의 모든 브라우저 맥락

AREAS = {
    "input": "이동·확대·끌기·클릭·단축키(판 조작)",
    "modal": "크게 보기·주석 달기(P)",
    "notes": "메모 패널·저장·보내기",
    "tools": "도구 막대·선택(V)·우클릭 메뉴·숨기기·되돌리기",
    "flow": "판에 늘 그리는 선(쌍마다 하나·줄 색·보이기/굵기/투명도)",
    "links": "연결 보기(Shift+클릭): 길·태그·색·범례·태그 이름",
    "motion": "카메라·움직임 줄이기",
    "helper": "로컬 도우미(helper.py): 바로 반영·out 안만·원본 남김·토큰·대기열",
    "layers": "레이어 패널: 줄·화면·판 글 나무, 숨김(눈)·잠금·검색·거르기·아래 막대",
    "theme": "테마 패널: 테마 고르기·복제·색 네 칸·대비 경고·이름/삭제(hd-themes)",
    "menu": "위쪽 보기 메뉴(배율 칩)·창 메뉴·Tab 패널 모두 숨기기",
    "dock": "패널 도크(오른쪽·왼쪽 S3): 묶음·탭 합치기/떼기·떠 있는 창·크기·접기·저장",
    "chat": "하단 대화창: 고른 카드·요소 칩·보내기(S1) · 대화 패널(S3)",
    "dscard": "판 위 디자인 시스템 카드(S6)",
    "dsedit": "Foundation 토큰·Components 부품 고르기·고치기(R55): 문서 탭 도구·속성 창·같은 묶음 토큰 목록·저장·되돌리기",
}


# 화면 동작(surface): 영역(AREAS)과 달리 여러 조각이 함께 기대는 실행 중 동작 — 한 조각이 바꾸면 이웃 조각이 깨진 곳(2026-10-25 후속 고침 6건).
# 그 동작을 바꾸는 조각은 커밋 전 `-m "<내 영역>" --surface <이름>` 으로 이웃 파일까지 돌린다. 새 테스트 파일이 그 동작을 쓰면 여기 한 줄.
SURFACES = {
    "frame": ("카드 iframe 다시 싣기·교체·요소 고르기(교체 뒤 배지·높이·선택 유지)",
              ("test_canvas_swap.py", "test_canvas_busy_app.py", "test_canvas_blocks.py", "test_canvas_blocks_b.py",
               "test_canvas_blocks_place.py", "test_canvas_instant.py", "test_canvas_text_remove.py",
               "test_canvas_claim_watch.py", "test_canvas_replies_live.py", "test_canvas_helper.py", "test_canvas_figma_keys.py",
               "test_canvas_cues.py", "test_canvas_blocks_clear.py", "test_canvas_icon_text.py", "test_canvas_memo_scroll.py",
               "test_canvas_el_multi.py", "test_canvas_attach.py", "test_canvas_text_edit.py",
               "test_canvas_ds_edit.py", "test_canvas_memo_state.py", "test_canvas_modal_zoom.py", "test_canvas_dismiss.py", "test_canvas_twin.py")),
    "board": ("판 위 줄 배치·겹침(판 글·DS 카드·화면 줄·하단 대화창·탭·카메라 첫 자리)",
              ("test_canvas_ds_card.py", "test_canvas_chat.py", "test_canvas_busy_app.py", "test_canvas_layer_flags.py",
               "test_canvas_artboard.py", "test_canvas_tabs.py", "test_canvas_rows.py",
               "test_canvas_receivers.py", "test_canvas_board_text.py", "test_canvas_card_copy.py", "test_canvas_placeholder.py",
               "test_canvas_chat_log.py", "test_canvas_attach.py", "test_canvas_board_notes.py", "test_canvas_labels.py",
               "test_canvas_r27_bars.py", "test_canvas_folders.py", "test_canvas_line_tags.py",
               "test_canvas_board_links.py", "test_canvas_info_card.py")),
}


def pytest_addoption(parser):
    parser.addoption("--surface", default="", help="쉼표로 화면 동작 이름(SURFACES) — -m 고른 것에 그 동작을 쓰는 테스트 파일을 더한다")


# 격리(fable #4): -n 4 에서만 가끔 깨지는 테스트 — -n 실행은 고르지 않고, 끝에 `pytest tests -m serial`(-n 없이)로 따로 돌린다. 원인을 찾으면 여기서 뺀다.
SERIAL = ("test_line_click_shows_end_handles_and_drag_retargets",)


def _xdist_main(config):                            # 일꾼이 아닌 주 프로세스, -n N(N>=1)
    return getattr(config, "workerinput", None) is None and bool(getattr(config.option, "numprocesses", 0))


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
    surf = [x.strip() for x in (config.getoption("--surface", "") or "").split(",") if x.strip()]
    bad = [x for x in surf if x not in SURFACES]
    if bad:
        raise pytest.UsageError(f"SURFACES(tests/conftest.py)에 없는 화면 동작: {bad} — 있는 것: {sorted(SURFACES)}")
    for name, (what, _) in SURFACES.items():
        config.addinivalue_line("markers", f"surface_{name}: {what}")
    if surf:                                          # 표시 고르기(-m)는 이 뒤 mark 플러그인이 읽는다 — 이웃 파일 표시를 OR 로 더함
        extra = " or ".join(f"surface_{x}" for x in surf)
        m = getattr(config.option, "markexpr", "") or ""
        config.option.markexpr = f"({m}) or {extra}" if m else extra
    n = getattr(config.option, "numprocesses", 0) or 0
    if (getattr(config, "workerinput", None) is None and isinstance(n, int) and n > 1
            and not getattr(config.option, "collectonly", False)
            and os.environ.get(hd_testrun.ENV_NOLOCK) != "1" and not os.environ.get(hd_testrun.ENV_RERUN)):
        _RUN["lock"] = hd_testrun.acquire(sys.argv[1:])   # 겹친 -n 실행은 차례로(브라우저 수백 개가 서로를 늦춰 시간 초과를 낸다)


def pytest_unconfigure(config):
    if _RUN.pop("lock", None):                        # 실패·Ctrl+C 에도 pytest 가 부른다
        hd_testrun.release()


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
        for name, (_, files) in SURFACES.items():
            if it.fspath.basename in files:
                it.add_marker(getattr(pytest.mark, "surface_" + name))
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
    _RUN.update(t0=time.time(), failed=[], failed_ids=[], passed=0, skipped=0)


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if report.failed:
            _RUN.setdefault("failed", []).append(report.nodeid.split("::")[-1])
            _RUN.setdefault("failed_ids", []).append(report.nodeid)
        elif report.skipped:
            _RUN["skipped"] = _RUN.get("skipped", 0) + 1
        elif report.when == "call":
            _RUN["passed"] = _RUN.get("passed", 0) + 1


def _abs_id(root, nodeid):                         # 실행마다 rootdir 이 달라도 같은 테스트로 맞추려 파일 부분을 절대 경로로
    f, sep, rest = nodeid.partition("::")
    return str((Path(root) / f).resolve()) + sep + rest


def _rerun_alone(config, ids):
    """-n 실행에서 깨진 것만 -n 0 하위 실행으로 한 번 더(잠금은 이 프로세스가 쥔 채). → (진짜 실패, 혼자 통과, 초)."""
    t0 = time.time()
    fd, out = tempfile.mkstemp(prefix="hd-rerun-", suffix=".json"); os.close(fd)
    env = dict(os.environ, **{hd_testrun.ENV_RERUN: "1", hd_testrun.ENV_NOLOCK: "1", hd_testrun.ENV_RERUN_OUT: out})
    ok = False
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", *[_abs_id(config.rootpath, i) for i in ids], "-n", "0", "-p", "no:cacheprovider", "-q", "--tb=line"],
                           cwd=str(config.rootpath), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        got = json.loads(Path(out).read_text(encoding="utf-8"))
        ok = r.returncode in (0, 1) and got.get("ran", 0) > 0
        again = got.get("failed_ids", [])
    except (OSError, ValueError):
        again = []
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass
    back = {_abs_id(config.rootpath, i): i for i in ids}
    real, flaky = hd_testrun.classify(list(back), again, ok)
    return [back[i] for i in real], [back[i] for i in flaky], round(time.time() - t0, 1)


def pytest_sessionfinish(session, exitstatus):
    if "t0" not in _RUN or getattr(session.config.option, "collectonly", False) or hasattr(session.config, "workerinput"):
        return                                     # xdist(-n): 일꾼마다 쓰지 않고 결과를 모두 받는 주 프로세스만 한 줄
    if os.environ.get(hd_testrun.ENV_RERUN):      # 다시 돌리는 하위 실행: 기록은 부른 실행이 — 결과만 넘긴다
        p = os.environ.get(hd_testrun.ENV_RERUN_OUT)
        if p:
            Path(p).write_text(json.dumps({"ran": session.testscollected,
                                           "failed_ids": [_abs_id(session.config.rootpath, i) for i in _RUN.get("failed_ids", [])]}), encoding="utf-8")
        return
    rerun = None
    ids = list(dict.fromkeys(_RUN.get("failed_ids", [])))
    if ids and _xdist_main(session.config):
        if len(ids) > hd_testrun.RERUN_MAX:
            rerun = {"skipped": f"{len(ids)} > {hd_testrun.RERUN_MAX}"}
        else:
            real, flaky, sec = _rerun_alone(session.config, ids)
            rerun = {"real": [i.split("::")[-1] for i in real], "flaky": [i.split("::")[-1] for i in flaky], "sec": sec}
        _RUN["rerun"] = rerun
    o = session.config.option
    sel = {"m": o.markexpr or "", "k": o.keyword or "", "lf": bool(getattr(o, "lf", False)),
           "files": sorted({Path(str(a)).name for a in session.config.args if str(a).endswith(".py")})}
    scope = "full" if not (sel["m"] or sel["k"] or sel["lf"] or sel["files"]) else ("unit" if sel["m"] == "unit" and not sel["k"] else "part")
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "scope": scope, "sel": sel, "n": session.testscollected,
           "passed": _RUN.get("passed", 0), "failed": _RUN.get("failed", []), "skipped": _RUN.get("skipped", 0),
           "sec": round(time.time() - _RUN["t0"], 1)}
    if rerun:                                      # 깨진 것을 혼자 다시 돌린 결과(review.py 는 읽지 않는 덧붙임 칸)
        rec["rerun"] = rerun
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


def pytest_terminal_summary(terminalreporter):
    rr = _RUN.get("rerun")
    if not rr:
        return
    lines = []
    if "skipped" in rr:
        lines.append(f"[hd-test] 혼자 다시 돌리기 건너뜀: 깨진 것 {rr['skipped']} — 부하가 아니라 고장으로 본다")
    else:
        lines.append(f"[hd-test] 깨진 것만 -n 0 으로 다시({rr['sec']}초):")
        if rr["real"]:
            lines.append("  진짜 실패: " + ", ".join(rr["real"]))
        if rr["flaky"]:
            lines.append("  혼자 통과: " + ", ".join(rr["flaky"]))
        lines.append("[hd-test] " + hd_testrun.summary_line(rr["real"], rr["flaky"]))
    terminalreporter.ensure_newline()
    sys.stdout.flush()                             # 아래 줄은 잠금 대기 줄처럼 utf-8 바이트로(콘솔 cp949 에서 깨지지 않게)
    for ln in lines:
        hd_testrun.say(sys.stdout, ln)
