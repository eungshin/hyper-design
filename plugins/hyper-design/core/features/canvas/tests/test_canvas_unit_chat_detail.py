"""대화 패널 — 메모에 있는 답 설명(detail)을 답 줄 아래에(unit, 브라우저 없음). 브라우저 = test_canvas_r24_chat.py 의 detail 테스트.

옛 기록(.hd-chat.jsonl, 42f8c85 전 · 또는 옛 도우미가 쓴 것)의 reply 줄은 요약 칸만 있고 detail 이 없다. 메모(.hd-canvas.json)의 답에는 detail 이 있다.
패널 Model(HD.chatLog)은 reply 기록이 이름 대는 메모(note)에서 같은 답(종류 + 요약 칸 글, 없으면 마지막 AI 답)의 detail 을 찾아 답 줄에 붙인다.
기록이 이미 detail 을 가진 경우 두 번 보이지 않는다. 길어도 전체(접지 않음 — login#7, test_canvas_unit_chat_full.py).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'chat-log.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const L = globalThis.HD.chatLog, out = {};
const D = '자세한 설명 첫 줄\n```\ncode\n```\n끝 줄';
const memo = {id: 'n1', replies: [
  {kind: '반영됨', what: '예전 반영', detail: '옛 설명', at: 1},
  {kind: '질문', question: '요약용 추가 토큰은 없습니다(상세 참고).', choices: ['a', 'b'], detail: D, at: 2},
  {kind: '확인', at: 3}]};
const find = id => id === 'n1' ? memo : null;
const rec = (text, extra) => Object.assign({seq: 2, at: 2, turn: 1, kind: 'reply', note: 'n1', rkind: '질문', status: 'decide', text: text}, extra || {});
// 1) 기록 = 요약만 → 메모의 같은 답 detail
out.found = L.memoDetail(rec('요약용 추가 토큰은 없습니다(상세 참고).'), memo);
// 2) 기록이 이미 요약 + 빈 줄 + detail → 두 번 보이지 않음
out.doubled = L.memoDetail(rec('요약용 추가 토큰은 없습니다(상세 참고).\n\n' + D), memo);
// 3) 글이 안 맞으면 마지막 AI 답(확인 = 사람 답은 건너뜀)
out.fallback = L.memoDetail(rec('모르는 요약', {rkind: ''}), memo);
// 4) 종류 + 글이 맞는 예전 답
out.older = L.memoDetail(rec('예전 반영', {rkind: '반영됨'}), memo);
// 5) 메모 없음 · note 없음 · 깨진 메모
out.none = [L.memoDetail(rec('x'), null), L.memoDetail(rec('x', {note: null}), memo), L.memoDetail(rec('x'), {id: 'n1', replies: 'bad'})];
// 6) turns 가 메모 찾기(opts.note)를 받으면 답 줄에 detail
const recs = [{seq: 1, at: 1, turn: 1, kind: 'sent', via: 'event', notes: ['n1'], text: '질문'}, rec('요약용 추가 토큰은 없습니다(상세 참고).')];
out.line = L.turns(recs, 3, {note: find})[0].lines.filter(l => l.kind === 'reply')[0];
out.lineNoFind = L.turns(recs, 3)[0].lines.filter(l => l.kind === 'reply')[0];
out.lineWhole = L.turns([recs[0], rec('요약용 추가 토큰은 없습니다(상세 참고).\n\n' + D)], 3, {note: find})[0].lines.filter(l => l.kind === 'reply')[0];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chatdetail-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


D = "자세한 설명 첫 줄\n```\ncode\n```\n끝 줄"


def test_reply_record_without_detail_gets_memo_detail(out):
    assert out["found"] == D, "기록에 detail 이 없으면 메모의 같은 답 detail"
    assert out["older"] == "옛 설명", "종류 + 요약 글이 맞는 답을 고른다(마지막 답이 아니어도)"
    assert out["fallback"] == D, "글이 안 맞으면 마지막 AI 답(사람 답 확인·다시는 건너뜀)"


def test_reply_record_with_detail_is_not_doubled(out):
    assert out["doubled"] == "", "기록이 이미 detail 을 가지면 다시 붙이지 않는다"
    assert out["lineWhole"].get("detail", "") == ""


def test_missing_memo_gives_no_detail(out):
    assert out["none"] == ["", "", ""]


def test_turns_attach_memo_detail_to_reply_line(out):
    assert out["line"]["text"] == "결정 필요 · 요약용 추가 토큰은 없습니다(상세 참고).", "답 줄 글은 그대로"
    assert out["line"]["detail"] == D
    assert out["lineNoFind"].get("detail", "") == "", "메모 찾기가 없으면 detail 없음(옛 부르기 그대로)"
