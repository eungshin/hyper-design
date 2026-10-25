/* View — 판의 화면 줄(.flow · 제목 .glabel · 카드) 그리기와 새 데이터에 맞추기(51-1). 처음 그리기와 쓴 뒤 다시 맞추기가 같은 길을 쓴다.
   HD.viewRows.mount(ctx) → {html(rows) → 줄 전체 HTML, polHtml(pol, cls) → 카드 아래 정책 줄 HTML,
                             sync(rows, has(id)) → {removed: [이름], added: [새로 만든 카드 요소]}}
   ctx = {rowsEl, $, $$, esc, warn(msg)}
   sync: 계획은 HD.rows.plan(Model). 걷은 줄은 이름별로 떼어 두었다가 같은 이름이 돌아오면(되살리기) 그 요소를 다시 끼운다 — 셸이 떼어 둔 카드(gone)가 제 상자로
   돌아가게. 처음 보는 줄은 rows 의 화면 중 has(id) 가 아닌 것(판에도·떼어 둔 곳에도 없음)으로 카드를 만든다. 붙이기(iframe 싣기·자리·크기)는 셸. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var esc = ctx.esc, $ = ctx.$, $$ = ctx.$$, parked = {};
  function polHtml(pol, cls) {                        // 카드 아래 정책 줄: 앞 셋은 목록, 나머지는 '정책 N개 더' 접기 · cls(i) = 줄마다 덧붙일 클래스(반영 대기)
    var li = function (p, i) { var c = cls ? cls(i) : ''; return '<li' + (c ? ' class="' + c + '"' : '') + '>' + esc(p) + '</li>'; };
    var shown = pol.slice(0, 3).map(li).join('');
    return (shown ? '<ul class="pol">' + shown + '</ul>' : '') + (pol.length > 3 ? '<details class="more"><summary>정책 ' + (pol.length - 3) + '개 더</summary><ul class="pol">' +
      pol.slice(3).map(function (p, i) { return li(p, i + 3); }).join('') + '</ul></details>' : '');
  }
  function cardHtml(s) {
    return '<div class="card" data-id="' + esc(s.id) + '"><div class="phone"><iframe scrolling="no" tabindex="-1" title="' + esc(s.title) +
      '" data-src="' + esc(s.file) + '"></iframe><button class="cover" data-file="' + esc(s.file) + '" data-title="' + esc(s.title) +
      '" aria-label="' + esc(s.title) + ' 크게 보기"></button></div><button class="pres" data-file="' + esc(s.file) + '" data-title="' + esc(s.title) +
      '" title="실제로 눌러 보기(두 번 눌러도 같아요)" aria-label="' + esc(s.title) + ' 크게 보기">보기</button>' +
      '<div class="ftitle">' + (s.state ? '<span class="state">상태</span>' : '') + esc(s.title) + '</div>' +
      '<div class="cbody">' + (s.purpose ? '<div class="fdesc">' + esc(s.purpose) + '</div>' : '') + polHtml(s.policies || []) + '</div></div>';
  }
  function rowHtml(row, screens) {
    return '<div class="flow"><div class="glabel">' + esc(row.group) + '</div><div class="cards">' + screens.map(cardHtml).join('') + '</div></div>';
  }
  function html(rows) { return (rows || []).map(function (r) { return rowHtml(r, r.screens || []); }).join(''); }
  function flows() { return $$('.flow', ctx.rowsEl); }
  function nameOf(f) { var g = $('.glabel', f); return g ? g.textContent : ''; }
  function sync(rows, has) {
    rows = Array.isArray(rows) ? rows : [];
    var byName = {}, now = {}, added = [];
    rows.forEach(function (r) { if (r && typeof r.group === 'string') byName[r.group] = r; });
    flows().forEach(function (f) { now[nameOf(f)] = f; });
    var p = HD.rows.plan(flows().map(function (f) { return {group: nameOf(f), n: $$('.card', f).length}; }), Object.keys(byName));
    p.remove.forEach(function (g) { var f = now[g]; if (!f) return; parked[g] = f; f.remove(); delete now[g]; });
    p.insert.forEach(function (it) {
      var f = parked[it.group];
      if (f) delete parked[it.group];
      else {
        var tmp = document.createElement('div');
        tmp.innerHTML = rowHtml(byName[it.group], (byName[it.group].screens || []).filter(function (s) { return !has(s.id); }));
        f = tmp.firstChild;
        $$('.card', f).forEach(function (c) { added.push(c); });
      }
      var at = it.before && now[it.before];
      if (it.before && !at) ctx.warn('[hd] 줄 맞추기: 기준 줄이 없어 끝에 붙여요 — ' + it.before);
      if (at) ctx.rowsEl.insertBefore(f, at);
      else { var last = flows().pop(); ctx.rowsEl.insertBefore(f, last ? last.nextSibling : null); }   // 끝 = 마지막 줄 뒤(빈 레이아웃 카드는 rowsEl 끝에 따로 붙는다)
      now[it.group] = f;
    });
    return {removed: p.remove, added: added};
  }
  return {html: html, polHtml: polHtml, sync: sync};
}

HD.viewRows = {mount: mount};
})();
