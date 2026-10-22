/* ViewModel — 오른쪽 패널 도크 배치(포토샵 오른쪽 창처럼). DOM·저장소·메시지를 쓰지 않는다.
   상태 = {v:1, w:220..560, collapsed:bool, groups:[{tabs:[패널…], active:패널, h:무게}],
          floats:[{tabs, active, x, y, w, h}], closed:[패널…], tools:bool, hint:bool, bare:bool}
     tools·hint = 창 메뉴의 도구 막대·판 아래 안내 보이기(H4 — 작업 공간 상태라 여기, §8-1).
     bare = 패널 모두 숨기기(Tab) — 저장하지 않는다(새로 열면 늘 보임).
     묶음(group) = 도크 안에 위아래로 쌓인 창 하나, 머리에 탭이 여럿. h 는 묶음끼리 나누는 높이 무게(합은 상관없음).
     떠 있는 창(float) = 판 위에 따로 뜬 창(x·y·w·h 는 판 기준 px). 목록 끝이 맨 위.
     모든 패널은 groups·floats 의 탭이나 closed 중 정확히 한 곳에 있다(normalize 가 지킨다).
   의도(action) → 새 상태(reduce, 원래 상태는 건드리지 않음):
     activate{id}        그 탭을 앞으로(닫혀 있으면 마지막 묶음에 다시 열고 도크를 편다, 떠 있는 창이면 맨 위로)
     close{id}           탭 닫기(빈 묶음·빈 떠 있는 창은 없어진다)
     move{id, to, at?}   탭 끌기: to = 묶음 번호 → 그 묶음에 합치기(at = 탭 자리), to = 'new' → at 번째 자리에 새 묶음으로 떼기,
                         to = 'float' → x·y 에 떠 있는 창으로 빼기(fi 가 있으면 그 떠 있는 창에 합치기)
     float{fi, x?, y?, w?, h?}  떠 있는 창 옮기기·크기(최소 200×120)
     width{w} · heights{hs} · collapse{on}
     chrome{part: 'tools'|'hint', on} · bare{on} · reset(작업 영역 기본으로)
   키 hd-dock(모든 캔버스 공용 — 작업 공간 배치라 화면 묶음과 상관없다). 저장소 함수는 밖에서 받는다.
   HD.dock = {KEY, PANELS, LABEL, defaults, normalize, reduce, visible, load, save} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEY = 'hd-dock', V = 1, W_MIN = 220, W_MAX = 560, W0 = 300, FW = 280, FH = 320, FW_MIN = 200, FH_MIN = 120;
var PANELS = ['links', 'show', 'align', 'notes', 'pending', 'history', 'layers', 'theme'];
var CLOSED0 = ['theme'];                          // 처음엔 닫힌 패널(창 메뉴로 켬)
var HOME = {align: 'show'};                       // 나중에 생긴 패널: 예전 저장 상태에 없으면 이 패널 옆에(없으면 마지막 묶음)
var LABEL = {links: '연결', show: '표시', notes: '메모', pending: '반영 대기', history: '기록', layers: '레이어', theme: '테마', align: '정렬'};

function defaults() {
  return {v: V, w: W0, collapsed: false, closed: CLOSED0.slice(), floats: [], tools: true, hint: true, bare: false,
          groups: [{tabs: ['links'], active: 'links', h: 1.4}, {tabs: ['show', 'align'], active: 'show', h: 0.6}, {tabs: ['notes', 'pending', 'history', 'layers'], active: 'notes', h: 1.2}]};   // 범례 줄과 선 색을 함께 보게 따로
}
function clampW(w) { return typeof w === 'number' && isFinite(w) ? Math.round(Math.max(W_MIN, Math.min(W_MAX, w))) : W0; }
function okH(h) { return typeof h === 'number' && isFinite(h) && h > 0 ? h : 1; }
function num(v, d) { return typeof v === 'number' && isFinite(v) ? Math.round(v) : d; }
function fbox(f) {
  return {tabs: f.tabs.slice(), active: f.active, x: num(f.x, 40), y: num(f.y, 40),
          w: Math.max(FW_MIN, num(f.w, FW)), h: Math.max(FH_MIN, num(f.h, FH))};
}
function copy(s) {
  return {v: V, w: s.w, collapsed: s.collapsed, closed: s.closed.slice(), tools: s.tools !== false, hint: s.hint !== false, bare: !!s.bare,
          groups: s.groups.map(function (g) { return {tabs: g.tabs.slice(), active: g.active, h: g.h}; }),
          floats: (s.floats || []).map(fbox)};
}
// 빈 묶음·빈 떠 있는 창 지우기 · 활성 탭이 그 안에 있게
function tidy(s) {
  var fix = function (g) { if (g.tabs.indexOf(g.active) < 0) g.active = g.tabs[0]; };
  s.groups = s.groups.filter(function (g) { return g.tabs.length; }); s.groups.forEach(fix);
  s.floats = s.floats.filter(function (g) { return g.tabs.length; }); s.floats.forEach(fix);
  return s;
}
// 아무 객체 → 올바른 도크 상태(모르는 패널·겹친 패널은 버리고, 빠진 패널은 마지막 묶음에)
function normalize(o) {
  if (!o || typeof o !== 'object' || !Array.isArray(o.groups)) return defaults();
  var seen = {}, s = {v: V, w: clampW(o.w), collapsed: o.collapsed === true, groups: [], floats: [], closed: [],
                      tools: o.tools !== false, hint: o.hint !== false, bare: false};
  var take = function (p) { if (PANELS.indexOf(p) < 0 || seen[p]) return false; seen[p] = 1; return true; };
  var old = function (t) { return t.map(function (p) { return p === 'hidden' ? 'layers' : p; }); };   // 조각 4: 숨긴 화면 패널 → 레이어(H7)
  o.groups.forEach(function (g) {
    if (!g || !Array.isArray(g.tabs)) return;
    var tabs = old(g.tabs).filter(take);
    if (tabs.length) s.groups.push({tabs: tabs, active: g.active === 'hidden' ? 'layers' : g.active, h: okH(g.h)});
  });
  (Array.isArray(o.floats) ? o.floats : []).forEach(function (g) {
    if (!g || !Array.isArray(g.tabs)) return;
    var tabs = old(g.tabs).filter(take);
    if (tabs.length) s.floats.push(fbox({tabs: tabs, active: g.active, x: g.x, y: g.y, w: g.w, h: g.h}));
  });
  old(Array.isArray(o.closed) ? o.closed : []).forEach(function (p) { if (take(p)) s.closed.push(p); });
  CLOSED0.forEach(function (p) { if (!seen[p]) { seen[p] = 1; s.closed.push(p); } });   // 새로 생긴 기본 닫힘 패널은 닫힌 채로
  var miss = PANELS.filter(function (p) { return !seen[p]; }).filter(function (p) {
    var f = HOME[p] ? find(s, HOME[p]) : null; if (!f) return true;
    f.box.tabs.splice(f.box.tabs.indexOf(HOME[p]) + 1, 0, p); return false;
  });
  if (miss.length) {
    if (!s.groups.length) s.groups.push({tabs: [], active: null, h: 1});
    var last = s.groups[s.groups.length - 1]; last.tabs = last.tabs.concat(miss);
  }
  return tidy(s);
}
// 패널이 든 곳 → 그 묶음(또는 떠 있는 창)과 들어 있는 목록
function find(s, id) {
  var i;
  for (i = 0; i < s.groups.length; i++) if (s.groups[i].tabs.indexOf(id) >= 0) return {box: s.groups[i], list: s.groups, i: i};
  for (i = 0; i < s.floats.length; i++) if (s.floats[i].tabs.indexOf(id) >= 0) return {box: s.floats[i], list: s.floats, i: i};
  return null;
}
function pull(box, id) { box.tabs = box.tabs.filter(function (p) { return p !== id; }); }

function reduce(state, a) {
  var s = copy(state), f;
  if (!a || (a.id != null && PANELS.indexOf(a.id) < 0)) return state;
  switch (a.type) {
    case 'chrome':
      if (a.part !== 'tools' && a.part !== 'hint') return state;
      s[a.part] = !!a.on; return s;
    case 'bare':
      s.bare = !!a.on; return s;
    case 'reset':
      return defaults();
    case 'activate':
      f = find(s, a.id);
      if (!f) {                                      // 닫힌 패널 → 마지막 묶음에 다시(묶음이 없으면 새로)
        s.closed = s.closed.filter(function (p) { return p !== a.id; });
        if (!s.groups.length) s.groups.push({tabs: [], active: null, h: 1});
        f = {box: s.groups[s.groups.length - 1], list: s.groups}; f.box.tabs.push(a.id);
      }
      f.box.active = a.id;
      if (f.list === s.floats) s.floats.push(s.floats.splice(f.i, 1)[0]);   // 누른 떠 있는 창이 맨 위로(도크는 그대로)
      else s.collapsed = false;
      return tidy(s);
    case 'close':
      f = find(s, a.id); if (!f) return state;
      pull(f.box, a.id); s.closed.push(a.id);
      return tidy(s);
    case 'move':
      f = find(s, a.id); if (!f) return state;
      var src = f.box, h = f.list === s.groups ? src.h : 1;
      if (a.to === 'float') {
        if (a.fi != null) {                            // 다른 떠 있는 창에 합치기
          var into = s.floats[a.fi]; if (!into || into === src) return state;
          pull(src, a.id); into.tabs.push(a.id); into.active = a.id;
          return tidy(s);
        }
        if (f.list === s.floats && src.tabs.length === 1) { src.x = num(a.x, src.x); src.y = num(a.y, src.y); return s; }   // 혼자 뜬 창 = 옮기기
        pull(src, a.id);
        s.floats.push(fbox({tabs: [a.id], active: a.id, x: a.x, y: a.y, w: a.w, h: a.h}));
        return tidy(s);
      }
      if (a.to === 'new') {
        if (f.list === s.groups && src.tabs.length === 1) return state;   // 도크에 혼자 있는 탭은 떼어도 그대로
        pull(src, a.id);
        var at = Math.max(0, Math.min(s.groups.length, a.at == null ? s.groups.length : a.at));
        s.groups.splice(at, 0, {tabs: [a.id], active: a.id, h: h});
        return tidy(s);
      }
      var to = s.groups[a.to]; if (!to) return state;
      pull(src, a.id);
      var pos = a.at == null ? to.tabs.length : Math.max(0, Math.min(to.tabs.length, a.at));
      to.tabs.splice(pos, 0, a.id); to.active = a.id;
      return tidy(s);
    case 'float':
      var fl = s.floats[a.fi]; if (!fl) return state;
      s.floats[a.fi] = fbox({tabs: fl.tabs, active: fl.active, x: a.x == null ? fl.x : a.x, y: a.y == null ? fl.y : a.y,
                             w: a.w == null ? fl.w : a.w, h: a.h == null ? fl.h : a.h});
      return s;
    case 'width':
      s.w = clampW(a.w); return s;
    case 'heights':
      if (!Array.isArray(a.hs) || a.hs.length !== s.groups.length) return state;
      s.groups.forEach(function (g, k) { g.h = okH(a.hs[k]); });
      return s;
    case 'collapse':
      s.collapsed = !!a.on; return s;
  }
  return state;
}
// 지금 보이는 패널(묶음마다 활성 탭, 도크가 접혀 있으면 떠 있는 창 것만)
function active(g) { return g.active; }
function visible(s) { return s.bare ? [] : (s.collapsed ? [] : s.groups.map(active)).concat(s.floats.map(active)); }

function load(getItem) {
  var raw = null, o = null;
  try { raw = getItem ? getItem(KEY) : null; } catch (e) { raw = null; }
  if (raw != null) { try { o = JSON.parse(raw); } catch (e) { o = null; } }
  return o && o.v === V ? normalize(o) : defaults();
}
function save(s, setItem) {
  var o = normalize(s);
  try { setItem(KEY, JSON.stringify(o)); } catch (e) {}
  return o;
}

HD.dock = {KEY: KEY, PANELS: PANELS, LABEL: LABEL, W_MIN: W_MIN, W_MAX: W_MAX,
           defaults: defaults, normalize: normalize, reduce: reduce, visible: visible, load: load, save: save};
})();
