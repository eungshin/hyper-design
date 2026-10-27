/* View — 주소 복사(R30, Figma '선택 링크 복사' · Ctrl+L): 카드·요소의 주소 줄(HD.address)을 클립보드에 넣고 "주소를 복사했어요" 토스트.
   들어오는 길: 카드 메뉴 '주소 복사'(셸 → cards(ids)) · 요소 메뉴 '주소 복사'(셸 → element(screen, h, inModal)) · Ctrl/Cmd+L(이 모듈이 듣는다 —
     크게 보기 = 고른 요소, 판 = 고른 요소 모두(R19 차례) → 없으면 고른 카드).
   프로젝트 이름 = 도우미가 주는 프로젝트 줄의 이름(GET /api/projects — hd open 이 받는 이름), 없으면 out 폴더 이름(HD.address.projectOf).
   상태 = 프로젝트 이름 · 복사 함수(attach 로 받음 — view-send 의 클립보드 + execCommand 예전 길). 마지막 복사한 글은 window.__hdLastAddress(테스트가 읽음).
   HD.feature('address', {needs: ['$', 'toast', 'warn', 'cardEl', 'selected', 'pickedAll', 'picked', 'api']})
     → {attach({copy(text) → Promise<bool>}), cards(ids), element(screen, h, inModal), items(list) → 주소 항목들, copy(items) → Promise<bool>}
   오류 탐지: 판에 없는 카드·path 없는 요소는 건너뛰고 [hd] 경고 한 줄 · 복사할 것이 없으면 토스트 · 클립보드가 막히면 "주소를 복사하지 못했어요" 토스트. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, A = HD.address, copyFn = null;
  var out = A.outOf(window.__hdOut, location.pathname), project = A.projectOf(out);
  if (ctx.api && ctx.api.on) {
    ctx.api.call('GET', '/api/projects').then(function (res) {
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      var cur = HD.projects.current(HD.projects.rows(res.body, window.__hdOut || null).rows);
      if (cur && cur.name) project = cur.name;
    }).catch(function (e) { ctx.warn('[hd] 주소 복사: 프로젝트 이름을 받지 못해 폴더 이름을 써요 — ' + (e && e.message || e)); });
  }

  function cover(id) { var c = ctx.cardEl(id); return c ? $('.cover', c) : null; }
  function cardItem(id) {
    var cv = cover(id);
    if (!cv || !cv.dataset.file) { ctx.warn('[hd] 주소 복사: 판에 없는 카드 ' + id); return null; }
    return {project: project, screen: id, file: A.fileOf(out, cv.dataset.file), text: cv.dataset.title || id};
  }
  function elItem(screen, h) {
    var base = cardItem(screen);
    if (!base) return null;
    if (!h || !h.path) { ctx.warn('[hd] 주소 복사: 경로 없는 요소(' + screen + ')'); return null; }
    base.path = h.path; base.text = h.text || h.full || ''; return base;
  }
  function items(list) {
    return (list || []).map(function (x) { return x.h ? elItem(x.screen, x.h) : cardItem(x.screen); }).filter(Boolean);
  }
  function copy(its) {
    if (!its.length) { ctx.toast('복사할 주소가 없어요'); return Promise.resolve(false); }
    var text = A.lines(its);
    window.__hdLastAddress = text;
    if (!copyFn) { ctx.toast('주소를 복사하지 못했어요 — 클립보드 길이 없어요'); console.error('[hd] 주소 복사: attach({copy}) 전이에요'); return Promise.resolve(false); }
    return copyFn(text).then(function (ok) {
      ctx.toast(ok ? A.say(its.length) : '주소를 복사하지 못했어요 — 다시 해 보세요');
      return !!ok;
    });
  }
  function key(x) { return HD.elPick.key(x.screen, x.h && x.h.path); }
  function cards(ids) { return copy(items((ids || []).map(function (id) { return {screen: id}; }))); }
  function element(screen, h, inModal) {           // 누른 요소가 판에서 고른 묶음 안이면 묶음 전체(고른 차례), 아니면 그 하나
    var clicked = {screen: screen, h: h};
    return copy(items(inModal ? [clicked] : A.targets(ctx.pickedAll(), clicked, key)));
  }

  function typing(e) { var t = e.target; return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || !!t.isContentEditable); }
  addEventListener('keydown', function (e) {        // Ctrl/Cmd+L = 고른 것의 주소(Figma Copy link). 브라우저 주소창 키는 캔버스에서 막는다
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey || (e.key || '').toLowerCase() !== 'l' || e.defaultPrevented || typing(e)) return;
    if (document.body.dataset.tab && document.body.dataset.tab !== 'screens') return;
    var modal = $('#modal'), inModal = !!modal && !modal.hidden;
    var list = inModal ? [] : ctx.pickedAll();
    if (!list.length) { var p = ctx.picked(); if (p && (inModal || ctx.selected().indexOf(p.screen) >= 0)) list = [p]; }
    if (!list.length && !inModal) list = ctx.selected().map(function (id) { return {screen: id}; });
    if (!list.length) return;                       // 고른 것이 없으면 브라우저 기본 그대로
    e.preventDefault();
    copy(items(list));
  });

  return {attach: function (o) { copyFn = o && typeof o.copy === 'function' ? o.copy : null; },
          cards: cards, element: element, items: items, copy: copy};
}

HD.feature('address', {needs: ['$', 'toast', 'warn', 'cardEl', 'selected', 'pickedAll', 'picked', 'api'], mount: mount});
})();
