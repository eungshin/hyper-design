/* Model — 판 위 디자인 시스템 카드(S6): 토큰 이름(tokens.css :root 변수) → 카드 칸(색 네 줄·Aa 셋·단추 셋·입력·모서리·그림자). DOM·저장소를 쓰지 않는다.
   값은 늘 var(--…) 참조 — 카드가 화면과 같은 tokens.css 를 읽으니 테마를 바꾸면 카드와 화면이 함께 바뀐다(Stitch 는 화면마다 값을 복사).
   토큰이 없으면 다음 후보, 그래도 없으면 그 색 줄은 빼고 글자·단추는 글자 값(fallback). 토큰 목록이 없거나 색 토큰이 0 이면 카드 없음(null).
   HD.dsCard = {sections(names) → {colors, type, font, buttons, input, radius, shadow, bad} | null, tones(token) → [{label, css}], ROWS}
   colors[i] = {key, label, token, steps:[{label, css}]} · type[i] = {key, label, sample, size, weight, lh} · buttons[i] = {key, label, bg, fg, border}
   bad = 버린 이름 수(이름이 아님·CSS 를 끼움) — View 가 [hd] 경고 한 줄 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAME = /^--[a-z0-9-]+$/i;
var ROWS = [                                         // 색 줄 = 후보 차례(앞의 것이 있으면 그것)
  {key: 'primary', label: 'Primary', chain: ['--c-primary', '--c-brand']},
  {key: 'secondary', label: 'Secondary', chain: ['--c-secondary', '--c-brand-tint']},
  {key: 'accent', label: 'Accent', chain: ['--c-accent', '--c-tertiary']}
];
var NEUTRAL = ['--c-bg', '--c-surface', '--c-line', '--c-line-strong', '--c-text-3', '--c-text-2', '--c-text-1'];
var GREYS = ['#F7F7F7', '#E5E5E5', '#C7C7C7', '#8F8F8F', '#5C5C5C', '#2E2E2E'];   // 중립 토큰이 모자랄 때만
var TYPE = [
  {key: 'headline', label: 'Headline', sample: 'Aa 제목', chain: ['title', 'h1', 'headline', 'h2'], fs: '28px', fw: '700'},
  {key: 'body', label: 'Body', sample: 'Aa 본문 글자', chain: ['body'], fs: '16px', fw: '400'},
  {key: 'label', label: 'Label', sample: 'Aa 라벨', chain: ['caption', 'label', 'sub'], fs: '12px', fw: '500'}
];

function tones(t) {                                  // 밝게 셋 · 그대로 · 어둡게 둘 — 섞기라 토큰 값이 바뀌면 단계도 같이
  var v = 'var(' + t + ')', mix = function (with_, p) { return 'color-mix(in srgb, ' + v + ', ' + with_ + ' ' + p + '%)'; };
  return [{label: '90', css: mix('#fff', 80)}, {label: '70', css: mix('#fff', 55)}, {label: '50', css: mix('#fff', 30)},
          {label: '40', css: v}, {label: '30', css: mix('#000', 25)}, {label: '20', css: mix('#000', 50)}];
}

function sections(names) {
  if (!Array.isArray(names)) return null;
  var has = {}, bad = 0;
  names.forEach(function (n) { if (typeof n === 'string' && NAME.test(n)) has[n] = 1; else bad++; });
  var pick = function (chain) { for (var i = 0; i < chain.length; i++) if (has[chain[i]]) return chain[i]; return null; };
  var v = function (chain, fb) { var n = pick(chain); return n ? 'var(' + n + ')' : fb; };
  if (!Object.keys(has).some(function (n) { return n.indexOf('--c-') === 0; })) return null;

  var colors = [];
  ROWS.forEach(function (r) { var t = pick(r.chain); if (t) colors.push({key: r.key, label: r.label, token: t, steps: tones(t)}); });
  var ladder = NEUTRAL.filter(function (n) { return has[n]; });
  colors.push(ladder.length >= 3
    ? {key: 'neutral', label: 'Neutral', token: ladder[ladder.length - 1], steps: ladder.map(function (n) { return {label: n.slice(4), css: 'var(' + n + ')'}; })}
    : {key: 'neutral', label: 'Neutral', token: null, steps: GREYS.map(function (g, i) { return {label: String(90 - i * 15), css: g}; })});

  var type = TYPE.map(function (t) {
    var s = pick(t.chain.map(function (c) { return '--fs-' + c; })), suf = s ? s.slice(5) : '';
    return {key: t.key, label: t.label, sample: t.sample, size: s ? 'var(' + s + ')' : t.fs,
            weight: has['--fw-' + suf] ? 'var(--fw-' + suf + ')' : t.fw, lh: has['--lh-' + suf] ? 'var(--lh-' + suf + ')' : '1.4'};
  });
  var radius = v(['--r-m', '--r-s'], '8px'), text = v(['--c-text-1', '--c-text'], '#1B1B1B');
  var buttons = [
    {key: 'primary', label: 'Primary', bg: v(['--c-primary', '--c-brand'], '#1B1B1B'), fg: v(['--c-on-primary', '--c-on-brand'], '#fff'), border: '0'},
    {key: 'secondary', label: 'Secondary', bg: v(['--c-brand-tint', '--c-bg'], '#F1F1F1'), fg: v(['--c-brand-tint-text', '--c-text-1'], '#1B1B1B'), border: '0'},
    {key: 'outlined', label: 'Outlined', bg: 'transparent', fg: text, border: '1px solid ' + v(['--c-line-strong', '--c-line'], '#BFBFBF')}
  ];
  buttons.forEach(function (b) { b.radius = radius; });
  return {colors: colors, type: type, font: has['--font'] ? 'var(--font)' : null, buttons: buttons,
          input: {bg: v(['--c-surface'], '#fff'), fg: text, placeholder: v(['--c-text-3'], '#8F8F8F'), border: '1px solid ' + v(['--c-line'], '#DEDEDE'), radius: radius},
          radius: Object.keys(has).filter(function (n) { return /^--r-/.test(n); }),
          shadow: Object.keys(has).filter(function (n) { return /^--shadow-/.test(n); }), bad: bad};
}

HD.dsCard = {sections: sections, tones: tones, ROWS: ROWS};
})();
