"""여러 화면에 같은 메모 Model — modules/memo-batch.js 순수 함수 단위 테스트(node). 브라우저 없음.

draft: 고른 카드 id(겹침·빈 값 빼고 차례 그대로) → 화면 전체(body) 메모 초안. 한 장이면 지금 openCardMemo 와 같은 모양.
scopes: 여러 장이면 '이 요소'를 빼고 '이 화면' 말을 '고른 화면 N개'로. build: 여러 장 + 범위 screen = 화면마다 메모 하나(같은 batch),
범위 all = 첫 화면에 메모 하나, 한 장 = 지금과 같은 메모 하나(batch 없음).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

BATCH_JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const B = globalThis.HD.memoBatch, S = globalThis.HD.annotation.SCOPES, out = {};
const title = id => ({a: '홈', b: '설정', c: '목록'})[id] || id;
let k = 0; const mk = () => 'id' + (++k);
out.one = B.draft(['a'], title);
out.many = B.draft(['a', 'b', 'a', '', null, 'c'], title);
out.empty = B.draft([], title);
out.multi = [B.multi(out.one), B.multi(out.many), B.multi(null)];
out.scopesOne = B.scopes(out.one, S);
out.scopesMany = B.scopes(out.many, S);
out.defOne = B.defaultScope(out.one); out.defMany = B.defaultScope(out.many);
out.label = [B.label(out.one), B.label(out.many)];
k = 0; out.buildMany = B.build(out.many, {note: '여백 줄이기', intent: 'change', scope: 'screen'}, mk);
k = 0; out.buildAll = B.build(out.many, {note: '글꼴 키우기', intent: 'question', scope: 'all'}, mk);
k = 0; out.buildElemOnMany = B.build(out.many, {note: 'x', intent: 'change', scope: 'element'}, mk);
k = 0; out.buildOne = B.build(out.one, {note: '한 장', intent: 'change', scope: 'screen'}, mk);
k = 0; out.buildOneElem = B.build(out.one, {note: '한 장', intent: 'change', scope: 'element'}, mk);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-batch-js-"))
    try:
        (tmp / "b.js").write_text(BATCH_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "b.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_single_draft_matches_card_memo(out):
    assert out["one"] == {"screen": "a", "screens": ["a"], "titles": ["홈"], "targets": [{"path": "body", "text": "홈", "rect": None}]}


def test_many_draft_drops_duplicates_and_blanks_keeps_order(out):
    assert out["many"]["screens"] == ["a", "b", "c"]
    assert out["many"]["titles"] == ["홈", "설정", "목록"]
    assert out["many"]["screen"] == "a"
    assert out["empty"] is None, "고른 카드가 없으면 초안도 없다"
    assert out["multi"] == [False, True, False]


def test_scopes_for_many_hide_element_and_name_the_count(out):
    assert out["scopesOne"] == [["element", "이 요소"], ["screen", "이 화면"], ["all", "모든 화면"]]
    assert out["scopesMany"] == [["screen", "고른 화면 3개"], ["all", "모든 화면"]]
    assert out["defOne"] == "screen" and out["defMany"] == "screen"


def test_label(out):
    assert out["label"] == ["홈 — 화면 전체", "고른 화면 3개 — 홈 · 설정 · 목록"]


def test_build_many_makes_one_memo_per_screen_with_shared_batch(out):
    ms = out["buildMany"]
    assert [m["screen"] for m in ms] == ["a", "b", "c"]
    assert {m["batch"] for m in ms} == {"id1"}, "같은 batch id 하나"
    assert len({m["id"] for m in ms}) == 3 and "id1" not in {m["id"] for m in ms}
    for m, t in zip(ms, ["홈", "설정", "목록"]):
        assert m["targets"] == [{"path": "body", "text": t, "rect": None}]
        assert (m["path"], m["text"], m["note"], m["intent"], m["scope"], m["sent"]) == ("body", t, "여백 줄이기", "change", "screen", False)


def test_build_all_scope_is_single_memo_on_first_screen(out):
    ms = out["buildAll"]
    assert len(ms) == 1 and ms[0]["screen"] == "a" and ms[0]["scope"] == "all" and ms[0]["intent"] == "question"
    assert "batch" not in ms[0]


def test_build_many_with_element_scope_still_goes_to_every_screen(out):
    assert [m["scope"] for m in out["buildElemOnMany"]] == ["screen"] * 3, "여러 장에는 '이 요소'가 없다 — 화면 전체로"


def test_build_single_is_unchanged_shape(out):
    (m,) = out["buildOne"]
    assert m == {"id": "id1", "screen": "a", "targets": [{"path": "body", "text": "홈", "rect": None}], "path": "body", "text": "홈",
                 "rect": None, "note": "한 장", "intent": "change", "sent": False, "scope": "screen"}
    (e,) = out["buildOneElem"]
    assert "scope" not in e and "batch" not in e, "이 요소 = 칸 없음(옛 메모와 같음)"
