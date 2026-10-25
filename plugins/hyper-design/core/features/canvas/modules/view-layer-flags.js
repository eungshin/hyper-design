/* View — 이 캔버스에서만 쓰는 화면 표시 세 가지(숨김 · 잠금 · 연결 태그 이름)의 주인: 저장 키 읽기·쓰기, 숨긴 카드·판 글 가리기, 숨긴 것 단추(#thid) 개수.
   거르기 규칙(없는 id·깨진 값)은 Model HD.layerFlags. 숨기기·잠그기·이름 바꾸기는 되돌리기 한 줄(ctx.record)로 남긴다.
   HD.viewLayerFlags.mount(ctx) → {hidden() → {id:1}, locked() → {id:1}, isHidden(id), isLocked(id), hide(ids, on), lock(ids, on), guard(ids) → 잠긴 것이 있었나(토스트),
     loadHidden() → 새로 숨은 id 목록, loadLocked(), loadLinkNames(), renderHidden(), names: {get(from, to), set(from, to, v)}}
   ctx = {$, $$, rowsEl, cardEl(id), getItem(k), setItem(k, v), hash, live() → 지금 있는 id 목록, record(op), toast(msg), redraw(), openHidden(),
          hiddenChanged(ids, on)(고르기에서 빼기·선·보이는 카드), layersChanged()(레이어 패널), lockedChanged()(레이어·정렬 패널)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$;
  var LNKEY = 'hd-link-names:' + ctx.hash, HKEY = 'hd-hidden:' + ctx.hash, LOCKKEY = 'hd-locked:' + ctx.hash;
  var linkNames = {}, hidden = {}, locked = {};

  function loadLinkNames() { try { linkNames = JSON.parse(ctx.getItem(LNKEY) || '{}') || {}; } catch (e) { linkNames = {}; } }   // 깨진 값 = 빈 이름(태그는 버튼 글로)
  function flags(key, what) {                      // 저장된 id 목록 → 지금 있는 화면만(set) · 걸렀거나 깨졌으면 다시 씀
    var r = HD.layerFlags.clean(ctx.getItem(key), ctx.live());
    if (r.bad) console.warn('[hd] ' + what + ' 목록이 깨져 비웠어요');
    else if (r.dropped.length) console.warn('[hd] ' + what + ' 목록에서 없는 화면 ' + r.dropped.length + '개를 뺐어요: ' + r.dropped.join(', '));
    if (r.changed) { try { ctx.setItem(key, JSON.stringify(r.ids)); } catch (e) {} }   // 저장 실패는 state-sync 가 알린다
    return r.set;
  }
  function paintHidden() {
    $$('.card', ctx.rowsEl).forEach(function (c) { c.classList.toggle('hid', !!hidden[c.dataset.id]); });
    ['@intro', '@foot', '@dscard'].concat(HD.boardText.IDS).forEach(function (id) { var t = $('#' + id.slice(1)); if (t) t.hidden = !!hidden[id]; });   // 판 글 레이어(t51-9)
  }
  function loadHidden() {                          // 시작 때 · 기록 줄로 오갈 때(셸 adoptState) → 새로 숨은 id
    var was = Object.keys(hidden);
    hidden = flags(HKEY, '숨긴 화면');
    paintHidden();
    return Object.keys(hidden).filter(function (id) { return was.indexOf(id) < 0; });
  }
  function loadLocked() { locked = flags(LOCKKEY, '잠긴 화면'); }

  function renderHidden() {
    var n = Object.keys(hidden).length;
    $('#thid').hidden = !n; $('#thr').hidden = !n; $('#thidn').textContent = n || '';
    $('#thid').setAttribute('aria-label', '숨긴 화면 ' + n + '개');
    ctx.layersChanged();
  }
  function setHidden(ids, on) {
    ids.forEach(function (id) {
      if (on) hidden[id] = 1; else delete hidden[id];
      if (id.charAt(0) === '@') { var t = $('#' + id.slice(1)); if (t) t.hidden = on; return; }   // 판 글
      var c = ctx.cardEl(id); if (c) c.classList.toggle('hid', on);
    });
    try { ctx.setItem(HKEY, JSON.stringify(Object.keys(hidden))); } catch (e) {}   // 저장 실패는 state-sync 가 알린다
    renderHidden();
    ctx.hiddenChanged(ids, on);
  }
  function hide(ids, on) {
    ids = ids.filter(function (id) { return !!hidden[id] !== on; }); if (!ids.length) return;
    setHidden(ids, on);
    ctx.record({label: on ? '화면 숨기기' : '숨긴 화면 보이기', undo: function () { setHidden(ids, !on); }, redo: function () { setHidden(ids, on); }});
  }
  function setLocked(ids, on) {
    ids.forEach(function (id) { if (on) locked[id] = 1; else delete locked[id]; });
    try { ctx.setItem(LOCKKEY, JSON.stringify(Object.keys(locked))); } catch (e) {}   // 저장 실패는 state-sync 가 알린다
    ctx.lockedChanged();
  }
  function lock(ids, on) {
    ids = ids.filter(function (id) { return !!locked[id] !== on; }); if (!ids.length) return;
    setLocked(ids, on);
    ctx.record({label: on ? '화면 잠그기' : '잠금 풀기', undo: function () { setLocked(ids, !on); }, redo: function () { setLocked(ids, on); }});
  }
  function guard(ids) {                            // 잠긴 화면이 있으면 알리고 true
    var hit = ids.filter(function (id) { return locked[id]; }); if (!hit.length) return false;
    ctx.toast('잠긴 화면이에요 — 레이어 패널에서 풀어요'); return true;
  }
  function setName(from, to, v) {
    if (v) linkNames[from + '>' + to] = v; else delete linkNames[from + '>' + to];
    try { ctx.setItem(LNKEY, JSON.stringify(linkNames)); } catch (e) {}   // 저장 실패는 state-sync 가 알린다
  }
  var names = {get: function (from, to) { return linkNames[from + '>' + to] || ''; },
               set: function (from, to, v) {
                 var old = names.get(from, to); if (old === v) return;
                 setName(from, to, v);
                 ctx.record({label: '태그 이름', undo: function () { setName(from, to, old); ctx.redraw(); }, redo: function () { setName(from, to, v); ctx.redraw(); }});
               }};

  loadLinkNames(); loadHidden(); loadLocked();
  $('#thid').addEventListener('click', function () { ctx.openHidden(); });

  return {hidden: function () { return hidden; }, locked: function () { return locked; },
          isHidden: function (id) { return !!hidden[id]; }, isLocked: function (id) { return !!locked[id]; },
          hide: hide, lock: lock, guard: guard, names: names,
          loadHidden: loadHidden, loadLocked: loadLocked, loadLinkNames: loadLinkNames, renderHidden: renderHidden};
}

HD.viewLayerFlags = {mount: mount};
})();
