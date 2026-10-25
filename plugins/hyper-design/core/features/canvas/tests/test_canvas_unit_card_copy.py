"""카드 바로 복제(51-6, Figma F19: Ctrl+D = 프레임 복제, 바로 오른쪽에) — 복제 계획.

Python(screen_copy.py, 순수): plan(screens.json, 원본 id, {want, title, files}) → 새 screens.json + 복사할 파일(원본 → 새 파일).
  새 id = '<원본>-copy'(쓰였으면 -copy-2 …, 화면 id·있는 파일 모두 피함) · 제목 = 원본 제목 + ' 복사'(옛 복제 메모와 같은 꼬리)
  · 자리 = screens 목록에서 원본 바로 뒤, 같은 줄 · 나가는 연결(branches·파일 안 링크) 그대로 · 들어오는 연결(다른 화면 → 원본) 그대로
  · 앱 카드(개발 서버 주소) = 거절. screen_edits.apply_edits 의 'clone' 편집 = 쓰기 한 번 → restore 한 번이면 새 파일까지 사라진다.
JS(modules/card-copy.js, 순수): 같은 id·제목 규칙 + 판에서 끼울 자리(after) — 셸이 화면에 먼저 보일 카드."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import screen_copy as SC  # noqa: E402
import screen_edits  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit

SJ = {"groups": ["홈", "설정"], "screens": [
    {"id": "home", "file": "screens/home.html", "title": "홈", "group": "홈", "purpose": "첫 화면", "policies": ["p1"],
     "branches": [{"to": "settings", "label": "설정으로"}]},
    {"id": "home--empty", "file": "screens/home--empty.html", "title": "홈 비었음", "group": "홈"},
    {"id": "home-copy", "file": "screens/home-copy.html", "title": "이미 있는 복사", "group": "홈"},
    {"id": "settings", "file": "screens/settings.html", "title": "설정", "group": "설정", "branches": [{"to": "home", "label": "홈으로"}]},
    {"id": "app", "file": "http://127.0.0.1:5173/hd-stage/app.html", "title": "앱 무대", "group": "설정"}]}


def ids(d):
    return [s["id"] for s in d["screens"]]


def test_new_id_is_unique_against_screens_and_files():
    r = SC.plan(SJ, "home")
    assert r["id"] == "home-copy-2", "home-copy 는 이미 화면 id"
    r = SC.plan(SJ, "home", files={"screens/home-copy-2.html"})
    assert r["id"] == "home-copy-3", "화면 목록에 없어도 파일이 있으면 피한다(덮어쓰지 않음)"
    assert r["file"] == "screens/home-copy-3.html" and r["src_file"] == "screens/home.html"
    r = SC.plan(SJ, "settings")
    assert r["id"] == "settings-copy" and r["file"] == "screens/settings-copy.html"


def test_title_gets_copy_suffix_and_entry_keeps_other_fields():
    r = SC.plan(SJ, "settings")
    new = next(s for s in r["data"]["screens"] if s["id"] == "settings-copy")
    assert r["title"] == "설정 복사" and new["title"] == "설정 복사"
    assert new["group"] == "설정" and new["file"] == "screens/settings-copy.html"
    r = SC.plan(SJ, "home", title="  내 이름  ")
    assert r["title"] == "내 이름", "캔버스가 보낸 이름(앞뒤 빈칸 자름)"
    assert SC.plan({"screens": [{"id": "x"}]}, "x")["title"] == "x 복사", "제목 없는 화면 = id + 꼬리"


def test_copy_sits_right_after_original_in_same_row():
    r = SC.plan(SJ, "home")
    assert ids(r["data"]) == ["home", "home-copy-2", "home--empty", "home-copy", "settings", "app"]
    assert ids(SJ) == ["home", "home--empty", "home-copy", "settings", "app"], "입력은 그대로(복사본)"
    r = SC.plan(SJ, "home--empty")
    assert r["id"] == "home--empty-copy" and ids(r["data"])[2] == "home--empty-copy", "상태 변형의 복사 = 그 변형 바로 뒤(같은 원래 화면 아래)"


def test_outgoing_links_kept_incoming_untouched():
    r = SC.plan(SJ, "home")
    by = {s["id"]: s for s in r["data"]["screens"]}
    assert by["home-copy-2"]["branches"] == [{"to": "settings", "label": "설정으로"}], "복사본의 나가는 연결 = 원본 그대로"
    assert by["settings"]["branches"] == [{"to": "home", "label": "홈으로"}], "들어오는 연결은 원본에만"
    assert by["home"] == SJ["screens"][0]
    by["home-copy-2"]["branches"][0]["to"] = "x"
    assert by["home"]["branches"][0]["to"] == "settings" and SJ["screens"][0]["branches"][0]["to"] == "settings", "복사본 항목은 원본·입력과 나눠 쓰지 않는다"


@pytest.mark.parametrize("src, kw, reason", [
    ("app", {}, "invalid"),                    # 앱 카드 = 요청으로만
    ("nope", {}, "missing"),
    ("home", {"want": "settings"}, "invalid"),  # 이미 있는 id
    ("home", {"want": "a/b"}, "invalid"),
    ("home", {"want": "home-x", "files": {"screens/home-x.html"}}, "invalid"),
    ("home", {"want": "home--x"}, "invalid"),   # 상태 변형이 아닌 원본에서 '--' = 다른 화면의 변형이 됨
    ("home", {"title": "x" * 201}, "invalid"),
])
def test_bad_requests_are_refused_with_reason(src, kw, reason):
    with pytest.raises(SC.CopyError) as e:
        SC.plan(SJ, src, **kw)
    assert e.value.reason == reason and str(e.value)


def test_requested_id_is_used_when_free():
    r = SC.plan(SJ, "home", want="home-copy-9")
    assert r["id"] == "home-copy-9" and ids(r["data"])[1] == "home-copy-9"


def OK(out):
    return subprocess.CompletedProcess([], 0, "", "")


def test_apply_edits_clone_copies_file_once_and_restore_removes_it(tmp_path):
    o = tmp_path / "out"; (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps(SJ, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for s in SJ["screens"][:4]:
        (o / s["file"]).write_text('<a data-href="settings.html">%s</a>' % s["id"], encoding="utf-8")
    before = (o / "screens.json").read_bytes()
    r = screen_edits.apply_edits(o, [{"id": "e1", "screen": "home", "edit": "clone", "to": "home-copy-2", "value": "홈 복사"},
                                {"id": "e2", "screen": "app", "edit": "clone", "to": "app-copy", "value": "x"}], stamp="c1", build=OK)
    assert r["applied"] == ["e1"] and [f["id"] for f in r["failed"]] == ["e2"] and r["stamp"] == "c1"
    assert r["changed"] == ["home-copy-2"]
    assert (o / "screens/home-copy-2.html").read_bytes() == (o / "screens/home.html").read_bytes(), "파일 그대로(나가는 링크 포함)"
    sj = json.loads((o / "screens.json").read_text(encoding="utf-8"))
    assert ids(sj)[:2] == ["home", "home-copy-2"]
    assert "error" not in write_record.restore(o, "c1", build=OK)
    assert (o / "screens.json").read_bytes() == before and not (o / "screens/home-copy-2.html").exists(), "되돌리기 한 번 = 새 파일도 사라짐"


JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/card-copy.js', 'utf8'), {filename: 'card-copy.js'});
const C = globalThis.HD.cardCopy, out = {};
const cards = [{id: 'home', title: '홈', file: 'screens/home.html'}, {id: 'home--empty', title: '홈 비었음', file: 'screens/home--empty.html'},
               {id: 'home-copy', title: 'x', file: 'screens/home-copy.html'}, {id: 'set', title: '설정', file: 'set.html'},
               {id: 'app', title: '앱', file: 'http://127.0.0.1:5173/hd-stage/app.html', app: true}];
out.one = C.plan(cards, ['home']);
out.two = C.plan(cards, ['set', 'set', 'app', 'nope']);
out.variant = C.plan(cards, ['home--empty']);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-cardcopy-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_js_plan_matches_server_rules(js):
    it = js["one"]["items"][0]
    py = SC.plan(SJ, "home")
    assert (it["id"], it["title"], it["file"]) == (py["id"], "홈 복사", py["file"])
    assert it["src"] == "home" and it["after"] == "home--empty", "판에서는 원본의 상태 변형 뒤에 끼운다(빌드 줄 차례와 같게)"
    two = js["two"]
    assert [i["id"] for i in two["items"]] == ["set-copy", "set-copy-2"], "한 번에 여럿 = 서로도 겹치지 않음"
    assert two["items"][0]["file"] == "set-copy.html", "원본과 같은 폴더"
    assert [(x["id"], x["why"]) for x in two["refused"]] == [("app", "app"), ("nope", "missing")]
    v = js["variant"]["items"][0]
    assert v["id"] == "home--empty-copy" and v["after"] == "home--empty"
