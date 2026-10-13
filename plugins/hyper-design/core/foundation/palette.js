/* 원클릭 팔레트 교체 — 화면은 <link id="tokens" href="tokens.css"> 하나만 바꾼다.
   캔버스가 postMessage({type:'hd-palette', slug})를 보내거나, 마지막 선택(localStorage)·?p= 를 따른다.
   요소 고르기(캔버스 크게 보기): {type:'hd-pick', on} 을 받으면 마우스 올린 요소에 테두리를 그리고
   {type:'hd-hover', rect} / 클릭 시 {type:'hd-picked', screen, path, text, rect} 를 부모에게 보낸다. */
(function () {
  var KEY = 'hd-palette';
  function apply(slug) {
    var l = document.getElementById('tokens'); if (!l || !slug) return;
    var base = l.getAttribute('data-base') || l.getAttribute('href'); l.setAttribute('data-base', base);
    l.setAttribute('href', base.replace(/tokens(-[^/]*)?\.css$/, 'tokens-' + slug + '.css'));
  }
  var s = new URLSearchParams(location.search).get('p');
  try { s = s || localStorage.getItem(KEY); } catch (e) {}
  if (s) apply(s);

  /* ---------- 요소 고르기 ---------- */
  var picking = false, box = null, last = null;
  function send(msg) { try { if (window.parent && window.parent !== window) window.parent.postMessage(msg, '*'); } catch (e) {} }
  function rectOf(el) { var r = el.getBoundingClientRect(); return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}; }
  function cssEsc(v) { return window.CSS && CSS.escape ? CSS.escape(v) : String(v).replace(/[^\w-]/g, '\\$&'); }
  function unique(sel, el) { try { var m = document.querySelectorAll(sel); return m.length === 1 && m[0] === el; } catch (e) { return false; } }
  function pathOf(el) {
    var segs = [], n = el;
    while (n && n.nodeType === 1 && n !== document.body && n !== document.documentElement) {
      var tag = n.tagName.toLowerCase();
      if (n.id) { segs.unshift('#' + cssEsc(n.id)); break; }
      var reg = n.getAttribute('data-region');
      if (reg != null) { segs.unshift(tag + '[data-region="' + reg.replace(/"/g, '\\"') + '"]'); break; }
      var cls = (n.getAttribute('class') || '').trim().split(/\s+/)[0];
      var i = 1, p = n.previousElementSibling;
      for (; p; p = p.previousElementSibling) if (p.tagName === n.tagName) i++;
      segs.unshift(tag + (cls ? '.' + cssEsc(cls) : '') + ':nth-of-type(' + i + ')');
      n = n.parentElement;
    }
    if (!segs.length) return 'body';
    for (var k = 1; k <= segs.length; k++) {           // 끝에서부터 가장 짧은 유일한 경로
      var sel = segs.slice(segs.length - k).join(' > ');
      if (unique(sel, el)) return sel;
    }
    var full = segs.join(' > ');
    return segs[0].charAt(0) === '#' || segs[0].indexOf('[data-region') > 0 ? full : 'body > ' + full;
  }
  function textOf(el) {
    var t = el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('alt') || '';
    return String(t).replace(/\s+/g, ' ').trim().slice(0, 60);
  }
  function screenId() {
    var f = decodeURIComponent(location.pathname.split('/').pop() || '');
    return f.replace(/\.html?$/i, '');
  }
  function showBox(el) {
    if (!box) {
      box = document.createElement('div');
      box.setAttribute('data-hd-pick', '');
      box.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;border:2px solid #2563eb;background:rgba(37,99,235,.10);border-radius:4px;display:none';
      document.documentElement.appendChild(box);
    }
    var r = rectOf(el);
    box.style.left = r.x + 'px'; box.style.top = r.y + 'px'; box.style.width = r.w + 'px'; box.style.height = r.h + 'px';
    box.style.display = 'block';
    return r;
  }
  function target(e) { var t = e.target; return t && t.nodeType === 1 && t !== box ? t : null; }
  document.addEventListener('mousemove', function (e) {
    if (!picking) return;
    var t = target(e); if (!t || t === last) return;
    last = t; send({type: 'hd-hover', rect: showBox(t)});
  }, true);
  function block(e) { if (!picking) return; e.preventDefault(); e.stopPropagation(); if (e.stopImmediatePropagation) e.stopImmediatePropagation(); }
  ['mousedown', 'mouseup', 'pointerdown', 'pointerup', 'submit', 'dblclick'].forEach(function (ev) { document.addEventListener(ev, block, true); });
  document.addEventListener('click', function (e) {
    if (!picking) return;
    block(e);
    var t = target(e); if (!t) return;
    send({type: 'hd-picked', screen: screenId(), path: pathOf(t), text: textOf(t), rect: showBox(t)});
  }, true);

  addEventListener('message', function (e) {
    var d = e.data; if (!d) return;
    if (d.type === 'hd-palette') apply(d.slug);
    else if (d.type === 'hd-pick') {
      picking = !!d.on; last = null;
      if (!picking && box) box.style.display = 'none';
      document.documentElement.style.cursor = picking ? 'crosshair' : '';
    }
  });
})();
