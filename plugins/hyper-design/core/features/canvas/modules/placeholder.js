/* Model — 생성 중 빈 틀(S5): 어떤 화면이 오는 중인지와 그 틀의 단계(pending → arriving → done | failed)를 서버 이벤트·메모 상태에서 정한다. 화면·저장소·메시지를 쓰지 않는다.
   틀 하나 = item {id, kind:'draft'|'screen', note, state:'pending'|'arriving'|'failed', agent, by, since, t, why}
     draft  = 빈 레이아웃 카드(메모 edit=new-screen, 카드 id new-…) — 그 카드 자리에 틀을 씌운다
     screen = 진행·claim 이 말한 화면 id 인데 판에 그 카드가 없음 — 판 위 빈 자리에 틀을 놓는다
   상태 = {items: {id: item}, cleared: {id: 1}(사람이 [지우기] — 다시 보내기 전에는 다시 띄우지 않음), names: {에이전트 id: 이름}}
   step(s, a, at) → {s, fx}   입력 s 는 고치지 않는다. a = 서버 이벤트(hd-event detail) 또는 판의 사실:
     request.sent  — notes 에 빈 레이아웃 메모가 있고 via 가 queue 가 아니면 그 카드 pending(받는 곳 = to). queue = 아무도 일하지 않음 → 그대로
     agent.progress · claim — screen 이 빈 레이아웃 id 면 그 카드, 판에 없는 화면이면 screen 틀 pending(이미 있으면 활동 시각만). 판에 있는 화면 = 아님
     screen.written — screen 틀이 그 화면이면 arriving · 판에 없는 새 화면이 쓰였으면 일하는 빈 레이아웃 틀도 arriving(fx landing — 판 데이터를 다시 받게)
     agent.reply   — 빈 레이아웃 메모의 답: 반영됨·대체됨 = arriving, 사람 '확인' = 그대로, 그 밖(질문·답변·일부·다시) = failed(까닭)
     release       — 아직 파일이 안 온(pending) 틀 = failed '파일 없이 작업이 끝났어요'
     agent.away    — 그 에이전트가 맡은 pending 틀 = failed 'AI 연결이 끊겼어요'
     build.failed  — 그 화면(빈 레이아웃이면 그 id 나 판에 없는 화면)이 든 실패 = failed '빌드가 깨졌어요 — …'
     agent.hello   — 이름 기억(틀 글의 받는 곳)
     {type:'scan'} — 판 사실 맞추기: screen 틀의 카드가 생김 = done · 빈 레이아웃 메모가 사라짐 = 승격(at.promoted)이면 done(to = 그 화면), 아니면 drop ·
                     보냈고 답이 없고 덮개가 working 인 빈 레이아웃(at.working)인데 틀이 없으면 pending(새로고침·SSE 없는 판)
     {type:'tick'} — 활동 없이 TIMEOUT_MS 넘은 pending = failed '오래 답이 없어요'
     {type:'clear', id} — [지우기]: 틀을 지우고 cleared
     {type:'agents', list:[{id, name}]} — 이름 기억
   at = {t: ms, has(id) → 판에 그 화면 카드가 있나, drafts: {메모 id: 빈 레이아웃 id}(지금 메모), promoted: {빈 레이아웃 id: 화면 id}, working: {빈 레이아웃 id: 1}}
   fx = [{do:'show', id}(새 틀 — 카메라) | {do:'paint', id} | {do:'landing', id, ids}(판에 없는 새 화면 id) | {do:'done', id, to} | {do:'drop', id}]
   look(item) → {state, title, sub, shimmer, clear} — 틀 글: '만드는 중…' + 받는 곳 이름 · '화면을 싣는 중…' · '만들지 못했어요' + 까닭 + [지우기]
   reveal(box, view, o) → {z, tx, ty} | null — box(판 창 기준 화면 px {x, y, w, h})가 margin 안에 다 보이게 하는 가장 작은 이동(안 들어가면 그만큼 축소, o.zMin 아래로는 안 함).
     view = {w, h, z, tx, ty}. 이미 다 보이면 null. o.centre = 가운데로(토스트 [보기])
   HD.placeholder = {TIMEOUT_MS, CROSS_MS, REPLY_WHY, initial, step, list, look, reveal} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var TIMEOUT_MS = 10 * 60 * 1000;                     // 아무 소식 없이 10분 = 실패로 보인다(지울 수 있게)
var CROSS_MS = 300;                                  // 틀 → 진짜 카드 겹쳐 바꾸기(Stitch 0.3초)
var REPLY_WHY = {'질문': 'AI 가 질문을 남겼어요 — 메모를 보세요', '답변': '화면 없이 답만 왔어요', '일부': '일부만 됐어요 — 메모를 보세요', '다시': '다시 하기로 했어요'};
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

function initial() { return {items: {}, cleared: {}, names: {}}; }
function copy(s) {
  var n = {items: {}, cleared: {}, names: {}}, k;
  for (k in s.items) if (has(s.items, k)) n.items[k] = s.items[k];
  for (k in s.cleared) if (has(s.cleared, k)) n.cleared[k] = 1;
  for (k in s.names) if (has(s.names, k)) n.names[k] = s.names[k];
  return n;
}
function set(n, id, ch) { var o = n.items[id], x = {}, k; for (k in o) if (has(o, k)) x[k] = o[k]; for (k in ch) if (has(ch, k)) x[k] = ch[k]; n.items[id] = x; }
function str(v) { return typeof v === 'string' && v ? v : null; }
function strs(l) { return Array.isArray(l) ? l.filter(function (x) { return typeof x === 'string' && x; }) : []; }
function draftIds(at) { var o = {}, d = at.drafts || {}, k; for (k in d) if (has(d, k) && str(d[k])) o[d[k]] = k; return o; }   // 빈 레이아웃 id → 메모 id
function nameOf(n, agent) { return agent && has(n.names, agent) ? n.names[agent] : null; }
function cut(s, m) { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > m ? s.slice(0, m - 1) + '…' : s; }

function open(n, fx, id, kind, note, agent, t) {     // 새 틀 또는 실패한 틀을 다시 pending
  var o = n.items[id];
  if (o && o.state !== 'failed') { set(n, id, {t: t, agent: agent || o.agent, by: nameOf(n, agent) || o.by}); return; }
  n.items[id] = {id: id, kind: kind, note: note || null, state: 'pending', agent: agent || null, by: nameOf(n, agent), since: t, t: t, why: null};
  fx.push({do: o ? 'paint' : 'show', id: id});
}
function fail(n, fx, id, why) { set(n, id, {state: 'failed', why: why}); fx.push({do: 'paint', id: id}); }

function step(s, a, at) {
  at = at || {};
  var n = copy(s || initial()), fx = [], t = +at.t || 0, hasCard = typeof at.has === 'function' ? at.has : function () { return false; };
  var dr = draftIds(at), type = a && a.type, ids = Object.keys(n.items);
  if (!type) return {s: s || initial(), fx: []};
  if (type === 'agent.hello' || type === 'agents') {
    var list = type === 'agents' ? (Array.isArray(a.list) ? a.list : []) : [a.agent];
    list.forEach(function (g) { if (g && str(g.id) && str(g.name)) n.names[g.id] = g.name; });
    ids.forEach(function (id) { var it = n.items[id]; if (it.agent && has(n.names, it.agent) && it.by !== n.names[it.agent]) { set(n, id, {by: n.names[it.agent]}); fx.push({do: 'paint', id: id}); } });
  } else if (type === 'request.sent') {
    if (a.via === 'queue') return {s: n, fx: []};
    strs(a.notes).forEach(function (nid) {
      var d = has(at.drafts, nid) ? str(at.drafts[nid]) : null; if (!d) return;
      delete n.cleared[d];                           // 다시 보냄 = 사람이 다시 원함
      open(n, fx, d, 'draft', nid, str(a.to), t);
    });
  } else if (type === 'agent.progress' || type === 'claim') {
    var x = str(a.screen), ag = str(type === 'claim' ? a.by : a.agent);
    if (!x || has(n.cleared, x)) return {s: n, fx: []};
    if (has(dr, x)) open(n, fx, x, 'draft', dr[x], ag, t);
    else if (!hasCard(x)) open(n, fx, x, 'screen', null, ag, t);
  } else if (type === 'screen.written') {
    var ws = strs(a.screens), fresh = ws.filter(function (id) { return !hasCard(id) && !has(dr, id); });
    ids.forEach(function (id) {
      var it = n.items[id]; if (it.state === 'failed') return;
      var mine = it.kind === 'screen' ? ws.indexOf(id) >= 0 : (fresh.length > 0 || ws.indexOf(id) >= 0);
      if (!mine) return;
      if (it.state !== 'arriving') { set(n, id, {state: 'arriving', t: t}); fx.push({do: 'paint', id: id}); }
      var land = it.kind === 'screen' ? [id] : fresh;
      if (land.length) fx.push({do: 'landing', id: id, ids: land});
    });
  } else if (type === 'agent.reply') {
    var nd = str(a.note) && has(at.drafts, a.note) ? str(at.drafts[a.note]) : null, it2 = nd && n.items[nd];
    if (!it2 || a.kind === '확인') return {s: n, fx: []};
    if (a.kind === '반영됨' || a.kind === '대체됨') {
      if (it2.state !== 'arriving') { set(n, nd, {state: 'arriving', t: t}); fx.push({do: 'paint', id: nd}); }
    } else fail(n, fx, nd, REPLY_WHY[a.kind] || '파일 없이 답만 왔어요');
  } else if (type === 'release') {
    var r = str(a.screen);
    if (r && has(n.items, r) && n.items[r].state === 'pending') fail(n, fx, r, '파일 없이 작업이 끝났어요');
  } else if (type === 'agent.away') {
    ids.forEach(function (id) { var it = n.items[id]; if (it.state === 'pending' && it.agent && it.agent === a.agent) fail(n, fx, id, 'AI 연결이 끊겼어요'); });
  } else if (type === 'build.failed') {
    var bs = strs(a.screens), news = bs.some(function (id) { return !hasCard(id) && !has(dr, id); });
    ids.forEach(function (id) {
      var it = n.items[id]; if (it.state === 'failed') return;
      if (bs.indexOf(id) >= 0 || (it.kind === 'draft' && news)) fail(n, fx, id, '빌드가 깨졌어요 — ' + cut(a.reason, 60));
    });
  } else if (type === 'scan') {
    var prom = at.promoted || {}, work = at.working || {}, k;
    ids.forEach(function (id) {
      var it = n.items[id];
      if (it.kind === 'screen' && hasCard(id)) { delete n.items[id]; fx.push({do: 'done', id: id, to: id}); }
      else if (it.kind === 'draft' && !has(dr, id)) {
        delete n.items[id];
        var to = has(prom, id) ? str(prom[id]) : null;
        fx.push(to && hasCard(to) ? {do: 'done', id: id, to: to} : {do: 'drop', id: id});
      }
    });
    for (k in work) if (has(work, k) && work[k] && has(dr, k) && !has(n.items, k) && !has(n.cleared, k)) open(n, fx, k, 'draft', dr[k], null, t);
  } else if (type === 'tick') {
    ids.forEach(function (id) { var it = n.items[id]; if (it.state === 'pending' && t - it.t > TIMEOUT_MS) fail(n, fx, id, '오래 답이 없어요'); });
  } else if (type === 'clear') {
    var c = str(a.id);
    if (c && has(n.items, c)) { delete n.items[c]; n.cleared[c] = 1; fx.push({do: 'drop', id: c}); }
  } else return {s: s, fx: []};
  return {s: n, fx: fx};
}

function list(s) { var o = []; for (var k in (s && s.items)) if (has(s.items, k)) o.push(s.items[k]); return o; }

function look(it) {
  if (!it) return null;
  if (it.state === 'failed') return {state: 'failed', title: '만들지 못했어요', sub: it.why || '', shimmer: false, clear: true};
  if (it.state === 'arriving') return {state: 'arriving', title: '화면을 싣는 중…', sub: it.by || '', shimmer: true, clear: false};
  return {state: 'pending', title: '만드는 중…', sub: it.by || '', shimmer: true, clear: false};
}

function reveal(box, view, o) {
  o = o || {};
  if (!box || !view || !(view.z > 0) || !(view.w > 0) || !(view.h > 0)) return null;
  var m = o.margin == null ? 48 : o.margin, z = view.z;
  var bx = (box.x - view.tx) / z, by = (box.y - view.ty) / z, bw = box.w / z, bh = box.h / z;   // 판(stage) 좌표
  var aw = Math.max(1, view.w - 2 * m), ah = Math.max(1, view.h - 2 * m);
  var z2 = Math.min(z, aw / bw, ah / bh);
  if (o.zMin != null) z2 = Math.max(o.zMin, z2);
  if (o.centre) return {z: z2, tx: view.w / 2 - (bx + bw / 2) * z2, ty: view.h / 2 - (by + bh / 2) * z2};
  if (z2 === z && box.x >= m && box.y >= m && box.x + box.w <= view.w - m && box.y + box.h <= view.h - m) return null;
  var tx, ty;                                        // 배율이 바뀌면 판 창 가운데를 기준으로
  if (z2 !== z) { var cx = (view.w / 2 - view.tx) / z, cy = (view.h / 2 - view.ty) / z; tx = view.w / 2 - cx * z2; ty = view.h / 2 - cy * z2; }
  else { tx = view.tx; ty = view.ty; }
  var sx = bx * z2 + tx, sy = by * z2 + ty, sw = bw * z2, sh = bh * z2;   // 새 배율에서 상자 자리 → 모자란 만큼만 민다
  if (sw > view.w - 2 * m) tx += view.w / 2 - (sx + sw / 2);
  else if (sx < m) tx += m - sx; else if (sx + sw > view.w - m) tx -= sx + sw - (view.w - m);
  if (sh > view.h - 2 * m) ty += view.h / 2 - (sy + sh / 2);
  else if (sy < m) ty += m - sy; else if (sy + sh > view.h - m) ty -= sy + sh - (view.h - m);
  return {z: z2, tx: tx, ty: ty};
}

HD.placeholder = {TIMEOUT_MS: TIMEOUT_MS, CROSS_MS: CROSS_MS, REPLY_WHY: REPLY_WHY, initial: initial, step: step, list: list, look: look, reveal: reveal};
})();
