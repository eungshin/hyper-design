/* View — 화면 파일에 바로 쓰기(helper.py 와 주고받기, 조각 2.2): 모드 칩 · 잇기·끊기·삭제 바로 쓰기(E1·E10) · 되돌리기 = 되살리기 · 보내기 · 쓴 뒤 바뀐 카드만 다시(E17).
   어떤 편집을 바로 쓰는지는 HD.edits.instantOf(Model). 판 다시 그리기·카드 다시 싣기·기록은 셸이 ctx 로 넘긴다(View 끼리 부르지 않음).
   바로 쓰기는 async apply(47-4b): {edits, async:true} → 답 {accepted,…}을 HD.live.answer 로 applied 로 읽는다(옛 도우미의 동기 답도 그대로). 빌드 실패는 이벤트(view-live → 셸).
   HD.viewSync.mount(ctx) → {on, write(label, list) → Promise, del(ids) → Promise, send(list) → Promise<{ok, done, left, fw, res}>, refresh(changed, stamp)(이벤트: 다른 곳의 사람 쓰기)}
   ctx = {chip, aiChip, agent, on, token, toast(msg, undoable), record(op), pend(label, list), request(list) → text, data(D, changed, stamp), retryMs?(쓴 뒤 다시 불러오기 재시도 간격, 기본 1초),
         fresh?(stamp|null, ids) → bool — 캔버스가 쓴 뒤 다시 실을까(실시간 알림이 이미 실었으면 false, view-live own) ·
         wrote?(res, list) — write() 가 파일에 쓴 직후·카드를 다시 싣기 전(res.paths = {편집 id: 그 요소의 새 경로}, task 49b 고른 요소 따라가기)}
   aiChip = 보내기가 어디로 가는지(agent = helper 의 --paseo-agent → 'AI 연결됨', 없으면 '받는 곳 없음' = 대기열 파일에만, R4)
     aiChip 에 'hd-agent' 이벤트 {detail:{agent, name}} 가 오면(view-agents 가 고른 뒤, #214) 'AI 연결됨 · <name>' 으로 고치고 window.__hdAgent 도 바꾼다
   보내기의 /api/forward 에 notes = 넘긴 메모 id(최대 200, 47-5b — 받는 에이전트가 어느 메모인지 안다). 받는 곳은 도우미의 붙은 에이전트(attach) 그대로.
   되돌리기 답 reverted:true(뒤 빌드가 깨져 이미 되돌린 쓰기, 47-5a) = 토스트 + 그 기록 줄에 '빌드 실패로 이미 되돌림'(op.bind 로 받은 표시 함수, HD.undoAnswer).
   on 이 아니면(file:// · 토큰 없음) 칩만 '파일로 열림' 이고 나머지는 부르지 않는다. 네트워크가 끊기면 Promise 가 실패 → 셸이 지금처럼(반영 대기·복사) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var on = !!(ctx.on && ctx.token);
  ctx.chip.textContent = on ? '파일에 바로 씀' : '파일로 열림 · 바로 쓰기 안 됨';
  ctx.chip.classList.toggle('on', on);
  ctx.chip.title = on ? '삭제·잇기·끊기가 화면 파일에 바로 써져요(되돌리기 됨)' : '보내기는 요청문을 복사해요 — 터미널에 붙여넣으세요';
  function paintAi(agent, name) {
    ctx.aiChip.textContent = agent ? 'AI 연결됨' + (name ? ' · ' + name : '') : '받는 곳 없음';
    ctx.aiChip.classList.toggle('on', !!agent);
    ctx.aiChip.title = agent ? '보내기 = Paseo 에이전트 ' + (name ? name + ' (' + agent + ')' : agent) + ' 터미널에 요청을 넣어요 — 바꾸려면 누르세요' : '연결된 AI 터미널이 없어요 — 보내기는 요청을 .hd-queue 대기열 파일에만 저장해요. 칩을 눌러 Paseo 에이전트를 고르거나, 터미널에서 hd notes 로 읽으세요';
  }
  if (ctx.aiChip) {
    ctx.aiChip.hidden = !on;
    paintAi(ctx.agent, null);
    // 보낼 곳이 바뀜(view-agents 가 /api/attach 성공 뒤 보내는 의도) — 칩과 셸이 읽는 window.__hdAgent 를 함께 고친다
    ctx.aiChip.addEventListener('hd-agent', function (e) {
      var d = e.detail || {};
      window.__hdAgent = d.agent || null;
      paintAi(d.agent || null, d.name || null);
    });
  }

  function post(url, body) {
    return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-HD-Token': ctx.token}, body: JSON.stringify(body || {})})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok && r.status !== 409) throw new Error('sync ' + r.status); j.status = r.status; return j; }); });
  }
  function wire(n) { return {id: n.id, screen: n.screen, edit: n.edit, op: n.op, to: n.to, path: n.path, value: n.value, old: n.old, index: n.index}; }
  function reload(changed, stamp) {                 // 새 데이터 → 셸이 판·바뀐 카드만 다시(보던 자리·배율·고른 것 유지)
    return post('/api/data').then(function (d) { delete d.status; ctx.data(d, changed || [], stamp); });
  }
  // 쓰는 중(답·다시 싣기 전)에 온 다른 곳의 쓰기 알림은 끝난 뒤에 — 쓴 뒤 고른 요소 따라가기(wrote, 49b)가 먼저 돌게
  var inflight = 0, later = [];
  function track(p) {
    inflight++;
    var done = function () { inflight--; if (!inflight) { var l = later; later = []; l.forEach(function (x) { refresh(x[0], x[1]); }); } };
    return p.then(function (v) { done(); return v; }, function (e) { done(); throw e; });
  }
  function takeLater(stamp) {                       // 쓰는 중에 먼저 온 내 쓰기의 알림 = 내 답이 맡는다(알림 줄에서 뺌 — 바로 반영의 hold·같은 내용 견주기가 그대로 돌게)
    if (!stamp) return false;
    var n = later.length; later = later.filter(function (x) { return x[1] !== stamp; });
    return later.length < n;
  }
  function apply(list) {                            // 바로 쓰기 — async(47-4b): 쓰고 바로 답, 빌드는 뒤에서(실패 = build.failed 이벤트, view-live)
    return post('/api/apply', {edits: list.map(wire), async: true}).then(function (r) { return HD.live ? HD.live.answer(r) : r; });
  }
  // 파일에 쓴 뒤의 다시 불러오기: 실패해도 쓰기는 이미 됐다 → 반영 대기로 되돌리지 않고(S2) 알린 뒤 한 번 더 불러온다. 늘 이루어진다.
  // own = 캔버스 스스로 쓴 것(stamp — 도장 없는 되살리기는 null): 실시간 알림이 같은 쓰기를 이미 실었으면 다시 싣지 않는다(ctx.fresh, 47-4b)
  function refresh(changed, stamp, own) {
    if (own !== undefined && !takeLater(own) && ctx.fresh && !ctx.fresh(own, changed || [])) return Promise.resolve();
    return reload(changed, stamp).catch(function () {
      ctx.toast('파일에는 썼어요 — 판을 새로 그리지 못해 다시 불러와요');
      return new Promise(function (ok) { setTimeout(ok, ctx.retryMs || 1000); })
        .then(function () { return reload(changed, stamp); })
        .catch(function () { ctx.toast('파일에는 썼어요 — 판을 새로 그리지 못했어요. 새로고침해 주세요'); });
    });
  }
  function restore(stamp, label, mark) {
    return post('/api/restore', {stamp: stamp}).then(function (r) {
      var a = HD.undoAnswer.read(r);
      if (mark) mark(a.note);                         // 기록 줄 표시(이미 되돌림 · 아니면 지움)
      if (a.kind === 'already') { ctx.toast(a.msg, false, 6000); return; }
      if (a.kind !== 'done') { ctx.toast(a.msg); return; }
      return refresh(r.changed, 'r' + stamp, null);
    }).catch(function () { ctx.toast('되돌리지 못했어요 — 파일에 바로 쓰기가 꺼져 있어요: ' + label); });
  }
  // 한 번 쓴 일 = 기록 한 줄(status file, 잠그지 않음). 되돌리기 = 되살리기, 다시 하기 = 같은 쓰기를 다시(새 stamp)
  function logged(label, again, stamp) {
    var cur = stamp, mark = null;
    ctx.record({label: label, status: 'file', bind: function (f) { mark = f; },   // 기록 패널이 줄 표시 함수를 건넨다(47-5b)
                undo: function () { track(restore(cur, label, mark)); },
                redo: function () {               // 다시 쓰기가 안 되면 말한다(기록은 다시 한 줄로 보이지만 파일은 그대로)
                  var fail = function () { ctx.toast('다시 하지 못했어요 — 파일에 쓰지 못했어요: ' + label); };
                  track(again().then(function (r) { if (r && r.stamp) { cur = r.stamp; if (mark) mark(''); return refresh(r.changed, r.stamp, r.stamp); } fail(); }, fail));
                }});
  }

  function write(label, list) {
    var go = function () { return apply(list); };
    return go().then(function (res) {
      var ok = {}; (res.applied || []).forEach(function (id) { ok[id] = 1; });
      var bad = list.filter(function (n) { return !ok[n.id]; });
      if (bad.length) ctx.pend(label, bad);          // 못 쓴 것은 반영 대기로(이유는 보내기 때 요청문에)
      if (!res.applied || !res.applied.length) return res;
      logged(label, function () { return apply(list.filter(function (n) { return ok[n.id]; })); }, res.stamp);
      if (ctx.wrote) { try { ctx.wrote(res, list); } catch (e) { console.error('[hd] 쓴 뒤 고른 요소 따라가기: ' + (e && e.message || e)); } }   // 다시 싣기 전에(task 49b)
      ctx.toast(label + ' — 파일에 썼어요' + (bad.length ? ' · ' + bad.length + '개는 반영 대기' : ''), true);
      return refresh(res.changed, res.stamp, res.stamp).then(function () { return res; });   // 쓴 뒤로는 실패해도 write() 는 이루어짐(다시 넣지 않게)
    });
  }
  function del(ids) {
    return post('/api/delete', {screens: ids}).then(function (res) {
      if (!res.deleted || !res.deleted.length) { ctx.toast('지우지 못했어요' + (res.error ? ': ' + res.error : '')); return res; }
      var label = '화면 삭제';
      logged(label, function () { return post('/api/delete', {screens: res.deleted}); }, res.stamp);
      var cut = (res.cut || []).length;
      ctx.toast(res.deleted.length + '개 화면을 지웠어요' + (cut ? ' · 오는 연결 ' + cut + '개도 끊김' : ''), true);   // E10
      return refresh(res.changed, res.stamp, res.stamp).then(function () { return res; });
    });
  }
  // 보내기: 바로 쓸 수 있는 편집 → 파일, 나머지·못 쓴 것 → 터미널(Paseo 또는 대기열 파일)
  function send(list) {
    var direct = list.filter(HD.edits.directOf), rest = list.filter(function (n) { return !HD.edits.directOf(n); });
    return apply(direct).then(function (res) {
      var ok = {}; (res.applied || []).forEach(function (id) { ok[id] = 1; });
      var done = direct.filter(function (n) { return ok[n.id]; }), left = rest.concat(direct.filter(function (n) { return !ok[n.id]; }));
      var fin = function (fw) {
        return (done.length ? refresh(res.changed, res.stamp, res.stamp) : Promise.resolve()).then(function () { return {ok: ok, done: done, left: left, fw: fw, res: res}; });
      };
      if (!left.length) return fin(null);
      var t = ctx.request(left); window.__hdLastSend = t;
      var ids = left.map(function (n) { return n && n.id != null ? String(n.id) : ''; }).filter(Boolean).slice(0, 200);   // 서버 한도 NOTES_MAX
      return post('/api/forward', {text: t, notes: ids}).then(fin);
    });
  }
  return {on: on, write: function (l, x) { return track(write(l, x)); }, del: function (x) { return track(del(x)); }, send: function (x) { return track(send(x)); },
          refresh: function (changed, stamp) { if (inflight) { later.push([changed, stamp]); return Promise.resolve(); } return refresh(changed, stamp); }};
}

HD.viewSync = {mount: mount};
})();
