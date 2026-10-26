/* View — 카드 화면에 묻기: 그 자리 요소(hd-hit-at → hd-hit, 1.5초 안에 답 없으면 null)와 고른 요소의 조상(hd-up → hd-upchain, tag 'cue…').
   메시지 모양은 contract.md(화면 ↔ 캔버스 메시지 — /hyper-design:fix 와 palette.js 가 읽음) 그대로. view-blocks 의 [상위] 는 제 tag 로 따로 묻는다.
   HD.viewFrameAsk.mount(ctx) → {hit(card, cx, cy, quiet, cb, leaf?, deep?), chain(frame, h, cb), lastFrame(card) → 그 카드의 마지막 틀(교체 중이면 새 틀)|null}
     hit cb: null = 답 없음(palette.js 없음 — quiet 가 아니면 토스트) · {none: true} = 그 자리에 요소 없음 · 아니면 hd-hit 답 · leaf = 글자 가진 그 요소 · deep = 가장 안쪽(Alt)
     chain cb: 조상 hit 목록(가까운 것부터) | null(답 없음·묻기 실패 — [hd] 경고)
   ctx = {$, $$, toast(msg), wOf(card) → 그 카드 폭, load(frame)(아직 안 실린 카드를 지금 싣기)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, hitWait = [], upWait = {}, upSeq = 0;

  function hit(card, cx, cy, quiet, cb, leaf, deep) {
    var ph = $('.phone', card), f = ph ? $('iframe', ph) : null; if (!f) { cb(null); return; }
    var r = ph.getBoundingClientRect(), s = r.width / ctx.wOf(card), w = {f: f, cb: cb};
    w.t = setTimeout(function () { var i = hitWait.indexOf(w); if (i < 0) return; hitWait.splice(i, 1); if (!quiet) ctx.toast('이 화면은 편집할 수 없어요'); cb(null); }, 1500);
    hitWait.push(w);
    var ask = function () { try { f.contentWindow.postMessage({type: 'hd-hit-at', x: (cx - r.left) / s, y: (cy - r.top) / s, leaf: !!leaf, deep: !!deep}, '*'); } catch (e) {} };   // 못 보내면 1.5초 뒤 답 없음으로
    if (f.hasAttribute('data-src')) { f.addEventListener('load', ask, {once: true}); ctx.load(f); }
    else ask();
  }
  function lastFrame(card) { var fs = card ? $$('.phone iframe', card) : []; return fs[fs.length - 1] || null; }
  function chain(f, h, cb) {
    var w = f && f.contentWindow; if (!w || !h || !h.path) { cb(null); return; }
    var tag = 'cue' + (++upSeq);
    upWait[tag] = {win: w, cb: cb, t: setTimeout(function () { if (!upWait[tag]) return; delete upWait[tag]; console.warn('[hd] 조상을 묻지 못함(답 없음) — ' + h.path); cb(null); }, 1500)};
    try { w.postMessage({type: 'hd-up', path: h.path, tag: tag}, '*'); } catch (e) { clearTimeout(upWait[tag].t); delete upWait[tag]; console.warn('[hd] 조상 묻기 실패 — ' + e); cb(null); }
  }

  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object') return;
    if (d.type === 'hd-hit') {
      for (var i = 0; i < hitWait.length; i++) {
        var w = hitWait[i]; if (w.f.contentWindow !== e.source) continue;
        hitWait.splice(i, 1); clearTimeout(w.t); w.cb(d.path ? d : {none: true}); return;
      }
    } else if (d.type === 'hd-upchain' && upWait[d.tag]) {
      var u = upWait[d.tag]; if (u.win !== e.source) return;
      clearTimeout(u.t); delete upWait[d.tag]; u.cb(Array.isArray(d.chain) ? d.chain : []);
    }
  });

  return {hit: hit, chain: chain, lastFrame: lastFrame};
}

HD.viewFrameAsk = {mount: mount};
})();
