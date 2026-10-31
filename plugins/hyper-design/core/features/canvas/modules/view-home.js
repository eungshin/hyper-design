/* View — 위쪽 줄 머리(task 44): 도우미로 열면 'hd' 표시 자리가 🏠 홈 단추(누르면 GET /api/home → 이 탭이 홈으로)가 되고, 제목 = 이 프로젝트의 제목(페이지 제목도 같게).
   도우미가 없으면(file://) 아무것도 바꾸지 않는다 — 제목은 셸이 HD.projects.shown(manifest 제목, 폴더)으로 이미 썼다.
   제목: GET /api/projects(HD.projectList — 페이지에 한 번, 탭 바·주소 복사와 나눠 씀) → HD.projects.rows → 지금 줄의 title(없으면 셸이 쓴 것 그대로, [hd] 경고 한 줄).
   의도(문서 이벤트, cancelable — 받으면 preventDefault 로 '받음'을 알린다): 'hd-home' → 홈으로 · 'hd-project-title' {name, title, current} → 지금 것이면 제목을 바꾼다.
   홈으로 가는 답이 0.3초 넘게 늦으면(허브를 처음 띄우는 몇 초) 기다림 토스트 — 답이 오면 이동하거나 실패 까닭 토스트로 바뀐다(F17).
   상태: 홈으로 가는 중인지(한 번에 하나) · 지금 프로젝트 이름(이 모듈만).
   HD.feature('home', {needs: ['api', '$', 'toast']}) → {home(), title(t)} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '.hd .hhome{flex:none;width:24px;height:24px;margin-right:4px;padding:0;border:0;border-radius:5px;background:none;color:#3a3a37;display:grid;place-items:center;cursor:pointer}' +
  '.hd .hhome:hover{background:#E6E6E1}' +
  '.hd .hhome[aria-busy="true"]{cursor:progress;color:#9a9a95}' +
  '.hd .hhome svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}';
var HOUSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>';

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// 또는 도우미 없음 — 머리는 셸이 쓴 그대로
  var $ = ctx.$, P = HD.projects;
  var box = $('header .hdname'), h1 = $('#title');
  if (!box || !h1) throw new Error('위쪽 줄 제목 자리(.hdname #title)가 없어요');

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'hhome'; btn.id = 'hhome'; btn.innerHTML = HOUSE;
  btn.title = '홈 — 모든 캔버스'; btn.setAttribute('aria-label', '홈 — 모든 캔버스');
  var badge = $('.app', box);
  if (badge) box.replaceChild(btn, badge); else box.insertBefore(btn, box.firstChild);

  var going = false, curName = null;
  function title(t) {
    if (typeof t !== 'string' || !t) return;
    h1.textContent = t; h1.title = t; document.title = t;
  }
  function home() {
    if (going) return;
    going = true; btn.setAttribute('aria-busy', 'true');
    var waitT = setTimeout(function () { ctx.toast('홈을 여는 중… 허브를 처음 켤 때는 몇 초 걸려요', false, 15000); }, 300);   // F17 — 회색 아이콘만으로 기다리지 않게(빠른 답이면 안 띄움)
    function done() { clearTimeout(waitT); going = false; btn.removeAttribute('aria-busy'); }
    ctx.api.call('GET', '/api/home').then(function (res) {
      if (res.status !== 200 || !res.body || !res.body.url) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      done();
      location.assign(res.body.url);                 // 보내지 않은 상태 쓰기는 떠날 때(pagehide) view-state-sync 가 마저 보낸다
    }).catch(function (e) {
      done();
      ctx.toast('홈을 열지 못했어요 — ' + (e && e.message || e), false, 6000);
    });
  }

  HD.projectList.get(ctx.api).then(function (res) {
    if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
    var r = P.rows(res.body, window.__hdOut || null), cur = P.current(r.rows);
    if (!cur) { console.warn('[hd] 이 캔버스가 프로젝트 목록에 없어 폴더 이름을 제목으로 써요'); return; }
    curName = cur.name; title(cur.title);
  }).catch(function (e) { console.warn('[hd] 프로젝트 제목을 받지 못했어요: ' + (e && e.message || e)); });

  btn.addEventListener('click', home);
  document.addEventListener('hd-home', function (e) { e.preventDefault(); home(); });
  document.addEventListener('hd-project-title', function (e) {
    var d = e.detail || {};
    if (d.current || (curName && d.name === curName)) { e.preventDefault(); title(d.title); }
  });
  return {home: home, title: title};
}

HD.viewHome = {mount: mount};
HD.feature('home', {needs: ['api', '$', 'toast'], mount: mount});
})();
