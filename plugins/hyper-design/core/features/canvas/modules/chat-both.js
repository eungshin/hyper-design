/* Model — 대화창 '/both'(V1): 캔버스 화면 ↔ parts.json 으로 이어진 실제 앱 — 연결 읽기 · 대상 화면 · 칩 · 요청 글에 붙일 줄. DOM·저장소·메시지를 쓰지 않는다.
   links(body) → {화면 id: {file, parts:[{file, repo, watch[]}]}} — 도우미 GET /api/app-parts 의 links 칸(part_stamp.screen_links). 틀린 항목은 버리고, 칸이 없으면(옛 도우미) {}.
   targets(chips, links) → {ids, missing, ok} — 대상 = 보이는 화면·요소 칩의 화면(고른 차례, 겹침 빼고), 칩이 없으면 연결된 화면 모두(이름 차례).
     missing = 연결 없는 대상, ok = 대상이 있고 missing 이 비었음(아니면 View 가 UNLINKED 토스트 · 칩·보내기 없음).
   chip() → {key:'both', kind:'both', label:'캔버스+앱'} — 범위를 정하지 않고 접히지 않으며 build 는 빼고 만든다(HD.chat 의 CONTEXT).
   block(ids, links, titleOf) → '캔버스+앱 함께 적용 …' 글 — 화면마다 '- 이름(id) · 캔버스: <화면 파일>' + 부품마다 '앱: <저장소> · 경로: <watch> (부품 <file>)' + '둘 다 고친 뒤 `hd verify <id>` 으로 확인'.
   apply(memos, ids, links, titleOf) → 새 메모 목록(원본은 그대로) — 대상 화면 메모 = 글 끝에 빈 줄 + 그 화면 줄만, scope all 메모 = 대상 모두. 요청문 모양(edits.request)은 그대로.
   UNLINKED · NO_HELPER = 토스트 말.
   HD.chatBoth = {KEY, LABEL, UNLINKED, NO_HELPER, links, targets, chip, block, apply} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var KEY = 'both', LABEL = '캔버스+앱';
var UNLINKED = '이 화면은 앱 부품이 연결되지 않았어요 — hd parts 로 연결해 주세요';
var NO_HELPER = '앱 부품 연결은 도우미로 연 캔버스에서만 읽을 수 있어요 — hd open 으로 열어 주세요';
var HEAD = '캔버스+앱 함께 적용 — 캔버스 화면과 이어진 실제 앱 코드도 같이 고쳐 주세요:';

function str(v) { return typeof v === 'string' && v.trim() ? v.trim() : null; }
function part(p) {
  if (!p || typeof p !== 'object') return null;
  var f = str(p.file), r = str(p.repo), w = Array.isArray(p.watch) ? p.watch.map(str).filter(Boolean) : [];
  return f && r && w.length ? {file: f, repo: r, watch: w} : null;
}
function links(body) {
  var src = body && typeof body === 'object' && body.links && typeof body.links === 'object' && !Array.isArray(body.links) ? body.links : {}, res = {};
  Object.keys(src).forEach(function (id) {
    var e = src[id], f = e && typeof e === 'object' ? str(e.file) : null;
    var ps = f && Array.isArray(e.parts) ? e.parts.map(part).filter(Boolean) : [];
    if (ps.length) res[id] = {file: f, parts: ps};
  });
  return res;
}
function targets(chips, map) {
  map = map || {};
  var ids = [];
  (chips || []).forEach(function (c) {
    if (c && (c.kind === 'screen' || c.kind === 'el') && c.screen != null && ids.indexOf(String(c.screen)) < 0) ids.push(String(c.screen));
  });
  if (!ids.length) ids = Object.keys(map).sort();
  var missing = ids.filter(function (id) { return !map[id]; });
  return {ids: ids, missing: missing, ok: ids.length > 0 && !missing.length};
}
function chip() { return {key: KEY, kind: KEY, label: LABEL}; }
function name(id, titleOf) { var t = titleOf ? titleOf(id) : null; return t == null || t === '' ? id : t + '(' + id + ')'; }
function block(ids, map, titleOf) {
  map = map || {};
  var lines = (ids || []).filter(function (id) { return map[id]; }).map(function (id) {
    var e = map[id];
    return '- ' + name(id, titleOf) + ' · 캔버스: ' + e.file + '\n' +
      e.parts.map(function (p) { return '  앱: ' + p.repo + ' · 경로: ' + p.watch.join(', ') + ' (부품 ' + p.file + ')\n'; }).join('') +
      '  둘 다 고친 뒤 `hd verify ' + id + '` 으로 확인';
  });
  return lines.length ? HEAD + '\n' + lines.join('\n') : '';
}
function apply(memos, ids, map, titleOf) {
  ids = ids || [];
  return (memos || []).map(function (m) {
    var mine = m.scope === 'all' ? ids : ids.indexOf(String(m.screen)) >= 0 ? [String(m.screen)] : [];
    var b = mine.length ? block(mine, map, titleOf) : '';
    if (!b) return m;
    var n = {}; Object.keys(m).forEach(function (k) { n[k] = m[k]; });
    n.note = String(m.note == null ? '' : m.note).replace(/\s+$/, '') + '\n\n' + b;
    return n;
  });
}

HD.chatBoth = {KEY: KEY, LABEL: LABEL, UNLINKED: UNLINKED, NO_HELPER: NO_HELPER, links: links, targets: targets, chip: chip, block: block, apply: apply};
})();
