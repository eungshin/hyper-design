/* Model — 접속한 에이전트 표(47-5b): GET /api/presence 답 + agent.hello/away/progress 이벤트 → 표 하나, 받는 곳 칩에 보일 상태. DOM·저장소를 쓰지 않는다.
   상태 s = {agents: {id: {id, name, kind, state:'here'|'away', progress: {text, screen}|null}}}
   initial() · load(s, body{agents}) → {s, bad}(답의 목록으로 통째로 바꿈 — 모양이 틀린 줄 수 bad, View 가 [hd] 경고)
   apply(s, ev) → 새 s | 같은 s(상관없는 이벤트·깨진 이벤트 — 바뀌지 않으면 같은 객체):
     agent.hello {agent} = 그 줄(here) · agent.away {agent: id, name, reason} = 그 줄 away(모르던 id 면 이름으로 더함) · agent.progress {agent, text, screen} = 아는 id 의 진행 글(접속 중으로)
   chip(s, current) → null(받는 곳 없음·표에 없음 = 상태 모름) | {state, name, text, title} — 칩 옆 글: 접속 중이면 진행 글(없으면 '접속 중'), 아니면 '자리 비움'
   HD.presence = {initial, load, apply, chip, TEXT_MAX} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var TEXT_MAX = 40;
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

function initial() { return {agents: {}}; }
function cut(t, n) { t = String(t == null ? '' : t).replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; }
function okId(id) { return typeof id === 'string' && !!id; }
function entry(a, old) {
  var pr = a.progress && typeof a.progress.text === 'string' && a.progress.text ? {text: a.progress.text, screen: typeof a.progress.screen === 'string' ? a.progress.screen : null} : null;
  return {id: a.id, name: typeof a.name === 'string' && a.name.trim() ? a.name.trim() : (old && old.name) || a.id,
          kind: typeof a.kind === 'string' ? a.kind : (old && old.kind) || 'other', state: a.state === 'away' ? 'away' : 'here',
          progress: pr || (old && old.progress) || null};
}
function copy(s) { var o = {}, k; for (k in s.agents) if (has(s.agents, k)) o[k] = s.agents[k]; return {agents: o}; }

function load(s, body) {
  var list = body && Array.isArray(body.agents) ? body.agents : null, bad = 0, n = {agents: {}};
  if (!list) return {s: s || initial(), bad: 1};
  list.forEach(function (a) { if (a && okId(a.id)) n.agents[a.id] = entry(a, null); else bad++; });
  return {s: n, bad: bad};
}

function apply(s, ev) {
  s = s || initial();
  if (!ev || typeof ev.type !== 'string') return s;
  var n;
  if (ev.type === 'agent.hello') {
    var a = ev.agent;
    if (!a || !okId(a.id)) return s;
    n = copy(s); n.agents[a.id] = entry({id: a.id, name: a.name, kind: a.kind, state: 'here', progress: a.progress}, s.agents[a.id]);
    return n;
  }
  if (ev.type === 'agent.away') {
    if (!okId(ev.agent)) return s;
    var old = s.agents[ev.agent];
    n = copy(s); n.agents[ev.agent] = old ? {id: old.id, name: old.name, kind: old.kind, state: 'away', progress: old.progress} : entry({id: ev.agent, name: ev.name, state: 'away'}, null);
    return n;
  }
  if (ev.type === 'agent.progress') {
    if (!okId(ev.agent) || !has(s.agents, ev.agent) || typeof ev.text !== 'string' || !ev.text.trim()) return s;
    var o = s.agents[ev.agent];
    n = copy(s); n.agents[ev.agent] = {id: o.id, name: o.name, kind: o.kind, state: 'here', progress: {text: ev.text, screen: typeof ev.screen === 'string' ? ev.screen : null}};
    return n;
  }
  return s;
}

function chip(s, current) {
  var a = s && okId(current) && has(s.agents, current) ? s.agents[current] : null;
  if (!a) return null;
  var here = a.state === 'here', text = here ? (a.progress ? cut(a.progress.text, TEXT_MAX) : '접속 중') : '자리 비움';
  var title = a.name + (here ? ' — 이 캔버스에 접속해 있어요' : ' — 지금 접속해 있지 않아요') + (here && a.progress ? ' · ' + a.progress.text : '');
  return {state: here ? 'here' : 'away', name: a.name, text: text, title: title};
}

HD.presence = {initial: initial, load: load, apply: apply, chip: chip, TEXT_MAX: TEXT_MAX};
})();
