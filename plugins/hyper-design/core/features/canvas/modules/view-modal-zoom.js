/* View — 크게 보기 확대·굴림(R57 C): 창 크기·화면 배율·굴림의 주인(전 셸 sizeModal 을 옮김). 규칙(열 때 폭 맞추기·창 크기·굴림 범위·커서 자리 확대·단계)은 modules/modal-zoom.js(Model).
   #mview(굴림 칸, overflow auto) 안에 #mbox(화면 × 배율 크기 — iframe transform scale · 메모 핀 #mpins · 고른 요소 테두리)가 있다 — 핀·테두리는 #mbox 안이라 굴림을 그냥 따라가고,
   배율이 바뀌면 ctx.changed(s) 로 셸이 다시 그린다(핀·테두리·요소 막대·글 칸). 굴림만 바뀌면 ctx.moved()(요소 막대·글 칸 자리).
   입력(크게 보기가 열렸을 때만): Ctrl/⌘+휠 = 커서 자리 확대(덮개 어디서든 · 화면 iframe 안이면 palette.js 가 hd-wheel 로 넘김) · 그냥 휠 = 굴림(브라우저 그대로) ·
     Ctrl/⌘ += / Ctrl/⌘ - = 단계 · Ctrl/⌘ 0 = 폭 맞추기(화면 안 초점이면 palette.js hd-key zoom:true). 브라우저 배율은 막는다.
   상태 = {s, mode:'fit'|'user', x, y}(저장하지 않음) — 'fit' 이면 창 크기가 바뀔 때 다시 맞춘다. 연 동안 위쪽 배율 칩은 이 배율(ctx.chip(글)), 닫으면 ctx.chip(null) = 판 배율로.
   HD.viewModalZoom.mount(ctx) → {open(), close(), layout(top?), scale() → s, label() → '76%'|null(닫힘), fit(), z100(), zin(), zout(), zoomAt(clientX, clientY, s)}
   ctx = {$, modal, mview, mbox, mframe, size() → {w, h, custom} 지금 화면 크기, open() → 열렸나, chip(text|null), changed(s), moved()}
   오류 탐지: 크기를 못 재면(0·숫자 아님) 100% 로 두고 [hd] 경고 한 줄. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var Z = HD.modalZoom, $ = ctx.$, modal = ctx.modal, mview = ctx.mview, mbox = ctx.mbox, mframe = ctx.mframe;
  var st = {s: 1, mode: 'fit', cw: 0, ch: 0, aw: 0, ah: 0, sb: 0}, warned = false, quiet = false;

  function px(v) { return parseFloat(document.body.style.getPropertyValue(v)) || 0; }
  function avail() {                                  // 덮개 = 위쪽 줄 아래 · 두 도크 사이 — 도구 막대·떠 있는 대화창 자리는 비운다(전 sizeModal 그대로, S3·10-29·10-30)
    var top = $('.hd').offsetHeight, dw = px('--dockw') + px('--dockl');
    var tb = $('#tools'), tr = tb && tb.offsetParent !== null ? tb.getBoundingClientRect() : null;
    var g = tr && tr.width ? Math.max(0, Math.round(tr.right - px('--dockl') + 8)) : 0;
    modal.style.paddingLeft = g ? g + 'px' : '';
    var hc = $('#hdchat'), hb = hc && hc.getClientRects().length && !hc.closest('.dk-body') ? hc.querySelector('.ch-box') : null, ch = hb ? hb.offsetHeight + 24 : 0;
    modal.style.paddingBottom = ch ? ch + 'px' : '';
    return {w: innerWidth - dw - 16 - g, h: innerHeight - top - 128 - 30 - ch};   // 위 주석 달기 버튼 56 + 여유 + 창 제목 막대 30(R27 F16)
  }
  var sbw = null;
  function bar() {                                    // 굴림 막대 두께 — #mview 와 같은 모양의 숨은 상자로 한 번 잰다(겹쳐 그리는 막대 = 0)
    if (sbw != null) return sbw;
    var t = document.createElement('div');
    t.id = 'mview-sb'; t.style.cssText = 'position:absolute;left:-9999px;top:0;width:100px;height:100px;overflow:scroll;scrollbar-width:thin;visibility:hidden';
    document.body.appendChild(t); sbw = Math.max(0, t.offsetWidth - t.clientWidth); t.remove();
    return sbw;
  }
  function chip() { if (ctx.open()) ctx.chip(Z.pct(st.s)); }
  function paint(x, y) {                              // 지금 st 로 크기·배율을 입히고 굴림을 x·y(잘라서)로
    var m = ctx.size(), v = Z.view(st.cw, st.ch, st.s, st.aw, st.ah, st.sb);
    mframe.style.width = m.custom ? m.w + 'px' : ''; mframe.style.height = m.custom ? m.h + 'px' : '';   // 크기를 바꾼 카드 = 그 크기로(task 46)
    mframe.style.transform = st.s !== 1 ? 'scale(' + st.s.toFixed(4) + ')' : '';
    mbox.style.width = Math.floor(st.cw * st.s + 1e-6) + 'px'; mbox.style.height = Math.floor(st.ch * st.s + 1e-6) + 'px';
    mview.style.width = v.w + 'px'; mview.style.height = v.h + 'px';
    var c = Z.scroll(st.cw, st.ch, st.s, v, x, y);
    quiet = true; mview.scrollLeft = c.x; mview.scrollTop = c.y; quiet = false;
    chip();
  }
  function measure() {
    var m = ctx.size(), a = avail();
    if (!(m.w > 0 && m.h > 0 && a.w > 0 && a.h > 0)) {
      if (!warned) { warned = true; console.warn('[hd] 크게 보기 크기를 재지 못해 100% 로 둬요'); }
      m = {w: m.w > 0 ? m.w : 390, h: m.h > 0 ? m.h : 844}; a = {w: Math.max(1, a.w), h: Math.max(1, a.h)};
    }
    st.cw = m.w; st.ch = m.h; st.aw = a.w; st.ah = a.h; st.sb = bar();
  }
  function layout(top) {                              // 창·화면 크기가 바뀜(열기·창 크기·카드 크기·다른 화면) — 'fit' 이면 다시 맞추고, 아니면 배율 그대로
    measure();
    if (st.mode === 'fit') st.s = Z.fit(st.cw, st.ch, st.aw, st.ah, st.sb);
    paint(top ? 0 : mview.scrollLeft, top ? 0 : mview.scrollTop);
    ctx.changed(st.s);
  }
  function to(s, p, mode) {                           // p = 창 가운데에서 커서까지(px)
    if (!ctx.open()) return;
    measure();
    var r = Z.at({cw: st.cw, ch: st.ch, s: st.s, x: mview.scrollLeft, y: mview.scrollTop, aw: st.aw, ah: st.ah, sb: st.sb}, s, p);
    st.s = r.s; st.mode = mode || 'user';
    paint(r.x, r.y);
    ctx.changed(st.s);
  }
  function centre() { return {x: 0, y: 0}; }
  function zoomAt(cx, cy, s) {
    var r = mview.getBoundingClientRect();
    to(s, {x: cx - (r.left + r.width / 2), y: cy - (r.top + r.height / 2)});
  }
  function fit() { measure(); to(Z.fit(st.cw, st.ch, st.aw, st.ah, st.sb), centre(), 'fit'); }
  function key(k) {                                    // Ctrl/⌘ 와 함께 — '=' '+' 확대 · '-' '_' 축소 · '0' 폭 맞추기
    if (k === '=' || k === '+') to(Z.step(st.s, 1), centre());
    else if (k === '-' || k === '_') to(Z.step(st.s, -1), centre());
    else if (k === '0') fit();
    else return false;
    return true;
  }

  modal.addEventListener('wheel', function (e) {       // Ctrl/⌘+휠 = 커서 자리 확대(덮개 어디서든) · 그냥 휠은 #mview 굴림 그대로
    if (!(e.ctrlKey || e.metaKey) || !ctx.open()) return;
    e.preventDefault();
    var k = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? innerHeight : 1;
    zoomAt(e.clientX, e.clientY, Z.wheel(st.s, e.deltaY * k));
  }, {passive: false});
  mview.addEventListener('scroll', function () { if (!quiet) ctx.moved(); });
  var watched = null;
  function watchChat() {                               // 덮개 위에 뜬 대화창 높이가 바뀌면(고른 화면 칩 줄 등) 칸이 바뀐다 — 다시 재기(배율·굴림 그대로). 대화창은 나중에 붙으니 열 때 잇는다
    var hc = $('#hdchat');
    if (!hc || hc === watched || typeof ResizeObserver !== 'function') return;
    watched = hc; new ResizeObserver(function () { if (ctx.open()) layout(); }).observe(hc);
  }
  addEventListener('keydown', function (e) {           // 캡처 — 브라우저 배율·판 키보다 먼저
    if (!ctx.open() || !(e.ctrlKey || e.metaKey) || e.altKey) return;
    if (key(e.key)) { e.preventDefault(); e.stopPropagation(); }
  }, true);
  addEventListener('message', function (e) {           // 화면 안의 Ctrl+휠·Ctrl+키(palette.js, R57)
    var d = e.data; if (!d || typeof d !== 'object' || !ctx.open() || e.source !== mframe.contentWindow) return;
    if (d.type === 'hd-wheel') {
      var f = mframe.getBoundingClientRect(), k = d.mode === 1 ? 16 : d.mode === 2 ? innerHeight : 1;
      zoomAt(f.left + (+d.x || 0) * st.s, f.top + (+d.y || 0) * st.s, Z.wheel(st.s, (+d.dy || 0) * k));
    } else if (d.type === 'hd-key' && d.zoom && (d.ctrl || d.meta)) key(String(d.key || ''));
  });

  return {
    open: function () { watchChat(); st.mode = 'fit'; layout(true); ctx.chip(Z.pct(st.s)); },   // 셸이 덮개를 보인 뒤에 부른다(굴림 칸을 잴 수 있게)
    close: function () { ctx.chip(null); },
    layout: layout,
    scale: function () { return st.s; },
    label: function () { return ctx.open() ? Z.pct(st.s) : null; },
    fit: fit,
    z100: function () { to(1, centre()); },
    zin: function () { to(Z.step(st.s, 1), centre()); },
    zout: function () { to(Z.step(st.s, -1), centre()); },
    zoomAt: zoomAt
  };
}

HD.viewModalZoom = {mount: mount};
})();
