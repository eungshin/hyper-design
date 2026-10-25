/* Model — 스며드는 교체(48a): 화면 파일이 바뀐 카드를 지금 바꿀지·미룰지·바로 바꿀지와 교체 작업 차례. DOM·저장소를 쓰지 않는다.
   plan(frame{live}) → 'preload'(실린 카드 = 숨긴 두 번째 iframe 에 미리 싣기) | 'lazy'(안 실린 카드 = 옛 길: data-src 로 두고 보일 때 싣기)
   touching(id, sig) → bool — 사용자가 지금 그 카드를 만지는 중. sig = {moving:[id](끄는 카드), memo: id|null(메모 창 대상),
     edit: id|null(화면 글자 고치기 칸), caption:[id](카드 이름·설명 고치기), modal: id|null(크게 보기 화면)}. 깨진 신호 = false(교체가 막히지 않게)
   next(job, sig{touching, reduced}) → 'wait'(아직 싣는 중) | 'defer'(알약 · 손 뺏지 않기) | 'instant'(움직임 줄이기) | 'fade'(FADE_MS 겹쳐 바꿈)
   상태 = {seq, jobs: {id: {seq, url, phase: 'loading'|'ready'}}} — 카드마다 지금 교체 하나. 새 start 가 오면 앞 것은 낡음(늦은 load 무시)
   reduce(s, a) → 새 상태(바뀐 게 없으면 같은 객체): start{id, url} · ready{id, seq} · end{id, seq}(끝남·실패·취소 — seq 가 지금 것일 때만)
   current(s, id, seq) → bool · pending(s) → [id] · initial()
   failed(nav{status?, timedOut?}) → 이유 글|null(시간 초과 · HTTP 4xx/5xx) · errorText(이유) → 카드 실패 줄 글
   boardUrl(u) → 판 카드 주소(?hd-mode=board — 셸 boardSrc 와 같은 규칙, contract/board-motion.md)
   flash(diff{changed, added, many}, reduced) → {outline:[i], rise:[i]} | null — 바뀐 곳 강조 계획(48b, diff = HD.swapDiff.diff). 움직임 줄이기 · many · 강조할 것 없음 = null
   FLASH = {OUTLINE, OUTLINE_END, OUTLINE_HOLD, OUTLINE_MS, RISE_MS, RISE_PX, AFTER_LOAD} — Stitch 값(외곽선 2px, OUTLINE_HOLD 동안 보인 뒤 0.4초 사라짐 · 새 요소 0.3초 ease 로 6px 아래에서 떠오름).
     AFTER_LOAD = 새 틀 load 뒤 강조를 시작하는 가장 이른 때(판 모드 palette.js 가 load+500ms 에 움직임을 끝내 버리므로 그 뒤 — contract/board-motion.md)
   HD.swap = {FADE_MS, LOAD_MS, PILL, FLASH, flash, plan, touching, next, initial, reduce, current, pending, failed, errorText, boardUrl} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var FADE_MS = 200, LOAD_MS = 10000, PILL = '새 버전 준비됨 · 반영';
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };

var FLASH = {OUTLINE: '2px solid rgba(96,86,240,.5)', OUTLINE_END: '2px solid rgba(96,86,240,0)', OUTLINE_HOLD: 600, OUTLINE_MS: 400, RISE_MS: 300, RISE_PX: 6, AFTER_LOAD: 600};
function flash(d, reduced) {
  if (reduced || !d || d.many) return null;
  var o = Array.isArray(d.changed) ? d.changed.slice() : [], r = Array.isArray(d.added) ? d.added.slice() : [];
  return o.length || r.length ? {outline: o, rise: r} : null;
}

function plan(f) { return f && f.live === true ? 'preload' : 'lazy'; }

function touching(id, sig) {
  if (typeof id !== 'string' || !id || !sig || typeof sig !== 'object') return false;
  function inList(l) { return Array.isArray(l) && l.indexOf(id) >= 0; }
  return inList(sig.moving) || inList(sig.caption) || sig.memo === id || sig.edit === id || sig.modal === id;
}

function next(job, sig) {
  if (!job || job.phase !== 'ready') return 'wait';
  sig = sig || {};
  if (sig.touching) return 'defer';
  return sig.reduced ? 'instant' : 'fade';
}

function initial() { return {seq: 0, jobs: {}}; }
function copy(o) { var n = {}, k; for (k in o) if (has(o, k)) n[k] = o[k]; return n; }
function reduce(s, a) {
  if (!s || !s.jobs || !a || typeof a.id !== 'string' || !a.id) return s;
  var jobs, j = has(s.jobs, a.id) ? s.jobs[a.id] : null;
  if (a.type === 'start') {
    if (typeof a.url !== 'string' || !a.url) return s;
    jobs = copy(s.jobs); jobs[a.id] = {seq: s.seq + 1, url: a.url, phase: 'loading'};
    return {seq: s.seq + 1, jobs: jobs};
  }
  if (!j || j.seq !== a.seq) return s;                // 낡은 교체의 신호 = 무시
  if (a.type === 'ready') {
    if (j.phase === 'ready') return s;
    jobs = copy(s.jobs); jobs[a.id] = {seq: j.seq, url: j.url, phase: 'ready'};
    return {seq: s.seq, jobs: jobs};
  }
  if (a.type === 'end') { jobs = copy(s.jobs); delete jobs[a.id]; return {seq: s.seq, jobs: jobs}; }
  return s;
}
function current(s, id, seq) { return !!s && has(s.jobs, id) && s.jobs[id].seq === seq; }
function pending(s) { return s && s.jobs ? Object.keys(s.jobs) : []; }

function failed(nav) {
  if (!nav) return null;
  if (nav.timedOut) return '시간 초과';
  if (typeof nav.status === 'number' && nav.status >= 400) return 'HTTP ' + nav.status;
  return null;
}
function errorText(why) { return '새 버전을 싣지 못했어요(' + why + ') — 옛 화면을 그대로 둬요'; }

function boardUrl(u) {
  var i = u.indexOf('#'), h = i < 0 ? '' : u.slice(i); u = i < 0 ? u : u.slice(0, i);
  return u + (u.indexOf('?') < 0 ? '?' : '&') + 'hd-mode=board' + h;
}

HD.swap = {FADE_MS: FADE_MS, LOAD_MS: LOAD_MS, PILL: PILL, FLASH: FLASH, flash: flash, plan: plan, touching: touching, next: next, initial: initial, reduce: reduce,
           current: current, pending: pending, failed: failed, errorText: errorText, boardUrl: boardUrl};
})();
