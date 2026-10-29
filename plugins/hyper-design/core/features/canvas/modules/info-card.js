/* Model — 정보 카드: 화면·묶음에 이어진 판 메모 사슬을 모으고(reach) AI 요청에 실을 글 덩어리(text)로. DOM·저장소·메시지를 쓰지 않는다.
   입력은 그냥 데이터 data = {notes: board-notes 상태 {<id>: {text, hidden?, at}}, links: board-links 상태 {<id>: {from:'note:<id>', to:'note:<id>'|'screen:<id>'|'folder:<줄 이름>'}},
     groups: {<화면 id>: <줄 이름>}(screens.json screens[].group)} — board-notes·board-links 모듈을 부르지 않는다(규칙 계약 contract/info-card.md).
   ends(data, screenId) → ['screen:S', 'folder:<S 의 줄>'?] · reach(data, ends) → [{id, text, depth, at}](바로 이어진 것 depth 1, 메모끼리 양쪽으로 depth ≤ DEPTH,
     숨긴 메모는 빼고 그 너머로도 가지 않음, 없는 끝·깨진 줄은 건너뜀, 차례 = depth → at → id) · collect(data, screenId) = reach(data, ends(…))
   para(t) → 첫 문단 한 줄(빈칸 하나로, PARA 자 넘으면 …) · text(list) → '유의(정보 카드):\n- …'(MAX 자까지, 넘으면 '…(N개 더)' 줄, 비면 '')
   forScreen(data, screenId) → text(collect(…)) — 보내기의 context 제공자 몸통 · counts(data, screenIds, groupNames) → {screens:{id:N}, folders:{이름:N}}(N>0 만, 레이어 '카드 N')
   글자 수는 코드 포인트(Python 미러 hd/hd_info_card.py 와 같은 수) — 같은 사례 파일 contract/info-card-cases.json 을 둘 다 돌린다.
   HD.infoCard = {HEAD, MAX, PARA, DEPTH, ends, reach, collect, para, text, forScreen, counts} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var HEAD = '유의(정보 카드):', MAX = 1200, PARA = 300, DEPTH = 4;
var own = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function len(s) { return Array.from(s).length; }
function cut(s, n) { var a = Array.from(s); return a.length > n ? a.slice(0, n - 1).join('') + '…' : s; }

function para(t) {
  var ps = String(t == null ? '' : t).replace(/\r\n?/g, '\n').split(/\n[ \t]*\n/);
  for (var i = 0; i < ps.length; i++) {
    var p = ps[i].replace(/\s+/g, ' ').trim();
    if (p) return cut(p, PARA);
  }
  return '';
}
function live(notes, id) {                         // 이어 볼 메모 — 있고, 숨기지 않았고, 글이 있음
  var n = own(notes, id) ? notes[id] : null;
  return isObj(n) && n.hidden !== true && !!para(n.text);
}
function noteOf(end) { return typeof end === 'string' && end.indexOf('note:') === 0 && end.length > 5 ? end.slice(5) : null; }
function edges(links) {                            // 쓸 수 있는 줄만 [{from 메모 id, to 끝}] — 모양이 틀리거나 제자리 줄은 건너뜀(저장은 그대로)
  var out = [];
  if (!isObj(links)) return out;
  Object.keys(links).forEach(function (k) {
    var l = links[k], f = isObj(l) ? noteOf(l.from) : null;
    if (f && typeof l.to === 'string' && l.to && l.to !== l.from) out.push({from: f, to: l.to});
  });
  return out;
}

function ends(data, screenId) {
  var s = String(screenId), g = data && isObj(data.groups) && own(data.groups, s) ? data.groups[s] : null, out = ['screen:' + s];
  if (typeof g === 'string' && g) out.push('folder:' + g);
  return out;
}
function reach(data, targets) {
  data = data || {};
  var notes = isObj(data.notes) ? data.notes : {}, es = edges(data.links), want = {}, seen = {}, out = [], frontier = [];
  (targets || []).forEach(function (t) { want[t] = 1; });
  es.forEach(function (e) {
    if (want[e.to] === 1 && !seen[e.from] && live(notes, e.from)) { seen[e.from] = 1; frontier.push(e.from); }
  });
  for (var d = 1; frontier.length && d <= DEPTH; d++) {
    var next = [];
    frontier.forEach(function (id) {
      var n = notes[id];
      out.push({id: id, text: para(n.text), depth: d, at: typeof n.at === 'number' && isFinite(n.at) ? n.at : 0});
      es.forEach(function (e) {                    // 메모끼리는 양쪽으로
        var to = noteOf(e.to), other = e.from === id ? to : to === id ? e.from : null;
        if (other && !seen[other] && live(notes, other)) { seen[other] = 1; next.push(other); }
      });
    });
    frontier = next;
  }
  return out.sort(function (a, b) { return a.depth - b.depth || a.at - b.at || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); });
}
function collect(data, screenId) { return reach(data, ends(data, screenId)); }

function text(list) {
  var ls = (list || []).map(function (n) { return '- ' + n.text; }), n = ls.length;
  for (var k = n; k >= 0; k--) {
    var b = [HEAD].concat(ls.slice(0, k)).join('\n') + (k < n ? '\n…(' + (n - k) + '개 더)' : '');
    if (k === 0 && n === 0) return '';
    if (len(b) <= MAX) return b;
  }
  return '';
}
function forScreen(data, screenId) { return text(collect(data, screenId)); }
function counts(data, screenIds, groupNames) {
  var out = {screens: {}, folders: {}};
  (screenIds || []).forEach(function (id) { var c = collect(data, id).length; if (c) out.screens[id] = c; });
  (groupNames || []).forEach(function (g) { var c = reach(data, ['folder:' + g]).length; if (c) out.folders[g] = c; });
  return out;
}

HD.infoCard = {HEAD: HEAD, MAX: MAX, PARA: PARA, DEPTH: DEPTH, ends: ends, reach: reach, collect: collect, para: para, text: text, forScreen: forScreen, counts: counts};
})();
