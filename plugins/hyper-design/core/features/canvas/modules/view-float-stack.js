/* View — 떠 있는 층 목록 하나(U1, 10-31): Esc·바깥 누르기(판 문서 + 크게 보기 화면 틀 안 hd-press)를 한 곳에서 받아 맨 위 한 층만 닫는다 — 규칙은 Model HD.floatStack.
   층은 쌓임 차례(z 작은 것 먼저)로 add 한다 — 크게 보기(20) · 메모 묶음 #thread(39) · 메모 창 #pop(40) · 칩 미리보기 #mschtip(60) · 맨 위에 '메뉴'(보이는 [role=menu] — 주인 모듈이 스스로 닫는다).
   층 = {id, isOpen(), close(why), hit(target) → 'inside'|'opener'|'outside'|'ignore', keep()?, escOnly?} — 층마다 따로 바깥 누르기·Esc 리스너를 두지 않는다.
     escOnly = 꼬리말처럼 Esc 로만 닫는 층(누르기 때는 없는 것으로 친다 — 아래 층이 그 누르기를 받는다).
   Esc: window 잡는 단계에서 맨 위를 적어 두고, 셸 Esc 사슬이 esc(e) 를 부르면 그 층을 닫는다(맨 위가 남의 메뉴면 아무것도 닫지 않고 true = 이 Esc 는 그 메뉴 몫).
   화면 틀(크게 보기) 안: palette.js 가 Esc 를 {type:'hd-esc'} 로 넘기면 셸 문서에 keydown Escape 로 다시 낸다 · 왼쪽 누름 {type:'hd-press'} = 그 iframe 을 누른 것.
   상태(저장하지 않음) = 층 목록 · 마지막 누르기 때 맨 위 id(pressedTop — 크게 보기 덮개 click 이 '맨 위가 크게 보기였나'를 묻는다) · 이 Esc 때 맨 위.
   HD.viewFloatStack.mount(ctx) → {add(layer), esc(e) → 닫았거나 남의 층 몫이면 true, pressedTop() → id|null}
   ctx = {frames() → 받을 iframe 목록, warn(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var F = HD.floatStack, layers = [], pressed = null, escAt = null;
  var menus = {id: 'menus', foreign: true, close: function () {}, hit: function () { return 'ignore'; },   // 위 막대·도크·오른쪽 클릭 메뉴 — 주인이 Esc·바깥 누르기로 닫는다(그대로, 고정 테스트)
    isOpen: function () {
      return Array.prototype.some.call(document.querySelectorAll('[role="menu"]'), function (m) { return !m.closest('[hidden]') && m.getClientRects().length > 0 && getComputedStyle(m).visibility !== 'hidden'; });
    }};
  function all() { return layers.concat([menus]); }
  function snap(target) {
    return all().map(function (l) {
      var open = false, hit = 'ignore', keep = false;
      try { open = !!l.isOpen() && !(target && l.escOnly); if (open && target) { hit = l.hit(target); keep = !!(l.keep && l.keep()); } }
      catch (err) { ctx.warn('[hd] 떠 있는 층 ' + l.id + ' 을 읽지 못함 — ' + err); }
      return {id: l.id, open: open, hit: hit, keep: keep};
    });
  }
  function byId(id) { return all().filter(function (l) { return l.id === id; })[0] || null; }
  function shut(id, why) { var l = byId(id); if (!l || l.foreign) return false; l.close(why); return true; }
  function press(target) {
    var r = F.press(snap(target));
    pressed = r.top;
    if (r.close) shut(r.close, 'outside');
  }
  addEventListener('pointerdown', function (e) { press(e.target); }, true);   // 오른쪽 누르기도 = 다른 메뉴를 여는 것이라 같은 규칙
  addEventListener('keydown', function (e) { if (e.key === 'Escape') escAt = {e: e, top: F.esc(snap(null))}; }, true);
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || (d.type !== 'hd-press' && d.type !== 'hd-esc')) return;
    var f = (ctx.frames() || []).filter(function (x) { return x && x.contentWindow === e.source; })[0]; if (!f) return;
    if (d.type === 'hd-press') press(f);
    else document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));   // 셸 Esc 사슬이 그대로 받게
  });

  return {
    add: function (l) { if (l && l.id != null && typeof l.isOpen === 'function' && typeof l.close === 'function' && typeof l.hit === 'function') layers.push(l); else ctx.warn('[hd] 떠 있는 층 모양이 틀림 — 빼고 씀'); },
    esc: function (e) {
      var top = escAt && escAt.e === e ? escAt.top : F.esc(snap(null));
      if (top == null) return false;
      return byId(top) && byId(top).foreign ? true : shut(top, 'esc');
    },
    pressedTop: function () { return pressed; }
  };
}

HD.viewFloatStack = {mount: mount};
})();
