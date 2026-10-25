/* View — 화면 파일을 바꾸는 편집을 쌓는 길 하나(DOM 없음): 편집 메모 만들기 · 바로 쓰기(도우미) 또는 반영 대기 + 되돌리기 한 줄 · 잇기·도착 바꾸기·선 자르기.
   바로 쓰기(잇기·끊기 = HD.edits.instantOf)는 ctx.sync() 가 켜져 있으면 VS.write — 도우미가 못 받으면(거절된 Promise) 같은 편집을 반영 대기로(keep) 다시 쌓는다.
   반영 대기: put = drops 빼고 list 더하기, take = list 빼고 drops 되돌리기 — record 의 redo/undo 가 그 둘(대칭).
   HD.viewEditPath.mount(ctx) → {scr(id), note(screen, h, text, op?, to?), add(label, list, msg?, drops?, keep?), linkTo(from, hits, to), cutText(to), linksTo(from, to, cb), cutPairs(pairs, oneWay?)}
   ctx = {notes: NS(store), save()(saveNotes), record(op), toast(msg, undoable?, ms?), title(id), sync() → VS|null, linksOf(from, cb)(VL.linksOf)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var NS = ctx.notes, E = HD.edits;

  function scr(id) { return '"' + ctx.title(id) + '"(' + id + ')'; }
  function note(screen, h, text, op, to) { return E.note(screen, h, text, op, to); }   // op: link · cut · untrigger · trigger · new
  function add(label, list, msg, drops, keep) {   // drops = 같이 취소할 보내지 않은 편집(E4) — 되돌리면 돌아온다 · keep = 바로 쓰지 않고 반영 대기로
    drops = drops || [];
    if (!list.length && !drops.length) return;
    var VS = ctx.sync();
    if (VS && VS.on && !keep && !drops.length && list.every(E.instantOf)) {   // 잇기·끊기 = 화면 파일에 바로(조각 2.2)
      VS.write(label, list).then(function (res) {      // 도우미가 거절한 까닭(한국어)을 알린다 — 그 편집은 반영 대기로 남았다
        var f = res && res.failed && res.failed[0]; if (f && f.reason) ctx.toast(label + ' — 파일에 쓰지 못해 반영 대기로 남겼어요: ' + f.reason, false, 6000);
      }, function () { add(label, list, msg, drops, true); });
      return;
    }
    var lids = list.map(function (n) { return n.id; }), dids = drops.map(function (d) { return d.id; });
    var put = function () {
      NS.remove(function (x) { return dids.indexOf(x.id) >= 0; });
      list.forEach(function (n) { if (!NS.find(n.id)) { n.sent = false; NS.add(n); } });
      ctx.save();
    };
    var take = function () {
      NS.remove(function (x) { return lids.indexOf(x.id) >= 0; });
      drops.forEach(function (d) { if (!NS.find(d.id)) NS.add(d); });
      ctx.save();
    };
    put();
    ctx.record({label: label, status: 'pending', undo: take, redo: put});
    ctx.toast(msg || label + ' — 반영 대기', true);
  }
  function linkTo(from, hits, to) {                    // 요소들 → 도착 화면 to (지금 가는 곳이 있으면 도착 바꾸기)
    var list = hits.filter(function (h) { return h.to !== to; }).map(function (h) {
      var n = note(from, h, h.to ? E.say.retarget(scr(h.to), scr(to)) : E.say.link(scr(to)), 'link', to);
      if (h.to) n.was = h.to;                          // 도착 바꾸기: 판의 선에서 예전 도착을 뺀다
      return n;
    });
    if (!list.length) { ctx.toast('이미 그 화면으로 가요'); return; }
    add(hits.some(function (h) { return h.to; }) ? '트리거 도착 바꾸기' : '트리거 연결', list, ctx.title(to) + '(으)로 이었어요 — 반영 대기');
  }
  function cutText(to) { return E.say.cut(scr(to)); }
  // 그 방향(from → to)의 화면 안 링크 — 고른 화면이면 바로, 아니면 그 화면에 물어서
  function linksTo(from, to, cb) {
    ctx.linksOf(from, function (its) {
      if (!its) { ctx.toast('이 화면은 연결을 알려 주지 않아요(palette.js 없음)'); cb([]); return; }
      cb(its.filter(function (it) { return it.to === to; }).map(function (it) { return {path: it.path, text: it.text, rect: it.rect, to: it.to}; }));
    });
  }
  // 선 자르기: 쌍마다 그 화면 안 링크 전부 끊기 메모. 아직 반영 안 된 연결(점선·바뀐 도착)이면 끊기 대신 그 편집 취소(E4). oneWay = 태그 하나(그 방향만)
  function cutPairs(pairs, oneWay) {
    var dirs = [];
    pairs.forEach(function (p) { dirs.push([p[0], p[1]]); if (!oneWay) dirs.push([p[1], p[0]]); });
    var list = [], drops = [], left = dirs.length;
    dirs.forEach(function (dr) {
      linksTo(dr[0], dr[1], function (its) {
        its.forEach(function (it) {
          var pn = E.pendingLink(NS.list(), dr[0], it.path, it.to);
          if (pn) { if (drops.indexOf(pn) < 0) drops.push(pn); } else list.push(note(dr[0], it, cutText(it.to), 'cut', it.to));
        });
        if (--left) return;
        if (!list.length && !drops.length) { ctx.toast('끊을 연결을 찾지 못했어요'); return; }
        add(list.length ? '선 자르기' : '반영 대기 연결 취소', list,
            (list.length ? list.length + '개 연결을 끊었어요' : '') + (list.length && drops.length ? ' · ' : '') + (drops.length ? '반영 대기 ' + drops.length + '개를 취소했어요' : ''), drops);
      });
    });
  }

  return {scr: scr, note: note, add: add, linkTo: linkTo, cutText: cutText, linksTo: linksTo, cutPairs: cutPairs};
}

HD.viewEditPath = {mount: mount};
})();
