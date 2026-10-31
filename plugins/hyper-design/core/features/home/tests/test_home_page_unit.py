"""홈 화면 Model — home-model.js 순수 규칙 단위 테스트(node). 브라우저 없음.

줄 고르기(모양 틀린 줄은 빼고 bad) · 구역(최근/모두/별표/휴지통)과 차례 · 찾기(대소문자 무시, 제목·이름) · 상대 시각 ·
키보드 고르기 이동(끝에서 멈춤) · 우클릭 메뉴(휴지통은 되돌리기·완전히 빼기) · 새 이름 · 이름 바꾸기 값 · 빈 화면 문구.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/home-model.js', 'utf8'), {filename: 'home-model.js'});
const M = globalThis.HDHomeModel, out = {};
const body = [
  {name: 'alpha', title: 'Alpha 결제', state: 'running', last_opened: '2026-10-25T09:00:00+09:00', created: '2026-10-01T00:00:00+09:00', starred: true},
  {name: 'beta', title: '', state: 'off', last_opened: '2026-10-24T09:00:00+09:00', created: '2026-10-02T00:00:00+09:00'},
  {name: 'gamma', title: '감마', state: 'missing', last_opened: null, created: '2026-10-20T00:00:00+09:00'},
  {name: 'old', title: '지운 것', state: 'off', last_opened: '2026-10-25T10:00:00+09:00', trashed: '2026-10-25T11:00:00+09:00', starred: true},
  {name: 'old2', title: '먼저 지운 것', state: 'weird', trashed: '2026-10-20T11:00:00+09:00'},
  {name: 'alpha', title: 'dup'}, {title: 'no name'}, 'junk', null
];
const n = M.normalize(body);
out.n = {names: n.rows.map(r => r.name), bad: n.bad, beta: n.rows[1], old2: n.rows[4].state};
out.notList = [M.normalize({error: 'x'}), M.normalize(null)];
const R = n.rows;
out.sec = {};
['recent', 'all', 'starred', 'trash'].forEach(s => out.sec[s] = M.section(R, s).map(r => r.name));
out.search = [M.search(R, 'alpha').map(r => r.name), M.search(R, '  ALPHA ').map(r => r.name), M.search(R, '감').map(r => r.name),
              M.search(R, 'bet').map(r => r.name), M.search(R, '').length, M.search(R, 'zzz').length];
out.view = M.view(R, 'trash', '먼저').map(r => r.name);
const now = new Date(2026, 9, 25, 15, 0, 0).getTime();
const at = (y, mo, d, h, mi, s) => new Date(y, mo - 1, d, h, mi || 0, s || 0).toISOString();
out.rel = [M.relTime(at(2026, 10, 25, 14, 59, 30), now), M.relTime(new Date(now - 20e3).toISOString(), now),
           M.relTime(at(2026, 10, 25, 14, 15), now), M.relTime(at(2026, 10, 25, 12, 0), now), M.relTime(at(2026, 10, 25, 0, 30), now),
           M.relTime(at(2026, 10, 24, 23, 0), now), M.relTime(at(2026, 10, 24, 0, 5), now), M.relTime(at(2026, 10, 21, 8), now),
           M.relTime(at(2025, 3, 2, 8), now), M.relTime(null, now), M.relTime('nope', now), M.relTime('2026-10-25 14:58:00', now)];
// 7칸, 3열: [0 1 2][3 4 5][6]
out.mv = [M.move(-1, 'ArrowRight', 7, 3), M.move(0, 'ArrowLeft', 7, 3), M.move(2, 'ArrowRight', 7, 3), M.move(6, 'ArrowRight', 7, 3),
          M.move(1, 'ArrowDown', 7, 3), M.move(4, 'ArrowDown', 7, 3), M.move(6, 'ArrowDown', 7, 3), M.move(4, 'ArrowUp', 7, 3),
          M.move(1, 'ArrowUp', 7, 3), M.move(3, 'Home', 7, 3), M.move(3, 'End', 7, 3), M.move(0, 'ArrowRight', 0, 3), M.move(5, 'ArrowDown', 7, 0)];
out.menu = {live: M.menu(R[0], 'recent'), gone: M.menu(R[2], 'all'), trash: M.menu(R[3], 'trash'), none: M.menu(null, 'all')};
out.newTitle = [M.newTitle([]), M.newTitle([{title: '새 프로젝트 1'}, {title: '새 프로젝트 3'}])];
out.rename = [M.renameValue('  새 이름 ', '옛'), M.renameValue('옛', '옛'), M.renameValue('   ', '옛'), M.renameValue(null, '옛')];
out.empty = [M.empty('recent', ''), M.empty('trash', ' '), M.empty('all', ' 결제 '), M.empty('starred')];
out.sv = [M.validSection('trash'), M.validSection('nope'), M.validSection(null)];
out.ini = [M.initial('laundry-v1'), M.initial('  감마 앱'), M.initial('(새) 결제'), M.initial(''), M.initial(null), M.initial('---')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-home-js-"))
    try:
        (tmp / "m.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "m.js"), str(HOME)], capture_output=True, text=True, encoding="utf-8",
                           env={"TZ": "Asia/Seoul", **__import__("os").environ})
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_normalize_drops_bad_rows_and_fills_defaults(out):
    assert out["n"]["names"] == ["alpha", "beta", "gamma", "old", "old2"], "이름 없는 줄·같은 이름 두 번째·객체 아닌 줄은 뺀다"
    assert out["n"]["bad"] == 4
    b = out["n"]["beta"]
    assert b["title"] == "beta" and b["starred"] is False and b["trashed"] is None and b["thumb"] is None, "빈 제목 = 이름"
    assert out["n"]["old2"] == "off", "모르는 state = off"
    assert all(x == {"rows": [], "bad": 1} for x in out["notList"]), "목록이 아니면 빈 줄 + bad"


def test_sections_filter_and_order(out):
    s = out["sec"]
    assert s["recent"] == ["alpha", "beta"], "최근 = 연 적 있는 것, 최근 것부터, 휴지통 빼고"
    assert s["all"] == ["alpha", "beta", "gamma"], "모두 = 휴지통 밖 전부, 연 때(없으면 만든 때) 최근 것부터"
    assert s["starred"] == ["alpha"], "별표 — 휴지통의 별표는 빼고"
    assert s["trash"] == ["old", "old2"], "휴지통 = 넣은 때 최근 것부터"


def test_search_casefold_title_and_name(out):
    a, upper, ko, by_name, empty_n, none = out["search"]
    assert a == ["alpha"] and upper == ["alpha"], "대소문자·앞뒤 공백 무시"
    assert ko == ["gamma"], "한글 제목 부분 일치"
    assert by_name == ["beta"], "이름(slug)으로도 찾는다"
    assert empty_n == 5 and none == 0
    assert out["view"] == ["old2"], "구역 안에서 찾기"


def test_relative_time_labels(out):
    assert out["rel"] == ["방금 전", "방금 전", "45분 전", "3시간 전", "14시간 전", "어제", "어제", "10-21", "2025-03-02", "", "", "2분 전"]


def test_keyboard_move_stops_at_edges(out):
    assert out["mv"] == [0, 0, 3, 6, 4, 6, 6, 1, 1, 0, 6, -1, 6], "→/←/↓/↑/Home/End — 끝에서 멈추고, 아래 줄에 그 열이 없으면 마지막 칸, 열 0 = 1열"


def test_context_menu_items(out):
    m = out["menu"]
    assert [x if x == "-" else x["id"] for x in m["live"]] == ["open", "rename", "star", "reveal", "-", "trash"]
    assert m["live"][2]["label"] == "별표 빼기", "별표된 것은 '별표 빼기'"
    assert [x["disabled"] for x in m["gone"] if x != "-" and x["id"] == "reveal"] == [True], "폴더 없음 = 폴더 열기 못 누름"
    assert [x["label"] for x in m["trash"]] == ["되돌리기", "목록에서 완전히 빼기"]
    assert m["none"] == []


def test_new_title_rename_empty_section(out):
    assert out["newTitle"] == ["새 프로젝트 1", "새 프로젝트 2"]
    assert out["rename"] == ["새 이름", None, None, None], "빈 값·같은 값은 무시"
    e = out["empty"]
    assert e[0] == "최근에 연 프로젝트가 없어요" and e[1] == "휴지통이 비었어요" and e[2] == "‘결제’와 맞는 프로젝트가 없어요" and "별표" in e[3]
    assert out["sv"] == ["trash", "recent", "recent"], "모르는 구역 = 최근 항목"


def test_placeholder_initial_letter(out):
    """F20(10-31): 썸네일이 아직 없으면 빈 상자 대신 이름 첫 글자 — 영문은 대문자, 앞 공백·문장 부호는 건너뜀, 글자가 없으면 '?'."""
    assert out["ini"] == ["L", "감", "새", "?", "?", "-"]
