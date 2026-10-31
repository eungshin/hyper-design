"""V1 — 대화창 '/both'(unit — modules/chat-both.js + chat-cmd 명령 표 + part_stamp.screen_links).
캔버스 화면과 parts.json 으로 이어진 실제 앱을 함께 고치라는 요청 줄: 화면마다 캔버스 파일 + 앱 저장소·경로 + 'hd verify <화면>' 한 줄.
연결 없는 화면이 대상이면 칩·보내기 없음(View 가 토스트). 브라우저 = test_canvas_chat_both.py."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import part_stamp as PS  # noqa: E402

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'chat-cmd.js', 'chat-both.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const C = globalThis.HD.chat, K = globalThis.HD.chatCmd, B = globalThis.HD.chatBoth, out = {};
const title = id => ({pay: '결제', done: '완료', home: '홈'})[id] || null;
const body = {parts: [], stale: [], links: {
  pay: {file: 'screens/pay.html', parts: [{file: 'screens/app-pay.html', repo: 'C:/Code/app', watch: ['src/pay', 'src/ui']}]},
  home: {file: 'screens/home.html', parts: [{file: 'screens/app-home.html', repo: 'C:/Code/app', watch: ['src/home']},
                                           {file: 'screens/app-nav.html', repo: 'D:/nav', watch: ['nav']}]},
  bad1: {file: 'screens/x.html', parts: [{file: 'a.html', repo: '', watch: ['x']}]},     // 저장소 없음 = 버림
  bad2: 'nope', bad3: {file: '', parts: []}}};
out.cmd = K.COMMANDS.filter(c => c.name === 'both')[0];
out.matchB = [K.match('/b').map(c => c.name), K.match('둘 다 /bo').map(c => c.name), K.match('/').map(c => c.name)];
const L = B.links(body);
out.links = L;
out.linksNone = [B.links(null), B.links({parts: []}), B.links({links: 'x'})];
const chips = ids => C.chips({ids: ids, titleOf: title, els: []});
const el = C.chips({ids: [], titleOf: title, els: [{screen: 'home', h: {path: 'body > h1', text: '홈', kind: 'text'}}]});
out.tLinked = B.targets(chips(['pay']), L);
out.tUnlinked = B.targets(chips(['pay', 'done']), L);
out.tMany = B.targets(chips(['home', 'pay']), L);
out.tEl = B.targets(el, L);
out.tAll = B.targets([], L);
out.tNone = B.targets([], {});
out.chip = B.chip();
out.blockOne = B.block(['pay'], L, title);
out.blockMany = B.block(['home', 'pay'], L, title);
const both = chips(['home', 'pay']).concat([B.chip()]);
out.scope = C.scope([B.chip()]);
out.fold = C.fold(chips(['pay', 'done', 'home']).concat([B.chip()]), false).shown.map(c => c.key);
let k = 0; const mk = () => 'n' + (++k);
const r = C.build(both, '버튼을 파랗게', {first: 'pay', titleOf: title}, mk);
out.built = B.apply(r.memos, ['home', 'pay'], L, title).map(m => ({screen: m.screen, note: m.note}));
out.orig = r.memos.map(m => m.note);
k = 0; const all = C.build([B.chip()], '전부 파랗게', {first: 'pay', titleOf: title}, mk);
out.builtAll = B.apply(all.memos, ['home', 'pay'], L, title).map(m => ({screen: m.screen, scope: m.scope, note: m.note}));
out.req = globalThis.HD.edits.request(out.built.map((m, i) => Object.assign({}, r.memos[i], {note: m.note})), 'C:/out', {}, null);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chat-both-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_both_is_a_slash_command(out):
    assert out["cmd"] == {"name": "both", "label": "/both", "hint": "캔버스 화면과 연결된 실제 앱에 함께 적용"}
    assert out["matchB"] == [["both"], ["both"], ["memo", "both"]], "글 도중에도 — '/' 만이면 둘 다"


def test_links_keep_only_well_formed_screens(out):
    assert sorted(out["links"]) == ["home", "pay"], "저장소·파일이 없는 항목은 버린다"
    assert out["links"]["pay"] == {"file": "screens/pay.html", "parts": [{"file": "screens/app-pay.html", "repo": "C:/Code/app", "watch": ["src/pay", "src/ui"]}]}
    assert out["linksNone"] == [{}, {}, {}], "답이 없거나 links 칸이 없으면(옛 도우미) 연결 없음"


def test_targets_linked_unlinked_and_many(out):
    assert out["tLinked"] == {"ids": ["pay"], "missing": [], "ok": True}
    assert out["tUnlinked"] == {"ids": ["pay", "done"], "missing": ["done"], "ok": False}, "하나라도 연결이 없으면 안 됨"
    assert out["tMany"] == {"ids": ["home", "pay"], "missing": [], "ok": True}, "고른 차례"
    assert out["tEl"] == {"ids": ["home"], "missing": [], "ok": True}, "요소 칩 = 그 화면"
    assert out["tAll"] == {"ids": ["home", "pay"], "missing": [], "ok": True}, "고른 것이 없으면 연결된 화면 모두"
    assert out["tNone"] == {"ids": [], "missing": [], "ok": False}, "연결된 화면이 하나도 없으면 안 됨"


def test_chip_is_context_only(out):
    assert out["chip"] == {"key": "both", "kind": "both", "label": "캔버스+앱"}
    assert out["scope"] == "all", "칩만으로 범위를 정하지 않는다"
    assert out["fold"] == ["screen:pay", "screen:done", "both"], "접히지 않는다"


def test_block_names_canvas_file_app_repo_paths_and_verify(out):
    b = out["blockOne"]
    assert b.startswith("캔버스+앱 함께 적용"), b
    assert "결제(pay) · 캔버스: screens/pay.html" in b
    assert "앱: C:/Code/app · 경로: src/pay, src/ui (부품 screens/app-pay.html)" in b
    assert "둘 다 고친 뒤 `hd verify pay` 으로 확인" in b
    m = out["blockMany"]
    assert m.index("홈(home)") < m.index("결제(pay)"), "화면 차례대로"
    assert "앱: D:/nav · 경로: nav (부품 screens/app-nav.html)" in m and m.count("hd verify home") == 1 and m.count("hd verify pay") == 1


def test_apply_puts_each_screens_block_in_its_memo(out):
    assert out["orig"] == ["버튼을 파랗게", "버튼을 파랗게"], "build 는 /both 칩으로 새 메모를 만들지 않고 글도 그대로"
    home, pay = out["built"]
    assert home["screen"] == "home" and home["note"].startswith("버튼을 파랗게\n\n캔버스+앱 함께 적용")
    assert "hd verify home" in home["note"] and "hd verify pay" not in home["note"], "화면마다 제 줄만"
    assert "hd verify pay" in pay["note"] and "screens/app-pay.html" in pay["note"]
    (a,) = out["builtAll"]
    assert a["scope"] == "all" and "hd verify home" in a["note"] and "hd verify pay" in a["note"], "모든 화면 요청 = 연결된 화면 모두"


def test_request_keeps_the_send_shape(out):
    req = out["req"]
    assert req.startswith("[hyper-design 수정 요청] out=C:/out · 2건"), req
    assert "요청: 버튼을 파랗게" in req and "hd verify pay" in req and "C:/Code/app" in req


def test_screen_links_from_deps_and_parts():
    parts = [{"file": "screens/app-pay.html", "repo": "C:/Code/app", "watch": ["src/pay"], "build": ["x", "{out}"]},
             {"file": "screens/app-nav.html", "repo": "D:/nav", "watch": ["nav"], "build": ["x", "{out}"]}]
    deps = {"pay": ["screens/pay.html", "screens/app-pay.html", "screens/app-nav.html"], "done": ["screens/done.html"],
            "nav": ["screens/nav.html", "screens/app-nav.html"]}
    got = PS.screen_links(deps, parts)
    assert sorted(got) == ["nav", "pay"], "부품을 끌어 쓰지 않는 화면은 없다"
    assert got["pay"] == {"file": "screens/pay.html", "parts": [
        {"file": "screens/app-pay.html", "repo": "C:/Code/app", "watch": ["src/pay"]},
        {"file": "screens/app-nav.html", "repo": "D:/nav", "watch": ["nav"]}]}
    assert PS.screen_links({}, parts) == {} and PS.screen_links(deps, []) == {} and PS.screen_links(None, None) == {}
