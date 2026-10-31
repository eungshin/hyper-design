"""V2 — 캔버스 화면 ↔ 앱 카드 짝 · 기억 열쇠 · 카드 표 · 결과 · 목록 줄 · 고쳐 달라는 짧은 요청(unit — modules/twin.js, 순수).
짝 = /api/app-parts 의 links(parts.json) 로 이어진 부품 파일을 그대로 싣는 카드, 없으면 그 부품 이름의 앱 무대 카드(app.json 무대 = 개발 서버 주소 카드 id).
짝이 없으면 '견줄 앱 화면 없음'. 비교 규칙은 test_canvas_unit_twin_diff.py, 브라우저 = test_canvas_twin.py."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['twin-diff.js', 'twin.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const D = globalThis.HD.twinDiff, T = globalThis.HD.twin, out = {};
const links = {
  home: {file: 'screens/home.html', parts: [{file: 'screens/mock-home.html', repo: 'C:/app', watch: ['ui']}]},
  pay: {file: 'screens/pay.html', parts: [{file: 'screens/./settings.html', repo: 'C:/app', watch: ['ui']}]},
  lone: {file: 'screens/lone.html', parts: [{file: 'screens/nowhere.html', repo: 'C:/app', watch: ['ui']}]}};
const cards = [{id: 'home', file: 'screens/home.html'}, {id: 'mock-home', file: 'screens/mock-home.html'},
  {id: 'pay', file: 'screens/pay.html'}, {id: 'settings', file: 'http://127.0.0.1:5199/hd-stage/settings.html'},
  {id: 'lone', file: 'screens/lone.html'}, {id: 'plain', file: 'screens/plain.html'}];
out.pair = ['home', 'pay', 'lone', 'plain', 'mock-home', 'nope'].map(id => T.pair(id, links, cards));
out.pairBad = [T.pair('home', null, cards), T.pair('home', links, null)];
out.key = [T.key('screens/home.html?v=1', 'g:abc'), T.key('', 'g:abc'), T.key('a', null)];
const it = (role, text) => ({role: role, text: text, tag: 'x', style: {color: 'rgb(0, 0, 0)', bg: 'rgba(0, 0, 0, 0)', fs: 16, fw: 400, radius: 0}});
const A = [it('heading', '결제'), it('button', '지금 결제하기'), it('link', '다음')];
const same = T.result('home', 'mock-home', D.diff(A, A), {size: [3, 3], capped: false, ms: 12});
const dif = T.result('home', 'mock-home', D.diff(A, [A[0], it('button', '결제하기'), A[2], it('img', '로고')]), {size: [3, 4], capped: false, ms: 9});
out.same = same; out.dif = dif;
out.noPair = T.noPair('lone');
out.failed = T.failed('home', 'mock-home', '앱 화면이 답하지 않아요');
out.badge = [T.badge(same), T.badge(dif), T.badge(out.failed), T.badge(out.noPair), T.badge(null)];
const title = id => ({home: '홈', 'mock-home': '앱 홈'})[id] || null;
out.lines = T.lines(dif);
out.req = T.request(dif, title);
const many = T.result('home', 'mock-home', D.diff(Array.from({length: 30}, (_, i) => it('text', 't' + i)), []), {size: [30, 0], capped: false, ms: 1});
out.reqMany = T.request(many, title);
out.reqSame = T.request(same, title);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-twin-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pair_from_parts_links_or_app_stage_name(out):
    home, pay, lone, plain, mock, nope = out["pair"]
    assert home == {"app": "mock-home", "part": "screens/mock-home.html", "how": "part"}, "부품 파일을 그대로 싣는 카드"
    assert pay == {"app": "settings", "part": "screens/settings.html", "how": "stage"}, "그 부품 이름의 앱 무대 카드(개발 서버 주소)"
    assert lone is None and plain is None and nope is None, "부품 카드도 무대도 없음 · 연결 없음 = 짝 없음"
    assert mock is None, "앱 카드 자신은 짝을 찾지 않는다(부품을 끌어 쓰지 않음)"
    assert out["pairBad"] == [None, None]


def test_memo_key_is_screen_fingerprint_and_app_stamp(out):
    assert out["key"] == ["screens/home.html?v=1\ng:abc", None, "a\n"], "지문이 없으면 기억하지 않는다"


def test_result_status_and_count(out):
    s, d = out["same"], out["dif"]
    assert s["status"] == "match" and s["count"] == 0 and s["screen"] == "home" and s["app"] == "mock-home" and s["match"] == 3
    assert s["size"] == [3, 3] and s["ms"] == 12 and s["capped"] is False
    assert d["status"] == "differ" and d["count"] == 2, "글자만 바뀐 버튼(불확실 1) + 앱에만 있는 그림 1"
    assert out["noPair"] == {"status": "no-pair", "screen": "lone", "app": None, "why": "견줄 앱 화면 없음"}
    assert out["failed"] == {"status": "error", "screen": "home", "app": "mock-home", "why": "앱 화면이 답하지 않아요"}


def test_badge_words(out):
    ok, dif, failed, none, nul = out["badge"]
    assert ok == {"text": "앱과 일치", "tone": "ok", "title": "앱 화면 mock-home 과 글자·구조·스타일 토큰이 같아요"}
    assert dif["text"] == "다름 2" and dif["tone"] == "diff"
    assert failed == {"text": "검증 못 함", "tone": "none", "title": "앱 화면이 답하지 않아요"}
    assert none is None and nul is None, "짝 없는 화면엔 표가 없다"


def test_list_lines_and_short_request(out):
    assert out["lines"] == [                                    # 차례 = 앱에 없음 · 앱에만 · 스타일 · 확실하지 않음
        {"kind": "extra", "a": None, "b": 3, "label": "앱에만 있음 · 그림 '로고'"},
        {"kind": "unsure", "a": 1, "b": 1, "label": "확실하지 않음 · 버튼 '지금 결제하기' ↔ '결제하기' (글자 다름)"}]
    r = out["req"]
    assert r.splitlines()[0] == "캔버스 화면 홈(home) ↔ 앱 화면 앱 홈(mock-home): 다른 곳 2개 — 캔버스(디자인)에 맞게 앱을 고친 뒤 `hd verify home` 으로 확인"
    assert "- 확실하지 않음 · 버튼 '지금 결제하기' ↔ '결제하기' (글자 다름)" in r and "- 앱에만 있음 · 그림 '로고'" in r
    assert len(r) < 600, "목록만 담은 짧은 글(스크린샷 없음)"
    many = out["reqMany"].splitlines()
    assert len(many) == 1 + 20 + 1 and many[-1] == "- 외 10개", "20줄까지, 나머지는 '외 N개'"
    assert out["reqSame"] == "", "다른 곳이 없으면 보낼 글도 없다"
