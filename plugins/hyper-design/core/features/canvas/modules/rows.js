/* Model — 판 줄 맞추기 계획: 지금 줄 + 새 데이터 줄 이름 → 걷을 줄·끼울 줄(51-1). DOM 을 쓰지 않는다.
   HD.rows = {plan(have, want) → {remove: [이름], insert: [{group, before: 이름|null}]}}
   have = 지금 판의 줄 [{group, n}](n = 그 줄 카드 수, 빈 레이아웃 포함) · want = 새 데이터의 줄 이름(nd.rows 차례).
   걷기 = 카드 0 이면서 want 에 없는 줄(Figma F18 빈 그룹은 없어진다) · 카드가 남은 줄은 want 에 없어도 둔다.
   끼우기 = want 에 있고 판에 없는 줄 — want 에서 그 뒤에 오는 남은 줄 앞(없으면 끝, before null). 차례대로 끼우면 want 차례가 된다.
   줄 = 섹션(51-4, Figma F16·F17) — 도우미에 묻기 전 같은 규칙(session.plan_group_rename · plan_group_dissolve 와 같은 글):
   target(names, name) → {into, where: 'above'|'below'} | {error} — 줄만 걷기 때 화면이 갈 줄: 위 줄, 첫 줄이면 아래 줄(사용자 결정 ①)
   checkName(names, from, to) → {name} | {name, same: true} | {error} — 앞뒤 빈칸을 자른 새 이름, 빈 이름·80자 넘음·같은 이름 줄·없는 줄은 이유
   rekeyPos(pos, live) → {pos, changed} — 옮긴 카드 자리(card-pos {id: {dx, dy, g}})의 줄 이름 g 를 지금 줄(live {id: 줄 이름})로 옮긴 새 값(S1c).
     줄 이름 바꾸기·줄만 걷기 뒤 view-card-pos 가 부른다 — 새로고침 뒤 cleanPos 가 g 가 다른 자리를 버리지 않게. live 에 없는 카드는 그대로, 입력은 고치지 않는다
   cleanPos(text, live) → {pos, dirty, bad} — 저장된 card-pos 글 → 지금 카드(live {id: 줄 이름})에 맞는 자리만 {dx, dy, g: 지금 줄}(셸 C4).
     없는 화면·다른 줄로 간 화면(g 가 있고 다름)·dx/dy 가 수가 아닌 값·빈 값은 버리고 dirty(다시 쓸 것) · 깨진 JSON·객체 아님 = 빈 자리 + bad(다시 쓰지 않음)
   space(rows, {base, clear}) → [px] — 줄 사이 띄우기(t51-8, Figma 섹션: 아래 줄 제목은 위 줄 내용과 겹치지 않는다). rows = 줄마다 {bottom, over}(같은 판 좌표:
     bottom = 그 줄 카드가 차지한 아래 끝, over = 그 줄 카드 아래 펼친 설명의 가장 아래 끝) → 줄마다 덧붙일 아래 여백(정수 ≥ 0) = over + clear 가
     bottom + base(기본 줄 사이)를 넘는 만큼. 깨진 값·base/clear 없음 = 0 · CLEAR = 설명 끝과 아래 줄 제목 사이 최소 띄움(px) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function plan(have, want) {
  have = Array.isArray(have) ? have : []; want = Array.isArray(want) ? want : [];
  var inWant = {}, kept = {}, remove = [], insert = [];
  want.forEach(function (g) { inWant[g] = 1; });
  have.forEach(function (r) {
    if (!r) return;
    if (!(r.n > 0) && !inWant[r.group]) remove.push(r.group); else kept[r.group] = 1;
  });
  want.forEach(function (g, i) {
    if (kept[g]) return;
    var before = null;
    for (var j = i + 1; j < want.length; j++) if (kept[want[j]]) { before = want[j]; break; }
    insert.push({group: g, before: before});
  });
  return {remove: remove, insert: insert};
}

var MAX = 80;                                         // session.GROUP_MAX 와 같다

function target(names, name) {
  names = Array.isArray(names) ? names : [];
  var i = names.indexOf(name);
  if (i < 0) return {error: '없는 줄이에요: ' + name};
  if (names.length < 2) return {error: '줄이 하나뿐이라 걷을 수 없어요'};
  return i > 0 ? {into: names[i - 1], where: 'above'} : {into: names[1], where: 'below'};
}

function checkName(names, from, to) {
  names = Array.isArray(names) ? names : [];
  if (names.indexOf(from) < 0) return {error: '없는 줄이에요: ' + from};
  var n = String(to == null ? '' : to).trim();
  if (!n) return {error: '줄 이름이 비었어요'};
  if (n.length > MAX) return {error: '줄 이름이 ' + MAX + '자를 넘어요'};
  if (n === from) return {name: n, same: true};
  if (names.indexOf(n) >= 0) return {error: '같은 이름의 줄이 이미 있어요: ' + n};
  return {name: n};
}

function rekeyPos(pos, live) {
  var out = {}, changed = false;
  live = live && typeof live === 'object' ? live : {};
  if (!pos || typeof pos !== 'object') return {pos: out, changed: false};
  Object.keys(pos).forEach(function (id) {
    var p = pos[id]; if (!p || typeof p !== 'object') return;
    var g = Object.prototype.hasOwnProperty.call(live, id) ? live[id] : p.g;
    if (g !== p.g) changed = true;
    out[id] = {dx: p.dx, dy: p.dy, g: g};
  });
  return {pos: out, changed: changed};
}

var CLEAR = 40;                                       // 펼친 설명 그림자(14px) + 숨 쉴 틈
function num(v) { return typeof v === 'number' && isFinite(v); }
function cleanPos(text, live) {
  var raw = {}, bad = false, pos = {}, dirty = false;
  live = live && typeof live === 'object' ? live : {};
  try { raw = JSON.parse(text || '{}') || {}; } catch (e) { raw = {}; bad = true; }
  if (typeof raw !== 'object' || Array.isArray(raw)) { raw = {}; bad = true; }
  Object.keys(raw).forEach(function (id) {
    var p = raw[id];
    if (live[id] === undefined || !p || !isFinite(p.dx) || !isFinite(p.dy) || (p.g != null && p.g !== live[id])) { dirty = true; return; }
    pos[id] = {dx: +p.dx, dy: +p.dy, g: live[id]};
  });
  return {pos: pos, dirty: dirty, bad: bad};
}

function space(rows, opt) {
  rows = Array.isArray(rows) ? rows : [];
  var base = opt && opt.base, clear = opt && opt.clear, ok = num(base) && num(clear);
  return rows.map(function (r) {
    if (!ok || !r || !num(r.bottom) || !num(r.over)) return 0;
    return Math.max(0, Math.ceil(r.over + clear - r.bottom - base - 1e-6));
  });
}

HD.rows = {plan: plan, target: target, checkName: checkName, rekeyPos: rekeyPos, cleanPos: cleanPos, space: space, CLEAR: CLEAR};
})();
