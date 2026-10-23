// Small copy of dictionary ui_host/popup/src/twin/registry.js (2026-10-23) — app_stages.parse_registry fixture.
// Keeps the shapes that matter: one-line entry, multi-line entries, group constants,
// comments inside the array, a multi-line label value, and a "//" inside a string.

export const PROJECT = 'dictionary';

const MOLECULES = 'molecules';
const ORGANISMS = 'organisms';

export const TWIN_COMPONENTS = [
  {id:'ocr-screen',name:'OcrApp',group:ORGANISMS,fixture:'ui_host/popup/src/twin/fixtures/ocr-screen.json',file:'ui_host/popup/src/lookup/ocr/OcrApp.svelte'},
  {
    id: 'word-header',
    name: 'WordHeader',
    group: MOLECULES,
    fixture: 'ui_host/popup/src/twin/fixtures/word-header.json',
    file: 'ui_host/popup/src/lookup/WordHeader.svelte',
  },
  /* { id: 'commented-out', name: 'Gone', group: MOLECULES } */
  {
    // The whole settings WINDOW — a comment with { braces } and 'quotes'.
    id: "settings-window",
    name: 'SettingsApp',
    group: ORGANISMS,
    fixture: 'ui_host/popup/src/twin/fixtures/usage-tab.json',
    file: 'ui_host/popup/src/settings/SettingsApp.svelte',
  },
];

export const SOURCE_DIRS = ['ui_host/popup/src/lookup'];

export const TWIN_LABELS = {
  'ocr-screen':'고정 화면 OCR — see http://example.com/x',
  'word-header': '단어 헤더 — 팝업 최상단 (단어 · 발음)',
  // 크기는 chapters.js 를 따른다.
  'settings-window':
    '설정 창 전체 — 헤더 · 레일 · it\'s escaped',
};
