/* Model — 대화창 아래 줄의 받는 터미널 정보(R28): 도우미 /api/agents/info 답 읽기 · 토큰 줄임 글 · 컨텍스트 고리 · 생각 깊이 메뉴 줄. DOM·저장소·메시지를 쓰지 않는다.
   parse(body) → {show:false, why} | {show:true, agent, model, modelLabel, effort, options, ctx:{used,max,pct}|null} — 모양이 틀린 칸은 버린다(ctx 틀림 = null → 고리 숨김, 0% 가 아니다)
   short(n) → '340k' · '1M' · '1.2M' · '950' · tip(ctx) → '컨텍스트 340k / 1M 토큰 · 34% 사용' · ring(pct, r) → {len, dash}(stroke-dasharray)
   effortLabel(e) → e | '자동' · menu(options, current) → [{id, label, on}] · same(a, b) → 다시 그릴 필요가 없나 · MODEL_TIP */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var MODEL_TIP = '모델은 Paseo에서 바꿔요';

function int(v) { return typeof v === 'number' && isFinite(v) && v >= 0 && Math.floor(v) === v; }
function str(v) { return typeof v === 'string' && v ? v : null; }

function parse(b) {
  if (!b || typeof b !== 'object') return {show: false, why: 'bad'};
  if (b.paseo !== true || !str(b.agent)) return {show: false, why: b.agent ? 'not-paseo' : 'none'};
  var c = b.context, ctx = null;
  if (c && typeof c === 'object' && int(c.used) && int(c.max) && c.max > 0 && int(c.pct) && c.pct <= 100) ctx = {used: c.used, max: c.max, pct: c.pct};
  var opts = Array.isArray(b.effortOptions) ? b.effortOptions.filter(function (o) { return str(o); }) : [];
  return {show: true, agent: b.agent, model: str(b.model), modelLabel: str(b.modelLabel) || str(b.model) || str(b.provider) || '',
          effort: str(b.effort), options: opts, ctx: ctx};
}
function short(n) {
  if (!int(n)) return '?';
  if (n >= 1e6) { var m = Math.round(n / 1e5) / 10; return (m % 1 ? m.toFixed(1) : String(m)) + 'M'; }
  if (n >= 1e3) return Math.round(n / 1e3) + 'k';
  return String(n);
}
function tip(ctx) { return ctx ? '컨텍스트 ' + short(ctx.used) + ' / ' + short(ctx.max) + ' 토큰 · ' + ctx.pct + '% 사용' : ''; }
function ring(pct, r) {
  var len = 2 * Math.PI * r, p = Math.max(0, Math.min(100, +pct || 0));
  return {len: +len.toFixed(2), dash: +(len * p / 100).toFixed(2)};
}
function effortLabel(e) { return e || '자동'; }
function menu(options, current) {
  return (options || []).map(function (o) { return {id: o, label: o, on: o === current}; });
}
function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

HD.agentInfo = {MODEL_TIP: MODEL_TIP, parse: parse, short: short, tip: tip, ring: ring, effortLabel: effortLabel, menu: menu, same: same};
})();
