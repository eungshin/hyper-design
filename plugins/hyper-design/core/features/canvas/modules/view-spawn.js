/* View — 새 터미널 에이전트 열기(47-5b): 의도 'hd-spawn-ask' {repo}(받는 곳 메뉴의 '새 터미널…') → 확인 창(무엇이 · 어느 폴더에서 뜨나, Claude/Codex 고르기)
   → [열기] 를 누른 뒤에만 POST /api/agents/spawn {kind}. 403 reason disabled = 같은 창이 꺼져 있다는 설명(켜는 법 HD_ALLOW_SPAWN=1)으로 바뀐다(오류 덤프 아님).
   성공 = 창 닫고 토스트, 그 밖 실패 = 창 안 한 줄 + [hd] 경고. 글·답 풀이는 HD.spawn(Model). 도우미가 없으면(ctx.api.on 거짓) 아무것도 만들지 않는다.
   상태: 열린 창 · 부르는 중(이 모듈만, 저장 안 함). Esc · 바깥 누르기 · [취소] = 닫기(부르지 않음).
   HD.feature('spawn', {needs: ['api', 'esc', 'toast']}) → {ask(repo), close()} | {} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#hdspawn{position:fixed;inset:0;z-index:41;background:rgba(28,28,28,.28);display:grid;place-items:center}' +
  '#hdspawn[hidden]{display:none}' +
  '#hdspawn .sp{width:min(440px,calc(100vw - 48px));box-sizing:border-box;padding:18px 20px 16px;background:#fff;border-radius:12px;box-shadow:0 18px 48px rgba(0,0,0,.22);font:13px/1.5 system-ui,sans-serif;color:#2b2b29}' +
  '#hdspawn h2{margin:0 0 10px;font-size:15px;font-weight:700}' +
  '#hdspawn p{margin:0 0 8px;color:#4a4a46}' +
  '#hdspawn .sp-dir{font:12px ui-monospace,Menlo,monospace;background:#F4F4F1;border-radius:6px;padding:4px 8px;word-break:break-all;color:#2b2b29}' +
  '#hdspawn .sp-kinds{display:flex;gap:6px;margin:4px 0 12px}' +
  '#hdspawn .sp-kinds label{display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 10px;border:1px solid #e3e3df;border-radius:8px;cursor:pointer}' +
  '#hdspawn .sp-kinds label:has(input:checked){border-color:#2b2b29;background:#F4F4F1}' +
  '#hdspawn .sp-err{color:var(--ui-danger,#c8463f)}' +
  '#hdspawn .sp-err:empty{display:none}' +
  '#hdspawn .sp-act{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}' +
  '#hdspawn .sp-act button{height:30px;padding:0 14px;border-radius:8px;font:600 13px system-ui,sans-serif;cursor:pointer}' +
  '#hdspawn .sp-no{border:1px solid #e3e3df;background:#fff;color:#2b2b29}' +
  '#hdspawn .sp-ok{border:0;background:var(--ui-primary,#2b2b29);color:#fff}' +
  '#hdspawn .sp-ok:disabled{opacity:.5;cursor:progress}';

function mount(ctx) {
  if (!ctx.api.on) return {};
  var S = HD.spawn, esc = ctx.esc, busy = false;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var back = document.createElement('div');
  back.id = 'hdspawn'; back.hidden = true;
  back.innerHTML = '<div class="sp" role="dialog" aria-modal="true" aria-labelledby="sp-h"><h2 id="sp-h"></h2><div class="sp-body"></div>' +
    '<p class="sp-err" role="alert"></p><div class="sp-act"><button type="button" class="sp-no">취소</button><button type="button" class="sp-ok"></button></div></div>';
  document.body.appendChild(back);
  var box = back.querySelector('.sp'), body = back.querySelector('.sp-body'), err = back.querySelector('.sp-err');
  var okB = back.querySelector('.sp-ok'), noB = back.querySelector('.sp-no'), dir = '', mode = 'ask';

  function project() { var t = document.getElementById('title'); return t ? (t.textContent || '').trim() : ''; }
  function paintAsk() {
    var kind = (back.querySelector('input[name="sp-kind"]:checked') || {}).value || 'claude', a = S.ask(kind, dir, project());
    back.querySelector('#sp-h').textContent = a.title;
    body.querySelector('.sp-what').textContent = a.lines[0];
    body.querySelector('.sp-dir').textContent = dir || '(알 수 없음)';
    body.querySelector('.sp-then').textContent = a.lines[2];
    okB.textContent = a.ok;
  }
  function ask(repo) {
    dir = S.folder(repo, typeof window.__hdOut === 'string' ? window.__hdOut : '');
    mode = 'ask'; busy = false; err.textContent = '';
    body.innerHTML = '<p class="sp-what"></p><div class="sp-kinds" role="radiogroup" aria-label="에이전트 종류">' +
      S.KINDS.map(function (k, i) { return '<label><input type="radio" name="sp-kind" value="' + esc(k) + '"' + (i ? '' : ' checked') + '>' + esc(S.NAME[k]) + '</label>'; }).join('') +
      '</div><p>일하는 폴더</p><p class="sp-dir"></p><p class="sp-then"></p>';
    okB.hidden = false; okB.disabled = false; noB.textContent = '취소';
    back.hidden = false; paintAsk(); okB.focus();
  }
  function explain(o) {                              // 꺼져 있음 — 같은 창에 설명만(오류 덤프 아님)
    mode = 'off';
    back.querySelector('#sp-h').textContent = o.title;
    body.innerHTML = o.lines.map(function (l) { return '<p>' + esc(l).replace('HD_ALLOW_SPAWN=1', '<code class="sp-dir">HD_ALLOW_SPAWN=1</code>') + '</p>'; }).join('');
    err.textContent = ''; okB.hidden = true; noB.textContent = '닫기'; noB.focus();
  }
  function close() { back.hidden = true; busy = false; }
  function go() {
    if (busy || mode !== 'ask') return;
    var kind = (back.querySelector('input[name="sp-kind"]:checked') || {}).value || 'claude';
    busy = true; okB.disabled = true; err.textContent = '';
    ctx.api.call('POST', '/api/agents/spawn', {kind: kind}).then(function (res) {
      busy = false; okB.disabled = false;
      var o = S.answer(res);
      if (o.ok) { close(); ctx.toast(o.msg, false, 6000); return; }
      if (o.off) { explain(o); return; }
      err.textContent = o.msg; console.warn('[hd] 새 터미널: ' + o.msg);
    }, function (e) {
      busy = false; okB.disabled = false;
      err.textContent = '새 터미널을 열지 못했어요 — 도우미에 닿지 않아요'; console.warn('[hd] 새 터미널: ' + (e && e.message || e));
    });
  }
  back.addEventListener('change', function (e) { if (e.target.name === 'sp-kind') paintAsk(); });
  okB.addEventListener('click', go);
  noB.addEventListener('click', close);
  back.addEventListener('pointerdown', function (e) { e.stopPropagation(); if (e.target === back) close(); });
  box.addEventListener('keydown', function (e) { e.stopPropagation(); if (e.key === 'Escape') close(); });
  document.addEventListener('hd-spawn-ask', function (e) { var d = e.detail || {}; d.done = true; ask(d.repo || null); });
  return {ask: ask, close: close};
}

HD.feature('spawn', {needs: ['api', 'esc', 'toast'], mount: mount});
})();
