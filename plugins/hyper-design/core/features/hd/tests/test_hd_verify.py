"""hd verify <화면>(V2) — 종료 코드 0 일치 / 1 다름 / 2 검증 못 함(캔버스 안 열림 · 짝 없음 · 시간 넘김 10초 · 도우미 없음) · JSON + 한 줄 요약.
순수: hd_verify.outcome(결과 → 코드·줄) + hd.main 을 가짜 허브로(소켓·브라우저 없음). 실제 길(도우미 → 열린 캔버스 → 결과)은 canvas test_canvas_twin.py."""
import json, sys
from pathlib import Path

import pytest

HD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HD))
sys.path.append(str(HD.parent / "canvas"))
import hd  # noqa: E402
import hd_sdk as S  # noqa: E402
import hd_verify as V  # noqa: E402

DIFFER = {"status": "differ", "screen": "home", "app": "mock-home", "count": 1, "match": 3, "missing": [], "extra": [], "style": [],
          "unsure": [{"a": 2, "b": 2, "role": "button", "text": "지금 결제하기", "why": "text", "other": {"role": "button", "text": "결제하기"}}],
          "size": [4, 4], "capped": False, "ms": 30}
MATCH = dict(DIFFER, status="match", count=0, match=4, unsure=[])


class FakeProject:
    name = "proj"

    def __init__(self, res=None, err=None):
        self.res, self.err, self.asked = res, err, []

    def verify(self, screen):
        self.asked.append(screen)
        if self.err:
            raise self.err
        return dict(self.res, screen=screen)


class FakeHub:
    def __init__(self, project=None, err=None):
        self.project, self.err = project, err

    def pick(self, ref=None):
        if self.err:
            raise self.err
        return self.project


def run(monkeypatch, capsys, hub, *args):
    monkeypatch.setattr(hd, "_hub", lambda: hub)
    code = hd.main(["verify", *args])
    o = capsys.readouterr()
    return code, o.out, o.err


@pytest.mark.parametrize("res,code", [
    (MATCH, 0), (DIFFER, 1),
    ({"status": "no-pair", "screen": "x", "app": None, "why": "견줄 앱 화면 없음"}, 2),
    ({"status": "no-canvas", "screen": "x", "why": "열린 캔버스가 없어요"}, 2),
    ({"status": "timeout", "screen": "x", "why": "답하지 않았어요"}, 2),
    ({"status": "error", "screen": "x", "why": "앱 화면이 답하지 않아요"}, 2),
    ({"status": "??"}, 2), (None, 2), ("x", 2)])
def test_outcome_code_per_status(res, code):
    assert V.outcome(res)[0] == code


def test_outcome_lines():
    assert V.outcome(MATCH)[1] == "home ↔ mock-home · 앱과 일치 (항목 4)"
    assert V.outcome(DIFFER)[1] == "home ↔ mock-home · 다름 1 — 앱에 없음 0 · 앱에만 0 · 스타일 0 · 확실하지 않음 1"
    assert V.outcome({"status": "no-pair", "screen": "x", "why": "견줄 앱 화면 없음"})[1] == "x · 검증 못 함: 견줄 앱 화면 없음"


def test_cli_match_is_0_and_prints_json_then_one_line(monkeypatch, capsys):
    p = FakeProject(MATCH)
    code, out, err = run(monkeypatch, capsys, FakeHub(p), "home")
    assert code == 0 and p.asked == ["home"]
    *body, last = out.strip().splitlines()
    assert json.loads("\n".join(body))["status"] == "match"
    assert last == "home ↔ mock-home · 앱과 일치 (항목 4)"


def test_cli_differ_is_1_and_json_mode_prints_json_only(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, FakeHub(FakeProject(DIFFER)), "home", "--json")
    assert code == 1 and json.loads(out)["unsure"][0]["other"]["text"] == "결제하기"


def test_cli_no_pair_and_no_canvas_are_2(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, FakeHub(FakeProject({"status": "no-pair", "app": None, "why": "견줄 앱 화면 없음"})), "lone")
    assert code == 2 and out.strip().splitlines()[-1] == "lone · 검증 못 함: 견줄 앱 화면 없음"
    code, _, _ = run(monkeypatch, capsys, FakeHub(FakeProject({"status": "no-canvas", "why": "열린 캔버스가 없어요"})), "home")
    assert code == 2


def test_cli_timeout_is_2_server_side_and_client_side(monkeypatch, capsys):
    code, _, _ = run(monkeypatch, capsys, FakeHub(FakeProject({"status": "timeout", "why": "열린 캔버스가 10초 안에 답하지 않았어요"})), "home")
    assert code == 2
    code, out, err = run(monkeypatch, capsys, FakeHub(FakeProject(err=S.TimedOut("도우미가 답하지 않았어요"))), "home")
    assert code == 2 and "검증 못 함" in out


def test_cli_no_helper_or_old_helper_is_2(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, FakeHub(err=S.NotFound("떠 있는 캔버스가 없어요")), "home")
    assert code == 2 and "검증 못 함" in out and "떠 있는 캔버스가 없어요" in out
    code, _, _ = run(monkeypatch, capsys, FakeHub(FakeProject(err=S.NotFound("도우미가 거절했어요(404): 모르는 주소"))), "home")
    assert code == 2


def test_cli_never_opens_a_browser(monkeypatch, capsys):
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: pytest.fail("브라우저를 띄우면 안 된다"))
    assert run(monkeypatch, capsys, FakeHub(FakeProject(MATCH)), "home")[0] == 0
