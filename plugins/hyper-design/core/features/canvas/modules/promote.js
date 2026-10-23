/* Model — 빈 레이아웃 승격(#241 R2): AI 가 만든 화면이 그 빈 레이아웃 자리를 이어받는 때(promotable)와 바뀐 상태(promote). DOM·저장소를 쓰지 않는다.
   때: 빈 레이아웃 메모(edit=new-screen)의 마지막 AI 답('확인'은 건너뜀)이 반영됨 → screens[0], 대체됨 → where 글에 든 화면 id 이고 그 화면이 지금 데이터에 있을 때.
     승격하면 그 메모는 더는 new-screen 이 아니라서 다시 걸리지 않는다(되풀이 폴링·새로고침에 한 번만). 한 화면은 한 빈 레이아웃만 이어받는다(먼저 온 것).
   promotable(notes, ids) → [{draft, screen, name}]   ids = 지금 데이터의 화면 id 배열 또는 {id: 1}
   target(n, ids) → 화면 id | null
   promote(state, draftId, screenId, place) → {state, undo, moved, name, memos, lines} | null(그 빈 레이아웃 메모 없음)
     state = {notes, cardPos, folders} — 입력은 고치지 않고 새 값을 돌려준다(undo = 입력의 사본 + 빈 레이아웃 메모에 stay = 화면:
       되돌린 승격은 폴링·새로고침에 다시 걸리지 않는다 — AI 가 다른 화면으로 다시 답하면 그때는 걸린다).
     메모: 빈 레이아웃 화면의 메모 전부 screen → 화면(번호 no·답 그대로), 빈 레이아웃 메모 자신은 edit 를 떼어 그 화면의 (완료된) 메모로 남고,
       사람 메모와 그것에 moved = {from, name} · 그리로 오는 잇기(edit=link, to=빈 레이아웃) → to = 화면(요청 글의 '(빈 id)'도).
     자리: place = {draft: {x, y}, screen: {x, y}, g}(판 좌표, 둘 다 같은 기준점) — 화면 옮긴 거리 += 빈 레이아웃 - 화면. 화면에 이미 옮긴 자리가 있어도
       빈 레이아웃 자리가 이긴다(moved = true, 알림이 말한다). place 가 없으면 자리는 그대로. 빈 레이아웃의 옮긴 거리는 지운다.
     폴더: 빈 레이아웃이 든 폴더가 있으면 그 자리(차례)에 화면이 들어가고 화면은 다른 폴더에서 빠진다. 없으면 폴더는 그대로.
   say(name, title, moved) → 알림 글 · movedSay(n) → 옮겨 온 메모 줄 글('' = 아님)
   HD.promote = {promotable, target, promote, say, movedSay} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
function clone(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
function num(v) { return typeof v === 'number' && isFinite(v); }
function idSet(ids) {
  var s = {};
  if (Array.isArray(ids)) ids.forEach(function (id) { if (typeof id === 'string' && id) s[id] = 1; });
  else if (ids && typeof ids === 'object') Object.keys(ids).forEach(function (id) { if (ids[id]) s[id] = 1; });
  return s;
}
var WORD = /[0-9A-Za-z_\-ㄱ-ㆎ가-힣]/;   // id 글자 — 이 글자가 앞뒤에 붙어 있으면 다른 id 의 일부

// 대체됨 where 글에서 데이터에 있는 화면 id(통째 글이면 그것, 아니면 앞뒤가 끊긴 가장 앞 자리의 것 — 같은 자리면 긴 것)
function whereId(where, set) {
  if (typeof where !== 'string') return null;
  var w = where.trim(); if (has(set, w)) return w;
  var best = null, at = -1;
  Object.keys(set).forEach(function (id) {
    var i = w.indexOf(id);
    while (i >= 0) {
      if (!WORD.test(w.charAt(i - 1) || ' ') && !WORD.test(w.charAt(i + id.length) || ' ')) {
        if (best === null || i < at || (i === at && id.length > best.length)) { best = id; at = i; }
        break;
      }
      i = w.indexOf(id, i + 1);
    }
  });
  return best;
}

function target(n, ids) {
  var set = idSet(ids), rs = n && Array.isArray(n.replies) ? n.replies : [];
  for (var i = rs.length - 1; i >= 0; i--) {
    var r = rs[i];
    if (!r || typeof r !== 'object' || r.kind === '확인') continue;     // 사람이 완료한 것은 그 앞 AI 답을 본다
    if (r.kind === '반영됨') { var s = Array.isArray(r.screens) ? r.screens[0] : null; return typeof s === 'string' && has(set, s) ? s : null; }
    if (r.kind === '대체됨') return whereId(r.where, set);
    return null;                                                       // 질문·일부·답변·다시 = 아직 아님
  }
  return null;
}

function promotable(notes, ids) {
  var set = idSet(ids), taken = {}, out = [];
  (notes || []).forEach(function (n) {
    if (!n || typeof n !== 'object' || n.edit !== 'new-screen' || n.screen == null) return;
    var d = String(n.screen); if (has(set, d)) return;                 // 이미 진짜 화면 id 면 빈 레이아웃이 아니다
    var s = target(n, set);
    if (!s || s === d || taken[s] || n.stay === s) return;             // stay = 사람이 이 승격을 되돌렸다 — 같은 화면으로 다시 하지 않는다
    taken[s] = 1; out.push({draft: d, screen: s, name: String(n.value == null ? '' : n.value)});
  });
  return out;
}

function promote(state, draftId, screenId, place) {
  state = state || {};
  var notes = clone(Array.isArray(state.notes) ? state.notes : []);
  var lay = null;
  notes.forEach(function (n) { if (!lay && n && n.edit === 'new-screen' && n.screen === draftId) lay = n; });
  if (!lay || !screenId || screenId === draftId) return null;
  var name = String(lay.value == null ? '' : lay.value), memos = 0, lines = 0;
  notes.forEach(function (n) {
    if (!n || typeof n !== 'object') return;
    if (n.screen === draftId) {
      if (n === lay) { delete n.edit; n.moved = {from: draftId, name: name}; }
      else if (!n.edit) { n.moved = {from: draftId, name: name}; memos++; }
      else if (n.edit === 'link') lines++;                             // 빈 레이아웃에서 나가는 잇기
      n.screen = screenId;
    }
    if (n.edit === 'link' && n.to === draftId) {                       // 빈 레이아웃으로 오는 잇기
      n.to = screenId; lines++;
      if (typeof n.note === 'string') n.note = n.note.split('(' + draftId + ')').join('(' + screenId + ')');
    }
  });

  var cardPos = clone(state.cardPos && typeof state.cardPos === 'object' ? state.cardPos : {}), had = has(cardPos, screenId);
  if (place && place.draft && place.screen && num(place.draft.x) && num(place.draft.y) && num(place.screen.x) && num(place.screen.y)) {
    var cur = cardPos[screenId] || {dx: 0, dy: 0};
    cardPos[screenId] = {dx: Math.round((+cur.dx || 0) + place.draft.x - place.screen.x), dy: Math.round((+cur.dy || 0) + place.draft.y - place.screen.y),
                         g: place.g != null ? place.g : (cur.g != null ? cur.g : '')};
  } else had = false;                                                  // 자리를 모르면 옮기지 않았으니 알릴 것도 없다
  delete cardPos[draftId];

  var folders = clone(state.folders && typeof state.folders === 'object' ? state.folders : {v: 1, folders: []});
  var fs = Array.isArray(folders.folders) ? folders.folders : [];
  var home = fs.filter(function (f) { return f && Array.isArray(f.ids) && f.ids.indexOf(draftId) >= 0; })[0];
  if (home) {
    fs.forEach(function (f) { if (f && Array.isArray(f.ids) && f !== home) f.ids = f.ids.filter(function (id) { return id !== screenId; }); });
    home.ids = home.ids.filter(function (id) { return id !== screenId; });
    home.ids = home.ids.map(function (id) { return id === draftId ? screenId : id; });
  }

  var back = clone(state.notes || []);
  back.forEach(function (n) { if (n && n.edit === 'new-screen' && n.screen === draftId) n.stay = screenId; });
  return {state: {notes: notes, cardPos: cardPos, folders: folders},
          undo: {notes: back, cardPos: clone(state.cardPos || {}), folders: clone(state.folders || {v: 1, folders: []})},
          moved: had, name: name, memos: memos, lines: lines};
}

function say(name, title, moved) {
  return "빈 레이아웃 '" + name + "' 자리에 " + title + '이 들어왔어요' + (moved ? ' — 따로 옮겨 둔 자리 대신 빈 레이아웃 자리로' : '');
}
function movedSay(n) { return n && n.moved && typeof n.moved === 'object' ? "빈 레이아웃 '" + String(n.moved.name || n.moved.from || '') + "'에서 옮겨 왔어요" : ''; }

HD.promote = {promotable: promotable, target: target, promote: promote, say: say, movedSay: movedSay};
})();
