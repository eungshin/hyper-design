/* ViewModel — 캔버스 설정 하나(버전 붙음). 저장소 함수는 밖에서 받는다(getItem(key) / setItem(key, value)).
   키 hd-canvas-prefs = {v:1, arrows:bool, sat:number}. 처음엔 예전 키(hd-arrows, hd-link-sat)를 읽어 옮긴다(예전 키엔 더 쓰지 않음).
   메모(hd-notes:*)·팔레트(hd-palette) 키는 여기서 다루지 않는다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEY = 'hd-canvas-prefs', V = 1, SAT_MIN = 0.2, SAT_MAX = 1.2;

function defaults() { return {v: V, arrows: true, sat: 0.7}; }
function okSat(x) { return typeof x === 'number' && x >= SAT_MIN && x <= SAT_MAX; }
function safe(get, k) { try { return get(k); } catch (e) { return null; } }

function load(getItem) {
  var p = defaults(), raw = getItem ? safe(getItem, KEY) : null, o = null;
  if (raw != null) { try { o = JSON.parse(raw); } catch (e) { o = null; } }
  if (o && typeof o === 'object' && o.v === V) {
    if (typeof o.arrows === 'boolean') p.arrows = o.arrows;
    if (okSat(o.sat)) p.sat = o.sat;
    return p;
  }
  if (!getItem) return p;                          // 예전 키 옮기기
  p.arrows = safe(getItem, 'hd-arrows') !== '0';
  var s = parseFloat(safe(getItem, 'hd-link-sat'));
  if (s >= SAT_MIN && s <= SAT_MAX) p.sat = s;
  return p;
}

function save(prefs, setItem) {
  var d = defaults(), o = {v: V, arrows: typeof prefs.arrows === 'boolean' ? prefs.arrows : d.arrows, sat: okSat(prefs.sat) ? prefs.sat : d.sat};
  try { setItem(KEY, JSON.stringify(o)); } catch (e) {}
  return o;
}

HD.prefs = {KEY: KEY, defaults: defaults, load: load, save: save};
})();
