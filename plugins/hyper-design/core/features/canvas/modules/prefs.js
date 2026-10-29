/* ViewModel — 캔버스 설정 하나(버전 붙음). 저장소 함수는 밖에서 받는다(getItem(key) / setItem(key, value)).
   키 hd-canvas-prefs = {v:3, lines:bool, op:0.15..1, preset:'calm'|'vivid'|'pastel'|'deep'|'random', rand:[hex…]|null,
                         custom:{'src>dst':'#hex'}, width:1..6(.5 단위), motion:bool, tags:bool}
     lines·op = 판에 늘 그리는 선 보이기·투명도(E7), width = 선 굵기(늘 그리는 선과 연결 보기 선 함께), tags = 선 태그 보이기(R46 — 끄면 고른 카드의 태그도 숨김)
   v2 의 arrows(주요 흐름 점선, 지움 — D9)·v1 의 sat 는 버리고 나머지는 옮긴다. 더 예전 키(hd-arrows)는 읽지 않는다.
   잘못된 값은 기본값으로. 메모(hd-notes:*)·팔레트(hd-palette) 키는 여기서 다루지 않는다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEY = 'hd-canvas-prefs', V = 3, PRESET_KEYS = ['calm', 'vivid', 'pastel', 'deep', 'random'];
var HEX = /^#[0-9a-f]{6}$/i;

function defaults() { return {v: V, lines: true, op: 0.55, preset: 'calm', rand: null, custom: {}, width: 2.5, motion: true, tags: true}; }
function safe(get, k) { try { return get(k); } catch (e) { return null; } }
function okRand(r) { return Array.isArray(r) && r.length >= 6 && r.length <= 8 && r.every(function (c) { return typeof c === 'string' && HEX.test(c); }); }
function okWidth(w) { return typeof w === 'number' && isFinite(w) && w >= 1 && w <= 6; }
function cleanCustom(c) {
  var out = {};
  if (c && typeof c === 'object' && !Array.isArray(c)) Object.keys(c).forEach(function (k) {
    if (k.indexOf('>') > 0 && typeof c[k] === 'string' && HEX.test(c[k])) out[k] = c[k];
  });
  return out;
}
// 아무 객체 → 올바른 v3 설정(모르는 값·틀린 값은 기본값)
function normalize(o) {
  var p = defaults();
  if (!o || typeof o !== 'object') return p;
  if (typeof o.lines === 'boolean') p.lines = o.lines;
  if (typeof o.op === 'number' && isFinite(o.op)) p.op = Math.round(Math.max(0.15, Math.min(1, o.op)) * 100) / 100;
  if (okRand(o.rand)) p.rand = o.rand.slice();
  if (PRESET_KEYS.indexOf(o.preset) >= 0 && (o.preset !== 'random' || p.rand)) p.preset = o.preset;
  p.custom = cleanCustom(o.custom);
  if (okWidth(o.width)) p.width = Math.round(o.width * 2) / 2;
  if (typeof o.motion === 'boolean') p.motion = o.motion;
  if (typeof o.tags === 'boolean') p.tags = o.tags;
  return p;
}

function load(getItem) {
  var raw = getItem ? safe(getItem, KEY) : null, o = null;
  if (raw != null) { try { o = JSON.parse(raw); } catch (e) { o = null; } }
  if (o && typeof o === 'object' && (o.v === V || o.v === 2)) return normalize(o);   // v2 → v3: 주요 흐름(arrows)은 버린다
  return defaults();
}

function save(prefs, setItem) {
  var o = normalize(prefs);
  try { setItem(KEY, JSON.stringify(o)); } catch (e) {}
  return o;
}

HD.prefs = {KEY: KEY, defaults: defaults, normalize: normalize, load: load, save: save};
})();
