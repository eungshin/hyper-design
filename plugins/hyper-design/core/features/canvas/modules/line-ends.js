/* Model — 선 끝 손잡이(Q3) 순수 기하. DOM 을 쓰지 않는다.
   ends(d) → {start:[x,y], end:[x,y]}: SVG path d 의 첫 점과 마지막 점(M·L·H·V·C·S·Q·T·A·Z, 절대·상대 모두)
   handles(line) → [{from, to, at:[x,y]}]: line = {from, to, both, plan, d} — 도착 끝(end)에 from→to 하나,
                   양방향이면 시작 끝(start)에 to→from 하나 더, 기획 갈래(plan)는 [](진짜 연결이 아니다)
   dropTarget(boxes, pt, line) → {id} | {blocked: 'del'} | null: boxes = [{id, x, y, w, h, hid, del}](판 좌표),
                   위에 그려진(배열 뒤쪽) 카드 우선 · 숨긴 카드는 없는 셈 · 빈 곳·출발 카드·지금 도착 카드 = null · 삭제 대기 = blocked
   HD.lineEnds = {ends, handles, dropTarget} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ARGS = {M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7, Z: 0};

function ends(d) {
  var toks = String(d || '').match(/[a-zA-Z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g) || [];
  var i = 0, cmd = null, cur = [0, 0], sub = [0, 0], start = null;
  while (i < toks.length) {
    if (/[a-zA-Z]/.test(toks[i])) cmd = toks[i++];
    else if (!cmd) { i++; continue; }
    var up = cmd.toUpperCase(), rel = cmd !== up, n = ARGS[up];
    if (n == null) { cmd = null; continue; }        // 모르는 명령은 건너뛴다
    if (up === 'Z') { cur = [sub[0], sub[1]]; cmd = null; continue; }
    if (i + n > toks.length) break;
    var a = toks.slice(i, i + n).map(Number); i += n;
    var bx = rel ? cur[0] : 0, by = rel ? cur[1] : 0;
    if (up === 'H') cur = [a[0] + bx, cur[1]];
    else if (up === 'V') cur = [cur[0], a[0] + by];
    else cur = [a[n - 2] + bx, a[n - 1] + by];     // 나머지는 끝 두 수가 도착점
    if (up === 'M') { sub = [cur[0], cur[1]]; cmd = rel ? 'l' : 'L'; }   // M 뒤 이어진 수 = 선
    if (!start) start = [cur[0], cur[1]];
  }
  return {start: start || [0, 0], end: [cur[0], cur[1]]};
}

function handles(line) {
  if (!line || line.plan) return [];
  var e = ends(line.d), out = [{from: line.from, to: line.to, at: e.end}];
  if (line.both) out.push({from: line.to, to: line.from, at: e.start});
  return out;
}

function dropTarget(boxes, pt, line) {
  var px = pt[0], py = pt[1], hit = null;
  (boxes || []).forEach(function (b) {
    if (b.hid) return;                              // 숨긴 카드 = display:none, 놓을 수 없다
    if (b.x <= px && px <= b.x + b.w && b.y <= py && py <= b.y + b.h) hit = b;   // 겹치면 나중(위) 것
  });
  if (!hit || hit.id === line.from || hit.id === line.to) return null;
  if (hit.del) return {blocked: 'del'};
  return {id: hit.id};
}

HD.lineEnds = {ends: ends, handles: handles, dropTarget: dropTarget};
})();
