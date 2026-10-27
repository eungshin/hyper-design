"""R24 규칙(unit, 브라우저 없음) — 브라우저 = test_canvas_r24_chat.py.

R24 — 대화 패널은 AI 답을 다 보인다: 서버(transcript_parse 의 assistant 글 · chat_log 의 reply 기록)가 답을 4000·1000 자에서 자르지 않고,
  패널 Model(chat-log.js)은 답 줄의 줄바꿈을 지키며, 글을 ``` 코드 덩이 · `인라인 코드` 로 나눈다(View 가 pre 로 그린다).
  짧게 남는 것: 대화창 위 상태 한 줄(chat.js REPLY_CUT·PROGRESS_CUT) · 칩 · 도구 줄 요약(펼치면 전체).
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import chat_log as CL  # noqa: E402
import transcript_parse as TP  # noqa: E402

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'chat-log.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const L = globalThis.HD.chatLog, C = globalThis.HD.chat, out = {};
// R24: 답 줄은 줄바꿈 그대로 · 길어도 그대로
const long = '첫 줄\n\n' + '가'.repeat(5000) + '\n```js\nconst a = 1;\n```\n끝';
const ts = L.turns([{seq: 1, at: 1, turn: 1, kind: 'sent', via: 'event', text: 'x'}, {seq: 2, at: 2, turn: 1, kind: 'reply', status: 'done', text: long}], 3);
out.reply = ts[0].lines.filter(l => l.kind === 'reply')[0].text;
out.progress = L.turns([{seq: 1, at: 1, turn: 1, kind: 'progress', text: '줄\n바꿈'}], 2)[0].lines[0].text;
out.blocks = L.blocks('앞 글\n```py\nprint(1)\n\nx = 2\n```\n뒤 글 `a` 끝\n```\n안 닫힘');
out.plain = L.blocks('그냥 글');
out.spans = L.spans('a `b` c `d');
out.ev = L.entryView({id: 'a', role: 'assistant', text: '  하나\n  둘  ', at: 1}).text;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chatfull-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- R24 답 전체
def test_reply_line_keeps_whole_text_and_newlines(out):
    r = out["reply"]
    assert r.startswith("첫 줄\n\n가") and "가" * 5000 in r and r.endswith("```\n끝"), "답은 자르지도 한 줄로 펴지도 않는다"
    assert out["progress"] == "줄 바꿈", "진행 줄은 한 줄 그대로"


def test_blocks_split_fenced_code_and_inline_code(out):
    assert out["blocks"] == [{"type": "text", "text": "앞 글"}, {"type": "code", "lang": "py", "text": "print(1)\n\nx = 2"},
                             {"type": "text", "text": "뒤 글 `a` 끝"}, {"type": "code", "lang": "", "text": "안 닫힘"}]
    assert out["plain"] == [{"type": "text", "text": "그냥 글"}]
    assert out["spans"] == [{"code": False, "text": "a "}, {"code": True, "text": "b"}, {"code": False, "text": " c `d"}], "닫히지 않은 ` 는 글"
    assert out["ev"] == "하나\n  둘", "터미널 답 글은 앞뒤만 걷고 줄 안 들여쓰기는 그대로"


def test_server_keeps_long_assistant_text():
    big = "답" * 20000
    line = json.dumps({"type": "assistant", "uuid": "a1", "timestamp": "2026-10-26T00:00:00Z",
                       "message": {"role": "assistant", "content": [{"type": "text", "text": big}]}}, ensure_ascii=False).encode("utf-8") + b"\n"
    got, _ = TP.parse_claude(line)
    assert got and got[0]["role"] == "assistant" and got[0]["text"] == big, "assistant 글은 4000 자에서 자르지 않는다"
    assert len(TP.tool_summary("Bash", {"command": "x" * 500})) <= TP.TOOL_MAX, "도구 요약은 한 줄 그대로"


def test_server_reply_record_keeps_long_text():
    t = "줄 하나\n" + "글" * 8000
    rec = CL.from_event({"id": 1, "type": "agent.reply", "ts": 1, "project": "p", "note": "n1", "kind": "답변", "status": "done", "text": t})
    assert rec[1]["text"] == t, "기록의 답 글은 1000 자에서 자르지 않는다"
    assert CL.reply_text({"kind": "답변", "text": t}) == t
    d = "자세히:\n1. 버튼\n2. 여백"
    assert CL.reply_text({"kind": "반영됨", "what": "키움", "detail": d}) == "키움\n\n" + d, "긴 설명(detail)도 답 줄에"


def test_server_reply_record_keeps_max_summary_plus_max_detail():
    """R26 — hd 답의 detail 은 50000 자(hd_model.DETAIL_MAX)까지: 요약 칸(최대 280) + 빈 줄 + detail 50000 이 기록에서 잘리지 않는다."""
    head, d = "요" * 280, "설" * 49999 + "끝"
    t = CL.reply_text({"kind": "답변", "text": head, "detail": d})
    assert t == head + "\n\n" + d
    rec = CL.from_event({"id": 1, "type": "agent.reply", "ts": 1, "project": "p", "note": "n1", "kind": "답변", "status": "done", "text": t})
    assert rec[1]["text"] == t and rec[1]["text"].endswith("끝"), "기록 = 요약 + detail 전체"
