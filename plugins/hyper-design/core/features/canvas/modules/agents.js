/* Model — 보낼 곳 고르기 규칙(#214): GET /api/agents 답 → 고를 줄(이 저장소 먼저 · 실행 중 먼저 · 이름)·자동 제안·줄 글. DOM·저장소를 쓰지 않는다.
   HD.agents.rows(body) → {rows:[{id, name, label, folder, status, mine, current}], current, repo, error, bad}
     body = 도우미 답 {agents, current, repo, error?}. 닫힌(closed)·보관된 에이전트와 모양이 틀린 줄은 뺀다(bad = 뺀 틀린 줄 수 — View 가 [hd] 경고)
   rank(list, repo) → 새 목록: repo 안(cwd 가 repo 이거나 그 아래) 먼저, 그다음 running < idle < 그 밖, 그다음 이름(없으면 id)
   suggest(list, repo) → repo 안에서 running 인 에이전트가 정확히 하나면 그것, 아니면 null
   inRepo(cwd, repo) · key(path)(역슬래시 → '/', 끝 '/' 빼기, 드라이브 경로는 대소문자 무시) · label(a) → 이름 40자(넘으면 …) · folder(cwd) → 마지막 폴더 이름
   NAME_MAX = 40
   받는 곳 메뉴(47-5b): menu(body) → {connected, rows, orphan, current, repo, error, bad, empty} — body.connected(접속한 에이전트, GET /api/agents 의 connected)를
     먼저(접속 중 here 먼저 · 이름), Paseo 줄(rows)은 접속 목록에 같은 id 가 있으면 뺀다. orphan = 지금 받는 곳(current)이 어느 목록에도 없으면 {id, label}(예전에 붙인 것 — 보이게).
     접속 줄 = {id, name, label, kind, kindSay, state:'here'|'away', stateSay, listen, progress(60자), current}. empty = 고를 에이전트가 하나도 없음
   KIND_SAY · STATE_SAY · PROGRESS_MAX = 60
   보낸 뒤(47-5b): delivery(fw, n) → {ok, text} — /api/forward 답 via 가 paseo·event·claude 면 에이전트가 받음(ok, 카드 덮개 'AI 수정 중'), 아니면 ok false·text null(대기열 — 셸의 지금 글)
   sentSay(r, {agent, warn}) → {text, ms, ok} — 도우미로 보낸 한 번(r = VS.send 답 {done, left, fw, res})의 알림 글(셸 C6, view-send):
     바로 반영 N건 · 받은 곳(delivery) 또는 대기열 글(agent 가 있으면 '보내지 못해', 없으면 터미널 안내) · 거절된 바로 쓰기의 까닭을 앞에 · warn(빈 레이아웃)을 맨 앞에.
     ms = 대기열·받은 곳·warn 이 있으면 9000, 아니면 0(기본) · ok = 에이전트가 받음(덮개 'AI 수정 중')
     · connect = 대기열에만 남았을 때 {label:'연결', tip}(R27 F04 — 알림은 한 줄, CLI 안내는 tip) */
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

var KIND_SAY = {claude: 'Claude', codex: 'Codex', paseo: 'Paseo', other: '에이전트'};
var STATE_SAY = {here: '접속 중', away: '자리 비움'};
var PROGRESS_MAX = 60;

function cut(t, n) { t = String(t == null ? '' : t).replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; }

