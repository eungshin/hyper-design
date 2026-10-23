/* Model — 프로젝트 상태 파일(.hd-canvas.json) 규칙: 키 이름 ↔ 저장 키, 처음 열 때 파일·브라우저 캐시 중 무엇을 쓰나, 바뀐 키만 보낼 본문. DOM·저장소를 쓰지 않는다.
   프로젝트별 키만(hd-<이름>:<hashStr(KEYPATH)>): NAMES. 전역 설정 키(hd-dock·hd-pop·hd-canvas-prefs …)는 다루지 않는다.
   파일 상태 = {이름: 풀어 둔 JSON 값}(문자열로 감싸지 않음). 모르는 이름도 그대로 둔다(보낼 때는 바뀐 이름만).
   keyOf(name, hash) → 저장 키 · nameOf(key, hash) → 이름 | null(이 프로젝트의 NAMES 가 아니면)
   snapshot(raw) → {ok:true, rev, state} | {ok:false, why}   raw = helper 가 페이지에 끼워 넣은 __hdState({rev, state})
   fromLocal(getItem, hash) → {values:{이름: 값}, bad:[이름]}   깨진 JSON 은 bad 로(View 가 [hd] 경고)
   decide(snap, values) → 'local'(스냅숏 없음·깨짐) | 'file'(파일이 있음 = 파일이 이김, 또는 둘 다 비었음) | 'migrate'(파일 없음 + 브라우저에 값 있음 = 한 번 올리기)
   boot(snap, values) → {mode, rev, state, cache:{이름: 글|null}(캐시에 덮어쓸 것, null = 지우기), upload:[이름]}
   read(state, name) → 저장 글 | null · write(state, name, text) → {ok, state(새 객체)} (JSON 이 아니면 ok:false, 상태 그대로) · drop(state, name) → 그 이름을 뺀 새 상태
   body(rev, state, names) → PUT 본문 {rev, state:{이름: 값 | null(지움)}}
   HD.stateFile = {NAMES, keyOf, nameOf, snapshot, fromLocal, decide, boot, read, write, drop, body} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAMES = ['notes', 'card-pos', 'edit-log', 'link-names', 'hidden', 'locked', 'folders', 'busy', 'note-seq'];
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

function boot(snap, values) {
  values = values || {};
  var mode = decide(snap, values);
  if (mode === 'local') return {mode: mode, rev: 0, state: copy(values), cache: {}, upload: []};
  if (mode === 'migrate') return {mode: mode, rev: snap.rev, state: copy(values), cache: {}, upload: NAMES.filter(function (n) { return has(values, n); })};
  var cache = {};
  NAMES.forEach(function (n) { cache[n] = has(snap.state, n) && snap.state[n] != null ? JSON.stringify(snap.state[n]) : null; });
  return {mode: mode, rev: snap.rev, state: copy(snap.state), cache: cache, upload: []};
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

HD.stateFile = {NAMES: NAMES, keyOf: keyOf, nameOf: nameOf, snapshot: snapshot, fromLocal: fromLocal, decide: decide, boot: boot, read: read, write: write, drop: drop, body: body};
})();
