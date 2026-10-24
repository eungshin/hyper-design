/* Model — 홈 화면의 순수 규칙: 줄 고르기(normalize) · 구역(section) · 찾기(search) · 차례 · 상대 시각 · 키보드 고르기 이동 · 우클릭 메뉴 항목 · 새 이름 */
(function (root) {
  'use strict';
  var STATES = {running: 1, off: 1, missing: 1};
  var SECTIONS = ['recent', 'all', 'starred', 'trash'];
  var LABEL = {recent: '최근 항목', all: '모든 프로젝트', starred: '별표', trash: '휴지통'};
  var RECENT_MAX = 100;

  function str(v) { return typeof v === 'string' ? v : ''; }
  function ms(iso) {
    if (typeof iso !== 'string' || !iso) return NaN;
    return Date.parse(iso.length === 19 && iso.charAt(10) === ' ' ? iso.replace(' ', 'T') : iso);
  }

  // 도우미/허브 GET /api/projects 줄 → {rows, bad}. 이름 없는 줄·객체 아닌 줄은 빼고 bad 로 센다(View 가 [hd] 경고 한 줄)
  function normalize(body) {
    if (!Array.isArray(body)) return {rows: [], bad: 1};
    var rows = [], bad = 0, seen = {};
    body.forEach(function (r) {
      if (!r || typeof r !== 'object' || !str(r.name) || seen[r.name]) { bad++; return; }
      seen[r.name] = 1;
      rows.push(row(r));
    });
    return {rows: rows, bad: bad};
  }
  function row(r) {
    return {
      name: r.name,
      title: str(r.title).trim() || r.name,
      out: str(r.out),
      state: STATES[r.state] ? r.state : 'off',
      url: str(r.url) || null,
      created: str(r.created) || null,
      last_opened: str(r.last_opened) || null,
      starred: r.starred === true,
      trashed: str(r.trashed) || (r.trashed === true ? 'true' : null),
      thumb: str(r.thumb) || null
    };
  }

  function when(r) { var t = ms(r.last_opened); return isNaN(t) ? (isNaN(ms(r.created)) ? 0 : ms(r.created)) : t; }
  function byRecent(a, b) { return when(b) - when(a) || a.title.localeCompare(b.title, 'ko'); }

  // 구역마다 보이는 줄과 차례. recent = 연 적 있는 것만(최근 것부터, 최대 100) · all = 휴지통 밖 전부(최근 것부터)
  // starred = 별표 · trash = 휴지통에 넣은 때가 최근인 것부터
  function section(rows, sec) {
    var live = rows.filter(function (r) { return !r.trashed; });
    if (sec === 'recent') return live.filter(function (r) { return !isNaN(ms(r.last_opened)); }).sort(byRecent).slice(0, RECENT_MAX);
    if (sec === 'starred') return live.filter(function (r) { return r.starred; }).sort(byRecent);
    if (sec === 'trash') {
      return rows.filter(function (r) { return r.trashed; }).sort(function (a, b) {
        var ta = ms(a.trashed), tb = ms(b.trashed);
        return (isNaN(tb) ? 0 : tb) - (isNaN(ta) ? 0 : ta) || a.title.localeCompare(b.title, 'ko');
      });
    }
    return live.sort(byRecent);
  }

  function fold(s) { return String(s).toLocaleLowerCase().normalize('NFC'); }
  // 제목·이름 부분 일치(대소문자 무시). 빈 찾기 = 그대로
  function search(rows, q) {
    var k = fold(str(q).trim());
    if (!k) return rows.slice();
    return rows.filter(function (r) { return fold(r.title).indexOf(k) >= 0 || fold(r.name).indexOf(k) >= 0; });
  }

  function view(rows, sec, q) { return search(section(rows, sec), q); }

  // 상대 시각: 방금 전(<1분) · N분 전 · N시간 전(같은 날) · 어제 · MM-DD(올해) · YYYY-MM-DD. 모르는 값 = ''
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function relTime(iso, now) {
    var t = ms(iso);
    if (isNaN(t)) return '';
    var d = new Date(t), n = new Date(now), diff = now - t;
    if (diff < 60e3 && diff > -60e3) return '방금 전';
    var day0 = new Date(n.getFullYear(), n.getMonth(), n.getDate()).getTime();
    if (diff > 0 && t >= day0) return diff < 3600e3 ? Math.floor(diff / 60e3) + '분 전' : Math.floor(diff / 3600e3) + '시간 전';
    if (t < day0 && t >= day0 - 86400e3) return '어제';
    var md = pad(d.getMonth() + 1) + '-' + pad(d.getDate());
    return d.getFullYear() === n.getFullYear() ? md : d.getFullYear() + '-' + md;
  }

  // 격자 안 고르기 이동. i = 지금 칸(-1 = 없음), count = 칸 수, cols = 한 줄 칸 수. 끝에서는 멈춘다
  function move(i, key, count, cols) {
    if (count <= 0) return -1;
    cols = Math.max(1, cols | 0);
    if (i < 0 || i >= count) return key === 'End' ? count - 1 : 0;
    var j = i;
    if (key === 'ArrowRight') j = i + 1;
    else if (key === 'ArrowLeft') j = i - 1;
    else if (key === 'ArrowDown') j = i + cols;
    else if (key === 'ArrowUp') j = i - cols;
    else if (key === 'Home') j = 0;
    else if (key === 'End') j = count - 1;
    if (key === 'ArrowDown' && j >= count) j = Math.floor((count - 1) / cols) > Math.floor(i / cols) ? count - 1 : i;
    return j < 0 || j >= count ? i : j;
  }

  // 우클릭 메뉴 — [{id, label, disabled?}] · '-' = 구분선
  function menu(r, sec) {
    if (!r) return [];
    if (sec === 'trash' || r.trashed) return [{id: 'restore', label: '되돌리기'}, {id: 'forget', label: '목록에서 완전히 빼기'}];
    var gone = r.state === 'missing';
    return [
      {id: 'open', label: '열기'},
      {id: 'rename', label: '이름 바꾸기'},
      {id: 'star', label: r.starred ? '별표 빼기' : '별표'},
      {id: 'reveal', label: '폴더 열기', disabled: gone},
      '-',
      {id: 'trash', label: '휴지통으로'}
    ];
  }

  // 새 프로젝트 기본 이름: "새 프로젝트 N" — 이미 있는 제목과 겹치지 않는 가장 작은 N(1부터)
  function newTitle(rows) {
    var have = {};
    rows.forEach(function (r) { have[r.title] = 1; });
    for (var n = 1; ; n++) if (!have['새 프로젝트 ' + n]) return '새 프로젝트 ' + n;
  }

  // 이름 바꾸기 확정 값: 앞뒤 공백 뺌, 빈 값·같은 값이면 null(아무것도 안 함)
  function renameValue(input, old) {
    var v = str(input).trim();
    return v && v !== old ? v : null;
  }

  function empty(sec, q) {
    if (str(q).trim()) return '‘' + str(q).trim() + '’와 맞는 프로젝트가 없어요';
    return {
      recent: '최근에 연 프로젝트가 없어요',
      all: '아직 프로젝트가 없어요 — ‘+ 새 프로젝트’로 시작하세요',
      starred: '별표한 프로젝트가 없어요 — 카드의 ☆을 눌러 보세요',
      trash: '휴지통이 비었어요'
    }[sec] || '';
  }

  function validSection(s) { return SECTIONS.indexOf(s) >= 0 ? s : 'recent'; }

  root.HDHomeModel = {
    SECTIONS: SECTIONS, LABEL: LABEL, normalize: normalize, row: row, section: section, search: search, view: view,
    relTime: relTime, move: move, menu: menu, newTitle: newTitle, renameValue: renameValue, empty: empty, validSection: validSection
  };
})(typeof window !== 'undefined' ? window : globalThis);
