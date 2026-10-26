/* View — 보내기 길 하나: 위쪽 [보내기](#nsend)·질문 고르기·등록부 sendNotes 가 같은 send, 도우미가 없거나 꺼지면 요청문 복사, [보낸 것 완료로](#nclear).
   보낸 뒤 말 = Model HD.agents.sentSay · 요청문 = HD.edits.request. 보낸 요청문은 window.__hdLastSend, 도우미 답은 window.__hdLastHelper(테스트가 읽음).
   HD.viewSend.mount(ctx) → {send(list), busy() → 보내는 중(두 번 누르기 = 같은 요청 두 번 · S1), answer(id, choice), request(list) → 요청문}
   ctx = {$, notes(NS), save(), record(op), toast(m, undo?, ms?), history: {sent(), applied()}, sync() → VS, cover() → VB|null, cardEl(id), sizes() → 카드 크기|null, agent() → 받는 곳|null(바뀔 수 있다), out() → out 폴더|''} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, NS = ctx.notes, sending = false;

  function outDir() {
    var o = ctx.out(); if (o) return o;
    var p = decodeURIComponent(location.pathname).replace(/\/[^\/]*$/, '');
    if (/^\/[A-Za-z]:/.test(p)) p = p.slice(1);
    return p || '/';
  }
  function request(list) { return HD.edits.request(list, outDir(), ctx.sizes()); }
  function copyText(t) {                              // → Promise<복사됐나>
    function fallback() {
      var ta = document.createElement('textarea'), ok = false; ta.value = t; ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      document.body.appendChild(ta); ta.select();
      try { ok = !!document.execCommand('copy'); } catch (e) {}   // 복사 실패 = ok false(아래에서 알린다)
      ta.remove();
      return ok;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).then(function () { return true; }, fallback);
    } catch (e) {}                                     // 클립보드 API 가 막힘 = 예전 방식으로
    return Promise.resolve(fallback());
  }
  function say(t) { $('#nmsg').textContent = t; return t; }
  function copySend(list, msg, warn) {                 // 복사가 된 때만 '보냄'(되돌리기 경계도) — 안 되면 보내지 않은 그대로 · warn = 알림 앞에 붙일 말
    var t = request(list);
    window.__hdLastSend = t;
    return copyText(t).then(function (ok) {
      if (!ok) { ctx.toast(say('복사하지 못했어요 — 다시 눌러 보세요(보내지 않은 그대로예요)')); return; }
      list.forEach(function (n) { n.sent = true; });
      ctx.save(); ctx.history.sent();
      ctx.toast(say((warn ? warn + ' · ' : '') + (msg || '복사했어요 — 터미널에 붙여넣으세요')), false, warn ? 9000 : 0);
    });
  }
  function done() { sending = false; $('#nsend').disabled = !NS.list().some(HD.annotation.isOpen); }
  function send(list) {
    sending = true; $('#nsend').disabled = true;
    var warn = HD.edits.emptyLayouts(list).length ? HD.edits.say.emptyLayout : '';   // 목적·메모 없는 빈 레이아웃(R5) — 보내기는 그대로, 결과 알림 앞에 한 번
    var VS = ctx.sync();
    if (!VS.on) { copySend(list, null, warn).then(done, done); return; }
    say('보내는 중…');
    VS.send(list).then(function (r) {
      NS.remove(function (n) { return r.ok[n.id]; });
      r.left.forEach(function (n) { n.sent = true; });
      ctx.save();
      if (r.left.length) ctx.history.sent(); else ctx.history.applied();   // 보낸 자리 = 기록의 경계(그 앞은 되돌리지 않는다)
      var s = HD.agents.sentSay(r, {agent: ctx.agent(), warn: warn});   // 어디로 갔는지·AI 가 켜졌는지 말로(대기열이면 아무도 안 읽는다)
      ctx.toast(say(s.text), false, s.ms);
      window.__hdLastHelper = {apply: r.res, forward: r.fw};
      var VB = ctx.cover();
      if (VB && r.left.length) {                        // 터미널로 넘긴 화면마다 덮개(Paseo = AI 수정 중 · 대기열 = 걷기 버튼)
        var seen = {}, scs = [];
        r.left.forEach(function (n) { var c = ctx.cardEl(n.screen), b = c && $('.cover', c); if (b && !seen[n.screen]) { seen[n.screen] = 1; scs.push({id: n.screen, file: b.dataset.file}); } });
        VB.mark(scs, s.ok ? 'paseo' : 'queue');         // 받은 곳이 있으면 'AI 수정 중'(덮개 종류 paseo — 접속한 에이전트·claude 도)
      }
    }).catch(function () { return copySend(list, '파일에 바로 쓰기가 꺼져 있어 복사했어요 — 터미널에 붙여넣으세요', warn); }).then(done, done);
  }
  // 질문 고르기(view-thread): 질문 메모에 고른 답(확인 + answer) = 닫기 + 같은 자리 새 메모 '질문 "…" → 고른 것' 을 그것만 보내기
  // 되돌리기 한 단계(둘을 함께) — 보내지면 보낸 자리가 기록의 경계라 그 앞으로는 되돌리지 않는다(보내기와 같음)
  function answer(id, choice) {
    var A = HD.annotation, q = NS.find(id), ask = q && A.question(q);
    if (!ask || ask.choices.indexOf(choice) < 0) { ctx.toast('그 질문은 이미 답했거나 없어요'); return; }
    if (sending) { ctx.toast('보내는 중이에요 — 잠시 뒤 다시 골라 주세요'); return; }
    var at = new Date().toISOString(), k = q.replies.length, ts = HD.notes.targets(q);
    var n = {id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), screen: q.screen, targets: ts.slice(), path: ts[0].path, text: ts[0].text, rect: ts[0].rect,
             note: A.followUp(ask.question, choice), intent: 'change', sent: false};
    if (A.scopeOf(q) !== 'element') n.scope = q.scope;   // 질문 메모의 범위(R7)를 이어받는다
    var go = function () { q.replies = q.replies.slice(0, k).concat([A.answer(choice, at)]); if (!NS.find(n.id)) NS.add(n); ctx.save(); };
    go();
    ctx.record({label: '질문에 답하기', redo: go, undo: function () { q.replies = q.replies.slice(0, k); NS.remove(function (x) { return x.id === n.id; }); ctx.save(); }});
    send([n]);
  }

  $('#nsend').addEventListener('click', function (e) {
    if (sending || (e && e.detail > 1)) return;       // 더블클릭의 두 번째 누르기도 한 번으로
    var open = NS.list().filter(HD.annotation.isOpen), list = open.filter(function (n) { return !n.sent; });   // 완료한 메모는 보내지 않는다
    if (!list.length) list = open;                    // 다 보냈으면 다시 보내기(따로 누른 한 번)
    if (!list.length) return;
    send(list);
  });
  $('#nclear').addEventListener('click', function () {   // 보낸 메모 = 완료(답 '확인'을 덧붙여 기록은 남긴다) · 보낸 편집(반영 대기)은 예전처럼 목록에서 뺀다 — 되돌리기 한 단계
    var A = HD.annotation, at = new Date().toISOString(), before = NS.list().slice();
    var memos = before.filter(function (n) { return n.sent && !n.edit && A.isOpen(n); }), k = memos.map(function (n) { return (n.replies || []).length; });
    var edits = before.filter(function (n) { return n.sent && n.edit; });
    if (!memos.length && !edits.length) return;
    var go = function () {
      memos.forEach(function (n) { n.replies = (n.replies || []).concat([A.reply('확인', at)]); });
      NS.remove(function (n) { return edits.indexOf(n) >= 0; }); say(''); ctx.save();
    };
    go();
    ctx.record({label: '보낸 것 완료로', redo: go, undo: function () { memos.forEach(function (n, i) { n.replies = n.replies.slice(0, k[i]); }); NS.set(before); ctx.save(); }});
  });

  return {send: send, busy: function () { return sending; }, answer: answer, request: request};
}

HD.viewSend = {mount: mount};
})();
