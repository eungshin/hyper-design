/* Model — 편집 메모(화면 파일을 바꾸는 편집). DOM·저장소·메시지를 쓰지 않는다.
   단일 진실 원천: 편집은 모두 메모 목록 하나에 쌓이고, 판 위 표시(반영 대기 선·빈 레이아웃·글자 미리보기)는 여기서 계산한다.
   메모 = {id, no, screen, targets:[{path,text,rect,quote?,src?}], replies:[], path, text, rect, note, intent:'change', sent, edit, op?, to?, value?, index?, x?, y?}
     edit: link(op: link·cut·untrigger·trigger·new) · text(value '' = 글 비우기) · remove(요소 지우기, task 30) · duplicate(요소 복제) · move(op up·down — 형제와 맞바꿈, task 49a · op to + to = 형제 사이 자리, 51-5) · attr(op = 속성 이름, value = 새 값) · insert·replace(value = 부품 key, task 49b) · title · purpose · policies(value = 줄 목록 전체, task 31) · policy(옛 메모만: index, op: delete = 그 줄 지우기 · 빈 value 도 지우기) · new-screen · cut-in · delete · copy · board(판 글, screen '@board' · op set|delete · to = 칸·묶음 키 — t51-9, board-text.js)
   n.scope = element|screen|all(없음 = element, R7) — 요청문에 범위 줄
   request(notes, out, sizes?, context?) — sizes = {화면 id: 'W×H(프리셋)'} 이면 그 항목 아래 '   화면 크기: …' 줄(task 46) ·
     context(screenId) → 정보 카드 글(R47) — 화면마다 첫 항목 머리 바로 아래 세 칸 들여 한 번, 없거나 빈 글이면 예전과 같은 글
   빈 레이아웃(셸 C9): layoutId(now, rnd) → 'new-…' id · layout(id, {x, y}, name?) → 빈 레이아웃 메모(edit 'new-screen', 이름 기본 '빈 레이아웃') ·
     layoutText(n) → 그 메모의 요청 글(say.layout) · layoutOf(list, id) → 그 화면의 빈 레이아웃 메모|null
   HD.edits = {note, pendingFor, overviewPending, pendingLink, directOf, instantOf, preview, split, tally, request, items, emptyLayouts, say} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

// 메모 하나 — h = 대상 요소 {path, text, rect}
function note(screen, h, text, op, to) {
  var t = {path: h.path, text: h.text, rect: h.rect}; if (h.quote) t.quote = h.quote;   // quote = 다시 찾을 글(palette.js, task 11)
  if (h.src) t.src = h.src;                          // src = 앱 소스 위치 {file, line, column}(palette.js, task 27) — 요청문 '소스:' 줄
  return {id: newId(), screen: screen, targets: [t],
          path: h.path, text: h.text, rect: h.rect, note: text, intent: 'change', sent: false, edit: 'link', op: op || '', to: to || ''};
}

// 아직 파일에 안 들어간 연결 편집 → 연결 보기가 겹쳐 그릴 것(출발 화면 from 기준)
function pendingFor(notes, from) {
  var pd = {byPath: {}, adds: [], cutIn: {}};
  (notes || []).forEach(function (n) {
    if (n.edit === 'cut-in' || n.edit === 'delete') pd.cutIn[n.screen] = 1;
    if (n.edit !== 'link' || n.screen !== from) return;
    if (n.op === 'link' && n.to) { pd.byPath[n.path] = {op: 'link', to: n.to}; pd.adds.push({to: n.to, path: n.path, text: n.text, rect: n.rect}); }
    else if (n.op === 'cut' || n.op === 'untrigger') pd.byPath[n.path] = {op: 'cut'};
  });
  return pd;
}

// 판에 늘 그리는 선에 겹칠 편집(graph.overview 의 pend) — 잇기 = 더함, 끊기·트리거 해제·도착 바꾸기 전 도착(was) = 뺌, 삭제·들어오는 연결 끊기 = 그 화면으로 오는 선 모두 뺌
function overviewPending(notes) {
  var pd = {add: [], drop: {}, cutIn: {}}, dec = function (k) { pd.drop[k] = (pd.drop[k] || 0) + 1; };
  (notes || []).forEach(function (n) {
    if (n.edit === 'cut-in' || n.edit === 'delete') pd.cutIn[n.screen] = 1;
    if (n.edit !== 'link' || !n.to) return;
    if (n.op === 'link') { pd.add.push({from: n.screen, to: String(n.to)}); if (n.was) dec(n.screen + '>' + n.was); }
    else if (n.op === 'cut' || n.op === 'untrigger') dec(n.screen + '>' + n.to);
  });
  return pd;
}

// 그 요소(from·path)를 to 로 잇는, 아직 보내지 않은 연결 편집 — 이 선을 자르면 끊기 메모 대신 이 편집을 취소한다(E4)
function pendingLink(notes, from, path, to) {
  return (notes || []).filter(function (n) {
    return !n.sent && n.edit === 'link' && n.op === 'link' && n.screen === from && n.path === path && String(n.to) === String(to);
  }).pop() || null;
}

// 도우미(helper.py)가 화면 파일에 바로 쓸 수 있는 편집
var BLOCK = {text: 1, remove: 1, duplicate: 1, move: 1, attr: 1, insert: 1, replace: 1};   // 요소 편집(task 49a·49b) — 도우미가 바로 쓴다
function directOf(n) {
  return BLOCK[n.edit] === 1 || n.edit === 'board' || n.edit === 'title' || n.edit === 'purpose' || n.edit === 'policy' || n.edit === 'policies' ||
         (n.edit === 'link' && ((n.op === 'link' && !!n.to) || n.op === 'cut' || n.op === 'untrigger'));
}

// 누르는 즉시 파일에 쓰는 편집(조각 2.2 D1): 잇기·끊기·트리거 해제 — 도착이 빈 레이아웃(new-…)이면 아직 파일이 없어 반영 대기로
// 요소 편집(task 49a): 글자·지우기·복제·옮기기도 바로(되돌리기 = 되살리기) — 도우미가 없으면 셸이 지금처럼 반영 대기로
function instantOf(n) {
  return BLOCK[n.edit] === 1 || n.edit === 'link' && (n.op === 'cut' || n.op === 'untrigger' || (n.op === 'link' && !!n.to && !/^new-/.test(n.to)));
}

// 반영 대기 미리보기(palette.js hd-pending 항목) — 그 화면의 글자 고치기 {path, text}(text '' = 비움) · 요소 지우기 {path, remove:true}
// · 복제 {path, dup:true} · 옮기기 {path, move:'up'|'down'}(task 49a) · 속성 {path, attr, value}(task 49b), 쌓인 차례대로 — 부품 넣기·바꾸기는 미리보기 없음(뼈대는 도우미가 뽑는다)
var PREVIEW = {text: 1, remove: 1, duplicate: 1, move: 1, attr: 1};
function preview(notes, screen) {
  return (notes || []).filter(function (n) { return n.screen === screen && PREVIEW[n.edit]; })
    .map(function (n) {
      if (n.edit === 'remove') return {path: n.path, remove: true};
      if (n.edit === 'duplicate') return {path: n.path, dup: true};
      if (n.edit === 'move' && n.op === 'to') return isSlot(n.to) ? {path: n.path, to: n.to} : null;   // 끌어 옮기기 반영 대기(51-3) — 자리 to(palette.js hd-pending)
      if (n.edit === 'move') return {path: n.path, move: n.op === 'up' ? 'up' : 'down'};
      if (n.edit === 'attr') return {path: n.path, attr: String(n.op || ''), value: String(n.value == null ? '' : n.value)};
      return {path: n.path, text: String(n.value == null ? '' : n.value)};
    }).filter(function (x) { return !!x; });
}
function isSlot(v) { return typeof v === 'number' && isFinite(v) && v >= 0 && Math.floor(v) === v; }

// 메모 패널 둘로(E5): pending = 기계적 편집(파일에 바로 쓸 수 있는 것) · memos = 나머지(AI 에 보내는 요청)
function split(notes) {
  var out = {memos: [], pending: []};
  (notes || []).forEach(function (n) { (directOf(n) ? out.pending : out.memos).push(n); });
  return out;
}

// 보내기 요청문(/hyper-design:fix 가 읽는 형식 — 항목 머리 '번호. screen=… · path=…'·text·요청 세 줄은 바꾸지 않는다)
// 항목 머리 끝 ' · no=N[,M…]'(#279) = 그 항목에 든 메모의 화면 안 번호(차례대로, 번호 없는 옛 메모는 줄 없음) — fix 가 hd reply <screen>#<no> 로 닫는다
// 요청 글이 여러 줄이면 둘째 줄부터 '요청: ' 뒤 글자 자리에 맞춰 들여 쓴다. 그 아래 덧붙는 줄(task 17):
//   소스(task 27·30) '   소스: 파일:줄'(첫 대상에 src 가 있을 때 — 앱 카드) · 빈 레이아웃(R5) = 그 화면 메모 본문 '- …'(번호 차례) · 범위(R7) '   범위: …' · 같은 요청의 다른 자리(R6) '   다른 곳: 경로 ("짧은 글") · …'
var CONT = '       ';
var SCOPE_LINE = {screen: '이 화면 전체', all: '모든 화면'};   // 범위 이름(이 요소 = 줄 없음) — 고르기 말은 annotation.SCOPES
function targetsOf(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text, rect: n.rect}]; }
function flat(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function scopeOf(n) { return n && SCOPE_LINE[n.scope] ? n.scope : 'element'; }
function byNo(a, b) { return (+a.no || 0) - (+b.no || 0); }
function isLayout(n) { return n.edit === 'new-screen'; }
// 보낼 메모 목록 → 항목들 [{screen, path, text, intent, note, scope, also:[{path,text}], memos:[메모], notes:[이 항목에 든 메모 전부]}]
function items(list) {
  list = list || [];
  var lay = {}, out = [], merge = {};
  list.forEach(function (n) { if (isLayout(n)) lay[n.screen] = 1; });
  var body = function (n) { return !n.edit && lay[n.screen]; };   // 빈 레이아웃 화면의 메모 = 그 레이아웃 항목에 실림(R5)
  list.forEach(function (n) {
    if (body(n)) return;
    var ts = targetsOf(n);
    if (isLayout(n)) {
      var ms = list.filter(function (m) { return body(m) && m.screen === n.screen; }).sort(byNo);
      out.push({screen: n.screen, path: ts[0].path, text: ts[0].text, intent: n.intent, note: n.note, scope: 'element', also: [], memos: ms, notes: [n].concat(ms)});
      return;
    }
    var key = n.edit ? null : [n.screen, n.intent, scopeOf(n), flat(n.note)].join('\u0001');   // 같은 화면·의도·범위·글 메모 = 한 항목(R6) — 편집은 하나씩
    var it = key && merge[key];
    if (!it) {
      it = {screen: n.screen, path: ts[0].path, text: ts[0].text, intent: n.intent, note: n.note, scope: scopeOf(n), also: [], memos: [], notes: []};
      if (ts[0].src) it.src = ts[0].src;
      ts = ts.slice(1); out.push(it); if (key) merge[key] = it;
    }
    it.notes.push(n);
    ts.forEach(function (t) {
      if (t.path !== it.path && !it.also.some(function (a) { return a.path === t.path; })) it.also.push({path: t.path, text: t.text});
    });
  });
  return out;
}
function indent(s, pad) { return String(s).replace(/[ \t]*\r?\n\s*/g, '\n' + pad); }   // 줄바꿈은 들여 쓴 다음 줄로 이어 남긴다(#225)
function nos(it) {
  var o = [];
  it.notes.forEach(function (n) { var v = +n.no; if (v > 0 && v === Math.floor(v) && o.indexOf(v) < 0) o.push(v); });
  return o.length ? ' · no=' + o.join(',') : '';
}
function place(a) { var t = flat(a.text); return a.path + (t && t.length <= 20 ? ' ("' + t + '")' : ''); }
// context(screenId) → 글 덩어리 | ''(R47 정보 카드 — 보내는 쪽이 넘기는 제공자, 이 모듈은 메모·연결을 모른다): 화면마다 첫 항목 머리 바로 아래, 줄마다 세 칸 들여 한 번.
//   제공자가 없거나 빈 글이면 요청문은 예전과 한 글자도 같다
var CARD_PAD = '   ';
function cardBlock(context, screen, seen) {
  if (typeof context !== 'function' || seen[screen]) return '';
  seen[screen] = 1;
  var t = context(screen);
  return typeof t === 'string' && t.trim() ? '\n' + CARD_PAD + t.replace(/\r\n?/g, '\n').split('\n').join('\n' + CARD_PAD) : '';
}
function request(notes, out, sizes, context) {      // sizes = {화면 id: 'W×H(프리셋)'} — 기본 크기가 아닌 카드만(task 46), 그 항목 아래 '화면 크기:' 줄
  var list = items(notes), sz = sizes && typeof sizes === 'object' ? sizes : {}, seen = {};
  return '[hyper-design 수정 요청] out=' + out + ' · ' + list.length + '건\n' + list.map(function (n, i) {
    return (i + 1) + '. screen=' + n.screen + ' · path=' + n.path + nos(n) + cardBlock(context, n.screen, seen) + '\n   text="' + String(n.text).replace(/\s+/g, ' ') + '" · intent=' + n.intent +
      '\n   요청: ' + indent(n.note, CONT) +
      (n.src && n.src.file ? '\n   소스: ' + n.src.file + (n.src.line ? ':' + n.src.line : '') : '') +
      n.memos.filter(function (m) { return flat(m.note); }).map(function (m) {
        return '\n' + CONT + '- ' + (m.intent === 'question' ? '(질문) ' : '') + indent(String(m.note).trim(), CONT + '  ');
      }).join('') +
      (n.scope !== 'element' ? '\n   범위: ' + SCOPE_LINE[n.scope] : '') +
      (n.also.length ? '\n   다른 곳: ' + n.also.map(place).join(' · ') : '') +
      (Object.prototype.hasOwnProperty.call(sz, n.screen) && sz[n.screen] ? '\n   화면 크기: ' + sz[n.screen] + ' — 이 뷰포트에 맞게 배치' : '');
  }).join('\n');
}
// 보낼 목록에서 목적도 메모 본문도 없는 빈 레이아웃 화면 id(복제는 내용이 있어 빼고) — 셸이 보낼 때 한 번 알린다(보내기는 그대로 간다)
function emptyLayouts(notes) {
  return items(notes).filter(function (it) {
    var n = it.notes[0];
    return isLayout(n) && !n.copyOf && !flat(n.purpose) && !it.memos.some(function (m) { return flat(m.note); });
  }).map(function (it) { return it.screen; });
}

