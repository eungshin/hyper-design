/* View — 바로 반영(task 49c): 글자(그 자리 contenteditable)·복제·옮기기·끌어 옮기기를 화면 틀에 먼저 보이고, 도우미 /api/apply 답이 오면 남기거나(applied) 되돌린다(applied:[]·오류).
   규칙(남김/되돌림 판정·건너뛸 다시 싣기·알림 글)은 HD.optimistic(Model), 옮길 칸 목록은 HD.reorder(Model). 편집 메모 모양은 HD.edits(note·say) 그대로 — /api/apply 약속은 바꾸지 않는다.
   화면 메시지(palette.js): hd-inline → hd-inline-on · hd-inline-done · hd-opt → hd-opt-done · hd-opt-undo. tag 하나 = 화면에 먼저 보인 변경 하나(모든 틀에 같은 tag).
   옮기기 k칸 = 도우미 move(up|down = 옆 형제와 맞바꿈)를 차례로 k번(앞 답의 paths 로 다음 경로) — apply_edits 는 한 묶음 안 같은 요소의 move 를 하나로 겹쳐 쓴다.
     중간 쓰기의 다시 싣기는 건너뛴다(hold) · 중간에 실패하면 화면을 실제로 쓴 칸까지만 되돌린다.
   상태 = 진행 중 변경(HD.optimistic reduce) + 화면마다 '방금 낙관 반영함'(take 가 한 번 읽고 지움) + 열린 글자 고치기(tag 마다). 저장 없음.
   HD.viewOptimistic.mount(ctx) → {inline(screen, h, where, fallback) → bool, run(label, screen, notes, items, where), moves(label, screen, h, dirs, where), hold(screen), take(screen), typing(where)}
   ctx = {on() → 도우미로 바로 쓰나, write(label, list) → Promise<res>(view-sync write), queue(label, list, msg)(반영 대기로 — 도우미 없음·연결 끊김),
          frames(screen) → [{f: iframe, where: 'board'|'modal'}](실린 틀만), toast(msg, undoable, ms), picked(screen, hit, where)(크게 보기 고른 요소를 옮긴 자리로), warn(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ACK_MS = 1500;                                    // hd-inline-on 이 이 안에 없으면(palette.js 가 옛것) 예전 글 칸으로

function mount(ctx) {
  var O = HD.optimistic, E = HD.edits, st = O.initial(), seq = 0, fresh = {}, ins = {}, waits = {};   // ins = 열린 글자 고치기(tag 마다 — 틀이 앞 것을 저장으로 끝내고 답할 수 있게)
  var warn = ctx.warn || function (m) { console.warn(m); };

  function newTag(k) { return k + ':' + Date.now().toString(36) + ':' + (++seq); }
  function post(f, msg) { try { if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*'); } catch (e) { warn('[hd] 바로 반영: 화면에 보내지 못했어요 — ' + (e && e.message || e)); } }
  function each(screen, msg, skip) { ctx.frames(screen).forEach(function (x) { if (x.f !== skip) { if (msg.type === 'hd-opt') x.f.setAttribute('data-hd-opt', ''); post(x.f, msg); } }); }   // data-hd-opt = 이 틀은 먼저 바뀌었다(view-swap 이 같은 내용이면 조용히 바꾸는 표시 — 틀과 함께 사라진다)
  function frameFor(screen, where) { var l = ctx.frames(screen).filter(function (x) { return x.where === where; }); return l.length ? l[l.length - 1].f : null; }
  function typingMark(f, on) { var c = f && f.closest ? f.closest('.card') : null; if (c) c.classList.toggle('hd-typing', on); }
  function mark(n) { n.opt = true; return n; }        // 낙관 반영 메모 — 셸 view-sync pend 가 실패를 반영 대기로 다시 넣지 않게(화면은 되돌렸다)
  function plain(list) { list.forEach(function (n) { delete n.opt; }); return list; }

  // 화면에 먼저 보인 변경 tag 를 도우미에 쓰기 — 남김 | 되돌림(+알림) | 연결 끊김(되돌리고 반영 대기로)
  function settle(label, screen, tag, notes) {
    st = O.reduce(st, {type: 'start', tag: tag, screen: screen, steps: 1});
    fresh[screen] = true;
    return ctx.write(label, notes).then(function (res) {
      st = O.reduce(st, {type: 'step', tag: tag});
      var oc = O.outcome(res, notes.map(function (n) { return n.id; }));
      if (oc.kept) { st = O.reduce(st, {type: 'keep', tag: tag}); end(tag); return {kept: true, res: res}; }
      st = O.reduce(st, {type: 'revert', tag: tag, why: oc.why});
      each(screen, {type: 'hd-opt-undo', tag: tag});
      end(tag);
      return {kept: false, why: oc.why, res: res};
    }, function (e) {
      st = O.reduce(st, {type: 'revert', tag: tag, why: O.WHY});
      each(screen, {type: 'hd-opt-undo', tag: tag});
      end(tag);
      warn('[hd] 바로 반영: 도우미에 쓰지 못했어요 — ' + (e && e.message || e));
      ctx.queue(label, plain(notes), label + ' — 도우미에 닿지 않아 화면을 되돌리고 반영 대기로 남겼어요');
      return {kept: false, why: O.WHY, offline: true};
    });
  }
  function end(tag) { st = O.reduce(st, {type: 'end', tag: tag}); }

  // 복제·옮기기 한 칸·글자(다른 틀) — items = palette.js hd-opt 항목
  function run(label, screen, notes, items, where) {
    var tag = newTag('op');
    if (where === 'modal') waits[tag] = {screen: screen, where: where};
    each(screen, {type: 'hd-opt', tag: tag, items: items});
    return settle(label, screen, tag, notes.map(mark)).then(function (r) {
      if (!r.kept && !r.offline) ctx.toast(O.failText(label, r.why, 0, 1), false, 6000);
      return r;
    });
  }

  // 끌어 옮기기: 같은 쪽으로 dirs.length 칸 — 화면은 한 번에, 도우미는 한 칸씩 차례로
  function moves(label, screen, h, dirs, where) {
    var dir = dirs[0], n = dirs.length, tag = newTag('mv'), path = h.path, done = 0;
    if (!n || dirs.some(function (d) { return d !== dir; })) { warn('[hd] 끌어 옮기기: 한쪽 방향 칸 목록이 아니에요 — ' + dirs.join(',')); return Promise.resolve({kept: false}); }
    if (where === 'modal') waits[tag] = {screen: screen, where: where};
    each(screen, {type: 'hd-opt', tag: tag, items: [{path: h.path, move: dir, n: n}]});
    st = O.reduce(st, {type: 'start', tag: tag, screen: screen, steps: n});
    fresh[screen] = true;
    var note = function () {
      var x = E.note(screen, {path: path, text: h.text, rect: h.rect, quote: h.quote}, E.say.move(dir), dir);
      x.edit = 'move'; return mark(x);
    };
    var back = function (why) {                       // 실제로 쓴 칸까지만 남기고 나머지는 되돌린다
      st = O.reduce(st, {type: 'revert', tag: tag, why: why}); end(tag);
      each(screen, {type: 'hd-opt-undo', tag: tag});
      if (done) each(screen, {type: 'hd-opt', tag: newTag('mvpart'), items: [{path: h.path, move: dir, n: done}]});
      ctx.toast(O.failText(label, why, done, n), false, 6000);
      return {kept: false, why: why, done: done};
    };
    var step = function () {
      var x = note();
      return ctx.write(label, [x]).then(function (res) {
        var oc = O.outcome(res, [x.id]);
        if (!oc.kept) return back(oc.why);
        done++; st = O.reduce(st, {type: 'step', tag: tag});
        if (done >= n) { st = O.reduce(st, {type: 'keep', tag: tag}); end(tag); return {kept: true, done: done}; }
        var np = res.paths && res.paths[x.id];
        if (!np) return back('옮긴 요소의 새 자리를 도우미가 알려 주지 않았어요');
        path = np; return step();
      }, function (e) {
        warn('[hd] 끌어 옮기기: 도우미에 쓰지 못했어요 — ' + (e && e.message || e));
        return back(O.WHY);
      });
    };
    return step();
  }

  // 그 자리 글자 고치기: 그 틀에 hd-inline → (hd-inline-on 없으면 fallback) → hd-inline-done 이면 다른 틀에도 같은 글 → 쓰기
  function inline(screen, h, where, fallback) {
    var f = frameFor(screen, where);
    if (!f || !f.contentWindow) return false;
    var tag = newTag('in');                           // 앞 것이 열려 있으면 틀(palette.js)이 저장으로 끝내고 그 tag 로 답한다
    ins[tag] = {tag: tag, f: f, screen: screen, h: h, where: where, on: false,
                t: setTimeout(function () { var q = ins[tag]; if (q && !q.on) { delete ins[tag]; warn('[hd] 그 자리 글자 고치기: 화면이 답하지 않아 글 칸으로 열어요(palette.js 옛것?)'); if (fallback) fallback(); } }, ACK_MS)};
    post(f, {type: 'hd-inline', path: h.path, tag: tag});
    return true;
  }
  function inlineDone(d) {
    var q = ins[d.tag]; if (!q) return;
    delete ins[d.tag]; clearTimeout(q.t); typingMark(q.f, false);
    q.f.setAttribute('data-hd-opt', '');
    if (document.activeElement === q.f) q.f.blur();   // 키(도구 키·Ctrl+Z·Esc)가 화면 iframe 이 아니라 캔버스로 오게
    if (!d.ok) {
      if (d.why === 'missing') ctx.toast('고칠 요소를 화면에서 찾지 못했어요 — 다시 골라 주세요');
      else if (d.why === 'text') ctx.toast('안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요');
      return;
    }
    var v = String(d.text == null ? '' : d.text), n = E.note(q.screen, q.h, E.say.text(v));
    n.edit = 'text'; n.value = v;
    if (!ctx.on()) {                                   // 도우미 없음 = 예전처럼 반영 대기(미리보기 점선) — 그 자리 바꿈은 거두고 미리보기가 맡는다
      post(q.f, {type: 'hd-opt-undo', tag: q.tag});
      ctx.queue('글자 고치기', [n]);
      return;
    }
    each(q.screen, {type: 'hd-opt', tag: q.tag, items: [{path: q.h.path, text: v}]}, q.f);
    settle('글자 고치기', q.screen, q.tag, [mark(n)]).then(function (r) {
      if (!r.kept && !r.offline) ctx.toast(O.failText('글자 고치기', r.why, 0, 1), false, 6000);
    });
  }

  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || typeof d.tag !== 'string') return;
    var q = ins[d.tag];
    if (d.type === 'hd-inline-on' && q && e.source === q.f.contentWindow) { q.on = true; clearTimeout(q.t); typingMark(q.f, true); }
    else if (d.type === 'hd-inline-done' && q && e.source === q.f.contentWindow) inlineDone(d);
    else if (d.type === 'hd-opt-done' && waits[d.tag]) {
      var w = waits[d.tag], f = frameFor(w.screen, w.where);
      if (!f || e.source !== f.contentWindow) return;
      delete waits[d.tag];
      if (d.hit && d.hit.path && O.phase(st, d.tag) !== 'reverted') ctx.picked(w.screen, d.hit, w.where);
      else if (!d.ok) warn('[hd] 바로 반영: 화면에서 요소를 찾지 못해 미리 바꾸지 못했어요 — 도우미 답을 기다려요');
    }
  });

  return {inline: inline, run: run, moves: moves,
          hold: function (screen) { return O.hold(st, screen); },
          take: function (screen) { var v = !!fresh[screen]; delete fresh[screen]; return v; },
          typing: function (where) { return Object.keys(ins).some(function (k) { return ins[k].on && (!where || ins[k].where === where); }); }};
}

HD.viewOptimistic = {mount: mount};
})();
