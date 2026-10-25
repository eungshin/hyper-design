/* Model — 여러 화면에 같은 메모: 고른 카드 여러 장 → 화면 전체 메모 초안·범위 말·화면마다 메모 하나. DOM·저장소·메시지를 쓰지 않는다.
   초안 draft = {screen: 첫 화면, screens: [고른 id — 겹침·빈 값 빼고 차례 그대로], titles: [그 제목], targets: [{path:'body', text: 첫 제목, rect:null}]}
     (한 장이면 셸 openCardMemo 의 초안과 같은 모양 + screens·titles). 고른 카드가 없으면 null.
   범위: 여러 장이면 '이 요소'는 없다(화면 전체 메모) — scopes 가 빼고 '이 화면' 말을 '고른 화면 N개'로 바꾼다. 기본 = screen.
   build(draft, {note, intent, scope}, mkId) → 메모 목록 — 셸이 NS.add 로 하나씩 넣는다:
     여러 장 + 범위 screen(또는 element) = 화면마다 메모 하나, 같은 batch = mkId() · 각자 screen=… · no=N 으로 나가 hd claim/reply 흐름 그대로.
     범위 all = 첫 화면에 메모 하나(모든 화면 요청이 여러 번 나가지 않게). 한 장 = 지금 메모와 같은 모양(batch 없음, 이 요소 = scope 칸 없음).
   HD.memoBatch = {draft(ids, titleOf), multi(draft), scopes(draft, SCOPES), defaultScope(draft), label(draft), build(draft, input, mkId)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function draft(ids, titleOf) {
  var seen = {}, screens = [];
  (ids || []).forEach(function (id) { if (id == null || id === '') return; id = String(id); if (!seen[id]) { seen[id] = 1; screens.push(id); } });
  if (!screens.length) return null;
  var titles = screens.map(function (id) { var t = titleOf ? titleOf(id) : id; return t == null || t === '' ? id : String(t); });
  return {screen: screens[0], screens: screens, titles: titles, targets: [{path: 'body', text: titles[0], rect: null}]};
}
function multi(d) { return !!(d && d.screens && d.screens.length > 1); }
function scopes(d, SCOPES) {
  if (!multi(d)) return SCOPES.slice();
  return SCOPES.filter(function (s) { return s[0] !== 'element'; })
               .map(function (s) { return s[0] === 'screen' ? ['screen', '고른 화면 ' + d.screens.length + '개'] : s; });
}
function defaultScope() { return 'screen'; }
function label(d) {
  if (!d) return '';
  return multi(d) ? '고른 화면 ' + d.screens.length + '개 — ' + d.titles.join(' · ') : d.titles[0] + ' — 화면 전체';
}
function memo(id, screen, title, input) {
  var m = {id: id, screen: screen, targets: [{path: 'body', text: title, rect: null}], path: 'body', text: title, rect: null,
           note: input.note, intent: input.intent, sent: false};
  return m;
}
function build(d, input, mkId) {
  if (!d) return [];
  var sc = input.scope;
  if (!multi(d) || sc === 'all') {
    var one = memo(mkId(), d.screen, d.titles[0], input);
    if (sc && sc !== 'element') one.scope = sc;
    return [one];
  }
  var batch = mkId();
  return d.screens.map(function (id, i) { var m = memo(mkId(), id, d.titles[i], input); m.scope = 'screen'; m.batch = batch; return m; });
}

HD.memoBatch = {draft: draft, multi: multi, scopes: scopes, defaultScope: defaultScope, label: label, build: build};
})();
