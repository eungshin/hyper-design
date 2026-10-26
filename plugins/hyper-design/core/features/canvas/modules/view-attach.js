/* View — 첨부 이미지(R22): [data-hd-attach] 입력 상자에 붙여넣기(Ctrl+V)·끌어 놓기·📎([data-hd-attach-pick])로 이미지 → 도우미 POST /api/image 로 out/.hd-attach 에 저장 · 썸네일 칩(×)을 상자의 [data-hd-attach-slot] 에.
   규칙(종류·크기·칩 목록·요청 글 줄)은 HD.attach(Model). 상태 = 상자마다 칩 목록(WeakMap, 저장 안 함) · 저장된 이미지 미리보기(rel → data: 주소, 이 탭 동안).
   상자 주인(메모 창 view-memo-pop · 대화창 view-chat)과는 의도로만 — 상자에 CustomEvent(bubbles):
     'hd-attach-get' detail {items, busy, done} → 저장된 것(HD.attach.saved 모양)과 올리는 중인 수를 채움 · 'hd-attach-set' {items} → 저장된 것으로 칩을 다시(빈 배열 = 비우기)
     이 파일이 내는 것: 'hd-attach-changed' {count, busy}(상자에) — 칩이 바뀔 때.
   오류 탐지: 도우미 없음(file://) = 토스트 '도우미로 열었을 때만' · 종류·크기·장 수 = 토스트(올리지 않음) · 저장 실패 = 그 칩을 빼고 토스트(서버 이유) · 미리보기 못 읽음 = [hd] 경고 + 빈 칩.
   HD.feature('attach', {needs: ['toast', 'esc', 'api']}) → {items(host), set(host, saved)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '.hd-att{display:flex;flex-wrap:wrap;gap:6px}' +
  '.hd-att[hidden]{display:none}' +
  '.hd-att-chip{position:relative;flex:none;width:52px;height:52px;border-radius:8px;overflow:hidden;background:#F2F2EF;box-shadow:0 0 0 1px rgba(0,0,0,.1)}' +
  '.hd-att-chip img{display:block;width:100%;height:100%;object-fit:cover}' +
  '.hd-att-chip.up img{opacity:.45}' +
  '.hd-att-chip.up::after{content:"";position:absolute;left:50%;top:50%;width:14px;height:14px;margin:-9px 0 0 -9px;border:2px solid var(--ui-primary,#2b2b29);border-right-color:transparent;border-radius:50%;animation:hdAttSpin 1s linear infinite}' +
  '@keyframes hdAttSpin{to{transform:rotate(360deg)}}' +
  '@media (prefers-reduced-motion: reduce){.hd-att-chip.up::after{animation:none}}' +
  '.hd-att-chip button{position:absolute;top:3px;right:3px;width:18px;height:18px;padding:0;border:0;border-radius:50%;background:rgba(0,0,0,.62);color:#fff;font:600 12px/18px system-ui,sans-serif;cursor:pointer}' +
  '.hd-att-chip button:hover{background:rgba(0,0,0,.85)}' +
  '[data-hd-attach].hd-att-over{outline:2px dashed var(--ui-primary,#2b2b29);outline-offset:2px}' +
  'html:not([data-hd-attach-on]) [data-hd-attach-pick]{display:none}';

var NEED_HELPER = '이미지 첨부는 도우미로 열었을 때만 돼요 — 터미널에서 hd open 으로 열어 주세요';

function mount(ctx) {
  var A = HD.attach, lists = new WeakMap(), thumbs = {}, seq = 0, warned = {};
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var input = document.createElement('input');
  input.type = 'file'; input.accept = A.TYPES.join(','); input.multiple = true; input.hidden = true; input.setAttribute('aria-hidden', 'true');
  document.body.appendChild(input);
  var pickFor = null;

  function hostOf(el) { return el && el.closest ? el.closest('[data-hd-attach]') : null; }
  function slotOf(host) { return host.querySelector('[data-hd-attach-slot]'); }
  function list(host) { return lists.get(host) || []; }
  function put(host, l) {
    lists.set(host, l);
    render(host);
    host.dispatchEvent(new CustomEvent('hd-attach-changed', {detail: {count: l.length, busy: A.busy(l)}}));
  }
  function render(host) {
    var slot = slotOf(host), l = list(host);
    if (!slot) { if (!warned.slot) { warned.slot = 1; console.warn('[hd] 첨부: 칩 자리([data-hd-attach-slot])가 없는 상자예요'); } return; }
    slot.hidden = !l.length;
    slot.innerHTML = l.map(function (c) {
      var url = c.url || (c.rel && thumbs[c.rel]) || '', label = c.name || (c.path || '').split(/[\\/]/).pop() || '이미지';
      return '<span class="hd-att-chip' + (c.state === 'up' ? ' up' : '') + '" data-id="' + ctx.esc(c.id) + '" title="' + ctx.esc(c.path || label) + '">' +
        (url ? '<img alt="" src="' + ctx.esc(url) + '">' : '') +
        '<button type="button" aria-label="' + ctx.esc(label) + ' 빼기">×</button></span>';
    }).join('');
    l.forEach(function (c) { if (c.state === 'ok' && !c.url && c.rel && !(c.rel in thumbs)) thumb(host, c.rel); });
  }
  function thumb(host, rel) {                         // 저장된 이미지 미리보기(메모를 다시 열 때) — 점 폴더라 정적 경로가 아니라 GET /api/image
    thumbs[rel] = '';
    if (!ctx.api.on) return;
    ctx.api.call('GET', '/api/image?rel=' + encodeURIComponent(rel)).then(function (r) {
      if (r.status !== 200 || !r.body || !r.body.data) { console.warn('[hd] 첨부 미리보기를 못 읽었어요: ' + rel + ' — ' + (r.body && r.body.error || r.status)); return; }
      thumbs[rel] = 'data:' + (r.body.type || 'image/png') + ';base64,' + r.body.data;
      render(host);
    }).catch(function (e) { console.warn('[hd] 첨부 미리보기를 못 읽었어요: ' + rel + ' — ' + (e && e.message || e)); });
  }
  function readData(file) {
    return new Promise(function (ok, bad) {
      var fr = new FileReader();
      fr.onload = function () { ok(String(fr.result || '')); };
      fr.onerror = function () { bad(fr.error || new Error('파일을 읽지 못했어요')); };
      fr.readAsDataURL(file);
    });
  }
  function upload(host, id, file) {
    var fail = function (why) {
      var l = list(host), had = l.some(function (c) { return c.id === id; });
      if (!had) return;                               // 그 사이 칩을 뺐거나 창을 닫았다
      l.forEach(function (c) { if (c.id === id && c.url && c.url.indexOf('blob:') === 0) URL.revokeObjectURL(c.url); });
      put(host, A.remove(l, id));
      ctx.toast('이미지를 붙이지 못했어요 — ' + why);
    };
    readData(file).then(function (data) {
      return ctx.api.call('POST', '/api/image', {data: data, name: file.name || ''});
    }).then(function (r) {
      if (r.status !== 200 || !r.body || !r.body.path) { fail(r.body && r.body.error || ('도우미 답 ' + r.status)); return; }
      var l = list(host);
      if (!l.some(function (c) { return c.id === id; })) return;
      put(host, A.done(l, id, r.body));
    }).catch(function (e) { fail((e && e.message) || '도우미에 닿지 못했어요'); });
  }
  function take(host, files) {
    if (!files.length) return;
    if (!ctx.api.on) { ctx.toast(NEED_HELPER); return; }
    var l = list(host);
    for (var i = 0; i < files.length; i++) {
      var f = files[i], why = A.check(f);
      if (why) { ctx.toast(why); continue; }
      var id = 'att' + (++seq), r = A.add(l, {id: id, name: f.name || '', type: f.type, size: f.size, url: URL.createObjectURL(f)});
      if (r.why) { ctx.toast(r.why); break; }
      l = r.list; put(host, l);
      upload(host, id, f);
    }
  }
  function filesOf(dt) {
    if (!dt) return [];
    var out = [];
    if (dt.items && dt.items.length) {
      for (var i = 0; i < dt.items.length; i++) { var it = dt.items[i]; if (it.kind === 'file') { var f = it.getAsFile(); if (f) out.push(f); } }
      if (out.length) return out;
    }
    return Array.prototype.slice.call(dt.files || []);
  }
  function hasFiles(dt) { return !!(dt && dt.types && Array.prototype.indexOf.call(dt.types, 'Files') >= 0); }

  document.addEventListener('paste', function (e) {   // 글 붙여넣기는 그대로 — 파일이 있을 때만 가로챈다
    var host = hostOf(e.target), fs = host ? filesOf(e.clipboardData) : [];
    if (!fs.length) return;
    e.preventDefault();
    take(host, fs);
  }, true);
  document.addEventListener('dragover', function (e) {
    var host = hostOf(e.target); if (!host || !hasFiles(e.dataTransfer)) return;
    e.preventDefault(); e.dataTransfer.dropEffect = ctx.api.on ? 'copy' : 'none';
    host.classList.add('hd-att-over');
  }, true);
  document.addEventListener('dragleave', function (e) {
    var host = hostOf(e.target); if (host && !host.contains(e.relatedTarget)) host.classList.remove('hd-att-over');
  }, true);
  document.addEventListener('drop', function (e) {
    var host = hostOf(e.target); if (!host || !hasFiles(e.dataTransfer)) return;
    e.preventDefault(); e.stopPropagation();
    host.classList.remove('hd-att-over');
    take(host, filesOf(e.dataTransfer));
  }, true);
  document.addEventListener('click', function (e) {   // 잡는 단계 — 대화창은 누르기를 판으로 흘리지 않으려 버블에서 막는다
    var t = e.target, host = hostOf(t); if (!host) return;
    var x = t.closest('.hd-att-chip button');
    if (x) {
      e.preventDefault(); e.stopPropagation();
      var id = x.closest('.hd-att-chip').dataset.id, l = list(host);
      l.forEach(function (c) { if (c.id === id && c.url && c.url.indexOf('blob:') === 0) URL.revokeObjectURL(c.url); });
      put(host, A.remove(l, id));
      return;
    }
    if (t.closest('[data-hd-attach-pick]')) {
      e.preventDefault(); e.stopPropagation();
      if (!ctx.api.on) { ctx.toast(NEED_HELPER); return; }
      pickFor = host; input.value = ''; input.click();
    }
  }, true);
  input.addEventListener('change', function () { if (pickFor) take(pickFor, Array.prototype.slice.call(input.files || [])); pickFor = null; });
  document.addEventListener('hd-attach-get', function (e) {
    var host = hostOf(e.target), d = e.detail; if (!host || !d) return;
    var l = list(host); d.items = A.saved(l); d.busy = A.busy(l); d.done = true;
  });
  document.addEventListener('hd-attach-set', function (e) {
    var host = hostOf(e.target), d = e.detail || {}; if (!host) return;
    list(host).forEach(function (c) { if (c.url && c.url.indexOf('blob:') === 0) URL.revokeObjectURL(c.url); });
    d.done = true;
    put(host, A.fromSaved(d.items || []));
  });
  document.documentElement.setAttribute('data-hd-attach-on', '');
  return {items: function (host) { return list(host).slice(); }, set: function (host, saved) { put(host, A.fromSaved(saved || [])); }};
}

HD.feature('attach', {needs: ['toast', 'esc', 'api'], mount: mount});
})();
