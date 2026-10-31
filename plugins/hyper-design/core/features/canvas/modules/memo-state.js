/* Model — 움직이는 화면(안내 단계)의 메모 상태: 메모를 단 때의 화면 상태 적기·지금과 같은가·그 단계로 가는 차례·칩 줄 자리. DOM·저장소·메시지를 쓰지 않는다.
   메모 칸 n.view = {hd: 화면이 알린 단계 값|null, trail: 메모를 단 때까지의 클릭 경로(최근 MAX 개)} — palette.js 가 hd-picked·hd-hit 답에 싣는 view 를 capture 로 적는다.
     view 가 없는 메모(옛 palette·옛 데이터 · 단계 값도 클릭도 없이 처음 실린 화면에 단 메모)는 늘 '같음' = 지금처럼(글이 바뀌면 '요소를 찾을 수 없음').
   같은가(same): 지금 상태 now = {hd, items{키 'id:i': {now:{text, shown}}}}(hd-located 답). 메모에 hd 가 있으면 그것만 견준다(now.hd undefined = 옛 palette 라 모름 = 같음, null = 화면이 단계를 안 알림 = 다름).
     없으면 핀이 될 대상마다 지금 보이는지 + 보이는 글(textOf, 60자 — 판 hd-hit 은 40자로 잘라 적으므로 40자 이상 스냅숏은 앞부분 맞춤)이 같은가. 답이 없으면 아직 모름 = 같음.
   가기 차례(plan): 'hd'(화면 약속 함수 hdGoto) → 'replay'(화면을 다시 읽고 trail 클릭 다시 하기). 둘 다 없으면 [] = 바로 실패(FAIL 토스트).
   칩 줄(side·row): 위 줄 상자가 다른 것에 겹치면 아래, 둘 다 겹치면 위 · 한 줄에 들어갈 칩 수(넘치면 마지막 자리는 '+N').
   HD.memoState = {MAX, FAIL, capture(v) → view|null, record(trail, path) → 새 trail, same(n, now) → bool, plan(view) → ['hd'|'replay'…],
                   side(top, bottom, obstacles) → 'top'|'bottom', row(count, avail, chipW, gap) → {show, more}, preview(n) → 미리보기 글} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MAX = 30, CUT = 40, PREVIEW = 140;
var FAIL = '이 단계로 바로 갈 수 없어요 — 직접 넘겨 주세요';

function str(v) { return typeof v === 'string' && v !== ''; }
function record(trail, path) {                        // 클릭 하나 더 — palette.js 의 trail 과 같은 규칙(빈 경로 빼고 최근 MAX 개)
  var t = Array.isArray(trail) ? trail.slice() : [];
  if (str(path)) t.push(path);
  return t.length > MAX ? t.slice(t.length - MAX) : t;
}
function capture(v) {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
  var t = (Array.isArray(v.trail) ? v.trail : []).filter(str), hd = str(v.hd) ? v.hd : null;
  if (!hd && !t.length) return null;                  // 단계 값도 클릭도 없음 = 처음 실린 그대로의 화면 — 글이 바뀌면 단계가 아니라 파일이 바뀐 것(요소를 찾을 수 없음)
  return {hd: hd, trail: t.length > MAX ? t.slice(t.length - MAX) : t};
}
function norm(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function textSame(saved, now) {
  var a = norm(saved), b = norm(now);
  if (!a) return true;                                // 스냅숏이 없으면 글로는 가르지 않는다
  return a === b || (a.length >= CUT && b.indexOf(a) === 0);
}
function pinnable(t) { return !!(t && t.path && t.path !== 'body' && t.path !== '(새 화면)'); }   // HD.relocate.pinnable 과 같은 규칙
function targets(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text}]; }
function same(n, now) {
  var v = n && n.view;
  if (!v || typeof v !== 'object' || !now) return true;
  if (str(v.hd)) return now.hd === undefined ? true : now.hd === v.hd;   // undefined = 옛 palette(모름) · null = 화면이 지금 단계를 알리지 않음(아직 시작 전 등) = 다름
  var items = now.items || {};
  return targets(n).every(function (t, i) {
    var a = items[n.id + ':' + i], c = a && a.now;
    if (!pinnable(t) || !c) return true;
    return !!c.shown && textSame(t.text, c.text);
  });
}
function plan(view) {
  if (!view || typeof view !== 'object') return [];
  var out = [];
  if (str(view.hd)) out.push('hd');
  if (Array.isArray(view.trail) && view.trail.some(str)) out.push('replay');
  return out;
}
function hits(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }   // 맞닿기만 하면 겹침 아님
function side(top, bottom, obstacles) {
  var obs = (obstacles || []).filter(function (o) { return o && o.w > 0 && o.h > 0; });
  var blocked = function (b) { return obs.some(function (o) { return hits(b, o); }); };
  return blocked(top) && !blocked(bottom) ? 'bottom' : 'top';
}
function row(count, avail, chipW, gap) {
  count = Math.max(0, count | 0);
  var fit = Math.max(0, Math.floor((avail + gap) / (chipW + gap)));
  if (count <= fit) return {show: count, more: 0};
  var show = Math.max(0, fit - 1);
  return {show: show, more: count - show};
}
function preview(n) {
  var t = norm(n && n.note);
  if (t.length > PREVIEW) t = t.slice(0, PREVIEW - 1) + '…';
  return '메모 ' + (n && n.no != null ? n.no : '') + ' — ' + t;
}

HD.memoState = {MAX: MAX, FAIL: FAIL, capture: capture, record: record, same: same, plan: plan, side: side, row: row, preview: preview};
})();
