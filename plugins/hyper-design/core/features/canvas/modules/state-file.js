/* Model — 프로젝트 상태 파일(.hd-canvas.json) 규칙: 키 이름 ↔ 저장 키, 처음 열 때 파일·브라우저 캐시 중 무엇을 쓰나, 바뀐 키만 보낼 본문. DOM·저장소를 쓰지 않는다.
   프로젝트별 키만(hd-<이름>:<hashStr(KEYPATH)>): NAMES. 전역 설정 키(hd-dock·hd-pop·hd-canvas-prefs …)는 다루지 않는다.
   파일 상태 = {이름: 풀어 둔 JSON 값}(문자열로 감싸지 않음). 모르는 이름도 그대로 둔다(보낼 때는 바뀐 이름만).
   keyOf(name, hash) → 저장 키 · nameOf(key, hash) → 이름 | null(이 프로젝트의 NAMES 가 아니면)
   snapshot(raw) → {ok:true, rev, state} | {ok:false, why}   raw = helper 가 페이지에 끼워 넣은 __hdState({rev, state})
   fromLocal(getItem, hash) → {values:{이름: 값}, bad:[이름]}   깨진 JSON 은 bad 로(View 가 [hd] 경고)
   decide(snap, values) → 'local'(스냅숏 없음·깨짐) | 'file'(파일이 있음 = 파일이 이김, 또는 둘 다 비었음) | 'migrate'(파일 없음 + 브라우저에 값 있음 = 한 번 올리기)
   unsentKey(hash) → 쓰기 대기 표시 키 'hd-unsent:<hash>'(NAMES 가 아님 — 파일로 가지 않는다) · unsent(text) → {base, names} | null(없음·깨짐; 모르는 이름은 뺌)
     표시 = 아직 파일에 닿았다고 확인 못 한 이름들과 그 변경의 기준 rev. 300ms 안의 새로고침에서 브라우저 캐시의 값이 새것임을 boot 가 알게 한다.
   boot(snap, values, mark?) → {mode, rev, state, cache:{이름: 글|null}(캐시에 덮어쓸 것, null = 지우기), upload:[이름], lost:[이름]}
     'file' + mark: 파일 rev === mark.base 면 표시된 이름의 브라우저 값(없으면 지움)이 이기고 upload(같은 rev 로 다시 보냄 — 그 사이 닿았으면 409 규칙).
     rev 가 다르면 파일이 이긴다; 파일 값이 브라우저 값과 같으면(닫을 때 보낸 것이 닿음) 그만, 다르면 lost(View 가 [hd] 경고).
   read(state, name) → 저장 글 | null · write(state, name, text) → {ok, state(새 객체)} (JSON 이 아니면 ok:false, 상태 그대로) · drop(state, name) → 그 이름을 뺀 새 상태
   body(rev, state, names) → PUT 본문 {rev, state:{이름: 값 | null(지움)}}
   LIVE = {이름: 1} — 파일에서 바뀌면 셸이 제자리에서 다시 읽는 이름(notes·note-seq·busy), 그 밖은 다시 불러오기
   두 탭(#274) — 같은 out 을 연 탭 가운데 파일에 쓰는 탭은 하나(BroadcastChannel 'hd:'+hash 메시지 {type, id, t}):
     tabStart(id, t) → {id, t, role:'pending'} · tab(s, ev) → {s(새 객체), send: 보낼 메시지 | null}
     ev = 내 일 {type:'timeout'}(알린 뒤 답 없음) | {type:'click'}(여기서 편집하기) 또는 남의 메시지 {type:'hello'|'here'|'take', id, t}
     새 탭은 hello 를 알리고, 쓰는 탭(writer)만 here 로 답한다 → 답을 받은 새 탭은 reader(읽기만). 답이 없으면 writer 가 되어 here 를 알림.
     둘 다 writer 면(동시에 시작) here 를 받은 쪽 중 더 새 탭(t 가 크고, 같으면 id 가 큰 쪽)이 reader, 먼저 연 탭은 here 로 다시 알림. click = writer + take, take 를 받으면 reader.
   HD.stateFile = {NAMES, LIVE, keyOf, nameOf, snapshot, fromLocal, decide, boot, read, write, drop, body, tabStart, tab} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAMES = ['notes', 'card-pos', 'edit-log', 'link-names', 'hidden', 'locked', 'folders', 'busy', 'note-seq', 'card-size'];   // card-size = 카드마다 크기(task 46, modules/artboard.js)
var LIVE = {notes: 1, 'note-seq': 1, busy: 1};                // 셸이 상태에서 바로 다시 읽을 수 있는 이름(view-state-sync) — 나머지는 다시 불러오기
var has = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };

function keyOf(name, hash) { return 'hd-' + name + ':' + hash; }
function nameOf(key, hash) {
  if (typeof key !== 'string') return null;
  for (var i = 0; i < NAMES.length; i++) if (key === keyOf(NAMES[i], hash)) return NAMES[i];
  return null;
}
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function copy(o) { var r = {}; for (var k in o) if (has(o, k)) r[k] = o[k]; return r; }

function snapshot(raw) {
  if (raw == null) return {ok: false, why: 'none'};
  if (!isObj(raw)) return {ok: false, why: 'not an object'};
  if (typeof raw.rev !== 'number' || !isFinite(raw.rev) || raw.rev < 0 || Math.floor(raw.rev) !== raw.rev) return {ok: false, why: 'bad rev'};
  if (!isObj(raw.state)) return {ok: false, why: 'bad state'};
  return {ok: true, rev: raw.rev, state: copy(raw.state)};
}

function fromLocal(getItem, hash) {
  var values = {}, bad = [];
  NAMES.forEach(function (n) {
    var t = null;
    try { t = getItem(keyOf(n, hash)); } catch (e) { t = null; }
    if (t == null) return;
    try { values[n] = JSON.parse(t); } catch (e) { bad.push(n); }
  });
  return {values: values, bad: bad};
}

function decide(snap, values) {
  if (!snap || !snap.ok) return 'local';
  if (snap.rev > 0) return 'file';
  return Object.keys(values || {}).length ? 'migrate' : 'file';
}

function unsentKey(hash) { return 'hd-unsent:' + hash; }
function unsent(text) {
  if (text == null) return null;
  var o; try { o = JSON.parse(text); } catch (e) { return null; }
  if (!isObj(o) || typeof o.base !== 'number' || o.base < 0 || Math.floor(o.base) !== o.base || !Array.isArray(o.names)) return null;
  return {base: o.base, names: NAMES.filter(function (n) { return o.names.indexOf(n) >= 0; })};
}
function text(o, n) { return has(o, n) && o[n] != null ? JSON.stringify(o[n]) : null; }

function boot(snap, values, mark) {
  values = values || {};
  var mode = decide(snap, values);
  if (mode === 'local') return {mode: mode, rev: 0, state: copy(values), cache: {}, upload: [], lost: []};
  if (mode === 'migrate') return {mode: mode, rev: snap.rev, state: copy(values), cache: {}, upload: NAMES.filter(function (n) { return has(values, n); }), lost: []};
  var state = copy(snap.state), cache = {}, upload = [], lost = [];
  NAMES.forEach(function (n) { cache[n] = text(state, n); });
  (mark ? mark.names : []).forEach(function (n) {
    var mine = text(values, n);
    if (mine === cache[n]) return;                    // 이미 파일에 있음
    if (snap.rev !== mark.base) { lost.push(n); return; }   // 그 사이 파일이 움직임 = 파일이 이긴다
    if (mine == null) delete state[n]; else state[n] = values[n];
    cache[n] = mine; upload.push(n);
  });
  return {mode: mode, rev: snap.rev, state: state, cache: cache, upload: upload, lost: lost};
}

function read(state, name) { return has(state, name) && state[name] != null ? JSON.stringify(state[name]) : null; }

function write(state, name, text) {
  var v;
  try { v = JSON.parse(text); } catch (e) { return {ok: false, state: state}; }
  var n = copy(state); n[name] = v;
  return {ok: true, state: n};
}

function drop(state, name) { var n = copy(state); delete n[name]; return n; }

function body(rev, state, names) {
  var s = {};
  (names || []).forEach(function (n) { s[n] = has(state, n) ? state[n] : null; });
  return {rev: rev, state: s};
}

function tabStart(id, t) { return {id: id, t: t, role: 'pending'}; }
function tab(s, ev) {
  var me = function (role) { return {id: s.id, t: s.t, role: role}; }, say = function (type) { return {type: type, id: s.id, t: s.t}; };
  var keep = {s: me(s.role), send: null};
  if (!ev || typeof ev !== 'object') return keep;
  if (ev.type === 'timeout') return s.role === 'pending' ? {s: me('writer'), send: say('here')} : keep;
  if (ev.type === 'click') return {s: me('writer'), send: say('take')};
  if (ev.id === s.id) return keep;                         // 제 메시지
  if (ev.type === 'hello') return s.role === 'writer' ? {s: me('writer'), send: say('here')} : keep;
  if (ev.type === 'take') return {s: me('reader'), send: null};
  if (ev.type === 'here') {
    if (s.role === 'pending') return {s: me('reader'), send: null};
    if (s.role !== 'writer') return keep;
    var older = ev.t < s.t || (ev.t === s.t && String(ev.id) < String(s.id));
    return older ? {s: me('reader'), send: null} : {s: me('writer'), send: say('here')};
  }
  return keep;
}

HD.stateFile = {tabStart: tabStart, tab: tab, NAMES: NAMES, LIVE: LIVE, unsentKey: unsentKey, unsent: unsent, keyOf: keyOf, nameOf: nameOf, snapshot: snapshot, fromLocal: fromLocal, decide: decide, boot: boot, read: read, write: write, drop: drop, body: body};
})();
