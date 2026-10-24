"""프로젝트 메뉴(#246) Model — modules/projects.js 순수 함수 단위 테스트(node). 브라우저 없음.

rows: 도우미 GET /api/projects 줄 → 상태(주소 있음 = 열림 · out 없음 = 없음 · 그 밖 꺼짐) · 지금 캔버스(out 경로 비교, hd_projects.key 와 같음) ·
'없음' 줄은 못 누르고 까닭이 있다 · 차례는 받은 그대로 · 모양이 틀린 줄은 빼고 bad 로 센다 · 목록이 아니면 빈 줄 + bad.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/projects.js', 'utf8'), {filename: 'projects.js'});
const P = globalThis.HD.projects, out = {};
const body = [
  {name: 'zeta', out: 'C:\\Runs\\Zeta\\out', state: 'running', url: 'http://127.0.0.1:5000/index.html?hd=t', pid: 1, last_opened: '2026-10-23T09:05:44+09:00'},
  {name: 'alpha', out: 'C:/runs/alpha/out', state: 'off', url: null, pid: null, last_opened: null},
  {name: 'gone', out: '/tmp/gone/out', state: 'missing', url: null, pid: null, last_opened: '2026-10-01T00:00:00'},
  {out: '/no/name'}, 'junk', null
];
out.r = P.rows(body, 'c:/runs/zeta/out/');
out.notList = [P.rows({error: 'x'}, null), P.rows(null, null)];
out.noCur = P.rows(body.slice(0, 2), null).rows.map(r => r.current);
out.keys = [P.key('C:\\A\\b\\'), P.key('/Home/X/'), P.key('C:/'), P.key('c:')];
out.when = [P.when(null), P.when(''), P.when('2026-01-02 03:04:05'), P.when('어제')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-projects-js-"))
    try:
        (tmp / "p.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "p.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_state_word_and_order_as_given(out):
    rs = out["r"]["rows"]
    assert [r["name"] for r in rs] == ["zeta", "alpha", "gone"], "차례는 도우미가 준 그대로"
    assert [(r["state"], r["word"]) for r in rs] == [("open", "열림"), ("off", "꺼짐"), ("missing", "없음")]


def test_current_canvas_by_out_path(out):
    assert [r["current"] for r in out["r"]["rows"]] == [True, False, False], "역슬래시·대소문자(드라이브 경로)·끝 '/' 를 무시하고 out 으로 비교"
    assert out["noCur"] == [False, False], "지금 out 을 모르면 표시 없음"


def test_missing_is_not_clickable_and_says_why(out):
    rs = {r["name"]: r for r in out["r"]["rows"]}
    assert rs["gone"]["clickable"] is False and "out 폴더가 없어" in rs["gone"]["why"] and "hd forget gone" in rs["gone"]["why"]
    assert rs["zeta"]["clickable"] and rs["alpha"]["clickable"] and rs["zeta"]["why"] == rs["alpha"]["why"] == ""


def test_last_opened_text(out):
    rs = out["r"]["rows"]
    assert [r["when"] for r in rs] == ["10-23 09:05", "-", "10-01 00:00"]
    assert out["when"] == ["-", "-", "01-02 03:04", "어제"], "모르는 모양은 받은 글 그대로"


def test_bad_rows_are_counted_not_drawn(out):
    assert out["r"]["bad"] == "모양이 틀린 줄 3개를 건너뜀"
    assert all(x == {"rows": [], "bad": "프로젝트 목록 모양이 아니에요"} for x in out["notList"])


def test_key_matches_hd_projects_key(out):
    assert out["keys"] == ["c:/a/b", "/Home/X", "c:/", "c:"]


# ---- task 44: 고르기 창·머리 제목이 쓰는 규칙 ----
JS2 = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/projects.js', 'utf8'), {filename: 'projects.js'});
const P = globalThis.HD.projects, out = {};
const now = new Date(2026, 9, 25, 15, 0, 0).getTime();
const iso = (y, mo, d, h, mi, s) => new Date(y, mo, d, h, mi, s || 0).toISOString();
out.ago = [P.ago(iso(2026, 9, 25, 14, 59, 40), now), P.ago(new Date(now - 20 * 1000).toISOString(), now), P.ago(iso(2026, 9, 25, 14, 30), now),
           P.ago(iso(2026, 9, 25, 12, 0), now), P.ago(iso(2026, 9, 24, 23, 0), now), P.ago(iso(2026, 9, 21, 9, 0), now),
           P.ago(iso(2025, 2, 3, 9, 0), now), P.ago(null, now), P.ago('어제쯤', now), P.ago(new Date(now + 60000).toISOString(), now)];
const rs = P.rows([
  {name: 'pay', title: '결제 흐름', out: '/a/out', state: 'running', url: 'http://x', thumb: 'http://127.0.0.1:12270/thumb/pay.png?t=1', starred: true, trashed: null},
  {name: 'gym', title: '', out: '/b/out', state: 'off', url: null, thumb: 5, trashed: '2026-10-20T00:00:00'},
  {name: 'Café', out: '/c/out', state: 'off', url: null}
], '/b/out').rows;
out.rows = rs.map(r => ({name: r.name, title: r.title, thumb: r.thumb, starred: r.starred, trashed: r.trashed}));
out.filter = [P.filter(rs, '').map(r => r.name), P.filter(rs, '결제').map(r => r.name), P.filter(rs, ' CAFÉ ').map(r => r.name),
              P.filter(rs, 'gym').map(r => r.name), P.filter(rs, 'PAY').map(r => r.name)];
out.current = [P.current(rs) && P.current(rs).name, P.current(rs.slice(0, 1))];
out.newTitle = [P.newTitle([]), P.newTitle(['새 프로젝트 1', '새 프로젝트 3']), P.newTitle(['새 프로젝트 1', '새 프로젝트 2', null])];
out.shown = [P.shown('세탁 앱', '/x/out'), P.shown('전체 화면 한눈에 보기', 'C:/runs/laundry-v1/out'), P.shown('', '/r/gym/'),
             P.shown(null, '/r/out/index.html'), P.shown(null, ''), P.shown('  ', 'C:\\runs\\dayfine\\out')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out2():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-projects-js2-"))
    try:
        (tmp / "p.js").write_text(JS2, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "p.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_relative_time_words(out2):
    assert out2["ago"] == ["방금 전", "방금 전", "30분 전", "3시간 전", "어제", "10-21", "2025-03-03", "-", "어제쯤", "방금 전"], \
        "1분 안 = 방금 전(앞선 시각도) · 1시간 안 = N분 · 같은 날 = N시간 · 하루 전 날 = 어제 · 그 밖 MM-DD(다른 해는 연도까지) · 모르는 글은 그대로"


def test_rows_carry_title_thumb_star_trash(out2):
    assert out2["rows"] == [
        {"name": "pay", "title": "결제 흐름", "thumb": "http://127.0.0.1:12270/thumb/pay.png?t=1", "starred": True, "trashed": False},
        {"name": "gym", "title": "gym", "thumb": None, "starred": False, "trashed": True},
        {"name": "Café", "title": "Café", "thumb": None, "starred": False, "trashed": False}], "제목이 없으면 이름 · 글 아닌 thumb 은 없음"


def test_filter_hides_trash_and_matches_casefold(out2):
    assert out2["filter"] == [["pay", "Café"], ["pay"], ["Café"], [], ["pay"]], "휴지통은 늘 빼고 · 제목·이름에서 대소문자 무시 부분 일치"


def test_current_row(out2):
    assert out2["current"] == ["gym", None]


def test_new_project_default_name(out2):
    assert out2["newTitle"] == ["새 프로젝트 1", "새 프로젝트 2", "새 프로젝트 3"], "쓰지 않은 가장 작은 번호"


def test_header_title_without_project_row(out2):
    assert out2["shown"] == ["세탁 앱", "laundry-v1", "gym", "r", "", "dayfine"], \
        "manifest 제목이 있으면 그것 · 옛 기본 문구('전체 화면 한눈에 보기')나 빈 값이면 폴더 이름(out 이면 그 위)"
