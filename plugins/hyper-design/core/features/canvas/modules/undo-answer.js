/* Model — 파일 쓰기 되돌리기(POST /api/restore) 답 풀이(47-5b): 기록 줄이 무엇을 보일지. DOM·저장소를 쓰지 않는다.
   read(r) → {kind:'done'|'already'|'changed'|'error', msg, note}
     r.reverted === true = 뒤 빌드가 깨져 서버가 이미 되돌린 쓰기(47-5a 묘비) → already, 기록 줄 표시 note = ALREADY · 토스트 msg
     r.error(reason changed-since) = changed · 그 밖 오류 = error · 아니면 done
   HD.undoAnswer = {read, ALREADY} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ALREADY = '빌드 실패로 이미 되돌림';

function read(r) {
  r = r && typeof r === 'object' ? r : {};
  if (r.reverted === true) return {kind: 'already', note: ALREADY, msg: '이 쓰기는 빌드가 깨져 이미 되돌려져 있었어요 — 파일은 그대로예요'};
  if (r.error) {
    if (r.reason === 'changed-since') return {kind: 'changed', note: '', msg: '그 뒤에 파일이 바뀌어 되돌릴 수 없어요'};
    return {kind: 'error', note: '', msg: '되돌리지 못했어요: ' + r.error};
  }
  return {kind: 'done', note: '', msg: ''};
}

HD.undoAnswer = {read: read, ALREADY: ALREADY};
})();
