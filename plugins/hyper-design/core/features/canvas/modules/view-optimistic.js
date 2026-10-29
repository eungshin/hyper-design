/* View — 바로 반영(task 49c·49d): 글자(그 자리 contenteditable)·지우기·복제·옮기기·끌어 옮기기를 화면 틀에 먼저 보이고, 도우미 /api/apply 답이 오면 남기거나(applied) 되돌린다(applied:[]·오류).
   규칙(남김/되돌림 판정·건너뛸 다시 싣기·알림 글)은 HD.optimistic(Model), 옮길 칸 목록은 HD.reorder(Model). 편집 메모 모양은 HD.edits(note·say) 그대로 — /api/apply 약속은 바꾸지 않는다.
   화면 메시지(palette.js): hd-inline → hd-inline-on · hd-inline-done · hd-opt → hd-opt-done · hd-opt-undo. tag 하나 = 화면에 먼저 보인 변경 하나(모든 틀에 같은 tag).
   끌어 옮기기(51-5) = 도우미 move op:to 쓰기 하나(되돌리기 한 줄) · Alt 끌기 = duplicate → 복사본 move op:to(쓰기 2, 틈이 원본 바로 뒤면 1 — 한 묶음으로는 못 보냄, reorder.plan).
     둘째 쓰기 전 다시 싣기는 건너뛴다(hold) · 옮기기만 실패하면 화면도 파일처럼(복사본 = 원본 바로 뒤) + partText.
   상태 = 진행 중 변경(HD.optimistic reduce) + 화면마다 '방금 낙관 반영함'(take 가 한 번 읽고 지움) + 열린 글자 고치기(tag 마다). 저장 없음.
   async apply(47-4b): 답이 async 면 받은 편집 id 를 빌드 확인까지 기억 — built(ids)(build.done) 가 지우고, reverted(ids, why)(build.failed) → 그 변경을 거두고(hd-opt-undo) 토스트,
     되돌린 것 중 내 것 id 목록을 돌려준다(셸이 그 화면을 다시 싣는다 — 파일은 도우미가 이미 되돌림).
   HD.viewOptimistic.mount(ctx) → {built(ids), reverted(ids, why) → [id], inline(screen, h, where, fallback) → bool, run(label, screen, notes, items, where), edit(label, screen, note, where) → Promise|null(항목은 HD.optimistic.item — 못 하면 null), moves(label, screen, h, dirs, where)(h.drop = {from, slot, copy} — 51-5), hold(screen), take(screen), typing(where),
                                       away(where)(고치는 중 다른 곳을 누름 — 끝난 뒤 그 요소를 다시 고르지 않는다, R52)}
   ctx = {on() → 도우미로 바로 쓰나, write(label, list) → Promise<res>(view-sync write), queue(label, list, msg)(반영 대기로 — 도우미 없음·연결 끊김),
          frames(screen) → [{f: iframe, where: 'board'|'modal'}](실린 틀만), toast(msg, undoable, ms), picked(screen, hit, where)(고른 요소를 옮긴 자리로 · 그 자리 글자 고치기를 마치거나 취소한 뒤 그 요소를 다시 — 판·크게 보기, 51-2), warn(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ACK_MS = 1500;                                    // hd-inline-on 이 이 안에 없으면(palette.js 가 옛것) 예전 글 칸으로

function mount(ctx) {
  var O = HD.optimistic, E = HD.edits, st = O.initial(), seq = 0, fresh = {}, ins = {}, waits = {};   // ins = 열린 글자 고치기(tag 마다 — 틀이 앞 것을 저장으로 끝내고 답할 수 있게)
  var warn = ctx.warn || function (m) { console.warn(m); };
  if (!document.getElementById('hd-opt-css')) {      // 그 자리 고치기 중인 카드 = 화면 안 파란 테두리 하나만 — 캔버스 hover 상자(점선·'글자' 이름표)가 글 위에 겹쳐 가렸다(사용자 10-25)
    var css = document.createElement('style'); css.id = 'hd-opt-css';
    css.textContent = '.card.hd-typing .elbox:not(.sel){display:none}';
    document.head.appendChild(css);
  }

  function newTag(k) { return k + ':' + Date.now().toString(36) + ':' + (++seq); }
  function post(f, msg) { try { if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*'); } catch (e) { warn('[hd] 바로 반영: 화면에 보내지 못했어요 — ' + (e && e.message || e)); } }
  function each(screen, msg, skip) { ctx.frames(screen).forEach(function (x) { if (x.f !== skip) { if (msg.type === 'hd-opt') x.f.setAttribute('data-hd-opt', ''); post(x.f, msg); } }); }   // data-hd-opt = 이 틀은 먼저 바뀌었다(view-swap 이 같은 내용이면 조용히 바꾸는 표시 — 틀과 함께 사라진다)
  function frameFor(screen, where) { var l = ctx.frames(screen).filter(function (x) { return x.where === where; }); return l.length ? l[l.length - 1].f : null; }
  function typingMark(f, on) { var c = f && f.closest ? f.closest('.card') : null; if (c) c.classList.toggle('hd-typing', on); }
  function mark(n) { n.opt = true; return n; }        // 낙관 반영 메모 — 셸 view-sync pend 가 실패를 반영 대기로 다시 넣지 않게(화면은 되돌렸다)
  function plain(list) { list.forEach(function (n) { delete n.opt; }); return list; }

  // 화면에 먼저 보인 변경 tag 를 도우미에 쓰기 — 남김 | 되돌림(+알림) | 연결 끊김(되돌리고 반영 대기로)
  function settle(label, screen, tag, notes, steps, offline) {   // offline() = 도우미에 닿지 않을 때 반영 대기로 넣는 길(없으면 그 메모 그대로)
    st = O.reduce(st, {type: 'start', tag: tag, screen: screen, steps: steps || 1});
    fresh[screen] = true;
    return ctx.write(label, notes).then(function (res) {
      st = O.reduce(st, {type: 'step', tag: tag});
      var oc = O.outcome(res, notes.map(function (n) { return n.id; }));
      if (oc.kept) { st = O.reduce(st, {type: 'keep', tag: tag}); end(tag); unbuilt(notes, screen, tag, label, res); return {kept: true, res: res}; }
      st = O.reduce(st, {type: 'revert', tag: tag, why: oc.why});
      each(screen, {type: 'hd-opt-undo', tag: tag});
      end(tag);
      return {kept: false, why: oc.why, res: res};
    }, function (e) {
      st = O.reduce(st, {type: 'revert', tag: tag, why: O.WHY});
      each(screen, {type: 'hd-opt-undo', tag: tag});
      end(tag);
      warn('[hd] 바로 반영: 도우미에 쓰지 못했어요 — ' + (e && e.message || e));
      if (offline) offline(); else ctx.queue(label, plain(notes), label + ' — 도우미에 닿지 않아 화면을 되돌리고 반영 대기로 남겼어요');
      return {kept: false, why: O.WHY, offline: true};
    });
  }
  function end(tag) { st = O.reduce(st, {type: 'end', tag: tag}); }

  // async apply(47-4b): 도우미가 받았지만 아직 빌드로 확인 안 된 편집 id → {screen, tag, label}. build.done 이 지우고, build.failed 의 reverted 면 되돌림을 알린다
  var pend = {}, PEND_MS = 120000;
  function unbuilt(notes, screen, tag, label, res) {
    if (!res || res.async !== true) return;          // 동기 답 = 이미 빌드됨
    var now = Date.now(), k;
    for (k in pend) if (now - pend[k].at > PEND_MS) delete pend[k];
    notes.forEach(function (n) { pend[n.id] = {screen: screen, tag: tag, label: label, at: now}; });
  }
  function built(ids) { (ids || []).forEach(function (id) { delete pend[id]; }); }
  function reverted(ids, why) {                       // 뒤 빌드가 깨져 도우미가 되돌린 편집 — 화면의 먼저 보인 변경을 거두고 한 번 알림(셸이 그 화면을 다시 싣는다)
    var told = {}, mine = [];
    (ids || []).forEach(function (id) {
      var p = pend[id]; if (!p) return;
      delete pend[id]; mine.push(id);
      each(p.screen, {type: 'hd-opt-undo', tag: p.tag});
      if (!told[p.tag]) { told[p.tag] = 1; ctx.toast(O.failText(p.label, why), false, 8000); }
    });
    return mine;
  }

  // 복제·옮기기 한 칸·글자(다른 틀) — items = palette.js hd-opt 항목
  function run(label, screen, notes, items, where) {
    var tag = newTag('op');
    if (where === 'modal') waits[tag] = {screen: screen, where: where};
    each(screen, {type: 'hd-opt', tag: tag, items: items});
    return settle(label, screen, tag, notes.map(mark)).then(function (r) {
      if (!r.kept && !r.offline) ctx.toast(O.failText(label, r.why), false, 6000);
      return r;
    });
  }

  // 편집 메모 하나(지우기 등, 49d) — 화면 항목은 Model 이 고른다. 바로 반영할 수 없는 편집이면 null(셸이 예전 길로)
  function edit(label, screen, n, where) {
    var it = O.item(n);
    return it ? run(label, screen, [n], [it], where) : null;
  }

  // 끌어 옮기기(51-5): h.drop = {from, slot, copy}(view-blocks 가 놓을 때 붙임) → HD.reorder.plan
  //   옮기기 = move op:to 쓰기 하나(되돌리기 한 줄) · Alt = duplicate 쓰기 → (틈이 바로 뒤가 아니면) 복사본을 그 자리로 move op:to 쓰기 하나 더
  //   dirs(위/아래 칸 목록)는 셸이 아직 넘기는 것 — 도우미에 닿지 않으면(네트워크) 그 칸 수만큼 위/아래 반영 대기로(셸의 도우미 없음 길과 같은 모양)
  function moves(label, screen, h, dirs, where) {
    var d = h && h.drop, p = d ? HD.reorder.plan(d.from, d.slot, !!d.copy) : null;
    if (!p) { warn('[hd] 끌어 옮기기: 놓은 자리(h.drop)가 없거나 제자리예요 — ' + JSON.stringify(d || null)); return Promise.resolve({kept: false}); }
    return p.dup ? copyTo(screen, h, p, where) : moveTo(label, screen, h, p.to, dirs, where);
  }
  function hit(h, path) { return {path: path, text: h.text, rect: h.rect, quote: h.quote}; }
  function toNote(screen, h, path, to) {
    var x = E.note(screen, hit(h, path), '요소 옮기기 — 이 요소를 같은 부모의 형제 요소 사이 ' + (to + 1) + '번째 자리로');
    x.edit = 'move'; x.op = 'to'; x.to = to; return mark(x);
  }
  function moveTo(label, screen, h, to, dirs, where) {
    var x = toNote(screen, h, h.path, to);
    var tag = newTag('mv');
    if (where === 'modal') waits[tag] = {screen: screen, where: where};
    each(screen, {type: 'hd-opt', tag: tag, items: [{path: h.path, to: to}]});
    return settle(label, screen, tag, [x], 1, function () {
      var ds = (dirs || []).filter(function (v) { return v === 'up' || v === 'down'; });
      ctx.queue(label, ds.map(function (v) { var n = E.note(screen, hit(h, h.path), E.say.move(v), v); n.edit = 'move'; return n; }),
                label + ' — 도우미에 닿지 않아 화면을 되돌리고 반영 대기로 남겼어요');
    }).then(function (r) {
      if (!r.kept && !r.offline) ctx.toast(O.failText(label, r.why), false, 6000);
      return r;
    });
  }
  // Alt 끌기 = 복제해 옮기기: 화면은 한 번에(복사본을 놓은 틈에), 도우미는 duplicate → move op:to(복사본 = 도우미가 알려 준 원본 경로의 다음 같은 태그)
  function copyTo(screen, h, p, where) {
    var label = '요소 복제해 옮기기', tag = newTag('cp'), done = 0;
    if (where === 'modal') waits[tag] = {screen: screen, where: where};
    each(screen, {type: 'hd-opt', tag: tag, items: [{path: h.path, dup: true, to: p.to}]});
    st = O.reduce(st, {type: 'start', tag: tag, screen: screen, steps: p.writes});
    fresh[screen] = true;
    var dn = E.note(screen, hit(h, h.path), E.say.duplicate()); dn.edit = 'duplicate'; mark(dn);
    var fail = function (why) {                       // 아무것도 못 씀 = 모두 되돌림
      st = O.reduce(st, {type: 'revert', tag: tag, why: why}); end(tag);
      each(screen, {type: 'hd-opt-undo', tag: tag});
      ctx.toast(O.failText(label, why), false, 6000);
      return {kept: false, why: why, done: 0};
    };
    var half = function (why) {                       // 복제는 씀, 옮기기는 못 함 = 화면도 파일처럼(원본 바로 뒤 복사본)
      st = O.reduce(st, {type: 'revert', tag: tag, why: why}); end(tag);
      each(screen, {type: 'hd-opt-undo', tag: tag});
      var pt = newTag('cphalf');
      each(screen, {type: 'hd-opt', tag: pt, items: [{path: h.path, dup: true}]});
      if (pend[dn.id]) pend[dn.id].tag = pt;          // 뒤 빌드가 깨지면 이 복사본을 거둔다
      ctx.toast(O.partText(label, why), false, 8000);
      return {kept: false, why: why, done: 1};
    };
    return ctx.write(label, [dn]).then(function (res) {
      var oc = O.outcome(res, [dn.id]);
      if (!oc.kept) return fail(oc.why);
      done = 1; st = O.reduce(st, {type: 'step', tag: tag}); unbuilt([dn], screen, tag, label, res);
      if (p.to == null) { st = O.reduce(st, {type: 'keep', tag: tag}); end(tag); return {kept: true, done: 1}; }
      var cp = HD.reorder.copyPath(res.paths && res.paths[dn.id]) || HD.reorder.copyPath(h.path);
      if (!cp) return half('복사본 자리를 알 수 없어요(도우미가 새 경로를 알려 주지 않았어요)');
      var mn = toNote(screen, h, cp, p.to);
      return ctx.write(label, [mn]).then(function (r2) {
        var o2 = O.outcome(r2, [mn.id]);
        if (!o2.kept) return half(o2.why);
        done = 2; st = O.reduce(st, {type: 'step', tag: tag}); unbuilt([mn], screen, tag, label, r2);
        st = O.reduce(st, {type: 'keep', tag: tag}); end(tag);
        return {kept: true, done: 2};
      }, function (e) { warn('[hd] 복제해 옮기기: 옮기기를 쓰지 못했어요 — ' + (e && e.message || e)); return half(O.WHY); });
    }, function (e) {
      warn('[hd] 복제해 옮기기: 도우미에 쓰지 못했어요 — ' + (e && e.message || e));
      return fail(O.WHY + ' — 다시 해 주세요');
    });
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
    if (document.activeElement === q.f && !opened(q.where)) q.f.blur();   // 키(도구 키·Ctrl+Z·Esc)가 화면 iframe 이 아니라 캔버스로 오게 — 다른 글자로 전환 중이면(R52) 그 틀의 새 고치기를 끊지 않게 그대로
    if (!d.ok) {
      if (d.why === 'missing') { ctx.toast('고칠 요소를 화면에서 찾지 못했어요 — 다시 골라 주세요'); return; }
      if (d.why === 'text') ctx.toast('안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요');
      repick(q, d);                                    // 그대로(Esc·Enter, 고친 것 없음 — 쓰기 없음) = 그 요소가 골라진 채(Figma F14, 51-2)
      return;
    }
    var v = String(d.text == null ? '' : d.text), n = E.note(q.screen, q.h, E.say.text(v));
    n.edit = 'text'; n.value = v;
    if (typeof d.old === 'string') n.old = d.old;     // 고치기 전 화면 글 — 단계 넘김 화면에서 스크립트가 그린 글이면 도우미가 스크립트 문자열을 고친다
    if (!ctx.on()) {                                   // 도우미 없음 = 예전처럼 반영 대기(미리보기 점선) — 그 자리 바꿈은 거두고 미리보기가 맡는다
      post(q.f, {type: 'hd-opt-undo', tag: q.tag});
      ctx.queue('글자 고치기', [n]);
      repick(q, d);
      return;
    }
    each(q.screen, {type: 'hd-opt', tag: q.tag, items: [{path: q.h.path, text: v}]}, q.f);
    repick(q, d);                                      // 고친 뒤에도 그 요소가 골라진 채(새 글 상자로 — Esc·Enter·Ctrl+Enter, R52)
    settle('글자 고치기', q.screen, q.tag, [mark(n)]).then(function (r) {
      if (!r.kept && !r.offline) ctx.toast(O.failText('글자 고치기', r.why), false, 6000);
    });
  }

  // 그 자리 고치기를 마친 뒤 그 요소 다시 고르기(51-2): 그 틀에 hd-find → hd-found(지금 상자) → ctx.picked
  //   다시 고르지 않음(R52): 다른 곳을 눌러 끝냄(d.away — 누른 것이 골라진다) · 그사이 다른 글자 고치기가 열림(전환 — 답이 늦게 와도 고르지 않는다)
  var finds = {};
  function opened(where) { return Object.keys(ins).some(function (k) { return ins[k].where === where; }); }
  function repick(q, d) {
    if ((d && d.away) || q.away || opened(q.where)) return;
    var tag = newTag('pk'); finds[tag] = q;
    post(q.f, {type: 'hd-find', path: q.h.path, tag: tag});
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || typeof d.tag !== 'string') return;
    if (d.type === 'hd-found' && finds[d.tag]) {
      var fq = finds[d.tag]; delete finds[d.tag];
      if (fq.f.contentWindow === e.source && d.path && !opened(fq.where)) ctx.picked(fq.screen, d, fq.where);
      return;
    }
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

  function away(where) { Object.keys(ins).forEach(function (k) { if (ins[k].where === where) ins[k].away = true; }); }   // 판: 고치는 중 다른 곳을 누름(R52) — 그 끝(blur 저장)에 앞 요소를 다시 고르지 않는다

  return {inline: inline, run: run, away: away, edit: edit, moves: moves, built: built, reverted: reverted,
          hold: function (screen) { return O.hold(st, screen); },
          take: function (screen) { var v = !!fresh[screen]; delete fresh[screen]; return v; },
          typing: function (where) { return Object.keys(ins).some(function (k) { return ins[k].on && (!where || ins[k].where === where); }); }};
}

HD.viewOptimistic = {mount: mount};
})();
