/* Model — 새 터미널 에이전트 열기(47-5b) 규칙: 묻는 글(무엇이 어디서 뜨나) · 일하는 폴더 · POST /api/agents/spawn 답 풀이. DOM·저장소를 쓰지 않는다.
   KINDS = ['claude', 'codex'] · folder(repo, out) → 서버와 같은 규칙(저장소, 없으면 out)
   ask(kind, folder, project) → {title, lines:[…], ok} — 확인 창 글(실제 AI 에이전트를 띄운다는 것 · Paseo · 폴더 · 그 뒤 일)
   answer(res{status, body}) → {ok:true, msg} | {ok:false, off:true, title, lines}(403 reason disabled = 꺼져 있음 — 켜는 법 HD_ALLOW_SPAWN=1) | {ok:false, msg}(그 밖 — 서버 한 줄)
   HD.spawn = {KINDS, NAME, folder, ask, answer} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KINDS = ['claude', 'codex'];
var NAME = {claude: 'Claude', codex: 'Codex'};

function folder(repo, out) {
  if (typeof repo === 'string' && repo) return repo;
  return typeof out === 'string' ? out : '';
}

function ask(kind, dir, project) {
  var k = NAME[kind] ? kind : 'claude';
  return {
    title: '새 터미널 에이전트 열기',
    lines: [
      'Paseo 로 새 ' + NAME[k] + ' 에이전트를 하나 띄워요 — 실제 AI 에이전트예요(창은 열리지 않아요).',
      '일하는 폴더: ' + (dir || '(알 수 없음 — 이 프로젝트 폴더)'),
      '띄운 에이전트는 이 캔버스' + (project ? ' "' + project + '"' : '') + '에 접속해 보낸 요청을 받아요. 접속하면 받는 곳 목록에 보여요.'
    ],
    ok: '열기'
  };
}

function answer(res) {
  var st = res && res.status, b = res && res.body || {};
  if (st === 200 && b.spawned) return {ok: true, msg: '새 에이전트를 열었어요' + (typeof b.agent === 'string' && b.agent ? ' (' + b.agent + ')' : '') + ' — 접속하면 받는 곳 목록에 보여요'};
  if (st === 403 && b.reason === 'disabled') {
    return {ok: false, off: true, title: '새 터미널 열기가 꺼져 있어요',
            lines: ['캔버스에서 실제 AI 에이전트를 띄우는 일이라 기본으로 꺼 두었어요.',
                    '켜려면 도우미(hd open · hd home)를 환경 변수 HD_ALLOW_SPAWN=1 로 다시 띄우세요.',
                    '지금은 터미널에서 에이전트를 직접 열고 hd attach 로 이 캔버스에 접속시키면 돼요.']};
  }
  return {ok: false, msg: '새 터미널을 열지 못했어요' + (typeof b.error === 'string' && b.error ? ' — ' + b.error : st ? ' — 도우미 답 ' + st : '')};
}

HD.spawn = {KINDS: KINDS, NAME: NAME, folder: folder, ask: ask, answer: answer};
})();
