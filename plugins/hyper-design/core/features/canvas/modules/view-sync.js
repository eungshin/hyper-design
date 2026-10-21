/* View — 화면 파일에 바로 쓰기(helper.py 와 주고받기, 조각 2.2): 모드 칩 · 잇기·끊기·삭제 바로 쓰기(E1·E10) · 되돌리기 = 되살리기 · 보내기 · 쓴 뒤 바뀐 카드만 다시(E17).
   어떤 편집을 바로 쓰는지는 HD.edits.instantOf(Model). 판 다시 그리기·카드 다시 싣기·기록은 셸이 ctx 로 넘긴다(View 끼리 부르지 않음).
   HD.viewSync.mount(ctx) → {on, write(label, list) → Promise, del(ids) → Promise, send(list) → Promise<{ok, done, left, fw, res}>}
   ctx = {chip, on, token, toast(msg, undoable), record(op), pend(label, list), request(list) → text, data(D, changed, stamp)}
   on 이 아니면(file:// · 토큰 없음) 칩만 '파일로 열림' 이고 나머지는 부르지 않는다. 네트워크가 끊기면 Promise 가 실패 → 셸이 지금처럼(반영 대기·복사) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var on = !!(ctx.on && ctx.token);
  ctx.chip.textContent = on ? '파일에 바로 씀' : '파일로 열림 · 바로 쓰기 안 됨';
  ctx.chip.classList.toggle('on', on);
  ctx.chip.title = on ? '삭제·잇기·끊기가 화면 파일에 바로 써져요(되돌리기 됨)' : '보내기는 요청문을 복사해요 — 터미널에 붙여넣으세요';

  function post(url, body) {
    return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-HD-Token': ctx.token}, body: JSON.stringify(body || {})})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok && r.status !== 409) throw new Error('sync ' + r.status); j.status = r.status; return j; }); });
  }
  function wire(n) { return {id: n.id, screen: n.screen, edit: n.edit, op: n.op, to: n.to, path: n.path, value: n.value, index: n.index}; }
  function reload(changed, stamp) {                 // 새 데이터 → 셸이 판·바뀐 카드만 다시(보던 자리·배율·고른 것 유지)
    return post('/api/data').then(function (d) { delete d.status; ctx.data(d, changed || [], stamp); });
  }
  function restore(stamp, label) {
    return post('/api/restore', {stamp: stamp}).then(function (r) {
      if (r.error) { ctx.toast(r.reason === 'changed-since' ? '그 뒤에 파일이 바뀌어 되돌릴 수 없어요' : '되돌리지 못했어요: ' + r.error); return; }
      return reload(r.changed, 'r' + stamp);
    }).catch(function () { ctx.toast('되돌리지 못했어요 — 파일에 바로 쓰기가 꺼져 있어요: ' + label); });
  }
  // 한 번 쓴 일 = 기록 한 줄(status file, 잠그지 않음). 되돌리기 = 되살리기, 다시 하기 = 같은 쓰기를 다시(새 stamp)
  function logged(label, again, stamp) {
    var cur = stamp;
    ctx.record({label: label, status: 'file',
                undo: function () { restore(cur, label); },
                redo: function () { again().then(function (r) { if (r && r.stamp) { cur = r.stamp; return reload(r.changed, r.stamp); } }); }});
  }

  function write(label, list) {
    var go = function () { return post('/api/apply', {edits: list.map(wire)}); };
    return go().then(function (res) {
      var ok = {}; (res.applied || []).forEach(function (id) { ok[id] = 1; });
      var bad = list.filter(function (n) { return !ok[n.id]; });
      if (bad.length) ctx.pend(label, bad);          // 못 쓴 것은 반영 대기로(이유는 보내기 때 요청문에)
      if (!res.applied || !res.applied.length) return res;
      logged(label, function () { return post('/api/apply', {edits: list.filter(function (n) { return ok[n.id]; }).map(wire)}); }, res.stamp);
      ctx.toast(label + ' — 파일에 썼어요' + (bad.length ? ' · ' + bad.length + '개는 반영 대기' : ''), true);
      return reload(res.changed, res.stamp).then(function () { return res; });
    });
  }
  function del(ids) {
    return post('/api/delete', {screens: ids}).then(function (res) {
      if (!res.deleted || !res.deleted.length) { ctx.toast('지우지 못했어요' + (res.error ? ': ' + res.error : '')); return res; }
      var label = '화면 삭제';
      logged(label, function () { return post('/api/delete', {screens: res.deleted}); }, res.stamp);
      var cut = (res.cut || []).length;
      ctx.toast(res.deleted.length + '개 화면을 지웠어요' + (cut ? ' · 오는 연결 ' + cut + '개도 끊김' : ''), true);   // E10
      return reload(res.changed, res.stamp).then(function () { return res; });
    });
  }
  // 보내기: 바로 쓸 수 있는 편집 → 파일, 나머지·못 쓴 것 → 터미널(Paseo 또는 대기열 파일)
  function send(list) {
    var direct = list.filter(HD.edits.directOf), rest = list.filter(function (n) { return !HD.edits.directOf(n); });
    return post('/api/apply', {edits: direct.map(wire)}).then(function (res) {
      var ok = {}; (res.applied || []).forEach(function (id) { ok[id] = 1; });
      var done = direct.filter(function (n) { return ok[n.id]; }), left = rest.concat(direct.filter(function (n) { return !ok[n.id]; }));
      var fin = function (fw) {
        return (done.length ? reload(res.changed, res.stamp) : Promise.resolve()).then(function () { return {ok: ok, done: done, left: left, fw: fw, res: res}; });
      };
      if (!left.length) return fin(null);
      var t = ctx.request(left); window.__hdLastSend = t;
      return post('/api/forward', {text: t}).then(fin);
    });
  }
  return {on: on, write: write, del: del, send: send};
}

HD.viewSync = {mount: mount};
})();
