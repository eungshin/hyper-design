/* Model — 프로젝트 메뉴 줄 규칙: GET /api/projects 한 줄 → 상태(열림·꺼짐·없음)·지금 캔버스·누를 수 있는지·연 때 글. DOM·저장소를 쓰지 않는다.
   HD.projects.rows(body, curOut) → {rows:[{name, out, state:'open'|'off'|'missing', word, when, current, clickable, why}], bad}
     차례는 도우미(등록부)가 준 그대로. 모양이 틀린 줄은 빼고 bad 에 센다(View 가 [hd] 경고), 목록이 아니면 rows:[] · bad:'…'
   HD.projects.row(p, curOut) · key(path)(hd_projects.key 와 같은 비교) · when(iso) → 'MM-DD HH:MM' | '-' · WORD{state: 글} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var WORD = {open: '열림', off: '꺼짐', missing: '없음'};

function key(path) {                                 // hd_projects.key: 역슬래시 → '/', 끝 '/' 빼기, 드라이브 경로는 대소문자 무시
  var p = String(path == null ? '' : path).replace(/\\/g, '/');
  while (p.length > 1 && p.slice(-1) === '/' && p.slice(-2) !== ':/') p = p.slice(0, -1);
  return p.length >= 2 && p[1] === ':' ? p.toLowerCase() : p;
}

function when(iso) {
  if (typeof iso !== 'string' || !iso) return '-';
  var m = /^\d{4}-(\d\d)-(\d\d)[T ](\d\d):(\d\d)/.exec(iso);
  return m ? m[1] + '-' + m[2] + ' ' + m[3] + ':' + m[4] : iso;
}

function state(p) {                                  // 열림 = 주소가 있음(떠 있는 도우미) · 없음 = out 폴더가 없음 · 그 밖 꺼짐
  if (typeof p.url === 'string' && p.url) return 'open';
  return p.state === 'missing' ? 'missing' : 'off';
}

function row(p, curOut) {
  var st = state(p);
  return {name: p.name, out: typeof p.out === 'string' ? p.out : '', state: st, word: WORD[st], when: when(p.last_opened),
          current: !!curOut && typeof p.out === 'string' && key(p.out) === key(curOut),
          clickable: st !== 'missing',
          why: st === 'missing' ? 'out 폴더가 없어 열 수 없어요 — 터미널에서 hd forget ' + p.name + ' 으로 링크를 지울 수 있어요' : ''};
}

function rows(body, curOut) {
  if (!Array.isArray(body)) return {rows: [], bad: '프로젝트 목록 모양이 아니에요'};
  var good = body.filter(function (p) { return p && typeof p === 'object' && typeof p.name === 'string' && p.name; });
  var n = body.length - good.length;
  return {rows: good.map(function (p) { return row(p, curOut); }), bad: n ? '모양이 틀린 줄 ' + n + '개를 건너뜀' : null};
}

HD.projects = {WORD: WORD, key: key, when: when, row: row, rows: rows};
})();
