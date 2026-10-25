/* Model — "AI 수정 중" 상태 칩 상태(Q2b, D14 · #254 hd claim)와 화면 파일이 바뀐 카드 중 무엇을 다시 실을지. DOM·저장소를 쓰지 않는다(저장은 넘겨받은 getItem/setItem 으로).
   상태 = {v: 1, items: {<화면 id>: {via: 'paseo'|'queue'|'cli', since: ms, file: out 기준 화면 파일, mtime: 기준 시각|null, by?, note?}}}
   via 'cli' = 터미널 에이전트가 `hd claim` 으로 직접 씌운 덮개(도우미가 상태 파일에 씀 — by = 에이전트 id, note = 하는 일 한 줄).
   끝 신호 = 화면 파일 mtime 이 덮개를 씌울 때 잡은 기준(mtime)보다 커짐. 기준이 null 이면 걷히지 않는다(손으로 걷기).
   reduce(state, a) → 새 상태(바뀐 게 없으면 같은 객체):
     mark{screens:[{id, file}], via, now}  덮개 더하기·덮어쓰기(mtime null = 기준 아직)
     baseline{mtimes:{file: number|null}}   null 기준 채우기
     seen{mtimes:{file: number|null}}       기준보다 새 mtime 인 것 걷기
     lift{id}                               하나 걷기
     here{id, kind, at, first?}             그 카드 화면이 새로 실림·바뀜 — shouldLift 이면 걷기(#272 앱 카드)
   load(getItem, key, warn?) → 상태(깨졌거나 판이 다르면 initial(), warn 이 있으면 '[hd] …' 한 줄) · save(state, setItem, key) 던지지 않음 · files(state) → 겹치지 않는 파일 목록
   label(item) → 상태 글 전체(cli: by·note 가 있으면 그것까지)
   look(item) → {kind: 'working'|'queued', text, title} — 상태 칩 모양(화면을 가리지 않는 작은 칩, task 37).
     paseo·cli = working(도는 표시 + 짧은 글, cli 는 label 을 MAX 자로 줄임) · queue = queued("대기열", 아무도 읽지 않음) · title = label 전체 + 걷히는 때
   refresh(changed, opt) → {cards:[id], modal: bool} — 도우미가 알린 바뀐 화면 중 다시 실을 것.
     opt = {known: [id](판에 있는 카드), busy: 상태(덮개가 있는 카드는 걷는 길이 다시 싣는다), skip: {id: 그때까지 ms}(방금 판이 스스로 쓴·다시 실은 것), now: ms, modal: 크게 보기 화면 id|null}
   isApp(file) → 앱 카드인가(file 이 http(s) 개발 서버 주소 — mtime 이 없어 파일 규칙으로는 걷히지 않는다)
   shouldLift(item, event) → bool(#272) — 앱 카드 덮개를 걷는 신호. event = {kind: 'hmr'|'load', at: ms(판이 받은 시각), first?: 이 판에서 그 카드의 첫 로드}
     앱 카드만 · at > item.since 일 때만 · hmr(개발 서버가 그 페이지를 바꿈) = 걷기 · load = 첫 로드가 아니면 걷기(판 새로 고침·처음 보임은 AI 수정이 아님)
   hereError(seen, d) → {seen(새 객체), show: 글|null, clear: bool} — 앱 카드 iframe 의 hd-here {error}(감싸개가 비공개 모듈을 못 읽음, #280).
     seen = {화면 id: 지금 보인 글}. 같은 카드·같은 글이면 show null(한 번만) · 글은 공백 정리 + ERR_MAX 자(넘으면 …) · error 없는 hd-here(다시 잘 실림) = 그 카드 clear
   lookDone() → {kind: 'done', text: '방금 반영됨 ✓', title} — 덮개가 걷힌 카드의 새 화면이 판에 반영된 뒤 DONE_MS 동안 보이는 칩(48a)
   landed(rec, ev) → {rec(새 객체), show: bool} — rec = {화면 id: 걷힌 시각}. ev = {type: 'lifted', ids, at}(파일이 바뀌어 걷힘 — 손 걷기 × 는 넣지 않는다)
     | {type: 'swapped', id, at}(그 카드 교체가 끝남 — 걷힌 지 LANDED_WAIT 안이면 show, 그 id 는 지움)
   HD.busy = {VIA, MAX, ERR_MAX, DONE_MS, LANDED_WAIT, initial, reduce, load, save, files, label, look, lookDone, landed, refresh, isApp, shouldLift, hereError} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var VIA = ['paseo', 'queue', 'cli'];
var MAX = 24;                                          // 칩 글 최대 글자(넘으면 … — 전체는 title)
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

function initial() { return {v: 1, items: {}}; }
function num(x) { return typeof x === 'number' && isFinite(x); }
function copy(items) { var o = {}; for (var k in items) if (has(items, k)) o[k] = items[k]; return o; }
function extra(it, src) {                             // cli 덮개의 by·note 는 그대로 옮긴다(글일 때만)
  if (typeof src.by === 'string' && src.by) it.by = src.by;
  if (typeof src.note === 'string' && src.note) it.note = src.note;
  return it;
}

function reduce(s, a) {
  if (!a || !s || !s.items) return s;
  var items, changed = false, k, it, m;
  if (a.type === 'mark') {
    if (VIA.indexOf(a.via) < 0 || !Array.isArray(a.screens)) return s;
    items = copy(s.items);
    a.screens.forEach(function (sc) {
      if (!sc || typeof sc.id !== 'string' || !sc.id || typeof sc.file !== 'string' || !sc.file) return;
      items[sc.id] = {via: a.via, since: num(a.now) ? a.now : 0, file: sc.file, mtime: null};
      changed = true;
    });
    return changed ? {v: 1, items: items} : s;
  }
  if (a.type === 'baseline' || a.type === 'seen') {
    m = a.mtimes || {}; items = copy(s.items);
    for (k in items) {
      it = items[k];
      if (!has(m, it.file) || !num(m[it.file])) continue;
      if (a.type === 'baseline' && it.mtime == null) {
        items[k] = extra({via: it.via, since: it.since, file: it.file, mtime: m[it.file]}, it); changed = true;
      } else if (a.type === 'seen' && num(it.mtime) && m[it.file] > it.mtime) {
        delete items[k]; changed = true;
      }
    }
    return changed ? {v: 1, items: items} : s;
  }
  if (a.type === 'here') {
    if (!has(s.items, a.id) || !shouldLift(s.items[a.id], a)) return s;
    items = copy(s.items); delete items[a.id];
    return {v: 1, items: items};
  }
  if (a.type === 'lift') {
    if (!has(s.items, a.id)) return s;
    items = copy(s.items); delete items[a.id];
    return {v: 1, items: items};
  }
  return s;
}

function isApp(file) { return typeof file === 'string' && /^https?:\/\//i.test(file); }
function shouldLift(it, ev) {
  if (!it || !ev || !isApp(it.file) || !num(ev.at) || !(ev.at > (num(it.since) ? it.since : 0))) return false;
  if (ev.kind === 'hmr') return true;
  if (ev.kind === 'load') return !ev.first;
  return false;
}

var ERR_MAX = 200;
function hereError(seen, d) {
  var cur = seen && typeof seen === 'object' ? seen : {}, none = {seen: cur, show: null, clear: false};
  if (!d || d.type !== 'hd-here' || typeof d.screen !== 'string' || !d.screen) return none;
  var id = d.screen, next;
  if (d.error == null) {
    if (!has(cur, id)) return none;
    next = copy(cur); delete next[id];
    return {seen: next, show: null, clear: true};
  }
  if (typeof d.error !== 'string') return none;
  var t = d.error.replace(/\s+/g, ' ').trim(), cut = Array.from(t);
  if (!t) return none;
  if (cut.length > ERR_MAX) t = cut.slice(0, ERR_MAX - 1).join('').trim() + '…';
  if (cur[id] === t) return none;
  next = copy(cur); next[id] = t;
  return {seen: next, show: t, clear: false};
}

function load(getItem, key, warn) {
  var raw, d, items = {}, k, it;
  function bad(why) { if (warn) warn('[hd] 덮개 상태(busy)가 깨져 비웠어요: ' + why); return initial(); }
  try { raw = getItem(key); } catch (e) { return initial(); }   // 저장소를 못 읽음 = 덮개 없음(판은 그대로)
  if (raw == null || raw === '') return initial();
  try { d = JSON.parse(raw); } catch (e) { return bad('JSON 아님'); }
  if (!d || typeof d !== 'object' || d.v !== 1 || !d.items || typeof d.items !== 'object' || Array.isArray(d.items)) return bad('모양이 다름');
  for (k in d.items) {
    if (!has(d.items, k)) continue;
    it = d.items[k];
    if (!it || VIA.indexOf(it.via) < 0 || typeof it.file !== 'string' || !it.file) { if (warn) warn('[hd] 덮개 항목이 깨져 건너뛰어요: ' + k); continue; }
    items[k] = extra({via: it.via, since: num(it.since) ? it.since : 0, file: it.file, mtime: num(it.mtime) ? it.mtime : null}, it);
  }
  return {v: 1, items: items};
}
function save(s, setItem, key) {
  try { setItem(key, JSON.stringify(s)); } catch (e) { /* 저장소가 막혀도 판은 그대로 */ }
}
function files(s) {
  var out = [], k;
  for (k in (s && s.items) || {}) if (out.indexOf(s.items[k].file) < 0) out.push(s.items[k].file);
  return out;
}
function label(it) {
  if (!it) return '';
  if (it.via === 'queue') return '대기열에 있음';
  if (it.via === 'cli') {
    var who = it.by ? it.by + ' 수정 중' : 'AI 수정 중';
    return it.note ? who + ' · ' + it.note : who;
  }
  return 'AI 수정 중';
}

