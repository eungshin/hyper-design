"""글자 고치기가 옛 글을 남기던 버그(task 30, K1) · 글 비우기 · 요소 지우기(remove).

도우미(I/O 없음, edit_html·apply_edits 직접): text = 요소 안 내용 전부(글 + 인라인 자식)를 새 글로(\\n → <br>), 안에 블록 자식이 있으면 거절(한국어 이유),
빈 값 = 글 비우기. remove = 시작 태그부터 닫는 태그 끝까지 지우기(void·self-closing 포함), html·body·화면 뿌리는 거절. 한 번에 여러 편집 = 뒤에서부터.
Model(node): edits.js say.remove · directOf/instantOf(remove) · preview(반영 대기 미리보기 항목) · 요청문 '소스:' 줄 · note 가 src 를 간직.
"""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

BLOCK_REASON = "안에 다른 요소가 있어 글자만 바꿀 수 없어요"


def edit(src, *ops):
    return helper.edit_html(src, list(ops))


# ---------------------------------------------------------------- text: 요소 안 내용 전부
def test_text_replaces_every_text_node_not_only_the_first():   # K1: <br> 뒤 줄이 남던 것
    assert edit("<main><p>old<br>line2</p></main>", ("p", "text", "new")) == "<main><p>new</p></main>"


def test_text_replaces_inline_markup_inside_the_element():
    assert edit("<main><p>a <b>b</b> c</p></main>", ("p", "text", "x")) == "<main><p>x</p></main>"


def test_second_edit_of_a_multi_line_value_leaves_nothing_behind():
    s = edit("<main><h1>제목</h1></main>", ("h1", "text", "줄1\n줄2"))
    assert s == "<main><h1>줄1<br>줄2</h1></main>"
    assert edit(s, ("h1", "text", "끝")) == "<main><h1>끝</h1></main>", "두 번째 고치기에 줄2 가 남으면 안 된다"


def test_text_keeps_surrounding_whitespace_and_escapes():
    assert edit("<main><h1>\n  하는 일\n</h1></main>", ("h1", "text", "<새>")) == "<main><h1>\n  &lt;새&gt;\n</h1></main>"


def test_text_refuses_when_a_block_child_is_inside():
    for src in ('<main><div class="c">글 <p>안</p></div></main>', '<main><div class="c">가기 <a href="x.html">링크</a></div></main>',
                '<main><div class="c"><svg></svg>글 <p>블록</p></div></main>', '<main><div class="c"><svg></svg><span><svg></svg>안 글</span></div></main>'):
        # 아이콘 + 글이 인라인으로 갈린 것(<svg/>글 <b>굵게</b>)은 이제 고친다 — test_canvas_unit_icon_text.py
        with pytest.raises(ValueError) as e:
            edit(src, ("div.c", "text", "x"))
        assert BLOCK_REASON in str(e.value), src


# ---------------------------------------------------------------- text: 아이콘 + 글(R15) — 글 조각만 바꾸고 아이콘(글 없는 자식)은 그대로
def test_text_next_to_an_icon_replaces_only_the_text():
    svg = '<svg viewBox="0 0 24 24"><path d="M19 12H5"/></svg>'
    assert edit('<main><a class="b" href="x.html">%s 이전</a></main>' % svg, ("a.b", "text", "뒤로")) == '<main><a class="b" href="x.html">%s 뒤로</a></main>' % svg
    assert edit('<main><div class="c">글 <img src="a.png"></div></main>', ("div.c", "text", "새")) == '<main><div class="c">새 <img src="a.png"></div></main>'
    assert edit('<main><div class="c"><span class="icon"></span>저장</div></main>', ("div.c", "text", "<x>")) == '<main><div class="c"><span class="icon"></span>&lt;x&gt;</div></main>'
    assert edit('<main><button><i class="fa"></i>\n  뜻 보기\n</button></main>', ("button", "text", "줄1\n줄2")) == '<main><button><i class="fa"></i>\n  줄1<br>줄2\n</button></main>'


