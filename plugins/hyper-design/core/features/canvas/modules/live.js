/* Model — 실시간 알림 규칙(47-4b): 서버 이벤트(protocol events.json) 하나 → 캔버스가 할 일, 흐름 상태(실시간·폴링·다시 붙기 간격), async apply 답 읽기. DOM·저장소·메시지를 쓰지 않는다.
   상태 = {last: 받은 마지막 id|null, mode: 'connecting'|'live'|'polling', fails, seen: {stamp:1}, order: [stamp](오래된 것부터 SEEN_MAX 개), echo: {screen: 먹을 때까지 ms}}
   plan(s, ev, at{rev: 상태 rev, files: 파일 seq|null, t: ms}) → {s, acts} — acts 는 [{do, …}]:
     notes.changed · claim · release = ev.rev > at.rev 일 때만 {do:'state'}(다시 읽기)
     screen.written by ai = ev.rev > at.files 일 때만 {do:'cards', ids, seq}(바뀐 카드 다시 싣기) — 그중 echo(되살리기 notify 의 지켜보기 메아리)는 한 번 먹는다
     screen.written by human = 처음 보는 stamp 일 때만 {do:'data', ids, stamp}(판 데이터 + 바뀐 카드) — 캔버스가 스스로 쓴 것(own)은 건너뜀
     ai.write = {do:'aiWrites'} · build.done = {do:'built', ids} · build.failed(async, repaired 가 null 아님) = {do:'revert', ids: reverted, why, screens}
     reset = {do:'state'}, {do:'files'}, {do:'aiWrites'}(놓친 것을 다시 맞춤), 기준 id = ev.last · 이미 받은 id(이어 받기로 다시 옴)·모르는 type·깨진 이벤트 = []
   own(s, stamp, ids, echo, t) → {s, fresh} — 캔버스가 스스로 쓴·되살린 것을 다시 실으려 함: 그 stamp 를 이벤트로 이미 실었으면 fresh false.
     도장 없는 쓰기(keep 없는 되살리기 — 이벤트 stamp null) = 화면마다 RECENT_MS 안에 반대쪽(이벤트 ↔ 캔버스)이 실었으면 건너뜀(어느 쪽이 먼저 와도 한 번)
     echo = 도우미가 지켜보기에 알리게 한 되살리기(notify) — 그 화면의 다음 ai 알림 하나를 ECHO_MS 안에 먹는다(두 번 싣지 않게)
   link(s, a{type:'open'|'error'}) → {s, poll: 폴링을 켤까, retry: 다시 붙을 ms|null} · backoff(n) = 1·2·4…초, 30초까지
   answer(res) → apply 답에 applied(async 답의 accepted) — 예전 답은 그대로
   HD.live = {TYPES, ECHO_MS, RECENT_MS, SEEN_MAX, initial, plan, own, link, backoff, answer} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var TYPES = ['screen.written', 'notes.changed', 'claim', 'release', 'ai.write', 'build.started', 'build.done', 'build.failed', 'reset'];
var ECHO_MS = 4000, RECENT_MS = 1500, SEEN_MAX = 200, MAX_WAIT = 30000;
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

function initial() { return {last: null, mode: 'connecting', fails: 0, seen: {}, order: [], echo: {}, byEv: {}, byOwn: {}}; }
function copy(s) { return {last: s.last, mode: s.mode, fails: s.fails, seen: s.seen, order: s.order, echo: s.echo, byEv: s.byEv || {}, byOwn: s.byOwn || {}}; }
function stampAt(m, ids, t) { var n = {}, k; for (k in m) if (has(m, k) && m[k] + RECENT_MS >= t) n[k] = m[k]; ids.forEach(function (id) { n[id] = t; }); return n; }
function recent(m, id, t) { return has(m, id) && m[id] + RECENT_MS >= t; }
function strs(l) { return Array.isArray(l) ? l.filter(function (x) { return typeof x === 'string' && x; }) : []; }

function remember(n, stamp) {                         // stamp 하나 기억(끝이 있다 — 오래된 것부터 잊음)
  var seen = {}, order = n.order.concat([stamp]), k;
  while (order.length > SEEN_MAX) order.shift();
  for (k = 0; k < order.length; k++) seen[order[k]] = 1;
  n.seen = seen; n.order = order;
}

function plan(s, ev, at) {
  at = at || {};
  if (!s || !ev || typeof ev.type !== 'string' || TYPES.indexOf(ev.type) < 0) return {s: s, acts: []};
  if (ev.type === 'reset') {
    var r = copy(s); r.last = typeof ev.last === 'number' ? ev.last : s.last;
    return {s: r, acts: [{do: 'state'}, {do: 'files'}, {do: 'aiWrites'}]};
  }
  if (typeof ev.id !== 'number') return {s: s, acts: []};
  if (s.last != null && ev.id <= s.last) return {s: s, acts: []};
  var n = copy(s), acts = [];
  n.last = ev.id;
  var t = ev.type, newer = typeof ev.rev === 'number' && (typeof at.rev !== 'number' || ev.rev > at.rev);
  if (t === 'notes.changed' || t === 'claim' || t === 'release') { if (newer) acts.push({do: 'state'}); }
  else if (t === 'screen.written') {
    var ids = strs(ev.screens);
    if (ev.by === 'ai') {
      if (typeof ev.rev === 'number' && typeof at.files === 'number' && ev.rev <= at.files) return {s: n, acts: []};
      var echo = {}, k, now = +at.t || 0;
      for (k in n.echo) if (has(n.echo, k)) echo[k] = n.echo[k];
      ids = ids.filter(function (id) {
        if (has(echo, id)) { var live = echo[id] >= now; delete echo[id]; return !live; }
        return true;
      });
      n.echo = echo;
      if (ids.length) acts.push({do: 'cards', ids: ids, seq: typeof ev.rev === 'number' ? ev.rev : null});
    } else {
      var st = typeof ev.stamp === 'string' && ev.stamp ? ev.stamp : null, tn = +at.t || 0;
      if (st && has(n.seen, st)) return {s: n, acts: []};
      if (st) remember(n, st);
      else ids = ids.filter(function (id) { return !recent(n.byOwn, id, tn); });   // 도장 없는 쓰기(되살리기) = 캔버스가 방금 스스로 실은 화면은 건너뜀
      if (ids.length) { n.byEv = stampAt(n.byEv, ids, tn); acts.push({do: 'data', ids: ids, stamp: st || 'e' + ev.id}); }
    }
  }
  else if (t === 'ai.write') acts.push({do: 'aiWrites'});
  else if (t === 'build.done') acts.push({do: 'built', ids: strs(ev.ids)});
  else if (t === 'build.failed') {
    if (ev.repaired !== null && ev.repaired !== undefined) acts.push({do: 'revert', ids: strs(ev.reverted), why: String(ev.reason || ''), screens: strs(ev.screens)});
  }
  return {s: n, acts: acts};
}

function own(s, stamp, ids, echo, t) {
  var n = copy(s), fresh = true;
  var list = strs(ids), tn = +t || 0;
  if (typeof stamp === 'string' && stamp) {
    if (has(n.seen, stamp)) fresh = false; else remember(n, stamp);
  } else if (list.length && list.every(function (id) { return recent(n.byEv, id, tn); })) fresh = false;   // 도장 없음 = 이벤트가 방금 실었으면
  if (fresh && list.length) n.byOwn = stampAt(n.byOwn, list, tn);
  if (echo) {
    var e = {}, k; for (k in n.echo) if (has(n.echo, k)) e[k] = n.echo[k];
    list.forEach(function (id) { e[id] = tn + ECHO_MS; });
    n.echo = e;
  }
  return {s: n, fresh: fresh};
}

function backoff(n) { return Math.min(MAX_WAIT, 1000 * Math.pow(2, Math.max(0, (n | 0) - 1))); }

function link(s, a) {
  var n = copy(s);
  if (a && a.type === 'open') { n.mode = 'live'; n.fails = 0; return {s: n, poll: false, retry: null}; }
  n.mode = 'polling'; n.fails = s.fails + 1;
  return {s: n, poll: true, retry: backoff(n.fails)};
}

function answer(res) {
  if (!res || typeof res !== 'object') return {};
  if (!Array.isArray(res.applied) && Array.isArray(res.accepted)) res.applied = res.accepted.slice();
  return res;
}

HD.live = {TYPES: TYPES, ECHO_MS: ECHO_MS, RECENT_MS: RECENT_MS, SEEN_MAX: SEEN_MAX, initial: initial, plan: plan, own: own, link: link, backoff: backoff, answer: answer};
})();
