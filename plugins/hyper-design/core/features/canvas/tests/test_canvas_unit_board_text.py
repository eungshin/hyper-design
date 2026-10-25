"""판 글 = 고를 수 있는 글 레이어(t51-9) — 고치기·지우기 계획과 판에 보일 묶음.

Python(board_text.py, 순수): plan(screens, decisions, {op, to, value}) → 새 screens.json · decisions.json(바뀐 것만).
  칸 키 = 판에 보인 차례(정한 것·시장 관례는 build_canvas 의 거르기와 같은 차례 → decisions.json 번호). 잘못된 요청 = BoardError, 아무것도 안 바꿈.
  screen_edits.apply_edits 의 'board' 편집 = 쓰기 한 번(.hd-history 원본) → restore 로 바이트 그대로.
JS(modules/board-text.js, 순수): HD.boardText.blocks(D) · apply(D, ops) · pending(notes) · check(key, text) · keepEm · captionDelete · layers."""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import board_text as BT  # noqa: E402
import screen_edits  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit

SJ = {"groups": ["홈"], "story": {"headline": "한 줄 <em>강조</em> 제목", "summary": "요약", "ideas": [{"title": "가", "desc": "가설명"}, {"title": "나", "desc": "나설명"}]},
      "people": [{"name": "사람1", "why": "이유", "win": "얻음"}], "screens": [{"id": "a", "title": "A", "group": "홈"}]}
DEC = {"core": "핵심", "items": [
    {"id": "S1", "name": "유지", "verdict": "keep", "source": "PRD"},
    {"id": "S2", "name": "뺀 것", "verdict": "cut", "source": "PRD", "why": "왜"},
    {"id": "M1", "name": "따른 관례", "verdict": "keep", "source": "시장"},
    {"id": "S3", "name": "가볍게", "verdict": "lighten", "source": "PM", "how": "어떻게", "why": "왜2"},
    {"id": "M2", "name": "벗어난 관례", "verdict": "cut", "source": "시장"}]}


def plan(edit, sj=SJ, dec=DEC):
    return BT.plan(sj, dec, edit)


def test_set_story_and_people_fields_change_only_that_field():
    r = plan({"op": "set", "to": "story.summary", "value": "  새\n  요약  "})
    assert r["decisions"] is None and r["screens"]["story"]["summary"] == "새\n요약"
    assert SJ["story"]["summary"] == "요약", "입력은 그대로(복사본)"
    r = plan({"op": "set", "to": "story.ideas.1.desc", "value": "새 설명"})
    assert r["screens"]["story"]["ideas"][1] == {"title": "나", "desc": "새 설명"}
    r = plan({"op": "set", "to": "people.0.why", "value": "새 이유"})
    assert r["screens"]["people"][0]["why"] == "새 이유"
    r = plan({"op": "set", "to": "story.headline", "value": "두\n줄  제목"})
    assert r["screens"]["story"]["headline"] == "두 줄 제목", "한 줄 칸"


def test_decision_keys_map_board_order_to_file_index():
    assert BT.shown_items(DEC) == [1, 3] and BT.shown_market(DEC) == [4, 2], "벗어난 것 먼저"
    r = plan({"op": "set", "to": "decisions.items.1.how", "value": "더 가볍게"})
    assert r["screens"] is None and r["decisions"]["items"][3]["how"] == "더 가볍게"
    r = plan({"op": "set", "to": "decisions.market.0.name", "value": "새 이름"})
    assert r["decisions"]["items"][4]["name"] == "새 이름"
    r = plan({"op": "set", "to": "decisions.core", "value": "새 핵심"})
    assert r["decisions"]["core"] == "새 핵심"


@pytest.mark.parametrize("edit,reason", [
    ({"op": "set", "to": "story.ideas.5.title", "value": "x"}, "missing"),
    ({"op": "set", "to": "decisions.items.2.name", "value": "x"}, "missing"),
    ({"op": "set", "to": "people.0.name", "value": "   "}, "invalid"),
    ({"op": "set", "to": "screens.0.title", "value": "x"}, "invalid"),
    ({"op": "set", "to": "story.summary", "value": 3}, "invalid"),
    ({"op": "set", "to": "story.summary", "value": "x" * 2001}, "invalid"),
    ({"op": "delete", "to": "hint"}, "invalid"),
    ({"op": "move", "to": "story"}, "invalid"),
])
def test_bad_edits_are_refused_with_reason(edit, reason):
    with pytest.raises(BT.BoardError) as e:
        plan(edit)
    assert e.value.reason == reason and str(e.value)