function menu(body) {
  var b = body && typeof body === 'object' ? body : {};
  var base = rows(b), cur = base.current;
  var raw = Array.isArray(b.connected) ? b.connected : [];
  var good = raw.filter(ok);
  var conn = good.map(function (a, i) { return {a: a, i: i}; }).sort(function (x, y) {
    var sx = x.a.state === 'here' ? 0 : 1, sy = y.a.state === 'here' ? 0 : 1;
    if (sx !== sy) return sx - sy;
    var nx = nameOf(x.a), ny = nameOf(y.a);
    return nx < ny ? -1 : nx > ny ? 1 : x.i - y.i;
  }).map(function (o) {
    var a = o.a, kind = KIND_SAY[a.kind] ? a.kind : 'other', state = a.state === 'here' ? 'here' : 'away';
    var pr = a.progress && typeof a.progress.text === 'string' ? cut(a.progress.text, PROGRESS_MAX) : '';
    return {id: a.id, name: nameOf(a), label: label(a), kind: kind, kindSay: KIND_SAY[kind], state: state, stateSay: STATE_SAY[state],
            listen: a.listen !== false, progress: pr, current: a.id === cur};
  });
  var seen = {}; conn.forEach(function (c) { seen[c.id] = 1; });
  var paseo = base.rows.filter(function (r) { return !seen[r.id]; });
  var known = !!seen[cur] || paseo.some(function (r) { return r.id === cur; });
  var orphan = cur && !known ? {id: cur, label: cut(cur, NAME_MAX)} : null;
  return {connected: conn, rows: paseo, orphan: orphan, current: cur, repo: base.repo, error: base.error,
          bad: base.bad + (raw.length - good.length), empty: !conn.length && !paseo.length && !orphan};
}

var DELIVERED = {
  paseo: function (n) { return 'AI 에이전트에게 ' + n + '건 보냈어요 — 카드에 “AI 수정 중”'; },
  event: function (n) { return '접속한 AI 에이전트에게 ' + n + '건 보냈어요(실시간) — 카드에 “AI 수정 중”'; },
  claude: function (n) { return 'Claude 세션을 깨워 ' + n + '건 보냈어요 — 카드에 “AI 수정 중”'; }
};
function delivery(fw, n) {
  var via = fw && typeof fw.via === 'string' ? fw.via : '';
  return Object.prototype.hasOwnProperty.call(DELIVERED, via) ? {ok: true, text: DELIVERED[via](n)} : {ok: false, text: null};
}

var QUEUE_TIP = '요청은 대기열 파일(.hd-queue)에 있어요. 받는 곳 칩에서 AI 에이전트를 고르거나, 터미널 에이전트에서 hd notes 로 읽거나, 도우미를 --paseo-agent <id> 로 다시 띄우세요';
function sentSay(r, opt) {
  r = r || {}; opt = opt || {};
  var done = r.done || [], left = r.left || [], warn = opt.warn || '', dv = delivery(r.fw, left.length);
  var queued = !!left.length && !dv.ok;               // 아무도 받지 않음 = 대기열 — 말은 한 줄, CLI 안내는 [연결] 툴팁(R27 F04)
  var ai = !left.length ? '' : dv.ok ? dv.text :
    opt.agent ? 'AI 에이전트에게 보내지 못해 ' + left.length + '건을 대기열에 저장했어요' :
    'AI가 연결되지 않아 ' + left.length + '건을 대기열에 저장했어요';
  var said = (done.length ? '바로 반영 ' + done.length + '건' : '') + (done.length && ai ? ' · ' : '') + ai;
  var refused = ((r.res && r.res.failed) || []).filter(function (f) { return f && f.reason; })[0];   // 도우미가 거절한 바로 쓰기(예: 정책 줄 500자 넘음) — 그 편집은 요청문으로 넘어갔다
  if (refused) said = '파일에 쓰지 못함: ' + refused.reason + (said ? ' · ' + said : '');
  var out = {text: (warn ? warn + (said ? ' · ' : '') : '') + said, ms: ai || warn ? 9000 : 0, ok: dv.ok};
  if (queued) out.connect = {label: '연결', tip: QUEUE_TIP};
  return out;
}

HD.agents = {delivery: delivery, sentSay: sentSay, menu: menu, KIND_SAY: KIND_SAY, STATE_SAY: STATE_SAY, PROGRESS_MAX: PROGRESS_MAX, rows: rows, rank: rank, suggest: suggest, inRepo: inRepo, key: key, label: label, folder: folder, NAME_MAX: NAME_MAX};
})();
