/* Model — 낙관 반영 상태(task 49c): 화면에 먼저 보인 요소 편집(글자·복제·옮기기)이 도우미 답을 기다리는 동안 → 남김(kept) | 되돌림(reverted). DOM·저장소·메시지를 쓰지 않는다.
   상태 = {ops: {tag: {screen, steps, done, phase:'pending'|'kept'|'reverted', why}}} — tag 하나 = 화면에 먼저 보인 변경 하나(옮기기 k칸 = steps k, 도우미 쓰기 k번)
   reduce(s, a) → 새 상태(바뀐 게 없으면 같은 객체): start{tag, screen, steps≥1} · step{tag}(쓰기 하나 끝) · keep{tag} · revert{tag, why} · end{tag}(치움)
   outcome(res, ids) → {kept, why} — /api/apply 답에 ids 가 모두 applied 면 남김, 아니면 되돌림(why = 도우미가 준 까닭 첫 줄 | 기본 글)
   hold(s, screen) → bool — 그 화면에 아직 보낼(또는 답을 기다리는) 쓰기가 지금 것 말고 더 있다 = 이번 다시 싣기는 건너뛴다(중간 모습으로 깜빡이지 않게)
   phase(s, tag) → 'pending'|'kept'|'reverted'|null · failText(label, why, done, steps) → 알림 글
   HD.optimistic = {initial, reduce, outcome, hold, phase, failText, WHY} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var WHY = '도우미가 답하지 않았어요';
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

function initial() { return {ops: {}}; }
function copy(o) { var n = {}, k; for (k in o) if (has(o, k)) n[k] = o[k]; return n; }
function put(s, tag, op) { var ops = copy(s.ops); if (op) ops[tag] = op; else delete ops[tag]; return {ops: ops}; }

function reduce(s, a) {
  if (!s || !s.ops || !a || typeof a.tag !== 'string' || !a.tag) return s;
  var o = has(s.ops, a.tag) ? s.ops[a.tag] : null;
  if (a.type === 'start') {
    if (o || typeof a.screen !== 'string' || !a.screen) return s;
    var n = Math.max(1, Math.floor(+a.steps || 1));
    return put(s, a.tag, {screen: a.screen, steps: n, done: 0, phase: 'pending', why: ''});
  }
  if (!o) return s;
  if (a.type === 'end') return put(s, a.tag, null);
  if (o.phase !== 'pending') return s;                // 남김·되돌림 뒤에 온 늦은 신호 = 무시
  if (a.type === 'step') return o.done >= o.steps ? s : put(s, a.tag, {screen: o.screen, steps: o.steps, done: o.done + 1, phase: 'pending', why: ''});
  if (a.type === 'keep') return put(s, a.tag, {screen: o.screen, steps: o.steps, done: o.done, phase: 'kept', why: ''});
  if (a.type === 'revert') return put(s, a.tag, {screen: o.screen, steps: o.steps, done: o.done, phase: 'reverted', why: String(a.why || WHY)});
  return s;
}

function outcome(res, ids) {
  ids = Array.isArray(ids) ? ids : [];
  var ap = res && Array.isArray(res.applied) ? res.applied : null;
  if (ap && ids.length && ids.every(function (id) { return ap.indexOf(id) >= 0; })) return {kept: true, why: ''};
  var f = res && Array.isArray(res.failed) ? res.failed.filter(function (x) { return x && x.reason && (!ids.length || ids.indexOf(x.id) >= 0); })[0] : null;
  return {kept: false, why: f ? String(f.reason) : res && res.error ? String(res.error) : '도우미가 이 편집을 쓰지 않았어요'};
}

function hold(s, screen) {
  if (!s || !s.ops) return false;
  var left = 0;
  Object.keys(s.ops).forEach(function (k) { var o = s.ops[k]; if (o.screen === screen && o.phase === 'pending') left += o.steps - o.done; });
  return left > 1;
}

function phase(s, tag) { return s && has(s.ops, tag) ? s.ops[tag].phase : null; }

function failText(label, why, done, steps) {
  var part = steps > 1 && done > 0 ? ' (' + steps + '칸 중 ' + done + '칸만 옮겼어요)' : '';
  return label + ' — 파일에 쓰지 못해 되돌렸어요' + part + ': ' + (why || WHY);
}

HD.optimistic = {initial: initial, reduce: reduce, outcome: outcome, hold: hold, phase: phase, failText: failText, WHY: WHY};
})();
