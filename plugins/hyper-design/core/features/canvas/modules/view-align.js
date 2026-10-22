/* View — 정렬 패널(task 7, H8·H13). 계산 규칙은 modules/align.js(Model), 여기는 그리기·누르기와 간격 저장.
   고른 화면 수 줄 · 맞추기 6개(2장 이상) · 간격 같게 2개(3장 이상) · 간격 칸(px, 기본 80) + 가로/세로로 늘어놓기(2장 이상) · 안내 줄.
   단추를 누르면 ctx.run(op) — op = {op:'align', how} | {op:'distribute', axis} | {op:'stack', axis, gap}. 옮기기·되돌리기·저장은 셸이 한다.
   간격 칸에서 Enter = 마지막에 쓴 늘어놓기 방향(처음은 가로). 잘못된 값은 칸을 떠날 때 마지막 바른 값으로.
   HD.viewAlign.mount(ctx) → {render(), gap()}   HD.viewAlign.CSS = 패널 CSS 한 줄(셸이 붙인다)
   ctx = {root, $, esc, count() → 고른(옮길 수 있는) 화면 수, run(op), getItem(k), setItem(k, v), key} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var DEF = 80, MAX = 2000;
function svg(d) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + d + '</svg>'; }

// 일러스트레이터식 그림: 기준선 하나 + 막대 둘
var ALIGN = [
  {how: 'left', name: '왼쪽 맞추기', d: '<path d="M4 3v18"/><rect x="7" y="6" width="12" height="4" rx="1"/><rect x="7" y="14" width="7" height="4" rx="1"/>'},
  {how: 'hcenter', name: '가로 가운데 맞추기', d: '<path d="M12 3v18"/><rect x="5" y="6" width="14" height="4" rx="1"/><rect x="8" y="14" width="8" height="4" rx="1"/>'},
  {how: 'right', name: '오른쪽 맞추기', d: '<path d="M20 3v18"/><rect x="5" y="6" width="12" height="4" rx="1"/><rect x="10" y="14" width="7" height="4" rx="1"/>'},
  {how: 'top', name: '위 맞추기', d: '<path d="M3 4h18"/><rect x="6" y="7" width="4" height="12" rx="1"/><rect x="14" y="7" width="4" height="7" rx="1"/>'},
  {how: 'vcenter', name: '세로 가운데 맞추기', d: '<path d="M3 12h18"/><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="8" width="4" height="8" rx="1"/>'},
  {how: 'bottom', name: '아래 맞추기', d: '<path d="M3 20h18"/><rect x="6" y="5" width="4" height="12" rx="1"/><rect x="14" y="10" width="4" height="7" rx="1"/>'}
];
var DIST = [
  {axis: 'x', name: '가로 간격 같게', d: '<rect x="3" y="7" width="4" height="10" rx="1"/><rect x="10" y="7" width="4" height="10" rx="1"/><rect x="17" y="7" width="4" height="10" rx="1"/><path d="M7 20h3M14 20h3"/>'},
  {axis: 'y', name: '세로 간격 같게', d: '<rect x="7" y="3" width="10" height="4" rx="1"/><rect x="7" y="10" width="10" height="4" rx="1"/><rect x="7" y="17" width="10" height="4" rx="1"/><path d="M20 7v3M20 14v3"/>'}
];
var STACK = [
  {axis: 'x', name: '가로로 늘어놓기', d: '<rect x="3" y="7" width="6" height="10" rx="1"/><rect x="15" y="7" width="6" height="10" rx="1"/><path d="M10.5 12h3M12.5 10.5l1.5 1.5-1.5 1.5"/>'},
  {axis: 'y', name: '세로로 늘어놓기', d: '<rect x="7" y="3" width="10" height="6" rx="1"/><rect x="7" y="15" width="10" height="6" rx="1"/><path d="M12 10.5v3M10.5 12.5l1.5 1.5 1.5-1.5"/>'}
];

var CSS = '.al{display:flex;flex-direction:column;gap:8px;font-size:12.5px;color:#3a3a37}' +
  '.al-n{margin:0;font-weight:700;font-size:13px}.al-n.off{font-weight:400;color:#999}' +
  '.al-s{display:flex;flex-direction:column;gap:4px;border-top:1px solid #eee;padding-top:6px}' +
  '.al-h{margin:0;font-size:11.5px;font-weight:600;color:#888}' +
  '.al-row{display:flex;align-items:center;gap:2px;flex-wrap:wrap}' +
  '.al-ib{width:32px;height:32px;border:0;border-radius:6px;background:none;color:#3a3a37;display:grid;place-items:center;cursor:pointer;padding:0}' +
  '.al-ib:hover{background:#F2F2EF}.al-ib:disabled{opacity:.35;cursor:default;background:none}' +
  '.al-ib svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}' +
  '.al-sep{width:1px;height:20px;background:#e6e6e2;margin:0 4px}' +
  '.al-gap{display:inline-flex;align-items:center;gap:4px;margin-right:6px;color:#555}' +
  '#alGap{width:64px;font:12.5px ui-monospace,Menlo,monospace;border:1px solid var(--ui-line,#ddd);border-radius:5px;padding:3px 6px;text-align:right}' +
  '#alGap:focus{outline:2px solid #2b2b29;outline-offset:0}' +
  '.al-hint{margin:0;color:#999;font-size:12px;line-height:1.45}';

function mount(ctx) {
  var root = ctx.root, esc = ctx.esc || function (s) { return String(s); };
  var last = 'x';                                          // 마지막에 쓴 늘어놓기 방향(Enter 용)

  function valid(v) {                                      // 바른 간격 = 0~2000 정수, 아니면 null
    if (v === '' || v == null) return null;
    var n = Number(v);
    if (!isFinite(n) || n < 0) return null;
    return Math.min(MAX, Math.round(n));
  }
  var saved = valid(ctx.getItem ? ctx.getItem(ctx.key) : null);
  var good = saved == null ? DEF : saved;                  // 마지막 바른 값

  function btn(attr, val, x) {
    return '<button type="button" class="al-ib" ' + attr + '="' + val + '" title="' + esc(x.name) + '" aria-label="' + esc(x.name) + '">' + svg(x.d) + '</button>';
  }
  root.innerHTML = '<div class="al">' +
    '<p class="al-n" role="status" aria-live="polite"></p>' +
    '<div class="al-s"><p class="al-h">정렬</p><div class="al-row">' +
      ALIGN.slice(0, 3).map(function (x) { return btn('data-al', x.how, x); }).join('') + '<span class="al-sep"></span>' +
      ALIGN.slice(3).map(function (x) { return btn('data-al', x.how, x); }).join('') + '</div></div>' +
    '<div class="al-s"><p class="al-h">분배</p><div class="al-row">' +
      DIST.map(function (x) { return btn('data-dist', x.axis, x); }).join('') + '</div></div>' +
    '<div class="al-s"><p class="al-h">간격</p><div class="al-row">' +
      '<label class="al-gap"><input id="alGap" type="number" min="0" max="' + MAX + '" step="1" value="' + good + '" aria-label="간격(px)" title="카드 사이 간격(px)"><span>px</span></label>' +
      STACK.map(function (x) { return btn('data-stack', x.axis, x); }).join('') + '</div></div>' +
    '<p class="al-hint">Shift+클릭으로 여러 장 고르기 · 레이어 폴더의 늘어놓기도 이 간격</p>' +
    '</div>';
  var status = root.querySelector('.al-n'), input = root.querySelector('#alGap');

  function setGood(n) {
    if (n === good) return;
    good = n;
    if (ctx.setItem) ctx.setItem(ctx.key, String(n));
  }
  function gap() {                                         // 칸에 바른 값이 있으면 그것, 아니면 마지막 바른 값
    var n = valid(input.value);
    if (n != null) setGood(n);
    return good;
  }
  function render() {
    var n = Math.max(0, Number(ctx.count()) || 0);
    status.textContent = n >= 2 ? '고른 화면 ' + n + '개' : '화면을 두 개 이상 고르세요';
    status.classList.toggle('off', n < 2);
    root.querySelectorAll('button[data-al], button[data-stack]').forEach(function (b) { b.disabled = n < 2; });
    root.querySelectorAll('button[data-dist]').forEach(function (b) { b.disabled = n < 3; });
  }
  function stack(axis) {
    last = axis;
    if (ctx.count() < 2) return;
    ctx.run({op: 'stack', axis: axis, gap: gap()});
  }

  root.addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b || b.disabled || !root.contains(b)) return;
    if (b.dataset.al) ctx.run({op: 'align', how: b.dataset.al});
    else if (b.dataset.dist) ctx.run({op: 'distribute', axis: b.dataset.dist});
    else if (b.dataset.stack) stack(b.dataset.stack);
  });
  input.addEventListener('input', function () { var n = valid(input.value); if (n != null) setGood(n); });
  input.addEventListener('blur', function () { input.value = String(gap()); });
  input.addEventListener('keydown', function (e) {
    e.stopPropagation();                                   // 판 단축키와 겹치지 않게
    if (e.key === 'Enter') { e.preventDefault(); input.value = String(gap()); stack(last); }
    else if (e.key === 'Escape') { input.value = String(good); input.blur(); }
  });

  render();
  return {render: render, gap: gap};
}

HD.viewAlign = {mount: mount, CSS: CSS};
})();