// 화면마다 반영 대기 편집 수
function tally(notes) {
  var c = {}; (notes || []).forEach(function (n) { if (n.edit) c[n.screen] = (c[n.screen] || 0) + 1; }); return c;
}

// 요청문 글귀 — label = '"제목"(id)' 처럼 사람이 읽는 화면 이름(View 가 만들어 넘긴다)
var FIELD = {title: '화면 이름', purpose: '화면 설명', policy: '정책 줄', policies: '정책 줄'};
function circled(i) { return i < 20 ? String.fromCharCode(0x2460 + i) : '(' + (i + 1) + ')'; }   // ① … ⑳, 그 뒤 (21)
var say = {
  link: function (to) { return '이 요소를 누르면 ' + to + ' 화면으로 가게 연결'; },
  retarget: function (from, to) { return '도착 바꾸기: 지금 ' + from + ' → ' + to + ' 화면으로 가게'; },
  cut: function (to) { return '연결 끊기: 이 요소를 눌러도 ' + to + ' 화면으로 가지 않게'; },
  untrigger: function (to) { return '트리거 해제: 이 요소를 눌러도 화면이 바뀌지 않게(지금 ' + to + '로 가는 연결 없애기)'; },
  trigger: function () { return '트리거 지정: 이 요소를 다른 화면으로 가는 버튼으로(도착은 아직 정하지 않음)'; },
  text: function (v) { return v === '' ? '글자 비우기 — 요소는 그대로 두고 안의 글만 지우기' : '글자를 "' + v + '"(으)로 바꾸기'; },
  field: function (field, v, index, old) {          // v '' = 지우기(#243): 정책 줄 = 그 줄 지우기 · 설명 = 비우기 (old = 원래 글, 있으면 따옴표로)
    if (field === 'policies') {                      // 정책 목록 통째로(task 31) — 새 목록 전체를 한 줄로
      var at2 = ' (screens.json의 policies 전체)';
      return (v && v.length ? '정책 줄 바꾸기: ' + v.map(function (l, i) { return circled(i) + ' ' + flat(l); }).join(' ') : '정책 줄 모두 지우기') + at2;
    }
    var at = ' (screens.json의 ' + (field === 'policy' ? 'policies[' + index + ']' : field) + ')';
    if (v === '' && field === 'policy') return '정책 ' + (index + 1) + '번째 줄 ' + (old ? '"' + old + '" ' : '') + '지우기' + at;
    if (v === '' && field === 'purpose') return FIELD[field] + ' 비우기' + at;
    return (field === 'policy' ? '정책 ' + (index + 1) + '번째 줄' : FIELD[field]) + '을 "' + v + '"(으)로 바꾸기 (screens.json의 ' +
           (field === 'policy' ? 'policies[' + index + ']' : field) + ')';
  },
  layout: function (value, id, purpose) {           // purpose = 이 화면의 목적(여러 줄 그대로) — 있으면 첫째 브리프(#225)
    var p = purpose == null ? '' : String(purpose).trim();
    return '새 화면 "' + value + '"(' + id + ')을 빈 레이아웃으로 만들기 — ' +
           (p ? '목적: ' + p + ' · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기' : '내용은 이 화면에 남긴 메모를 따라 채우기');
  },
  linkNew: function (value, id) { return '이 요소를 누르면 새 화면 "' + value + '"(' + id + ')으로 가게 연결'; },
  copy: function (value, id, src) { return '새 화면 "' + value + '"(' + id + ')을 ' + src + ' 화면을 복제해 만들기'; },
  remove: function () { return '요소 지우기 — 이 요소(안의 글·자식 포함)를 화면에서 없애기'; },   // 요소 하나(task 30)
  duplicate: function () { return '요소 복제 — 이 요소(안의 글·자식 포함)를 바로 뒤에 하나 더(복사본의 id·data-region 은 빼기)'; },   // task 49a
  move: function (dir) { return dir === 'up' ? '요소 위로 옮기기 — 이 요소를 바로 앞 형제 요소와 자리 바꾸기' : '요소 아래로 옮기기 — 이 요소를 바로 뒤 형제 요소와 자리 바꾸기'; },
  moveTo: function (to) { return '요소 옮기기 — 이 요소를 같은 부모의 형제 요소 사이 ' + (to + 1) + '번째 자리로'; },   // 끌기 한 번(move op:to, 51-3 — view-optimistic 과 같은 글)
  attr: function (name, v) { return v === '' ? '속성 ' + name + ' 비우기' : '속성 ' + name + ' 를 "' + v + '"(으)로 바꾸기'; },   // task 49b
  insert: function (title) { return '부품 넣기: ' + title + ' — 이 요소 바로 아래에 Components 부품의 뼈대(글은 중립 글, 데이터는 화면에 맞게 채우기)'; },
  replace: function (title) { return '부품으로 바꾸기: ' + title + ' — 이 요소 자리에 Components 부품의 뼈대(글은 중립 글, 데이터는 화면에 맞게 채우기)'; },
  removeScreen: function (label) { return '이 화면 ' + label + '을 지우기 — 화면 파일과 screens.json 항목, 이 화면으로 오는 연결도 정리'; },
  cutIn: function (label) { return '이 화면 ' + label + '으로 오는 연결을 모두 끊기(다른 화면의 버튼·링크에서)'; },
  emptyLayout: '빈 레이아웃에 목적이나 메모가 없어요 — AI가 채울 내용을 모를 수 있어요'
};

function layoutId(now, rnd) { return 'new-' + now.toString(36).slice(-5) + rnd.toString(36).slice(2, 4); }
function layoutText(n) { return say.layout(n.value, n.screen, n.purpose); }
function layout(id, p, name) {
  var n = note(id, {path: '(새 화면)', text: '빈 레이아웃', rect: null}, '', 'new');
  n.edit = 'new-screen'; n.value = name || '빈 레이아웃'; n.x = p.x; n.y = p.y; n.note = layoutText(n);
  return n;
}
function layoutOf(list, id) { return (list || []).filter(function (x) { return x.edit === 'new-screen' && x.screen === id; })[0] || null; }

HD.edits = {note: note, newId: newId, layoutId: layoutId, layout: layout, layoutText: layoutText, layoutOf: layoutOf, pendingFor: pendingFor, overviewPending: overviewPending, pendingLink: pendingLink, directOf: directOf, instantOf: instantOf, preview: preview, split: split, tally: tally, request: request, items: items, emptyLayouts: emptyLayouts, say: say, FIELD: FIELD};
})();
