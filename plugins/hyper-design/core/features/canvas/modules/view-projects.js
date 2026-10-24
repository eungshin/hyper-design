/* View — 프로젝트 고르기 창(#246 → task 44): 위쪽 줄 '프로젝트'(#pbtn)·아래 탭 바 '+' 가 여는 대화 창 — + 새 프로젝트 · 폴더 열기 · 최근 프로젝트 카드(홈과 같은 모양) · 검색 · 홈에서 모두 보기.
   도우미가 없으면(ctx.api.on 거짓 — file:// 또는 도우미 꺼짐) 단추를 만들지 않고 아무것도 바꾸지 않는다.
   열 때마다 GET /api/projects → HD.projects.rows/filter(휴지통 빼고 검색) → 카드: 썸네일(없으면 빈 무늬) · 제목 · 언제(ago) · 열림 점 · 지금 표시. '없음' 카드는 회색 '폴더 없음', 누르면 까닭 토스트.
   카드 누르기 → POST /api/open {name} → 받은 url 로 이 탭이 간다(지금 것이면 창만 닫음). 새 프로젝트 → 이름 묻기(기본 '새 프로젝트 N') → POST /api/new {title} → url.
   폴더 열기 → POST /api/pick-folder → {name} 이면 그것을 연다 · {cancel} 은 조용히 · {error}·실패는 토스트. 기다리는 동안 그 카드 aria-busy, 한 번에 하나만.
   보내지 않은 상태 쓰기는 떠날 때(pagehide) view-state-sync 가 keepalive 로 마저 보내고, 못 닿으면 쓰기 대기 표시로 다음에 다시 올린다 — 여기서 따로 하지 않는다.
   의도(문서 이벤트): 'hd-pick-project' → 창을 연다(preventDefault = 받음) · 'hd-home' 을 보낸다(홈에서 모두 보기 — 받는 곳이 없으면 토스트).
   상태: 창 열림 · 받은 줄 · 검색어 · 기다리는 카드(이 View 만). 지금 캔버스 = 도우미가 index.html 에 끼운 window.__hdOut.
   HD.feature('projects', {needs: ['api', '$', 'esc', 'toast']}) → {open(), close()} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#ppick{position:fixed;inset:0;z-index:40;background:rgba(28,28,28,.28);display:grid;place-items:center}' +
  '#ppick[hidden]{display:none}' +
  '#ppick .pk{width:min(820px,calc(100vw - 48px));max-height:calc(100vh - 96px);display:flex;flex-direction:column;background:#fff;border-radius:12px;box-shadow:0 18px 48px rgba(0,0,0,.22);font-size:13px;color:#2b2b29}' +
  '#ppick .pk-head{display:flex;align-items:center;gap:10px;padding:14px 16px 10px}' +
  '#ppick .pk-head h2{margin:0;font-size:15px;font-weight:700;flex:1}' +
  '#ppick .pk-q{width:220px;height:30px;border:1px solid #dcdcd7;border-radius:8px;padding:0 10px;font:inherit;background:#F7F7F5}' +
  '#ppick .pk-q:focus{outline:2px solid var(--ui-mark);outline-offset:-1px;background:#fff}' +
  '#ppick .pk-x{width:30px;height:30px;border:0;border-radius:8px;background:none;font-size:18px;color:#6b6b66;cursor:pointer}' +
  '#ppick .pk-x:hover{background:#F2F2EF}' +
  '#ppick .pk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:20px 14px;padding:6px 16px 16px;overflow:auto}' +
  '#ppick .pk-card{position:relative;display:flex;flex-direction:column;gap:6px;padding:0;border:0;background:none;text-align:left;cursor:pointer;min-width:0;font:inherit;color:inherit}' +
  '#ppick .pk-th{position:relative;aspect-ratio:42/26;border-radius:10px;border:1px solid #e3e3df;background:#F4F4F1 center/cover no-repeat;overflow:hidden;display:grid;place-items:center;color:#8a8a85}' +
  '#ppick .pk-th img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}' +
  '#ppick .pk-card:hover .pk-th,#ppick .pk-card:focus-visible .pk-th{border-color:#2b2b29}' +
  '#ppick .pk-card:focus-visible{outline:none}' +
  '#ppick .pk-card[aria-current="true"] .pk-th{border:2px solid var(--ui-mark)}' +
  '#ppick .pk-ttl{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:0 2px}' +
  '#ppick .pk-meta{display:flex;align-items:center;gap:6px;font-size:11.5px;color:#8a8a85;padding:0 2px;min-height:15px}' +
  '#ppick .pk-dot{width:7px;height:7px;border-radius:50%;background:var(--ui-ok)}' +
  '#ppick .pk-cur{font-size:11px;color:var(--ui-on-badge-soft);background:var(--ui-badge-soft);border-radius:999px;padding:0 6px}' +
  '#ppick .pk-new .pk-th,#ppick .pk-folder .pk-th{border-style:dashed;background:#fff;font-size:13px;gap:2px;align-content:center}' +
  '#ppick .pk-new .pk-th b{font-size:26px;font-weight:300;line-height:1;color:#2b2b29}' +
  '#ppick .pk-folder svg{width:24px;height:24px;fill:none;stroke:#55554f;stroke-width:1.6;stroke-linejoin:round}' +
  '#ppick .pk-card[data-state="missing"]{cursor:not-allowed}' +
  '#ppick .pk-card[data-state="missing"] .pk-th{filter:grayscale(1);opacity:.55}' +
  '#ppick .pk-card[data-state="missing"] .pk-th::after{content:"폴더 없음";position:absolute;inset:auto 0 0 0;padding:3px 0;background:rgba(255,255,255,.9);font-size:11.5px;text-align:center;color:#55554f}' +
  '#ppick .pk-card[aria-busy="true"]{cursor:progress}' +
  '#ppick .pk-card[aria-busy="true"] .pk-th{opacity:.6}' +
  '#ppick .pk-skel .pk-th{background:linear-gradient(90deg,#F2F2EF,#E9E9E5,#F2F2EF);border-color:#efefeb}' +
  '#ppick .pk-skel .pk-ttl{height:12px;width:70%;background:#efefeb;border-radius:4px}' +
  '#ppick .pk-form{display:flex;flex-direction:column;gap:6px}' +
  '#ppick .pk-form input{height:30px;border:2px solid var(--ui-mark);border-radius:8px;padding:0 8px;font:inherit}' +
  '#ppick .pk-form .pk-btns{display:flex;gap:6px}' +
  '#ppick .pk-form button{height:28px;padding:0 10px;border:1px solid #dcdcd7;border-radius:7px;background:#fff;font:inherit;cursor:pointer}' +
  '#ppick .pk-form button.pk-ok{background:var(--ui-primary);border-color:var(--ui-primary);color:#fff;font-weight:600}' +
  '#ppick .pk-msg{grid-column:1/-1;padding:18px 4px;color:#6f6f6a}' +
  '#ppick .pk-foot{display:flex;justify-content:flex-end;padding:10px 16px 14px;border-top:1px solid #eee}' +
  '#ppick .pk-home{border:0;background:none;font:inherit;color:#3a3a37;cursor:pointer;padding:4px 6px;border-radius:6px}' +
  '#ppick .pk-home:hover{background:#F2F2EF}';
var FOLDER = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>';

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// 또는 도우미 없음 — 단추도 창도 없다
  var $ = ctx.$, esc = ctx.esc, P = HD.projects;
  var anchor = $('#wbtn'), bar = anchor ? anchor.parentNode : $('header .view');
  if (!bar) throw new Error('위쪽 줄(.view)이 없어요');

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'vbtn wbtn'; btn.id = 'pbtn'; btn.textContent = '프로젝트';
  btn.title = '프로젝트 — 새로 만들기·열기';
  btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'ppick');
  bar.insertBefore(btn, anchor || null);
  var back = document.createElement('div');
  back.id = 'ppick'; back.hidden = true;
  back.innerHTML = '<div class="pk" role="dialog" aria-modal="true" aria-labelledby="pk-h">' +
    '<div class="pk-head"><h2 id="pk-h">프로젝트</h2><input class="pk-q" type="search" placeholder="검색" aria-label="프로젝트 검색">' +
    '<button type="button" class="pk-x" aria-label="닫기" title="닫기 (Esc)">×</button></div>' +
    '<div class="pk-grid" role="list"></div>' +
    '<div class="pk-foot"><button type="button" class="pk-home">홈에서 모두 보기 →</button></div></div>';
  document.body.appendChild(back);
  var grid = $('.pk-grid', back), q = $('.pk-q', back);

  var rows = null, busy = null, seq = 0, naming = false, last = null;   // rows = 받은 줄(null = 불러오는 중) · busy = 기다리는 카드 키 · naming = 새 이름 묻는 중

  function fixed() {
    return naming
      ? '<div class="pk-card pk-new pk-form" role="listitem"><div class="pk-th"><b>+</b>새 프로젝트</div>' +
        '<input class="pk-name" aria-label="새 프로젝트 이름" maxlength="80" value="' + esc(P.newTitle((rows || []).map(function (r) { return r.title; }))) + '">' +
        '<span class="pk-btns"><button type="button" class="pk-ok">만들기</button><button type="button" class="pk-no">취소</button></span></div>'
      : '<button type="button" class="pk-card pk-new" role="listitem" data-act="new"' + (busy === '+new' ? ' aria-busy="true"' : '') +
        '><span class="pk-th"><b>+</b>' + (busy === '+new' ? '만드는 중…' : '새 프로젝트') + '</span></button>';
  }
  function draw() {
    var html = fixed() + '<button type="button" class="pk-card pk-folder" role="listitem" data-act="folder"' + (busy === '+folder' ? ' aria-busy="true"' : '') +
      '><span class="pk-th">' + FOLDER + (busy === '+folder' ? '여는 중…' : '폴더 열기') + '</span></button>';
    if (rows == null) html += [0, 1, 2].map(function () { return '<div class="pk-card pk-skel" aria-hidden="true"><span class="pk-th"></span><span class="pk-ttl"></span></div>'; }).join('');
    else {
      var shown = P.filter(rows, q.value), now = Date.now();
      if (!shown.length) html += '<div class="pk-msg">' + esc(q.value.trim() ? '"' + q.value.trim() + '" 에 맞는 프로젝트가 없어요' : '저장한 프로젝트가 없어요 — + 새 프로젝트로 시작해요') + '</div>';
      html += shown.map(function (r) {
        return '<button type="button" class="pk-card" role="listitem" data-name="' + esc(r.name) + '" data-state="' + r.state + '"' +
          (r.current ? ' aria-current="true"' : '') + (r.clickable ? '' : ' aria-disabled="true"') + (busy === r.name ? ' aria-busy="true"' : '') +
          ' title="' + esc(r.why || r.title) + '">' +
          '<span class="pk-th">' + (r.thumb ? '<img alt="" loading="lazy" src="' + esc(r.thumb) + '">' : '') + '</span>' +
          '<span class="pk-ttl">' + esc(r.title) + '</span>' +
          '<span class="pk-meta">' + (r.state === 'open' ? '<span class="pk-dot" title="열림"></span>' : '') +
          (r.current ? '<span class="pk-cur">지금</span>' : '') + '<span class="pk-when">' + esc(busy === r.name ? '여는 중…' : P.ago(r.last_opened, now)) + '</span></span></button>';
      }).join('');
    }
    grid.innerHTML = html;
    var nm = $('.pk-name', grid); if (nm) { nm.focus(); nm.select(); }
  }
  function load() {
    var my = ++seq;
    rows = null; draw();
    ctx.api.call('GET', '/api/projects').then(function (res) {
      if (my !== seq || back.hidden) return;
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      var r = P.rows(res.body, window.__hdOut || null);
      if (r.bad) console.warn('[hd] 프로젝트 목록: ' + r.bad);
      rows = r.rows; draw();
    }).catch(function (e) {
      if (my !== seq) return;
      var t = '프로젝트 목록을 불러오지 못했어요 — ' + (e && e.message || e);
      rows = []; draw(); grid.insertAdjacentHTML('beforeend', '<div class="pk-msg">' + esc(t) + '</div>'); ctx.toast(t);
    });
  }
  function open() {
    if (!back.hidden) return;
    last = document.activeElement;
    back.hidden = false; btn.setAttribute('aria-expanded', 'true'); naming = false; q.value = '';
    load(); q.focus();
  }
  function close() {
    seq++; back.hidden = true; naming = false; btn.setAttribute('aria-expanded', 'false');
    if (last && last.focus && document.contains(last)) last.focus();
  }

  function wait(key, call, what) {                   // 한 번에 하나: key 카드를 기다림으로 그리고 call() → {url} 이면 이 탭이 간다
    if (busy) return;
    busy = key; draw();
    call().then(function (res) {
      if (res.status !== 200 || !res.body) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      if (res.body.cancel) { busy = null; draw(); return; }
      if (res.body.error) throw new Error(res.body.error);
      if (!res.body.url) throw new Error('도우미가 주소를 주지 않았어요');
      busy = null;
      location.assign(res.body.url);
    }).catch(function (e) {
      busy = null; if (!back.hidden) draw();
      ctx.toast(what + ' — ' + (e && e.message || e), false, 6000);
    });
  }
  function openName(name) {
    return ctx.api.call('POST', '/api/open', {name: name});
  }
  function go(card) {
    var name = card.dataset.name, r = (rows || []).filter(function (x) { return x.name === name; })[0];
    if (!r) return;
    if (!r.clickable) { ctx.toast(r.why, false, 6000); return; }
    if (r.current) { close(); return; }              // 이미 여기
    wait(name, function () { return openName(name); }, '열지 못했어요');
  }
  function create() {
    var nm = $('.pk-name', grid), t = nm ? nm.value.replace(/\s+/g, ' ').trim() : '';
    if (!t) { ctx.toast('이름을 적어 주세요'); if (nm) nm.focus(); return; }
    naming = false;
    wait('+new', function () { return ctx.api.call('POST', '/api/new', {title: t}); }, '새 프로젝트를 만들지 못했어요');
  }
  function folder() {
    wait('+folder', function () {
      return ctx.api.call('POST', '/api/pick-folder', {}).then(function (res) {
        if (res.status !== 200 || !res.body || res.body.cancel || res.body.error || !res.body.name) return res;
        return openName(res.body.name);
      });
    }, '폴더를 열지 못했어요');
  }
  function goHome() {
    var ev = new CustomEvent('hd-home', {cancelable: true});
    document.dispatchEvent(ev);
    if (!ev.defaultPrevented) ctx.toast('홈 단추가 붙지 않아 홈을 열 수 없어요');
  }

  btn.addEventListener('click', function () { if (back.hidden) open(); else close(); });
  document.addEventListener('hd-pick-project', function (e) { e.preventDefault(); open(); });
  back.addEventListener('click', function (e) {
    var t = e.target;
    if (t === back || t.closest('.pk-x')) { close(); return; }
    if (t.closest('.pk-home')) { goHome(); return; }
    if (t.closest('.pk-ok')) { create(); return; }
    if (t.closest('.pk-no')) { naming = false; draw(); return; }
    var c = t.closest('button.pk-card');
    if (!c) return;
    if (c.dataset.act === 'new') { if (!busy) { naming = true; draw(); } return; }
    if (c.dataset.act === 'folder') { folder(); return; }
    go(c);
  });
  q.addEventListener('input', function () { if (rows) draw(); });
  back.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopPropagation();
      if (naming) { naming = false; draw(); $('.pk-new', grid).focus(); } else close();
    } else if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('pk-name')) { e.preventDefault(); create(); }
  });
  return {open: open, close: close};
}

HD.viewProjects = {mount: mount};
HD.feature('projects', {needs: ['api', '$', 'esc', 'toast'], mount: mount});
})();
