"""R29 — 대화창 '/' 명령(unit — modules/chat-cmd.js + chat.js 의 메모 N건 칩).
'/' 로 시작하는 빈칸 없는 글만 명령 목록, /memo = 보내기 전 메모만(보낸·완료·결정·일부·반영 대기 편집은 빠짐), 칩 '메모 N건' + 툴팁 줄(화면 이름 + 첫 글),
메모 N건 칩은 범위를 정하지 않고 접히지 않으며 build 가 새 메모를 만들지 않는다. 브라우저 = test_canvas_chat_memo.py."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'chat-cmd.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const C = globalThis.HD.chat, K = globalThis.HD.chatCmd, out = {};
const title = id => ({pay: '결제', done: '완료'})[id] || null;
out.match = ['/', '/m', '/MEM', '/memo', '/memox', '/memo ', 'x/', '', ' /', '/m o', null].map(t => K.match(t).map(c => c.name));
out.move = [K.move(-1, 1, 1), K.move(0, 3, 1), K.move(2, 3, 1), K.move(0, 3, -1), K.move(-1, 3, -1), K.move(0, 0, 1)];
const list = [
  {id: 'a', screen: 'pay', note: '버튼을 화면 가운데로 옮기고 더 크게 해 주세요 부탁해요', sent: false},
  {id: 'b', screen: 'done', note: '완료 문구', sent: true, replies: [{kind: '반영됨'}]},           // 완료
  {id: 'c', screen: 'pay', note: '보낸 것', sent: true},                                          // AI 작업 중
  {id: 'd', screen: 'zzz', note: '  ', sent: false},                                              // 보내기 전 · 글 없음 · 이름 없는 화면
  {id: 'e', screen: 'pay', note: '닫은 것', sent: false, replies: [{kind: '확인'}]},              // 사람이 닫음 = 완료
  {id: 'f', screen: 'pay', path: 'h1', edit: 'text', value: '새 글', sent: false},                // 반영 대기 편집 — 메모가 아님
  {id: 'g', screen: 'done', note: '질문 보낸 뒤 답', sent: true, replies: [{kind: '질문', question: 'q', choices: ['a']}]},   // 결정 필요
  null, {screen: 'pay', note: 'id 없음'}];
out.drafts = K.drafts(list).map(n => n.id);
out.chip = K.memoChip(K.drafts(list), title);
out.none = K.memoChip([], title);
const many = Array.from({length: 11}, (_, i) => ({id: 'm' + i, screen: 'pay', note: '메모 ' + i, sent: false}));
out.many = K.memoChip(many, title);
const sc = C.chips({ids: ['pay'], titleOf: title, els: []}).concat([out.chip]);
out.scope = [C.scope([out.chip]), C.scope(sc), C.placeholder([out.chip])];
const five = C.chips({ids: ['pay', 'done', 's3', 's4'], titleOf: title, els: []}).concat([out.chip]);
out.fold = C.fold(five, false).shown.map(c => c.key);
let k = 0; const mk = () => 'n' + (++k);
out.buildOnly = C.build([out.chip], '', {first: 'pay', titleOf: title}, mk);
k = 0; out.buildText = C.build([out.chip], '같이 반영해 줘', {first: 'pay', titleOf: title}, mk).memos.map(m => ({screen: m.screen, scope: m.scope, note: m.note}));
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chat-cmd-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_slash_opens_list_only_for_a_bare_command_word(out):
    assert out["match"] == [["memo"], ["memo"], ["memo"], ["memo"], [], [], [], [], [], [], []]


def test_arrow_keys_wrap(out):
    assert out["move"] == [0, 1, 0, 2, 2, -1]


def test_only_unsent_memos_qualify(out):
    assert out["drafts"] == ["a", "d"], "보낸·완료·결정 필요·닫은 메모·반영 대기 편집·깨진 항목은 빠진다"


def test_chip_label_and_tooltip_lines(out):
    c = out["chip"]
    assert c["key"] == "memos" and c["kind"] == "memos" and c["n"] == 2 and c["label"] == "메모 2건"
    assert c["tip"] == ["결제 — 버튼을 화면 가운데로 옮기고 더 크게 해 주…", "zzz — (글 없음)"]
    assert out["none"] is None, "0건 = 칩 없음(View 가 토스트)"
    assert len(out["many"]["tip"]) == 8 and out["many"]["tip"][-1] == "외 4건" and out["many"]["label"] == "메모 11건"


def test_memo_chip_does_not_set_scope_fold_or_new_memos(out):
    assert out["scope"] == ["all", "screen", "무엇을 바꿀까요?"], "메모 N건만 = 범위는 모든 화면(안내 글은 노트 칩처럼 고른 것이 있을 때 말)"
    assert out["fold"] == ["screen:pay", "screen:done", "memos"], "메모 N건 칩은 접히지 않는다"
    assert out["buildOnly"]["memos"] == [] and out["buildOnly"]["why"], "글 없이 메모 N건만 = 새 메모 없음(함께 보낼 메모는 View 가 싣는다)"
    assert out["buildText"] == [{"screen": "pay", "scope": "all", "note": "같이 반영해 줘"}]
