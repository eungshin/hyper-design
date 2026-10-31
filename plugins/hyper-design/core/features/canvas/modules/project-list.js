/* ViewModel — 이 페이지의 프로젝트 목록 받기 하나(보드 전환 S2): GET /api/projects 를 페이지 열기에 한 번 받아 머리 제목·탭 바·주소 복사가 나눠 쓴다. DOM·저장소를 쓰지 않는다.
   상태 = 나눠 쓰는 답 하나(Promise<{status, body}> | null — 이 모듈만). 부르기는 받은 api({call(method, path)}) 로 — 도우미가 없는지(api.on)는 부른 쪽이 본다.
   HD.projectList.get(api) → 처음이면 받고, 그 뒤는 같은 Promise(받는 중이어도 하나) · fresh(api) → 새로 받아 그 답을 나눠 쓸 답으로(고르기 창 — 열 때마다 새로)
   오류 탐지: 실패(끊김)는 부른 쪽에 그대로 넘기고(쪽마다 [hd] 경고·토스트) 남기지 않는다 — 다음 get 이 다시 받는다. 4xx/5xx 답은 받은 그대로(쪽마다 status 를 본다). */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var shared = null;

function fresh(api) {
  var p = api.call('GET', '/api/projects');
  shared = p;
  p.catch(function () { if (shared === p) shared = null; });   // 실패한 답은 남기지 않는다(알리는 일은 부른 쪽이 받은 Promise 로)
  return p;
}

function get(api) { return shared || fresh(api); }

HD.projectList = {get: get, fresh: fresh};
})();
