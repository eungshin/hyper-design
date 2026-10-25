/* Model — 요소 막대 규칙(블록 편집, task 49a): 고른 요소에 띄울 단추·켜짐·앱 카드면 AI 요청·단축키·막대 자리. DOM·저장소·메시지를 쓰지 않는다.
   h = palette.js hd-hit 답 {path, text, full, textOk, prev, next, root, src?} · o = {app}(앱 카드 = 개발 서버 주소 화면, 또는 h.src 가 있음)
   HD.blocks = {ACTS, bar(h, o) → [{act, label, title, on, ask}], isApp(file), keyAct({key, alt, ctrl, meta, shift}) → act|null(Alt+↑↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기),
                askText(act, h) → 요청 글(앱 카드), place(anchor, size, view, avoid) → {x, y, below}} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ACTS = ['text', 'remove', 'dup', 'up', 'down', 'memo'];
var SPEC = {
  text:   {label: '글자', title: '글자 고치기 (T · 크게 보기에서 더블클릭)'},
  remove: {label: '지우기', title: '요소 지우기 (Del)'},
  dup:    {label: '복제', title: '요소 복제 — 바로 뒤에 (Ctrl+D)'},
  up:     {label: '↑', title: '위로 옮기기 (Alt+↑)'},
  down:   {label: '↓', title: '아래로 옮기기 (Alt+↓)'},
  memo:   {label: '메모', title: '이 요소에 메모 (AI에게 요청)'}
};
var WHY = {
  text: '안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요',   // helper.py BLOCK_REASON · palette.js textOk 와 같은 규칙
  root: '화면 뿌리(맨 바깥 요소)는 지우거나 복제·옮길 수 없어요',
  first: '맨 위 요소라 더 위로 옮길 수 없어요',
  last: '맨 아래 요소라 더 아래로 옮길 수 없어요'
};
var DEV = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d{1,5})?\//i;   // build_canvas.DEV_URL 과 같은 규칙(앱 카드)

function isApp(file) { return typeof file === 'string' && DEV.test(file); }

function why(act, h) {                               // 꺼진 까닭 | '' (켜짐)
  if (act === 'memo') return '';
  if (act === 'text') return h.textOk === false ? WHY.text : '';
  if (h.root) return WHY.root;
  if (act === 'up' && h.prev === false) return WHY.first;
  if (act === 'down' && h.next === false) return WHY.last;
  return '';
}

function bar(h, o) {
  h = h || {}; o = o || {};
  var app = !!o.app || !!(h.src && h.src.file);
  return ACTS.map(function (act) {
    var s = SPEC[act];
    if (app && act !== 'memo') return {act: act, label: s.label, title: 'AI에게 요청 — ' + s.title.replace(/ \(.*\)$/, '') + '(앱 카드는 파일에 바로 쓰지 않아요)', on: true, ask: true};
    var w = why(act, h);
    return {act: act, label: s.label, title: w || s.title, on: !w, ask: false};
  });
}

function keyAct(e) {
  if (!e || typeof e.key !== 'string' || e.shift) return null;
  var mod = !!(e.ctrl || e.meta);
  if (e.key === 'Delete' && !mod && !e.alt) return 'remove';
  if (e.alt && !mod) return e.key === 'ArrowUp' ? 'up' : e.key === 'ArrowDown' ? 'down' : null;
  if (mod && !e.alt && e.key.toLowerCase() === 'd') return 'dup';
  return null;
}

function askText(act, h) {                           // 앱 카드: 파일 대신 AI 에게 보낼 요청 글(메모 창에 미리 채움)
  var S = HD.edits && HD.edits.say;
  if (act === 'text') return '글자 바꾸기: "' + String((h && (h.full || h.text)) || '').replace(/\s+/g, ' ').trim() + '" → ""';
  if (!S) return '';
  return act === 'remove' ? S.remove() : act === 'dup' ? S.duplicate() : act === 'up' || act === 'down' ? S.move(act) : '';
}

// 막대 자리(화면 좌표): 요소 위 왼쪽 맞춤, 위에 자리가 없거나 avoid(카드 선택 막대)와 겹치면 아래 · 창 안으로
function place(anchor, size, view, avoid) {
  var gap = 6, m = 8;
  var x = Math.max(m, Math.min(view.w - size.w - m, anchor.x));
  var y = anchor.y - size.h - gap, below = false;
  var hit = function (yy) { return avoid && x < avoid.x + avoid.w && x + size.w > avoid.x && yy < avoid.y + avoid.h && yy + size.h > avoid.y; };
  if (y < m || hit(y)) { y = anchor.y + anchor.h + gap; below = true; }
  y = Math.max(m, Math.min(view.h - size.h - m, y));
  return {x: x, y: y, below: below};
}

HD.blocks = {ACTS: ACTS, bar: bar, isApp: isApp, keyAct: keyAct, askText: askText, place: place};
})();