def test_text_between_icons_goes_to_the_first_text_and_drops_the_rest():
    assert edit('<main><p><svg></svg>앞 &amp; 말<svg></svg>뒤</p></main>', ("p", "text", "하나")) == '<main><p><svg></svg>하나<svg></svg></p></main>'


def test_icon_text_multi_line_edited_twice_leaves_only_the_latest():   # br 은 글의 줄바꿈 — 두 번째 고치기에 남는 줄·br 없음
    s = edit('<main><button><svg></svg> 뜻 보기</button></main>', ("button", "text", "줄1\n줄2"))
    assert s == '<main><button><svg></svg> 줄1<br>줄2</button></main>'
    assert edit(s, ("button", "text", "끝")) == '<main><button><svg></svg> 끝</button></main>'


def test_icon_text_cleared_keeps_the_icon():
    assert edit('<main><button><svg></svg> 뜻 보기</button></main>', ("button", "text", "")) == '<main><button><svg></svg> </button></main>'


def test_icon_only_element_without_text_still_refuses():
    with pytest.raises(ValueError) as e:
        edit('<main><button><svg></svg></button></main>', ("button", "text", "x"))
    assert BLOCK_REASON in str(e.value)


def test_empty_value_clears_the_text_and_keeps_the_element():
    assert edit("<main><p class='k'>old<br>x</p><p>둘</p></main>", ("p:nth-of-type(1)", "text", "")) == "<main><p class='k'></p><p>둘</p></main>"


# ---------------------------------------------------------------- remove: 요소 통째로
def test_remove_drops_the_whole_element_source_span():
    assert edit("<main><ul><li>a</li><li>b <b>c</b></li></ul></main>", ("li:nth-of-type(2)", "remove", None)) == "<main><ul><li>a</li></ul></main>"


def test_remove_void_and_self_closing_elements():
    assert edit('<main><p>x</p><img src="a.png"><hr/></main>', ("img", "remove", None)) == "<main><p>x</p><hr/></main>"
    assert edit('<main><p>x</p><img src="a.png"><hr/></main>', ("hr", "remove", None)) == '<main><p>x</p><img src="a.png"></main>'


def test_remove_refuses_html_body_and_the_screen_root():
    doc = "<html><head><title>t</title></head><body><main><p>x</p></main></body></html>"
    for path in ("html", "body", "body > main"):
        with pytest.raises(ValueError) as e:
            edit(doc, (path, "remove", None))
        assert "지울 수 없어요" in str(e.value), path
    assert edit(doc, ("p", "remove", None)) == "<html><head><title>t</title></head><body><main></main></body></html>"


def test_text_edit_and_sibling_remove_in_one_batch():
    src = "<main><h1>제목<br>둘째</h1><p>설명</p><button>시작</button></main>"
    assert edit(src, ("h1", "text", "새 제목"), ("p", "remove", None)) == "<main><h1>새 제목</h1><button>시작</button></main>"
    assert edit(src, ("p", "remove", None), ("h1", "text", "새 제목")) == "<main><h1>새 제목</h1><button>시작</button></main>", "차례와 무관"


def test_two_text_edits_of_one_element_last_wins_and_nested_overlap_is_refused():
    assert edit("<main><p>a</p></main>", ("p", "text", "b"), ("p", "text", "c")) == "<main><p>c</p></main>"
    with pytest.raises(ValueError):
        edit("<main><p>a <b>b</b></p></main>", ("p", "text", "x"), ("b", "remove", None))


