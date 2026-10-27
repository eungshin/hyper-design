/* Model — 허브 옛 코드 칩(R34): 서버 판단 hubStale {sha, since} | null → 칩에 보일 것, 다시 켠 뒤 홈 글에서 새 허브 토큰 읽기. DOM·저장소를 쓰지 않는다.
   판단은 서버 한 곳(code_stamp.hub_stale — 허브가 뜬 코드 도장 ≠ 지금 도장). 여기는 모양 검사와 글만.
   HD.hubStale.read(v) → {stale:false} | {stale:true, sha, since, label, title} | {stale:false, bad:'까닭'}(모양이 깨짐 — 칩 없음, 보는 쪽이 [hd] 경고)
     v === undefined(답에 칸이 없음 = 도우미·옛 허브) → null(모름 — 보던 것 그대로)
   HD.hubStale.when(iso) → 'MM-DD HH:MM'(켠 시각, 읽지 못하면 '')
   HD.hubStale.tokenOf(html) → 홈 글에 끼운 허브 토큰(__hdToken="…") | null
   HD.hubStale.CMD = 터미널에서 같은 일 — 'hd home --restart' */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var LABEL = '허브 옛 코드 · 다시 켜기';
var CMD = 'hd home --restart';
var SHA = /^[0-9a-f?]{1,16}$/i;
var ISO = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/;

function when(iso) {
  var m = typeof iso === 'string' ? ISO.exec(iso) : null;
  return m ? m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5] : '';
}

function read(v) {
  if (v === undefined) return null;
  if (v === null) return {stale: false};
  if (typeof v !== 'object' || Array.isArray(v)) return {stale: false, bad: 'hubStale 가 객체가 아니에요'};
  if (typeof v.sha !== 'string' || !SHA.test(v.sha)) return {stale: false, bad: 'hubStale.sha 모양이 아니에요'};
  if (v.since != null && typeof v.since !== 'string') return {stale: false, bad: 'hubStale.since 가 글이 아니에요'};
  var at = when(v.since);
  return {stale: true, sha: v.sha, since: v.since || null, label: LABEL,
          title: '허브가 옛 코드(' + v.sha + (at ? ', ' + at + ' 켬' : '') + ')로 떠 있어요 — 병합한 Python 변경이 아직 안 보여요. ' +
                 '누르면 허브를 다시 켜고 이 프로젝트를 다시 열어요(터미널: ' + CMD + ')'};
}

function tokenOf(html) {
  var m = typeof html === 'string' ? /window\.__hdToken=("(?:[^"\\]|\\.)*")/.exec(html) : null;
  if (!m) return null;
  try { var t = JSON.parse(m[1]); return typeof t === 'string' && t ? t : null; } catch (e) { return null; }
}

HD.hubStale = {read: read, when: when, tokenOf: tokenOf, CMD: CMD, LABEL: LABEL};
})();
