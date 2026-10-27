/* Model — 주소 복사 규칙(R30, Figma '선택 링크 복사'): 카드·요소 하나를 터미널에 붙일 한 줄로 만들고 다시 읽는다. DOM·저장소를 쓰지 않는다.
   줄 = 'hd://<프로젝트>/<화면 id>[#<요소 경로>]  <화면 파일 절대 경로> · "<짧은 글>"' — 요소 경로는 palette.js pathOf 의 것 그대로(메모 요청문 path=… 와 같은 것),
     화면 id 는 메모 요청문 screen=… 와 같은 것. 토큰(?hd=)은 넣지 않는다. 같은 규칙의 Python 읽기 = hd/hd_address.py(공유 fixture tests/fixtures/addresses.json).
   글자 바꾸기(퍼센트): 프로젝트·화면 = % · 공백 · # · / · ? · " · 제어 글자, 요소 경로 = % · 공백 · # · " · 제어 글자(한글은 그대로). 파일 경로는 그대로(줄 끝 ' · "' 로 가른다).
     글 = 공백을 하나로, 40자 넘으면 39자 + '…', \ 와 " 는 앞에 \.
   HD.address = {build({project, screen, path?, file, text}) → 줄, parse(줄) → {project, screen, path|null, file|null, text|null}|null,
     lines(items) → 줄들(\n), short(t) → 40자 글, projectOf(out) → 프로젝트 이름(hd_model.project_name — out 폴더 이름이 'out' 이면 그 위),
     outOf(hdOut, pathname) → out 폴더(도우미 주입 __hdOut, 아니면 file:// 경로의 폴더), fileOf(out, file) → 절대 경로,
     targets(list, clicked, keyOf) → 복사할 것(누른 것이 고른 묶음 안이면 묶음 차례 그대로, 아니면 그 하나), say(n) → 토스트 글}
   오류 탐지: 화면 id 가 없으면 build 는 '' (부르는 쪽이 건너뜀) · parse 는 'hd://' 로 시작하지 않거나 프로젝트·화면이 비었거나 %가 깨졌으면 null. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var MAX = 40;
var SEG_RE = /[%\s#\/?"\u0000-\u001f\u007f]/g, PATH_RE = /[%\s#"\u0000-\u001f\u007f]/g;
function enc(s, re) { return String(s == null ? '' : s).replace(re, function (c) { return encodeURIComponent(c); }); }
function dec(s) { try { return decodeURIComponent(s); } catch (e) { return null; } }   // 깨진 % = 읽지 못함(null)

function short(t) {
  var s = String(t == null ? '' : t).replace(/\s+/g, ' ').trim();
  return s.length > MAX ? s.slice(0, MAX - 1) + '…' : s;
}
function quote(t) { return '"' + short(t).replace(/[\\"]/g, '\\$&') + '"'; }
function unquote(q) { return q.replace(/\\([\\"])/g, '$1'); }

function build(o) {
  o = o || {};
  if (o.screen == null || o.screen === '') return '';
  var a = 'hd://' + enc(o.project, SEG_RE) + '/' + enc(o.screen, SEG_RE) + (o.path ? '#' + enc(o.path, PATH_RE) : '');
  return a + '  ' + String(o.file == null ? '' : o.file) + ' · ' + quote(o.text);
}

function parse(line) {
  var s = String(line == null ? '' : line).trim();
  if (s.slice(0, 5) !== 'hd://') return null;
  var sp = s.search(/\s/), addr = sp < 0 ? s : s.slice(0, sp), rest = sp < 0 ? '' : s.slice(sp).trim();
  var body = addr.slice(5), h = body.indexOf('#'), head = h < 0 ? body : body.slice(0, h), frag = h < 0 ? null : body.slice(h + 1);
  var sl = head.indexOf('/');
  if (sl <= 0 || sl === head.length - 1) return null;
  var project = dec(head.slice(0, sl)), screen = dec(head.slice(sl + 1).replace(/\/$/, '')), path = frag == null || frag === '' ? null : dec(frag);
  if (!project || !screen || (frag && path == null)) return null;
  var file = rest || null, text = null, m = /^(.*?)\s*· "((?:[^"\\]|\\.)*)"$/.exec(rest);
  if (m) { file = m[1].trim() || null; text = unquote(m[2]); }
  return {project: project, screen: screen, path: path, file: file, text: text};
}

function lines(items) { return (Array.isArray(items) ? items : []).map(build).filter(Boolean).join('\n'); }

function base(p) {
  var parts = String(p == null ? '' : p).replace(/\\/g, '/').split('/').filter(Boolean);
  return parts;
}
function projectOf(out) {
  var parts = base(out), last = parts[parts.length - 1] || '';
  var name = last === 'out' && parts.length > 1 ? parts[parts.length - 2] : last;
  return /^[A-Za-z]:$/.test(name) ? '' : name;
}
function outOf(hdOut, pathname) {
  if (typeof hdOut === 'string' && hdOut) return hdOut.replace(/\\/g, '/').replace(/\/+$/, '');
  var p = String(pathname == null ? '' : pathname);
  p = dec(p) == null ? p : dec(p);
  p = p.replace(/\/[^\/]*$/, '');
  if (/^\/[A-Za-z]:/.test(p)) p = p.slice(1);
  return p || '/';
}
function fileOf(out, file) {
  var f = String(file == null ? '' : file).replace(/\\/g, '/');
  if (/^([A-Za-z]:)?\//.test(f)) return f;
  var o = String(out == null ? '' : out).replace(/\/+$/, '');
  return (o ? o + '/' : '') + f.replace(/^\.\//, '');
}

function targets(list, clicked, keyOf) {
  list = Array.isArray(list) ? list : [];
  if (clicked == null) return list.slice();
  var k = keyOf(clicked);
  for (var i = 0; i < list.length; i++) if (keyOf(list[i]) === k) return list.slice();
  return [clicked];
}
function say(n) { return n > 1 ? '주소 ' + n + '개를 복사했어요' : '주소를 복사했어요'; }

HD.address = {MAX: MAX, build: build, parse: parse, lines: lines, short: short, projectOf: projectOf, outOf: outOf, fileOf: fileOf, targets: targets, say: say};
})();
