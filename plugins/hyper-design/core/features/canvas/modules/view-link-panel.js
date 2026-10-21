/* View — 연결 패널(#legend): 고른 화면의 연결을 도착마다 한 줄 — 점 = 선 색 + 번호(선 태그와 같음), 이름 고치기, 휴지통(그 연결 하나 끊기).
   줄 목록은 view-links 가 만들어 셸이 넘긴다. 끊기·이름 저장은 셸에 맡긴다(되돌리기 기록은 셸).
   HD.viewLinkPanel.mount(ctx) → {render(rows, title)}   rows = [{from, to, texts:[버튼 글], mk:{n, color}|null}]
   ctx = {$, esc, circled(n), title(id), names:{get(from,to)}, cut(from, to), rename(from, to, text)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var GREY = '#8A8D86';
var ICON_NAME = '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>';
var ICON_CUT = '<svg viewBox="0 0 24 24"><path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/></svg>';

function mount(ctx) {
  var $ = ctx.$, esc = ctx.esc, lg = $('#legend'), list = $('#lgRows');

  function render(rows, title) {
    if (!rows.length) { lg.hidden = true; list.innerHTML = ''; return; }
    $('#lgTitle').textContent = title;
    list.innerHTML = rows.map(function (r) {
      var color = r.mk ? r.mk.color : GREY, nm = ctx.names.get(r.from, r.to);
      return '<div class="lgrow" data-from="' + esc(r.from) + '" data-to="' + esc(r.to) + '"><span class="lgdot" style="background:' + color + '">' + (r.mk ? esc(ctx.circled(r.mk.n)) : '') + '</span>' +
        '<span class="lgtx">' + (nm ? '<b class="lgnm">' + esc(nm) + '</b><br>' : '') + esc(ctx.title(r.from)) + ' › <b>[' + esc(r.texts.join(' · ')) + ']</b><br><i>→ ' + esc(ctx.title(r.to)) + '</i></span>' +
        '<button type="button" class="lgbtn lgname" title="연결 이름 고치기" aria-label="연결 이름 고치기">' + ICON_NAME + '</button>' +
        '<button type="button" class="lgbtn lgcut" title="이 연결 끊기" aria-label="이 연결 끊기">' + ICON_CUT + '</button></div>';
    }).join('');
    lg.hidden = false;
  }
  function startRename(row) {
    var from = row.dataset.from, to = row.dataset.to, tx = $('.lgtx', row), inp = document.createElement('input');
    inp.className = 'lgname-in'; inp.value = ctx.names.get(from, to); inp.placeholder = '연결 이름'; inp.setAttribute('aria-label', '연결 이름');
    tx.insertBefore(inp, tx.firstChild); inp.focus(); inp.select();
    var done = false, finish = function (save) {
      if (done) return; done = true;
      var v = inp.value.replace(/\s+/g, ' ').trim();
      inp.remove();
      if (save) ctx.rename(from, to, v);
    };
    inp.addEventListener('keydown', function (ev) {
      ev.stopPropagation();                             // Esc 가 고르기를 풀지 않게 · 캔버스 단축키도 막는다
      if (ev.key === 'Enter') { ev.preventDefault(); finish(true); } else if (ev.key === 'Escape') { ev.preventDefault(); finish(false); }
    });
    inp.addEventListener('blur', function () { finish(true); });
  }
  list.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button.lgbtn'), row = b && b.closest('.lgrow');
    if (!row) return;
    e.preventDefault(); e.stopPropagation();
    if (b.classList.contains('lgcut')) ctx.cut(row.dataset.from, row.dataset.to);
    else if (!$('input', row)) startRename(row);
  });
  ['pointerdown', 'wheel', 'dblclick'].forEach(function (ev) { lg.addEventListener(ev, function (e) { e.stopPropagation(); }); });
  return {render: render};
}

HD.viewLinkPanel = {mount: mount};
})();
