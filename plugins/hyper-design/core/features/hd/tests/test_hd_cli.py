"""hd CLI 통합 — 도우미(자식 프로세스, HD_HOME 임시) 하나를 띄우고 hd ls · notes · reply 를 실제로 돌린다. 브라우저 없음."""
import json, subprocess, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"


def hd(home, *args):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=hdfix.env(home), timeout=30)
    return r.returncode, r.stdout, r.stderr


def hdj(home, *args):
    code, out, err = hd(home, *args, "--json")
    return code, json.loads(out), err


@pytest.fixture()
def canvas(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    yield out, home, url
    hdfix.stop_helper(p)


def test_ls_lists_running_and_skips_dead_markers(canvas):
    out, home, url = canvas
    (home / "active" / "999999.json").write_text(json.dumps({"pid": 999999, "project": "dead", "out": str(out), "url": "x",
                                                             "token": "t", "port": 1}), encoding="utf-8")
    code, rows, err = hdj(home, "ls")
    assert code == 0, err
    assert [(r["project"], r["url"], r["open"]) for r in rows] == [("proj-a", url, 3)], "죽은 표지는 거른다 · 열린 메모 = 보낸 것 3"
    code, text, _ = hd(home, "ls")
    assert text.strip() == "proj-a · %s · - · 열린 메모 3" % url


def test_notes_shows_numbers_status_and_reply_changes_status(canvas):
    out, home, url = canvas
    code, d, err = hdj(home, "notes")
    assert code == 0, err
    assert [(n["screen"], n["no"], n["status"]) for n in d["notes"]] == [("home", 1, "working"), ("home", 2, "working"), ("list", 1, "working")]
    assert d["notes"][0]["target"]["quote"] == "다음" and d["helper"] is True
    code, text, _ = hd(home, "notes", "proj-a")
    assert 'home #1 · working · change · button:nth-of-type(1) "다음" · 버튼 문구를' in text

    code, res, err = hdj(home, "reply", "home#1", "--kind", "반영됨", "--what", "버튼 문구 '다음'→'계속' (home)",
                         "--screens", "home", "--captured", "yes")
    assert code == 0 and res["status"] == "done" and res["rev"] == 4, (res, err)
    code, res, err = hdj(home, "reply", "n2", "--kind", "질문", "--question", "토큰으로 바꿀까요?", "--choice", "네", "--choice", "아니요", "--by", "codex")
    assert code == 0 and res["status"] == "decide", err
    code, d, _ = hdj(home, "notes")
    assert [(n["screen"], n["no"], n["status"]) for n in d["notes"]] == [("home", 2, "decide"), ("list", 1, "working")]
    code, d, _ = hdj(home, "notes", "--sent")
    assert d["notes"][0]["replies"][0]["kind"] == "반영됨" and d["notes"][0]["replies"][0]["by"] == "agent"
    code, text, _ = hd(home, "notes", "--all")
    assert "    ↳ 질문 — 토큰으로 바꿀까요? (네 / 아니요)  (codex " in text and "list #2 · draft" in text


def test_reply_validates_locally_and_names_the_failing_fields(canvas):
    out, home, url = canvas
    code, o, err = hd(home, "reply", "home#1", "--kind", "반영됨", "--what", "x", "--screens", "ghost")
    assert code == 1 and "screens: 없는 화면 ghost" in err and "captured: 없어요" in err
    code, o, err = hd(home, "reply", "home#1", "--kind", "답변", "--text", "네")
    assert code == 1 and "답변은 질문 메모에만" in err
    code, o, err = hd(home, "reply", "home#9", "--kind", "대체됨", "--where", "x")
    assert code == 1 and "없는 메모" in err
    assert json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["rev"] == 3


def test_notes_reads_file_without_helper_but_reply_needs_it(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    code, d, err = hdj(home, "notes", "--out", str(out), "--all")
    assert code == 0 and len(d["notes"]) == 4 and d["helper"] is False, err
    code, o, err = hd(home, "notes")
    assert code == 1 and "떠 있는 캔버스가 없어요" in err
    code, o, err = hd(home, "reply", "home#1", "--out", str(out), "--kind", "대체됨", "--where", "tokens.css")
    assert code == 1 and "도우미가 없어요" in err and "helper.py" in err


def test_several_canvases_require_a_choice(tmp_path):
    home = tmp_path / "home"
    a = hdfix.make_out(tmp_path / "a")
    b_root = tmp_path / "b"; b = hdfix.make_out(b_root); b2 = b_root / "proj-b"; b.parent.rename(b2); b = b2 / "out"
    pa, _ = hdfix.start_helper(a, home)
    pb, _ = hdfix.start_helper(b, home)
    try:
        code, o, err = hd(home, "notes")
        assert code == 1 and "여럿" in err and "proj-a" in err and "proj-b" in err
        code, d, err = hdj(home, "notes", "proj-b")
        assert code == 0 and d["project"] == "proj-b", err
    finally:
        hdfix.stop_helper(pa); hdfix.stop_helper(pb)


CHAT_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2], 'utf8'), {filename: 'chat-log.js'});
const C = globalThis.HD.chatLog, body = JSON.parse(fs.readFileSync(0, 'utf8')), p = C.parse(body);
const lines = [].concat(...C.turns(p.records, Date.now()).map(t => t.lines)).filter(l => l.kind === 'reply');
process.stdout.write(JSON.stringify(lines.map(l => l.text)));
"""


def test_long_reply_through_hd_reply_reaches_the_chat_panel_whole(canvas, tmp_path):
    """R26 — 10,000자 답: hd reply --detail-file(명령줄 길이 한도를 넘는 글) → 도우미가 저장 → 대화 기록(/api/chat) → 대화 패널 Model(chat-log.js turns)의 답 줄에 전체."""
    import shutil, urllib.parse, urllib.request
    out, home, url = canvas
    detail = "".join("%04d 줄 — 긴 답의 한 줄이에요.\n" % i for i in range(500))
    detail = (detail * 2)[:9997] + "끝-표"
    assert len(detail) == 10000
    f = tmp_path / "detail.md"
    f.write_text(detail, encoding="utf-8")
    code, res, err = hdj(home, "reply", "home#2", "--kind", "답변", "--text", "네, 토큰이에요(아래 자세히)", "--detail-file", str(f))
    assert code == 0 and res["status"] == "done", (res, err)
    st = json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]
    assert next(n for n in st["notes"] if n["id"] == "n2")["replies"][-1]["detail"] == detail, "저장된 detail = 파일 글 그대로"
    tok = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["hd"][0]
    base = "http://" + urllib.parse.urlparse(url).netloc
    with urllib.request.urlopen(urllib.request.Request(base + "/api/chat", headers={"X-HD-Token": tok}), timeout=10) as r:
        chat = r.read().decode("utf-8")
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음")
    js = tmp_path / "c.js"
    js.write_text(CHAT_JS, encoding="utf-8")
    p = subprocess.run([node, str(js), str(hdfix.CANVAS / "modules" / "chat-log.js")], input=chat, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert p.returncode == 0, p.stderr
    texts = json.loads(p.stdout)
    assert texts and texts[-1] == "네, 토큰이에요(아래 자세히)\n\n" + detail, "패널 답 줄 = 요약 + 10,000자 설명 전체"
