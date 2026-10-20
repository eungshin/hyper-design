/* View — 판에 늘 그리는 연결선(E7): 화면 쌍마다 선 하나, 출발 줄마다 한 색(D6b), 양방향 = 양쪽 화살촉(D6c), 반영 대기 = 점선(E14),
   기획 갈래 = 얇은 회색 실선(D8, 글자 표시 없음). 마우스를 올린 카드의 선만 진하게 + 태그, 나머지는 흐리게(D6c ②).
   쌍 목록은 HD.graph.overview(Model), 색은 HD.lineStyle.rowColor, 모양은 HD.route.routeCurve. 표시 패널의 보이기(#lnShow)·투명도(#lnOp)도 여기서.
   HD.viewLines.mount(ctx) → {render() → 가장 왼쪽 통로 x, apply()}
   ctx = {rowsEl, svg, $, $$, esc, CARD, LEFT, graph(), pending(), prefs, savePrefs(), record?({label, undo(), redo()})} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var PLAN = '#B5B8B2';

function mount(ctx) {
  var rowsEl = ctx.rowsEl, svg = ctx.svg, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, CARD = ctx.CARD, LEFT = ctx.LEFT, prefs = ctx.prefs;
  var R = HD.route, RADIUS = R.RADIUS, hov = null;

  function render() {
    var box = {}, rowOf = {}, rows = $$('.flow', rowsEl);
    $$('.card:not(.hid):not(.del)', rowsEl).forEach(function (c) {   // 숨긴·삭제 대기 화면의 선은 그리지 않는다
      box[c.dataset.id] = {x: c.offsetLeft, y: c.offsetTop, row: c.parentNode};
      rowOf[c.dataset.id] = rows.indexOf(c.closest('.flow'));
    });
    $$('.alabel', rowsEl).forEach(function (n) { n.remove(); });
    $$('path.ln, marker.lnm', svg).forEach(function (n) { n.remove(); });
    var pairs = HD.graph.overview(ctx.graph(), ctx.pending()).filter(function (p) { return box[p.a] && box[p.b]; });
    var per = {}, seen = {}, lab = {}, cols = [], paths = '', labels = '', cross = 0, minX = LEFT;
    pairs.forEach(function (p) { if (!p.ab && p.ba) { var t = p.a; p.a = p.b; p.b = t; p.ab = true; p.ba = false; } per[p.a] = (per[p.a] || 0) + 1; });
    pairs.forEach(function (p) {
      var s = box[p.a], t = box[p.b];
      var j = seen[p.a] || 0, n = per[p.a]; seen[p.a] = j + 1;
      var sx = s.x + CARD.w / 2 + (j - (n - 1) / 2) * 28, tx = t.x + CARD.w / 2, d;
      if (Math.abs(sx - tx) < 3 * RADIUS) sx = tx + (tx > s.x + CARD.w / 2 - 1 ? -1 : 1) * (CARD.w / 2 - 40);   // 같은 칸(위아래 줄): 세로선이 겹치지 않게
      if (s.row === t.row) d = R.routeCurve({x: sx, y: s.y - 6, dir: 'up'}, {x: tx, y: t.y - 10}, {lift: 54, apex: 14 * j});
      else {                                        // 다른 줄: 왼쪽 통로(LEFT − 56 − 22·k)로 우회
        var ck = cross++, lane = LEFT - 56 - 22 * (ck % 4);
        sx = s.x + 60 + 24 * (ck % 3); tx = t.x + 60 + 24 * (ck % 3);
        d = R.routeCurve({x: sx, y: s.y - 6, dir: 'up'}, {x: tx, y: t.y - 8}, {lift: 16, apex: 10 * (ck % 4), laneX: lane});
        minX = Math.min(minX, lane);
      }
      var color = p.plan ? PLAN : HD.lineStyle.rowColor(prefs, rowOf[p.a]);
      var ci = cols.indexOf(color); if (ci < 0) { ci = cols.length; cols.push(color); }
      var ft = ' data-from="' + esc(p.a) + '" data-to="' + esc(p.b) + '"';
      paths += '<path class="ln' + (p.pend ? ' pd' : '') + (p.plan ? ' plan' : '') + '"' + ft + ' data-both="' + (p.ba ? 1 : 0) + '" stroke="' + color +
        '" marker-end="url(#hd-ln-' + ci + ')"' + (p.ba ? ' marker-start="url(#hd-lns-' + ci + ')"' : '') + ' d="' + d + '"/>';
      if (p.labels.length && !p.plan) {
        var li = lab[p.a] || 0; lab[p.a] = li + 1;
        labels += '<div class="alabel"' + ft + ' style="left:' + (s.x + CARD.w + 10) + 'px;top:' + (s.y + 24 + li * 44) + 'px">' + esc(p.labels.slice(0, 2).join(' · ')) + '</div>';
      }
    });
    var defs = '';
    cols.forEach(function (c, i) {                    // 화살촉 색 = 선 색 · 양방향은 시작에도(반대로)
      var head = '<path d="M0,0 L10,5 L0,10 z" fill="' + c + '"/>';
      defs += '<marker class="lnm" id="hd-ln-' + i + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto">' + head + '</marker>' +
              '<marker class="lnm" id="hd-lns-' + i + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">' + head + '</marker>';
    });
    $('defs', svg).insertAdjacentHTML('beforeend', defs);
    svg.insertAdjacentHTML('beforeend', paths);
    rowsEl.insertAdjacentHTML('beforeend', labels);
    mark();
    return minX;
  }
  // 마우스를 올린 카드: 그 카드의 선·태그만 진하게
  function mark() {
    rowsEl.classList.toggle('lnhov', !!hov);
    $$('path.ln, .alabel', rowsEl).forEach(function (n) { n.classList.toggle('em', !!hov && (n.getAttribute('data-from') === hov || n.getAttribute('data-to') === hov)); });
  }
  rowsEl.addEventListener('mouseover', function (e) {
    var c = e.target.closest ? e.target.closest('.card') : null, id = c ? c.dataset.id : null;
    if (id !== hov) { hov = id; mark(); }
  });
  rowsEl.addEventListener('mouseleave', function () { if (hov) { hov = null; mark(); } });

  // 표시 패널: 보이기 · 투명도(끌기 한 번 = 되돌리기 한 단계)
  var show = $('#lnShow'), op = $('#lnOp');
  function apply() {
    rowsEl.classList.toggle('nolines', !prefs.lines);
    rowsEl.style.setProperty('--lnop', String(prefs.op));
    if (show) { show.setAttribute('aria-pressed', String(prefs.lines)); show.title = prefs.lines ? '선 숨기기' : '선 보이기'; }
    if (op) op.value = String(prefs.op);
  }
  function set(patch) { for (var k in patch) prefs[k] = patch[k]; ctx.savePrefs(); apply(); }
  if (show) show.addEventListener('click', function () {
    var a = prefs.lines, b = !a; set({lines: b});
    if (ctx.record) ctx.record({label: b ? '선 보이기' : '선 숨기기', undo: function () { set({lines: a}); }, redo: function () { set({lines: b}); }});
  });
  var opFrom = prefs.op;
  if (op) {
    op.addEventListener('input', function () { set({op: Math.max(0.15, Math.min(1, +op.value || 0.55))}); });
    op.addEventListener('change', function () {
      var a = opFrom, b = prefs.op; opFrom = b;
      if (a !== b && ctx.record) ctx.record({label: '선 투명도', undo: function () { set({op: a}); opFrom = a; }, redo: function () { set({op: b}); opFrom = b; }});
    });
  }
  apply();
  return {render: render, apply: apply};
}

HD.viewLines = {mount: mount};
})();
