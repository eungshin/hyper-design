"""주소 복사(R30, Figma '선택 링크 복사') — 주소 줄 규칙(modules/address.js, node).

build(x) = 'hd://<프로젝트>/<화면>[#<요소 경로>]  <화면 파일> · "<글>"' · parse(build(x)) == x (한글 프로젝트·띄어쓰기 경로·# 든 경로 포함).
공유 fixture tests/fixtures/addresses.json — hd/hd_address.py 도 같은 줄을 읽는다(test_hd_address.py).
글 40자 줄이기 · 프로젝트 이름(out → 그 위 폴더) · out 폴더(도우미 __hdOut, 아니면 file:// 경로) · 복사 대상(고른 묶음 안을 누르면 묶음 전체)."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
FIX = json.loads((HERE / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['el-pick.js', 'address.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const A = globalThis.HD.address, fx = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')), out = {};
out.built = fx.lines.map(c => A.build(c.x));
out.parsed = fx.lines.map(c => A.parse(c.line));
out.bad = fx.bad.map(l => A.parse(l));
out.noScreen = A.build({project: 'p', screen: '', file: 'f'});
const long = '가'.repeat(30) + '   나\n다 ' + 'x'.repeat(30);
out.short = [A.short(long), A.short(long).length, A.short('  a \n b  ')];
out.longRound = A.parse(A.build({project: 'p', screen: 's', path: 'body', file: 'C:/o/s.html', text: long})).text;
out.lines = A.lines([{project: 'p', screen: 'a', file: '/o/a.html', text: 'A'}, {project: 'p', screen: '', file: 'x'}, {project: 'p', screen: 'b', path: 'h1', file: '/o/b.html', text: 'B'}]);
out.project = [A.projectOf('C:/Code/hyper-design/runs/dayfine-onboarding-v1/out'), A.projectOf('C:\\runs\\온보딩 시안\\out\\'), A.projectOf('/tmp/canvas'), A.projectOf('C:/'), A.projectOf('')];
out.outOf = [A.outOf('C:/runs/x/out', '/ignored/index.html'), A.outOf('', '/C:/runs/my%20proj/out/index.html'), A.outOf(null, '/home/u/out/index.html')];
out.fileOf = [A.fileOf('C:/runs/x/out', 'screens/home.html'), A.fileOf('C:/runs/x/out/', './a.html'), A.fileOf('C:/runs/x/out', 'C:/abs/b.html')];
const key = x => HD.elPick.key(x.screen, x.path), sel = [{screen: 'a', path: 'h1'}, {screen: 'b', path: 'p'}];
out.targets = [A.targets(sel, {screen: 'b', path: 'p'}, key).map(key), A.targets(sel, {screen: 'c', path: 'x'}, key).map(key), A.targets([], {screen: 'c', path: 'x'}, key).map(key)];
out.say = [A.say(1), A.say(3)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-address-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD), str(HERE / "fixtures" / "addresses.json")],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_matches_shared_fixture_lines(js):
    assert js["built"] == [c["line"] for c in FIX["lines"]]


def test_parse_round_trips_every_fixture_including_korean_and_spaces(js):
    assert js["parsed"] == [c["x"] for c in FIX["lines"]]


def test_line_shape_keeps_path_readable_and_file_raw():
    ko = next(c for c in FIX["lines"] if c["name"] == "korean-project-and-spaces")["line"]
    addr, rest = ko.split("  ", 1)
    assert " " not in addr and addr.count("#") == 1, "주소는 공백 없이 한 덩어리 · # 은 요소 경로 앞 하나뿐"
    assert addr.startswith("hd://온보딩%20시안%202/홈%20화면#%23main"), "한글은 그대로, 공백·# 만 바꿈"
    assert rest.startswith("C:/Users/me/My Designs/온보딩/out/screens/홈 화면.html · "), "파일 경로는 바로 열 수 있게 그대로"
    assert "?hd=" not in ko


def test_unreadable_lines_are_null(js):
    assert js["bad"] == [None] * len(FIX["bad"])


def test_no_screen_builds_nothing_and_lines_skip_it(js):
    assert js["noScreen"] == ""
    assert js["lines"] == 'hd://p/a  /o/a.html · "A"\nhd://p/b#h1  /o/b.html · "B"'


def test_text_is_one_line_and_at_most_40_chars(js):
    s, n, small = js["short"]
    assert n == 40 and s.endswith("…") and "\n" not in s and "  " not in s
    assert small == "a b"
    assert js["longRound"] == s


def test_project_is_folder_above_out_like_hd(js):
    assert js["project"] == ["dayfine-onboarding-v1", "온보딩 시안", "canvas", "", ""]


def test_out_folder_from_helper_or_file_url(js):
    assert js["outOf"] == ["C:/runs/x/out", "C:/runs/my proj/out", "/home/u/out"]
    assert js["fileOf"] == ["C:/runs/x/out/screens/home.html", "C:/runs/x/out/a.html", "C:/abs/b.html"]


def test_targets_whole_selection_when_clicked_inside_else_only_clicked(js):
    assert js["targets"] == [["a:h1", "b:p"], ["c:x"], ["c:x"]]


def test_toast_words(js):
    assert js["say"] == ["주소를 복사했어요", "주소 3개를 복사했어요"]