# ---------------------------------------------------------------- apply_edits: 화면 파일에
@pytest.fixture()
def out(tmp_path, monkeypatch):
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"screens": [{"id": "job", "file": "screens/job.html", "title": "일"}]}), encoding="utf-8")
    (o / "screens" / "job.html").write_text("<html><body><main><h1>제목<br>둘째</h1><p>설명</p><p>남김</p></main></body></html>", encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return o


def test_apply_text_and_remove_in_one_write(out):
    res = helper.apply_edits(out, [{"id": "t", "screen": "job", "edit": "text", "path": "h1", "value": "새"},
                                   {"id": "r", "screen": "job", "edit": "remove", "path": "p:nth-of-type(1)"}], stamp="s1")
    assert sorted(res["applied"]) == ["r", "t"] and not res["failed"], res
    assert (out / "screens" / "job.html").read_text(encoding="utf-8") == "<html><body><main><h1>새</h1><p>남김</p></main></body></html>"


def test_apply_refusal_carries_the_korean_reason_and_others_still_apply(out):
    res = helper.apply_edits(out, [{"id": "root", "screen": "job", "edit": "remove", "path": "body > main"},
                                   {"id": "ok", "screen": "job", "edit": "text", "path": "p:nth-of-type(2)", "value": ""}], stamp="s2")
    assert res["applied"] == ["ok"] and res["failed"][0]["id"] == "root" and "지울 수 없어요" in res["failed"][0]["reason"], res
    assert "<p></p>" in (out / "screens" / "job.html").read_text(encoding="utf-8")


def test_apply_overlapping_edits_keep_the_first_and_fail_the_later(out):
    res = helper.apply_edits(out, [{"id": "a", "screen": "job", "edit": "text", "path": "h1", "value": "x"},
                                   {"id": "b", "screen": "job", "edit": "remove", "path": "h1 > br"}], stamp="s3")
    assert res["applied"] == ["a"] and [f["id"] for f in res["failed"]] == ["b"], res


# ---------------------------------------------------------------- edits.js (node)
JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/edits.js', 'utf8'), {filename: 'edits.js'});
const E = globalThis.HD.edits, out = {};
out.say = E.say.remove();
out.sayScreen = E.say.removeScreen('"홈"(home)');
out.sayEmpty = E.say.text(''); out.sayText = E.say.text('새');
const h = {path: 'p', text: '설명', rect: null, src: {file: 'src/A.svelte', line: 12, column: 3}};
const rm = E.note('job', h, E.say.remove()); rm.edit = 'remove';
const tx = E.note('job', {path: 'h1', text: '제목', rect: null}, E.say.text('')); tx.edit = 'text'; tx.value = '';
out.keepsSrc = rm.targets[0].src;
out.direct = [E.directOf(rm), E.instantOf(rm), E.instantOf(tx)];
out.preview = E.preview([tx, rm, Object.assign({}, rm, {screen: 'other'})], 'job');
out.req = E.request([rm, tx], '/o');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-textrm-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_say_remove_element_and_screen(js):
    assert js["say"].startswith("요소 지우기"), js["say"]
    assert js["sayEmpty"].startswith("글자 비우기") and js["sayText"] == '글자를 "새"(으)로 바꾸기'
    assert js["sayScreen"] == '이 화면 "홈"(home)을 지우기 — 화면 파일과 screens.json 항목, 이 화면으로 오는 연결도 정리'


def test_remove_and_text_are_mechanical_instant_edits(js):   # task 49a: 글자도 도우미가 있으면 바로 파일에(예전 = 보내기까지 반영 대기)
    assert js["direct"] == [True, True, True]


def test_preview_items_carry_text_and_removes_of_that_screen(js):
    assert js["preview"] == [{"path": "h1", "text": ""}, {"path": "p", "remove": True}]


def test_request_has_a_source_line_after_the_request_line(js):
    lines = js["req"].split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("   요청: 요소 지우기"))
    assert lines[i + 1] == "   소스: src/A.svelte:12", lines
    assert js["keepsSrc"] == {"file": "src/A.svelte", "line": 12, "column": 3}
    assert sum(1 for ln in lines if ln.startswith("   소스:")) == 1, "src 없는 항목에는 소스 줄이 없다"
