/* Model — 프로젝트 줄 규칙(고르기 창·머리 제목·탭 바가 함께 씀): GET /api/projects 한 줄 → 상태(열림·꺼짐·없음)·지금 캔버스·제목·썸네일·누를 수 있는지·연 때 글. DOM·저장소를 쓰지 않는다.
   HD.projects.rows(body, curOut) → {rows:[{name, title, out, state:'open'|'off'|'missing', word, when, last_opened, thumb, starred, trashed, current, clickable, why}], bad}
     차례는 도우미(등록부)가 준 그대로. 모양이 틀린 줄은 빼고 bad 에 센다(View 가 [hd] 경고), 목록이 아니면 rows:[] · bad:'…'. 제목이 없으면 이름
   HD.projects.row(p, curOut) · key(path)(hd_projects.key 와 같은 비교) · when(iso) → 'MM-DD HH:MM' | '-' · WORD{state: 글}
   ago(iso, nowMs) → 방금 전·N분 전·N시간 전·어제·MM-DD · filter(rows, q) → 휴지통 뺀 검색 결과 · current(rows) → 지금 줄|null
   newTitle(titles) → '새 프로젝트 N' · shown(manifestTitle, outPath) → 프로젝트 줄이 없을 때 머리 제목(옛 기본 문구는 쓰지 않음) */
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
  return {name: p.name, title: typeof p.title === 'string' && p.title.trim() ? p.title.trim() : p.name,
          out: typeof p.out === 'string' ? p.out : '', state: st, word: WORD[st], when: when(p.last_opened), last_opened: p.last_opened || null,
          thumb: typeof p.thumb === 'string' && p.thumb ? p.thumb : null, starred: p.starred === true, trashed: !!p.trashed,
          current: !!curOut && typeof p.out === 'string' && key(p.out) === key(curOut),
          clickable: st !== 'missing',
          why: st === 'missing' ? 'out 폴더가 없어 열 수 없어요 — 터미널에서 hd forget ' + p.name + ' 으로 링크를 지울 수 있어요' : ''};
}

function pad(n) { return (n < 10 ? '0' : '') + n; }
function ago(iso, now) {                             // 카드 아래 작은 글(홈과 같은 말): 방금 전 · N분 전 · N시간 전(같은 날) · 어제 · MM-DD(다른 해 YYYY-MM-DD)
  if (typeof iso !== 'string' || !iso) return '-';
  var t = Date.parse(iso);
  if (isNaN(t)) return iso;
  var d = now - t;
  if (d < 60000) return '방금 전';
  if (d < 3600000) return Math.floor(d / 60000) + '분 전';
  var a = new Date(t), b = new Date(now), day = function (x) { return new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime(); };
  var days = Math.round((day(b) - day(a)) / 86400000);
  if (days === 0) return Math.floor(d / 3600000) + '시간 전';
  if (days === 1) return '어제';
  var md = pad(a.getMonth() + 1) + '-' + pad(a.getDate());
  return a.getFullYear() === b.getFullYear() ? md : a.getFullYear() + '-' + md;
}

function filter(rows, q) {                           // 고르기 창 카드: 휴지통은 늘 빼고, 제목·이름에서 대소문자 무시 부분 일치
  var s = String(q == null ? '' : q).trim().toLowerCase();
  return rows.filter(function (r) {
    return !r.trashed && (!s || r.title.toLowerCase().indexOf(s) >= 0 || r.name.toLowerCase().indexOf(s) >= 0);
  });
}

function current(rows) {
  for (var i = 0; i < rows.length; i++) if (rows[i].current) return rows[i];
  return null;
}

function newTitle(titles) {                          // '새 프로젝트 N' — 쓰지 않은 가장 작은 N
  var used = {};
  (titles || []).forEach(function (t) { var m = /^새 프로젝트 (\d+)$/.exec(String(t == null ? '' : t).trim()); if (m) used[+m[1]] = 1; });
  for (var n = 1; ; n++) if (!used[n]) return '새 프로젝트 ' + n;
}

var OLD_DEFAULT = '전체 화면 한눈에 보기';            // build_canvas 의 옛 기본 제목 — 머리에는 쓰지 않는다
function shown(manifest, outPath) {                  // 프로젝트 줄이 없을 때 머리 제목: manifest 제목, 아니면 폴더 이름(out 이면 그 위)
  var m = typeof manifest === 'string' ? manifest.trim() : '';
  if (m && m !== OLD_DEFAULT) return m;
  var parts = String(outPath == null ? '' : outPath).replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length && /\.html?$/i.test(parts[parts.length - 1])) parts.pop();
  if (parts.length > 1 && parts[parts.length - 1].toLowerCase() === 'out') parts.pop();
  var last = parts.length ? parts[parts.length - 1] : '';
  return /^[A-Za-z]:$/.test(last) ? '' : last;
}

function rows(body, curOut) {
  if (!Array.isArray(body)) return {rows: [], bad: '프로젝트 목록 모양이 아니에요'};
  var good = body.filter(function (p) { return p && typeof p === 'object' && typeof p.name === 'string' && p.name; });
  var n = body.length - good.length;
  return {rows: good.map(function (p) { return row(p, curOut); }), bad: n ? '모양이 틀린 줄 ' + n + '개를 건너뜀' : null};
}

HD.projects = {WORD: WORD, key: key, when: when, row: row, rows: rows, ago: ago, filter: filter, current: current, newTitle: newTitle, shown: shown};
})();
