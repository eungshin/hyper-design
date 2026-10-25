/* Model — AI 되돌리기(48c) 규칙: 도우미 GET /api/ai-writes 답에서 기록에 새로 올릴 줄 고르기 · 되살리기 본문 · 되살리기 답 풀이. DOM·저장소를 쓰지 않는다.
   답 {seq, writes:[{seq, stamp, screen, label, at}]} — 덮개(hd claim) 동안 AI 가 쓴 화면마다 한 줄(도우미가 쓰기 전 모습을 .hd-history 에 남김).
   fresh(seen{stamp:1}, writes) → 새 줄(stamp·label 이 글인 것만, 차례 그대로) · first(since, seq) → 기준만 잡을 때인가(처음 · 도우미가 다시 떠 seq 가 줄었음)
   body(stamp) → POST /api/restore 본문 {stamp, keep:true(되살리기 전 모습을 남겨 다시 하기 stamp 를 받음), notify:true(그 카드를 지켜보기가 다시 싣게)}
   outcome(res{status, body}) → {ok:true, next: 다음에 되살릴 stamp} | {ok:false, msg: 토스트 글}
   again(src, now) → 카드 iframe 을 다시 실을 주소(지금 주소의 다른 값·hd-mode 는 그대로, v 만 새로) | null(깨진 src) — 되살린 직후 view-busy 의 '방금 다시 실음 5초 건너뛰기'에 막히지 않게 이 기능이 직접 싣는다
   HD.aiUndo = {EVERY, fresh, first, body, outcome, again, CHANGED} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 2000;
var CHANGED = '그 뒤에 파일이 바뀌어 되돌릴 수 없어요';

function fresh(seen, writes) {
  if (!Array.isArray(writes)) return [];
  return writes.filter(function (w) {
    return !!w && typeof w.stamp === 'string' && !!w.stamp && typeof w.label === 'string' && !(seen && Object.prototype.hasOwnProperty.call(seen, w.stamp));
  });
}

function first(since, seq) { return since == null || typeof seq !== 'number' || seq < since; }

function body(stamp) { return {stamp: stamp, keep: true, notify: true}; }

function outcome(res) {
  var b = res && res.body || {}, st = res && res.status;
  if (st === 200 && typeof b.redo === 'string' && b.redo) return {ok: true, next: b.redo};
  if (st === 409 || b.reason === 'changed-since') return {ok: false, msg: CHANGED};
  if (st === 404 || b.reason === 'missing') return {ok: false, msg: '되돌릴 기록이 없어요'};
  return {ok: false, msg: '되돌리지 못했어요' + (b.error ? ': ' + b.error : '')};
}

function again(src, now) {
  if (typeof src !== 'string' || !src) return null;
  var hash = src.indexOf('#'), tail = hash >= 0 ? src.slice(hash) : '';
  if (hash >= 0) src = src.slice(0, hash);
  var q = src.indexOf('?'), path = q >= 0 ? src.slice(0, q) : src, kept = q >= 0 ? src.slice(q + 1).split('&').filter(function (p) { return p && !/^v=/.test(p); }) : [];
  kept.push('v=ai' + (typeof now === 'number' ? now : 0));
  return path + '?' + kept.join('&') + tail;
}

HD.aiUndo = {EVERY: EVERY, CHANGED: CHANGED, fresh: fresh, first: first, body: body, outcome: outcome, again: again};
})();