def test_delete_blocks_remove_their_source_fields_only():
    r = plan({"op": "delete", "to": "ideas"})
    assert "ideas" not in r["screens"]["story"] and r["screens"]["story"]["headline"]
    r = plan({"op": "delete", "to": "story"})
    assert r["screens"]["story"] == {"ideas": SJ["story"]["ideas"]}
    r = plan({"op": "delete", "to": "people"})
    assert "people" not in r["screens"]
    r = plan({"op": "delete", "to": "decisions"})
    assert "core" not in r["decisions"] and [i["id"] for i in r["decisions"]["items"]] == ["S1", "M1", "M2"]
    r = plan({"op": "delete", "to": "market"})
    assert [i["id"] for i in r["decisions"]["items"]] == ["S1", "S2", "S3"] and r["decisions"]["core"] == "핵심"
    with pytest.raises(BT.BoardError):
        plan({"op": "delete", "to": "market"}, dec={"items": []})
    with pytest.raises(BT.BoardError):
        plan({"op": "delete", "to": "decisions"}, dec=None)
    sj2 = dict(SJ, story={"ideas": []})
    with pytest.raises(BT.BoardError):
        plan({"op": "delete", "to": "story"}, sj=sj2)


OK = lambda out: types.SimpleNamespace(returncode=0, stderr="")  # noqa: E731


