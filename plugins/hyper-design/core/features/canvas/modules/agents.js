/* Model — 보낼 곳 고르기 규칙(#214): GET /api/agents 답 → 고를 줄(이 저장소 먼저 · 실행 중 먼저 · 이름)·자동 제안·줄 글. DOM·저장소를 쓰지 않는다.
   HD.agents.rows(body) → {rows:[{id, name, label, folder, status, mine, current}], current, repo, error, bad}
     body = 도우미 답 {agents, current, repo, error?}. 닫힌(closed)·보관된 에이전트와 모양이 틀린 줄은 뺀다(bad = 뺀 틀린 줄 수 — View 가 [hd] 경고)
   rank(list, repo) → 새 목록: repo 안(cwd 가 repo 이거나 그 아래) 먼저, 그다음 running < idle < 그 밖, 그다음 이름(없으면 id)
   suggest(list, repo) → repo 안에서 running 인 에이전트가 정확히 하나면 그것, 아니면 null
   inRepo(cwd, repo) · key(path)(역슬래시 → '/', 끝 '/' 빼기, 드라이브 경로는 대소문자 무시) · label(a) → 이름 40자(넘으면 …) · folder(cwd) → 마지막 폴더 이름
   NAME_MAX = 40 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAME_MAX = 40, ORDER = {running: 0, idle: 1};

function key(path) {
  var p = String(path == null ? '' : path).replace(/\\/g, '/');
  while (p.length > 1 && p.slice(-1) === '/' && p.slice(-2) !== ':/') p = p.slice(0, -1);
  return p.length >= 2 && p[1] === ':' ? p.toLowerCase() : p;
}

function inRepo(cwd, repo) {
  if (typeof cwd !== 'string' || !cwd || typeof repo !== 'string' || !repo) return false;
  var c = key(cwd), r = key(repo);
  return c === r || c.indexOf(r.slice(-1) === '/' ? r : r + '/') === 0;
}

function nameOf(a) { return typeof a.name === 'string' && a.name.trim() ? a.name.trim() : a.id; }

function label(a) {
  var n = nameOf(a).replace(/\s+/g, ' ');
  return n.length > NAME_MAX ? n.slice(0, NAME_MAX - 1) + '…' : n;
}

function folder(cwd) {
  var p = key(cwd);
  return p ? p.split('/').filter(Boolean).pop() || p : '';
}

function rank(list, repo) {
  return (list || []).map(function (a, i) { return {a: a, i: i}; }).sort(function (x, y) {
    var mx = inRepo(x.a.cwd, repo) ? 0 : 1, my = inRepo(y.a.cwd, repo) ? 0 : 1;
    if (mx !== my) return mx - my;
    var sx = ORDER[x.a.status] != null ? ORDER[x.a.status] : 2, sy = ORDER[y.a.status] != null ? ORDER[y.a.status] : 2;
    if (sx !== sy) return sx - sy;
    var nx = nameOf(x.a), ny = nameOf(y.a);
    return nx < ny ? -1 : nx > ny ? 1 : x.i - y.i;
  }).map(function (o) { return o.a; });
}

function suggest(list, repo) {
  var hit = (list || []).filter(function (a) { return ok(a) && a.status === 'running' && inRepo(a.cwd, repo); });
  return hit.length === 1 ? hit[0] : null;
}

function ok(a) { return a && typeof a === 'object' && typeof a.id === 'string' && !!a.id; }

function rows(body) {
  var b = body && typeof body === 'object' ? body : {};
  var raw = Array.isArray(b.agents) ? b.agents : [];
  var good = raw.filter(ok), bad = raw.length - good.length;
  var live = good.filter(function (a) { return a.status !== 'closed' && a.status !== 'archived' && !a.archived; });
  var repo = typeof b.repo === 'string' ? b.repo : null, cur = typeof b.current === 'string' ? b.current : null;
  return {rows: rank(live, repo).map(function (a) {
    return {id: a.id, name: nameOf(a), label: label(a), folder: folder(a.cwd), status: a.status || '', mine: inRepo(a.cwd, repo), current: a.id === cur};
  }), current: cur, repo: repo, error: typeof b.error === 'string' && b.error ? b.error : null, bad: bad};
}

HD.agents = {rows: rows, rank: rank, suggest: suggest, inRepo: inRepo, key: key, label: label, folder: folder, NAME_MAX: NAME_MAX};
})();