function look(it) {
  if (!it) return null;
  var full = label(it);
  if (it.via === 'queue') return {kind: 'queued', text: '대기열', title: full + ' — AI 터미널이 받지 않아 대기열 파일에만 있어요(× = 지우기)'};
  var t = full.replace(/\s+/g, ' ').trim(), cut = Array.from(t);
  if (cut.length > MAX) t = cut.slice(0, MAX - 1).join('').trim() + '…';
  return {kind: 'working', text: t, title: full + ' — 화면 파일이 바뀌면 사라져요(× = 지우기)'};
}

var DONE_MS = 2000, LANDED_WAIT = 10 * 60 * 1000;    // 미룬 교체(알약)는 사용자가 손을 뗄 때까지 — 넉넉히
function lookDone() { return {kind: 'done', text: '방금 반영됨 ✓', title: 'AI 수정이 이 카드에 반영됐어요'}; }
function landed(rec, ev) {
  var cur = rec && typeof rec === 'object' ? rec : {}, next;
  if (!ev) return {rec: cur, show: false};
  if (ev.type === 'lifted' && Array.isArray(ev.ids) && num(ev.at)) {
    next = copy(cur);
    ev.ids.forEach(function (id) { if (typeof id === 'string' && id) next[id] = ev.at; });
    return {rec: next, show: false};
  }
  if (ev.type === 'swapped' && has(cur, ev.id) && num(ev.at)) {
    next = copy(cur); delete next[ev.id];
    return {rec: next, show: num(cur[ev.id]) && ev.at - cur[ev.id] <= LANDED_WAIT};
  }
  return {rec: cur, show: false};
}

function refresh(changed, opt) {
  opt = opt || {};
  var known = {}, cards = [], skip = opt.skip || {}, now = num(opt.now) ? opt.now : 0, items = (opt.busy && opt.busy.items) || {};
  (opt.known || []).forEach(function (id) { known[id] = 1; });
  function skipped(id) { return has(skip, id) && num(skip[id]) && skip[id] >= now; }
  var modal = false;
  (Array.isArray(changed) ? changed : []).forEach(function (id) {
    if (typeof id !== 'string' || skipped(id)) return;
    if (id === opt.modal) modal = true;
    if (!known[id] || has(items, id) || cards.indexOf(id) >= 0) return;
    cards.push(id);
  });
  return {cards: cards, modal: modal};
}

HD.busy = {VIA: VIA, MAX: MAX, initial: initial, reduce: reduce, load: load, save: save, files: files, label: label, look: look, refresh: refresh, isApp: isApp, shouldLift: shouldLift, ERR_MAX: ERR_MAX, hereError: hereError,
           DONE_MS: DONE_MS, LANDED_WAIT: LANDED_WAIT, lookDone: lookDone, landed: landed};
})();