def test_apply_edits_board_writes_once_and_restore_brings_bytes_back(tmp_path):
    o = tmp_path / "out"; o.mkdir()
    (o / "screens.json").write_text(json.dumps(SJ, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (o / "decisions.json").write_text(json.dumps(DEC, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before = {f: (o / f).read_bytes() for f in ("screens.json", "decisions.json")}
    r = screen_edits.apply_edits(o, [{"id": "e1", "screen": "@board", "edit": "board", "op": "delete", "to": "ideas"},
                                {"id": "e2", "screen": "@board", "edit": "board", "op": "set", "to": "decisions.core", "value": "새"},
                                {"id": "e3", "screen": "@board", "edit": "board", "op": "delete", "to": "nope"}], stamp="b1", build=OK)
    assert r["applied"] == ["e1", "e2"] and [f["id"] for f in r["failed"]] == ["e3"] and r["stamp"] == "b1" and r["changed"] == []
    assert "ideas" not in json.loads((o / "screens.json").read_text(encoding="utf-8"))["story"]
    assert json.loads((o / "decisions.json").read_text(encoding="utf-8"))["core"] == "새"
    assert "error" not in write_record.restore(o, "b1", build=OK)
    assert {f: (o / f).read_bytes() for f in before} == before, "되돌리기 한 번 = 두 파일 모두 바이트 그대로"
    r = screen_edits.apply_edits(o, [{"id": "e4", "screen": "@board", "edit": "board", "op": "delete", "to": "nope"}], build=OK)
    assert r["applied"] == [] and r["stamp"] is None


JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/board-text.js', 'utf8'), {filename: 'board-text.js'});
const B = globalThis.HD.boardText, out = {};
const D = JSON.parse(process.argv[3]);
out.keys = B.blocks(D, {dscard: true}).map(b => [b.key, b.layer, b.del, b.fields.map(f => f.key)]);
out.none = B.blocks({}, {}).map(b => b.key);
const ops = [{op: 'delete', to: 'ideas'}, {op: 'set', to: 'decisions.items.0.why', value: '새 왜'}, {op: 'set', to: 'people.3.why', value: 'x'}];
const D2 = B.apply(D, ops);
out.applied = [!!D2.story.ideas && D2.story.ideas.length, D2.decisions.items[0].why, D.story.ideas.length, D2.people.length];
out.del = ['story', 'people', 'decisions', 'market'].map(k => { const x = B.apply(D, [{op: 'delete', to: k}]); return B.blocks(x, {}).map(b => b.key); });
out.pending = B.pending([{edit: 'board', op: 'delete', to: 'people', id: 'n1'}, {edit: 'title', screen: 'a'}, {edit: 'board', op: 'set', to: 'story.summary', value: 'v', id: 'n2'}]);
out.check = [B.check('story.summary', ' a \n  b '), B.check('people.0.name', '  '), B.check('foo', 'x'), B.check('story.headline', 'a\nb')];
out.em = [B.keepEm('한 줄 <em>강조</em> 제목', '두 줄 강조 제목'), B.keepEm('한 줄 <em>강조</em> 제목', '아예 다름'), B.keepEm('그냥', '바뀜'), B.plain('a <em>b</em>')];
out.cap = [B.captionDelete('title', {title: 'T'}), B.captionDelete('purpose', {purpose: 'P'}), B.captionDelete('purpose', {purpose: ''}),
           B.captionDelete('policies', {policies: ['x', 'y']}), B.captionDelete('policies', {policies: []}), B.captionDelete('zz', {})];
out.layers = B.layers(B.blocks(D, {}), {'@intro': 1}).map(l => l.id);
out.say = [B.say({op: 'delete', to: 'ideas'}), B.say({op: 'set', to: 'decisions.items.0.why', value: 'v'})];
out.blockOf = [B.blockOf('story.ideas.0.title'), B.blockOf('decisions.market.0.name'), B.blockOf('x')];
console.log(JSON.stringify(out));
"""

DATA = {"stage": "go", "pending": 2,
        "story": {"headline": "제목 <em>강조</em>", "summary": "요약", "ideas": [{"title": "가", "desc": "d"}, {"title": "나", "desc": "d2"}]},
        "people": [{"name": "p", "why": "w", "win": "x", "core": True}],
        "decisions": {"core": "핵심", "items": [{"verdict": "lighten", "label": "가볍게", "name": "n", "how": "h", "why": "y"}],
                      "market": [{"verdict": "cut", "label": "벗어남", "name": "m", "how": "", "why": "y"}]},
        "palettes": {"options": [{"name": "A"}]}, "credits": [{"file": "a.jpg"}]}


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-boardtext-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD), json.dumps(DATA, ensure_ascii=False)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_js_blocks_are_separate_layers_with_their_fields(js):
    keys = {k[0]: k for k in js["keys"]}
    assert [k[0] for k in js["keys"]] == ["hint", "story", "ideas", "people", "decisions", "market", "palettes", "credits", "dscard"]
    assert keys["story"][1] == "@intro-story" and keys["story"][2] == "file" and keys["story"][3] == ["story.headline", "story.summary"]
    assert keys["ideas"][3] == ["story.ideas.0.title", "story.ideas.0.desc", "story.ideas.1.title", "story.ideas.1.desc"]
    assert keys["decisions"][3] == ["decisions.core", "decisions.items.0.name", "decisions.items.0.how", "decisions.items.0.why"]
    assert keys["market"][3] == ["decisions.market.0.name"]
    assert [keys[k][2] for k in ("hint", "palettes", "credits", "dscard")] == ["hide"] * 4, "만든 글·출처·DS 카드 = 숨기기"
    assert keys["dscard"][1] == "@dscard"
    assert js["none"] == ["hint"], "데이터가 없으면 안내 줄만"


def test_js_apply_and_pending_preview_follow_the_file_rules(js):
    assert js["applied"] == [False, "새 왜", 2, 1], "지운 묶음 · 고친 칸 · 원래 데이터 그대로 · 없는 자리는 건너뜀"
    assert js["del"] == [["hint", "ideas", "people", "decisions", "market", "palettes", "credits"],
                         ["hint", "story", "ideas", "decisions", "market", "palettes", "credits"],
                         ["hint", "story", "ideas", "people", "market", "palettes", "credits"],
                         ["hint", "story", "ideas", "people", "decisions", "palettes", "credits"]]
    assert js["pending"] == [{"id": "n1", "op": "delete", "to": "people", "value": None}, {"id": "n2", "op": "set", "to": "story.summary", "value": "v"}]


def test_js_check_em_caption_layers(js):
    ok, empty, bad, line = js["check"]
    assert ok == {"value": "a\nb"} and "error" in empty and "error" in bad and line == {"value": "a b"}
    assert js["em"] == ["두 줄 <em>강조</em> 제목", "아예 다름", "바뀜", "a b"]
    t, p, p0, pol, pol0, zz = js["cap"]
    assert "제목은 비울 수 없어요" in t["error"]
    assert p == {"changes": [{"field": "purpose", "value": "", "old": "P"}]} and "error" in p0
    assert pol == {"changes": [{"field": "policies", "value": [], "old": ["x", "y"]}]} and "error" in pol0 and "error" in zz
    assert js["layers"] == ["@intro-hint", "@intro-story", "@intro-ideas", "@intro-people", "@intro-decisions", "@intro-market",
                            "@foot-palettes", "@foot-credits", "@intro"], "숨겨 둔 옛 '@intro' 는 다시 보이게 할 수 있게 남긴다"
    d, s = js["say"]
    assert d["path"] == "screens.json > story > ideas" and "지우기" in d["note"]
    assert s["path"] == "decisions.json > items(판 차례 1) > why" and '"v"' in s["note"]
    assert js["blockOf"] == ["ideas", "market", None]
