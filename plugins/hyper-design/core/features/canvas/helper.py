"""로컬 도우미 — 캔버스 편집을 화면 파일에 바로 쓴다 (docs/eungshin/canvas-edit-plan-2026-10-19.md 7단계, 결정 8B).

python3 helper.py <out> [--port 0] [--paseo-agent ID] [--no-open]

- 포트(#270): --port 가 없으면 <out>/.hd-helper.json 의 지난 포트를 먼저, 막혔으면 빈 포트(한 줄 남김) — 주소가 같아야 캔버스 localStorage 가 이어진다.
- 한 out 에 하나(#271): .hd-helper.json 의 pid 가 살아 있고 그 주소가 답하면 띄우지 않고 종료 코드 1. 죽은 pid 면 덮어쓴다.
  .hd-helper.json = 떠 있는 동안 {url, pid, port, token} · 정상 종료 뒤 {port}.
- 읽기(GET /api/state · index.html 스냅숏)는 빌드 자물쇠를 기다리지 않는다(쓰기가 임시 파일 + os.replace) — 쓰기만 하나씩.
- 127.0.0.1 에만 열고, 실행마다 새 토큰을 만든다. 출력한 주소(…/index.html?hd=<토큰>)로 캔버스를 열면 '보내기'가 도우미를 쓴다.
- 쓰는 곳은 <out> 안뿐이다. 쓰기 전에 원본을 <out>/.hd-history/<시각>/ 에 남기고, 쓴 뒤 build_canvas.py 로 캔버스를 다시 만든다(실패하면 원본으로 되돌림).
- 바로 쓰는 편집(결정형): 글자(text — 요소 안 내용 전부, '' = 비우기) · 요소 지우기(remove) · 카드 이름(title) · 설명(purpose) · 정책 목록(policies, task 31) · 옛 정책 줄(policy, index) · 잇기/도착 바꾸기(link) · 끊기/트리거 해제(cut).
  나머지 메모(질문, 새 화면, 도착 없는 트리거 지정 등)는 요청문 그대로 <out>/.hd-queue/<시각>.txt 대기열 파일에 쓰고,
  --paseo-agent 가 있으면 그 파일을 `paseo send <agent> --prompt-file … --no-wait` 로 그 에이전트 터미널에 넣는다
  (없으면 터미널에서 /hyper-design:fix 에 그 내용을 붙여 넣는다).
- 도우미가 꺼져 있으면 캔버스는 지금처럼 요청문을 복사한다.

- 쓰기마다 <out>/.hd-history/<stamp>/manifest.json = {files:{relpath:{before, after_sha}}, changed} — 되살리기는 그 뒤 파일이 안 바뀌었을 때만.

API (모두 POST, JSON, 머리글 X-HD-Token 필수 · Host 는 127.0.0.1/localhost 의 그 포트만)
  /api/apply   {edits:[{id, screen, edit, path, value?, to?}]} → {applied:[id], failed:[{id, reason}], stamp, changed:[screen]}
    edit: text(value — 요소 안 글·인라인 자식 전부를 바꿈, 안에 블록 자식이면 거절) · remove(요소 통째로, html·body·화면 뿌리 거절) · title · purpose
      · policies(value = [글] — 화면의 policies 를 통째로 바꿈, 글 목록·50줄·줄마다 500자 아니면 거절) · policy(옛 메모: index, op delete) · link · reason = 한국어
  /api/delete  {screens:[id]}                                 → {deleted:[id], cut:[{screen, path, to}], failed, stamp, changed:[screen]}
  /api/restore {stamp}                                        → {restored:[relpath], changed:[screen]} | 409 {error, reason:'changed-since'}
  /api/data    {}                                             → build_canvas.index_data (index.html 의 hd-data 와 같은 객체)
  /api/forward {text}                                         → {via:'paseo'|'queue', agent?, path?}
  /api/watch   {files:[relpath]}                              → {mtimes:{relpath: mtime|null}} (없거나 out 밖이면 null)
  GET /api/state                                              → {rev, state} (<out>/.hd-canvas.json, 없으면 rev 0)
  PUT /api/state {rev, state:{이름: 값|null}}                 → {rev} | 409 {rev, state}(rev 가 다름) · 400(JSON 아님) · 413(2 MB 넘음)
  POST /api/reply {note: id | {screen, no}, reply:{kind, …칸, detail?, by?}} → {rev, status} · 400 {error, errors:[칸마다 한 줄]} · 404(없는 메모)
    — 답 규칙은 ../hd/hd_model.py(tasks/PLAN-2026-10-23.md §3). 늘 최신 파일에 붙이고 rev+1(rev 를 받지 않는다). by 기본 'agent', at = 지금.
  POST /api/stop {}                                           → {stopping:true} 를 답한 뒤 서버를 정상 종료(표지 지움 · .hd-helper.json 은 {port} 만 남김) — `hd stop`
  POST /api/attach {agent: id|null}                           → {agent} — /api/forward 가 보낼 Paseo 에이전트를 바꾸고 표지의 agent 를 고쳐 씀(다시 띄우지 않음).
    id = 빈 글 아님·128자 이하·띄어쓰기 없음(hd_model.agent_error), 아니면 400 · null = 떼기(대기열 파일로) — `hd attach`
  GET /api/projects                                           → `hd projects --json` 과 같은 줄 [{name, out, state: running|off|missing, url, pid, last_opened}]
  POST /api/open {name, agent?}                               → {name, out, url, pid, agent, reused} — `hd open` 과 같은 hd_client.open_project(브라우저 없음).
    agent 기본 = 이 도우미의 지금 agent · 모르는 이름·없어진 out 404 {error} · 빌드·띄우기 실패 500 {error}
  POST /api/claim {screen, by?, note?}                       → {rev, screen, file} — `hd claim`: state.busy 에 cli 덮개 {via:'cli', since, file, mtime(지금 파일 시각), by?, note?}
    를 늘 최신 파일에 넣고 rev+1(rev 를 받지 않는다 — /api/reply 와 같은 까닭: 쓰는 곳 하나·자물쇠 하나, CLI 가 409 를 다시 시도할 일이 없다). 모르는 화면 404 · 칸 오류 400
  POST /api/release {screen}                                  → {rev, released: bool} — `hd release`: 그 덮개를 걷는다(없으면 released false, 쓰지 않음)
  GET /api/agents[?auto=1]                                    → {agents:[{id, name, status, cwd, provider}], current: 지금 보낼 곳 id|null, repo: 저장소 뿌리|null, error?}
    auto=1(캔버스가 열 때) = 이미 붙어 있거나 repo 를 모르면 paseo 를 띄우지 않고 {agents:[], skipped:true}
    — `paseo ls -g --json`(읽기만, UTF-8 로 풂, 보관된 것 뺌, 5초 캐시). Paseo 가 없으면 200 {agents:[], error:'Paseo 를 찾을 수 없어요'}.
    repo = app.json 의 repo, 아니면 out 위 .git 폴더. 캔버스가 고르면 POST /api/attach(아래) — 줄 차례·제안은 modules/agents.js(#214)
  GET /api/files?since=N                                      → {seq, changed:[screen]} — 도우미가 1초마다 screens.json 에 적힌 화면 파일(out 안만) mtime 을 보고,
    바뀔 때마다 seq+1. changed = since 보다 뒤에 바뀐 화면(since 없거나 -1 = 기준만, changed []). 캔버스는 그 카드만 다시 싣는다
  예) curl -X POST -H "X-HD-Token: …" -d '{"screen":"home","note":"버튼 고치는 중"}' http://127.0.0.1:PORT/api/claim
  떠 있는 표지: ~/.hyper-design/active/<pid>.json = {pid, project, out, url, token, port, agent, started} (HD_HOME 으로 바꿈) — `hd ls` 가 읽는다. 정상 종료 때 지운다.
  시작할 때 out 이 프로젝트 목록(~/.hyper-design/projects.json, 링크만)에 없으면 넣는다 — 연 캔버스는 나중에 `hd open <이름>` 으로 다시 연다.
  상태 파일 = {version:1, rev, updated, state:{notes, card-pos, edit-log, link-names, hidden, locked, folders, busy, …}} — 캔버스 프로젝트별 키의 진실 원천.
  index.html 을 줄 때 window.__hdState = {rev, state} 를 끼워 넣는다(캔버스는 동기로 읽는다). 쓰기는 임시 파일 + os.replace, 앞 것 하나는 .bak.
"""
import argparse, atexit, datetime, hashlib, html, json, os, pathlib, re, secrets, shutil, signal, subprocess, sys, threading, time, urllib.parse, webbrowser
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import build_canvas

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_model  # noqa: E402  — 답 규칙(순수 Model) 하나를 CLI 와 같이 쓴다
import hd_client  # noqa: E402  — 프로젝트 목록(링크) 쓰기는 CLI 와 같은 Client 하나로

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE / "build_canvas.py"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
PASEO_DEFAULT = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Paseo" / "resources" / "bin" / "paseo.cmd"


# ---------------------------------------------------------------- HTML: 원문 위치를 아는 작은 트리
class Node:
    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag, self.attrs, self.start, self.open_end, self.parent = tag, dict(attrs), start, open_end, parent
        self.children, self.texts = [], []          # texts: (원문 위치, 길이, 글) — 이 요소 바로 아래 글
        self.close = None                           # 닫는 태그 (시작, 끝) — void·self-closing 은 없음(끝 = open_end), 닫히지 않은 요소도 없음
        self.void = False
        self.order = []                             # 아이·글을 문서 순서대로: ('el', Node) | ('tx', (pos, len, data))


class Tree(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src, self.lines = src, [0]
        for m in re.finditer("\n", src):
            self.lines.append(m.end())
        self.root = Node("#root", [], 0, 0, None)
        self.stack = [self.root]
        self.feed(src); self.close()

    def _pos(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        pos = self._pos(); raw = self.get_starttag_text() or ""
        n = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        self.stack[-1].children.append(n); self.stack[-1].order.append(("el", n))
        if tag not in VOID and not raw.rstrip().endswith("/>"):
            self.stack.append(n)
        else:
            n.void = True

    def handle_startendtag(self, tag, attrs):
        pos = self._pos(); raw = self.get_starttag_text() or ""
        n = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        n.void = True
        self.stack[-1].children.append(n); self.stack[-1].order.append(("el", n))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                pos = self._pos(); gt = self.src.find(">", pos)
                self.stack[i].close = (pos, gt + 1 if gt >= 0 else len(self.src))
                del self.stack[i:]
                return

    def _text(self, data):
        if self.stack[-1].tag in ("script", "style"):
            return
        t = (self._pos(), len(data), data)
        self.stack[-1].texts.append(t); self.stack[-1].order.append(("tx", t))

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        self._text("&" + name + ";")

    def handle_charref(self, name):
        self._text("&#" + name + ";")

    def walk(self, n=None):
        n = n or self.root
        for c in n.children:
            yield c
            yield from self.walk(c)


def _unesc(s):                                       # CSS.escape 되돌리기(\31 · \: 등)
    s = re.sub(r"\\([0-9a-fA-F]{1,6}) ?", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"\\(.)", r"\1", s)


SEG = re.compile(r'^(?:#(?P<id>.+)|(?P<tag>[a-zA-Z][\w-]*)(?:\[data-region="(?P<reg>(?:[^"\\]|\\.)*)"\]|(?:\.(?P<cls>(?:[^:\\]|\\.)+))?(?::nth-of-type\((?P<nth>\d+)\))?))$')


def _seg_ok(n, seg):
    m = SEG.match(seg)
    if not m:
        raise ValueError("모르는 경로 조각: " + seg)
    if m.group("id") is not None:
        return n.attrs.get("id") == _unesc(m.group("id"))
    if n.tag != m.group("tag").lower():
        return False
    if m.group("reg") is not None:
        return n.attrs.get("data-region") == m.group("reg").replace('\\"', '"')
    if m.group("cls") is not None and ((n.attrs.get("class") or "").split() or [""])[0] != _unesc(m.group("cls")):
        return False
    if m.group("nth") is not None:
        sib = [c for c in (n.parent.children if n.parent else []) if c.tag == n.tag]
        if sib.index(n) + 1 != int(m.group("nth")):
            return False
    return True


def select(tree, path):
    """palette.js pathOf 가 만든 경로(조각 ' > ' 조각, 자식 관계) → 요소 하나. 없거나 여럿이면 ValueError."""
    segs = [s.strip() for s in path.split(" > ") if s.strip()]
    if not segs:
        raise ValueError("빈 경로")
    hits = []
    for n in tree.walk():
        cur, ok = n, True
        for seg in reversed(segs):
            if cur is None or cur.tag == "#root":
                ok = False; break
            if seg == "body" and cur.tag != "body" or seg != "body" and not _seg_ok(cur, seg):
                ok = False; break
            cur = cur.parent
        if ok:
            hits.append(n)
    if len(hits) != 1:
        raise ValueError(f"경로에 맞는 요소 {len(hits)}개: {path}")
    return hits[0]


def _set_attr(tag_src, name, value):                # 시작 태그 원문에서 속성 하나 바꾸기(없으면 더하기 · None 이면 지우기)
    rx = re.compile(r'(\s' + re.escape(name) + r')(\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?', re.I)
    if value is None:
        return rx.sub("", tag_src, count=1)
    new = ' %s="%s"' % (name, html.escape(value, quote=True))
    if rx.search(tag_src):
        return rx.sub(lambda m: new, tag_src, count=1)
    end = len(tag_src) - (2 if tag_src.endswith("/>") else 1)
    return tag_src[:end].rstrip() + new + tag_src[end:]


# 글자 고치기(task 30): 요소 안 내용 전부(글 + 인라인 자식)를 새 글로 — 이 태그들(글이 든 것, br·wbr)만 안에 있어도 된다.
# 그 밖(블록·그림·입력·링크 a·글 없는 아이콘 자식)이 안에 있으면 거절 — 일부만 바꾸지 않는다. palette.js 미리보기(pending)와 같은 규칙.
INLINE = {"b", "strong", "i", "em", "span", "small", "u", "s", "mark", "sub", "sup", "code", "abbr", "cite", "q", "kbd", "var", "time",
          "font", "del", "ins", "br", "wbr"}
BLOCK_REASON = "안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요"


def _has_text(n):
    return any(x[2].strip() for x in n.texts) or any(_has_text(c) for c in n.children if c.tag not in ("script", "style"))


def _inline_only(n):
    for c in n.children:
        if c.tag not in INLINE or (c.tag not in ("br", "wbr") and not _has_text(c)) or not _inline_only(c):
            return False
    return True


def _is_root(el):                                    # html·head·body · 화면 뿌리(body 또는 조각 맨 위의 유일한 요소)
    if el.tag in ("html", "head", "body"):
        return True
    p = el.parent
    if p is None or p.tag not in ("body", "#root"):
        return False
    return [c for c in p.children if c.tag not in ("script", "style", "link", "meta")] == [el]


def _text_patch(src, el, value, path):
    if el.void or el.close is None:
        raise ValueError("글자를 넣을 수 없는 요소예요(닫는 태그 없음): " + path)
    if not _inline_only(el):
        raise ValueError(BLOCK_REASON)
    a, b = el.open_end, el.close[0]
    inner = src[a:b]
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):] if inner.strip() else ""
    return a, b, lead + html.escape(value, quote=False).replace("\n", "<br>") + trail


def _remove_patch(el, path):
    if _is_root(el):
        raise ValueError("화면 뿌리(html·body·맨 바깥 요소)는 지울 수 없어요 — 화면을 지우려면 카드 메뉴의 삭제: " + path)
    if el.void:
        return el.start, el.open_end, ""
    if el.close is None:
        raise ValueError("닫는 태그를 찾지 못해 지울 수 없어요: " + path)
    return el.start, el.close[1], ""


def edit_html(src, edits):
    """edits = [(path, op, value)] — op: text(요소 안 내용 전부를 value 로, '' = 비우기) | remove(요소 통째로) | link(value=도착 id) | cut.
    원문 위치 기준으로 뒤에서부터 바꾼다. 같은 자리 두 편집 = 나중 것, 겹치는 자리(안팎) = ValueError."""
    tree, spans = Tree(src), {}
    for path, op, value in edits:
        el = select(tree, path)
        if op == "text":
            p = _text_patch(src, el, value, path)
        elif op == "remove":
            p = _remove_patch(el, path)
        elif op in ("link", "cut"):
            p = _relink(src, el, op, value, path)
        else:
            raise ValueError("모르는 편집: " + op)
        spans[(p[0], p[1])] = p                       # 같은 자리 = 나중 것
    patches = sorted(spans.values(), key=lambda p: (p[0], p[1]))
    for x, y in zip(patches, patches[1:]):
        if y[0] < x[1]:
            raise ValueError("한 요소에 겹치는 편집이에요 — 하나씩 반영해 주세요")
    return _patch(src, patches)


def _relink(src, el, op, value, path=""):
    """요소 하나의 시작 태그 → 잇기(value=도착 id)·끊기 한 패치 (start, end, 새 태그)."""
    tag_src = src[el.start:el.open_end]
    href = value + ".html" if op == "link" else None
    onclick = el.attrs.get("onclick") or ""
    if el.tag == "a" or "href" in el.attrs:
        tag_src = _set_attr(tag_src, "href", href)
    elif "data-href" in el.attrs:
        tag_src = _set_attr(tag_src, "data-href", href)
    elif re.search(r"\.html?", onclick):
        tag_src = _set_attr(tag_src, "onclick", "location.href='%s'" % href if href else None)
    elif op == "link":
        tag_src = _set_attr(tag_src, "onclick", "location.href='%s'" % href)
    else:
        raise ValueError("이 요소에는 끊을 연결이 없어요: " + path)
    if op == "cut" and "href" in el.attrs and "data-href" in el.attrs:   # 둘 다 있으면 둘 다 끊는다
        tag_src = _set_attr(tag_src, "data-href", None)
    return el.start, el.open_end, tag_src


def _patch(src, patches):                            # 원문 위치 기준으로 뒤에서부터
    for a, b, new in sorted(patches, key=lambda p: -p[0]):
        src = src[:a] + new + src[b:]
    return src


def _path_of(n):                                     # 요소 → select() 가 다시 찾는 경로(태그:nth-of-type 사슬)
    segs = []
    while n.parent is not None:
        if n.tag == "body":
            segs.append("body"); break
        segs.append("%s:nth-of-type(%d)" % (n.tag, [c for c in n.parent.children if c.tag == n.tag].index(n) + 1))
        n = n.parent
    return " > ".join(reversed(segs))


def _link_to(attrs):
    """요소 속성 → 가는 화면 id | None — build_canvas._Links + link_target 과 같은 규칙(href · data-href · onclick 안 .html, 공유 fixture links.json)."""
    h = attrs.get("href") or attrs.get("data-href")
    if not h and attrs.get("onclick"):
        m = build_canvas.GO_ONCLICK.search(attrs["onclick"]); h = m and m.group(1)
    return build_canvas.link_target(h) if h else None


# ---------------------------------------------------------------- 편집 적용(out 안만 · 원본 남김 · 다시 빌드)
def _inside(out, p):
    p = p.resolve()
    return p == out or out in p.parents


def _sha(p):                                         # 파일 sha256 | None(없음)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 자식 프로세스가 콘솔 창을 띄웠다 닫지 않게(창 없이 뜬 도우미에서 편집마다 깜빡임)


def _build(out):
    return subprocess.run([sys.executable, str(BUILD), str(out)], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=NO_WINDOW)


def _screen_files(data):
    return {s["id"]: s.get("file") or f"screens/{s['id']}.html" for s in data.get("screens", [])}


def _write_json(sj, data, raw):                      # 원래 들여쓰기·끝 줄바꿈을 따라 쓴다
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2 if '\n  "' in raw else None) + ("\n" if raw.endswith("\n") else ""),
                  encoding="utf-8", newline="")


class _Writes:
    """쓰기 한 번 — 원본을 .hd-history/<stamp>/<relpath> 에 남기고, 끝나면 manifest(쓴 뒤 해시)를 적는다."""
    def __init__(self, out, stamp=None):
        self.out = out
        self.stamp = stamp or datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.hist = out / ".hd-history" / self.stamp
        self.before = {}                             # relpath → 쓰기 전에 있었나

    def _dst(self, f):
        rel = f.relative_to(self.out).as_posix()
        dst = self.hist / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        return rel, dst

    def keep(self, f):                               # 쓰기 전 원본 복사(처음 한 번만)
        rel, dst = self._dst(f)
        if rel not in self.before:
            self.before[rel] = f.is_file()
            if self.before[rel]:
                shutil.copy2(f, dst)

    def move(self, f):                               # 지우기 = 기록으로 옮기기
        rel, dst = self._dst(f)
        if rel in self.before:
            f.unlink()
        else:
            self.before[rel] = True; shutil.move(str(f), str(dst))

    def undo(self):
        for rel, had in self.before.items():
            f = self.out / rel
            if had:
                shutil.copy2(self.hist / rel, f)
            elif f.exists():
                f.unlink()

    def commit(self, changed):
        """다시 빌드 → 성공이면 manifest 를 적고 None, 실패면 원본으로 되돌리고 이유."""
        r = _build(self.out)
        if r.returncode != 0:
            self.undo(); _build(self.out)
            return "캔버스 다시 빌드 실패 — 되돌림: " + (r.stderr or "")[-300:]
        files = {rel: {"before": had, "after_sha": _sha(self.out / rel)} for rel, had in sorted(self.before.items())}
        (self.hist / "manifest.json").write_text(json.dumps({"files": files, "changed": changed}, ensure_ascii=False, indent=2), encoding="utf-8")
        return None


POLICY_MAX_LINES, POLICY_MAX_CHARS = 50, 500


def _policies(v):
    """policies 편집 값 검사 — 글 목록, 50줄 이하, 줄마다 500자 이하. 앞뒤 빈칸을 자르고 빈 줄은 버린다. 아니면 ValueError(한국어)."""
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise ValueError("정책 줄은 글 목록이어야 해요")
    v = [x.strip() for x in v if x.strip()]
    if len(v) > POLICY_MAX_LINES:
        raise ValueError("정책 줄이 %d줄을 넘어요(%d줄)" % (POLICY_MAX_LINES, len(v)))
    for i, x in enumerate(v):
        if len(x) > POLICY_MAX_CHARS:
            raise ValueError("정책 %d번째 줄이 %d자를 넘어요" % (i + 1, POLICY_MAX_CHARS))
    return v


def apply_edits(out, edits, stamp=None):
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    data = json.loads(sj.read_text(encoding="utf-8"))
    files = _screen_files(data)
    applied, failed, html_ops, json_ops, owner = [], [], {}, [], {}
    for e in edits:
        eid, sid, kind = e.get("id"), e.get("screen"), e.get("edit")
        try:
            if sid not in files:
                raise ValueError("없는 화면: %s" % sid)
            if kind == "policies":                  # 정책 목록 통째로(task 31)
                json_ops.append((eid, sid, "policies", _policies(e.get("value"))))
                continue
            if kind in ("title", "purpose", "policy"):
                if kind == "policy" and not isinstance(e.get("index"), int):
                    raise ValueError("정책 줄 번호가 없어요")
                v = str(e.get("value", ""))
                if kind == "policy" and (e.get("op") == "delete" or not v.strip()):   # 비운 정책 줄 = 그 줄 지우기(#243)
                    kind = "policy-delete"
                json_ops.append((eid, sid, kind if kind not in ("policy", "policy-delete") else (kind, e["index"]), v))
                continue
            if kind == "text":
                op = ("text", str(e.get("value", "")))
            elif kind == "remove":
                op = ("remove", None)
            elif kind == "link" and e.get("op") == "link" and e.get("to") in files:
                op = ("link", e["to"])
            elif kind == "link" and e.get("op") in ("cut", "untrigger"):
                op = ("cut", None)
            else:
                raise ValueError("바로 쓸 수 없는 편집(터미널로): %s/%s" % (kind, e.get("op")))
            f = (out / files[sid])
            if not _inside(out, f) or not f.is_file():
                raise ValueError("out 밖이거나 없는 파일: %s" % files[sid])
            html_ops.setdefault(f, []).append((eid, e.get("path") or "", op[0], op[1])); owner[f] = sid
        except ValueError as err:
            failed.append({"id": eid, "reason": str(err)})
    if not html_ops and not json_ops:
        return {"applied": applied, "failed": failed, "stamp": None, "changed": []}
    w, changed = _Writes(out, stamp), set()
    for f, ops in html_ops.items():                 # 한 화면 안에서 하나가 실패하면 그 하나만 빼고 다시
        src = f.read_text(encoding="utf-8")
        good = []
        for o in ops:                               # 앞서 된 것과 함께 되는지 — 겹치면 나중 것만 실패
            try:
                edit_html(src, [(g[1], g[2], g[3]) for g in good] + [(o[1], o[2], o[3])]); good.append(o)
            except ValueError as err:
                failed.append({"id": o[0], "reason": str(err)})
        if good:
            new = edit_html(src, [(o[1], o[2], o[3]) for o in good])
            w.keep(f); f.write_text(new, encoding="utf-8", newline="")
            applied += [o[0] for o in good]; changed.add(owner[f])
    if json_ops:
        by = {s["id"]: s for s in data["screens"]}
        drop = {}                                   # 화면 → 지울 정책 줄 번호(원래 번호) — 바꾸기를 다 한 뒤 큰 번호부터
        for eid, sid, kind, v in json_ops:
            if isinstance(kind, tuple):                 # 정책 줄 i
                pol = by[sid].setdefault("policies", [])
                if not 0 <= kind[1] < len(pol):
                    failed.append({"id": eid, "reason": "없는 정책 줄: %d" % kind[1]}); continue
                if kind[0] == "policy-delete":
                    drop.setdefault(sid, set()).add(kind[1])
                else:
                    pol[kind[1]] = v
            elif kind == "policies":                # 목록 통째로 — 앞선 옛 줄 지우기는 이 목록에 닿지 않는다
                by[sid]["policies"] = list(v); drop.pop(sid, None)
            else:
                by[sid][kind] = v
            applied.append(eid); changed.add(sid)
        for sid, idx in drop.items():
            for i in sorted(idx, reverse=True):
                del by[sid]["policies"][i]
        raw = sj.read_text(encoding="utf-8")
        w.keep(sj); _write_json(sj, data, raw)
    changed = sorted(changed)
    err = w.commit(changed)
    if err:                                         # 다시 빌드가 깨지면 원본으로 되돌렸다
        return {"applied": [], "failed": failed + [{"id": i, "reason": err} for i in applied], "stamp": None, "changed": []}
    return {"applied": applied, "failed": failed, "history": str(w.hist), "stamp": w.stamp, "changed": changed}


def delete_screens(out, ids, stamp=None):
    """화면 지우기(2.2 D3) — screens.json 에서 빼고(그리로 가는 branches 도), 화면 파일은 기록으로 옮기고, 다른 화면에서 오는 링크는 끊는다."""
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    raw = sj.read_text(encoding="utf-8")
    data = json.loads(raw)
    files = _screen_files(data)
    gone = [i for i in dict.fromkeys(ids) if i in files]
    failed = [{"id": i, "reason": "없는 화면: %s" % i} for i in ids if i not in files]
    if not gone:
        return {"deleted": [], "cut": [], "failed": failed, "stamp": None, "changed": []}
    w, cut, changed = _Writes(out, stamp), [], set(gone)
    for sid, rel in files.items():                  # 오는 링크 끊기(E10)
        f = out / rel
        if sid in gone or not _inside(out, f) or not f.is_file():
            continue
        src = f.read_text(encoding="utf-8")
        tree, patches = Tree(src), []
        for n in tree.walk():
            to = _link_to(n.attrs)
            if to in gone and to != sid:
                path = _path_of(n)
                patches.append(_relink(src, n, "cut", None, path)); cut.append({"screen": sid, "path": path, "to": to})
        if patches:
            w.keep(f); f.write_text(_patch(src, patches), encoding="utf-8", newline=""); changed.add(sid)
    data["screens"] = [s for s in data["screens"] if s["id"] not in gone]
    for s in data["screens"]:
        br = s.get("branches")
        if br and any(b.get("to") in gone for b in br):
            s["branches"] = [b for b in br if b.get("to") not in gone]; changed.add(s["id"])
    w.keep(sj); _write_json(sj, data, raw)
    for i in gone:
        f = out / files[i]
        if _inside(out, f) and f.is_file():
            w.move(f)
    changed = sorted(changed)
    err = w.commit(changed)
    if err:
        return {"deleted": [], "cut": [], "failed": failed + [{"id": i, "reason": err} for i in gone], "stamp": None, "changed": []}
    return {"deleted": gone, "cut": cut, "failed": failed, "stamp": w.stamp, "changed": changed}


def restore(out, stamp):
    """쓰기 하나 되살리기(2.2 D4) — manifest 의 파일이 쓴 직후 그대로일 때만. 아니면 아무것도 안 바꾸고 reason:'changed-since'."""
    out = pathlib.Path(out).resolve()
    root = out / ".hd-history"
    hist = root / str(stamp or "")
    man = hist / "manifest.json"
    if not stamp or hist.resolve().parent != root.resolve() or not man.is_file():
        return {"error": "없는 기록: %s" % stamp, "reason": "missing"}
    m = json.loads(man.read_text(encoding="utf-8"))
    files = m.get("files") or {}
    for rel, info in files.items():
        f = out / rel
        if not _inside(out, f):
            return {"error": "out 밖 경로: %s" % rel}
        if _sha(f) != info.get("after_sha"):
            return {"error": "그 뒤에 파일이 바뀌어 되돌릴 수 없어요: %s" % rel, "reason": "changed-since", "path": rel}
    now = {rel: (out / rel).read_bytes() if (out / rel).is_file() else None for rel in files}
    for rel, info in files.items():
        f = out / rel
        if info.get("before"):
            f.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(hist / rel, f)
        elif f.exists():
            f.unlink()
    r = _build(out)
    if r.returncode != 0:                           # 다시 빌드가 깨지면 되살리기 전으로
        for rel, b in now.items():
            if b is None:
                (out / rel).unlink(missing_ok=True)
            else:
                (out / rel).write_bytes(b)
        _build(out)
        return {"error": "캔버스 다시 빌드 실패 — 되돌림: " + (r.stderr or "")[-300:]}
    return {"restored": sorted(files), "changed": m.get("changed") or []}


def _paseo_cmd(paseo=None):
    """Paseo CLI 경로 — 넘긴 것(--paseo-cmd·HD_PASEO_CMD, 테스트의 가짜) > 설치 위치(PASEO_DEFAULT) > PATH. 없으면 None."""
    return paseo or (str(PASEO_DEFAULT) if PASEO_DEFAULT.exists() else shutil.which("paseo"))


def _paseo_args(cmd, rest):
    args = [cmd] + rest
    return ["cmd", "/c"] + args if cmd.lower().endswith((".cmd", ".bat")) else args


def forward(out, text, agent=None, paseo=None):
    """결정형이 아닌 메모 → 터미널. 늘 대기열 파일에 쓰고, Paseo 에이전트가 있으면 그 파일을 paseo send 로 넘긴다."""
    q = pathlib.Path(out).resolve() / ".hd-queue"
    q.mkdir(exist_ok=True)
    p = q / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
    p.write_text(text, encoding="utf-8")
    if agent:
        cmd = _paseo_cmd(paseo)
        if cmd:
            args = _paseo_args(cmd, ["send", agent, "--prompt-file", str(p), "--no-wait"])
            try:
                r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=60, creationflags=NO_WINDOW)
                if r.returncode == 0:
                    return {"via": "paseo", "agent": agent, "path": str(p)}
            except (OSError, subprocess.TimeoutExpired):
                pass
    return {"via": "queue", "path": str(p)}


# ---------------------------------------------------------------- 보낼 곳 고르기(#214): Paseo 에이전트 목록 · 프로젝트 저장소
AGENTS_TTL = 5.0                                     # GET /api/agents 답을 이만큼(초) 다시 쓴다 — 메뉴를 열 때마다 paseo 를 띄우지 않게
NO_PASEO = "Paseo 를 찾을 수 없어요"


def list_agents(paseo=None):
    """`paseo ls -g --json`(읽기만) → {agents:[{id, name, status, cwd, provider}]} | {agents:[], error:한국어}.
    보관(archived)된 것은 뺀다. 출력은 바이트로 받아 UTF-8 로 푼다(Windows 기본 코드 페이지로 풀면 한글 이름이 깨진다)."""
    cmd = _paseo_cmd(paseo)
    if not cmd or (("/" in cmd or "\\" in cmd) and not pathlib.Path(cmd).exists()):
        return {"agents": [], "error": NO_PASEO}
    try:
        r = subprocess.run(_paseo_args(cmd, ["ls", "-g", "--json"]), capture_output=True, timeout=30, creationflags=NO_WINDOW,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1"))
    except FileNotFoundError:
        return {"agents": [], "error": NO_PASEO}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요: %s" % e}
    if r.returncode != 0:
        why = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요" + (": " + why[-1][:200] if why else " (종료 코드 %d)" % r.returncode)}
    try:
        rows = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return {"agents": [], "error": "Paseo 목록이 JSON 이 아니에요"}
    if not isinstance(rows, list):
        return {"agents": [], "error": "Paseo 목록이 목록이 아니에요"}
    agents = []
    for a in rows:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"]:
            continue
        if a.get("archived") or a.get("status") == "archived" or a.get("archivedAt"):
            continue
        agents.append({k: (a.get(k) if isinstance(a.get(k), str) else None) for k in ("id", "name", "status", "cwd", "provider")})
    return {"agents": agents}


def project_repo(out):
    """이 캔버스의 저장소 뿌리 — 앱 프로젝트면 app.json 의 repo, 아니면 out 위로 처음 만나는 .git 이 있는 폴더. 없으면 None."""
    out = pathlib.Path(out).resolve()
    try:
        app = json.loads((out / "app.json").read_text(encoding="utf-8"))
        if isinstance(app, dict) and isinstance(app.get("repo"), str) and app["repo"]:
            return str(pathlib.Path(app["repo"]))
    except (OSError, ValueError):
        pass                                          # app.json 이 없거나 깨짐 = 정적 프로젝트로 본다
    for d in [out] + list(out.parents):
        if (d / ".git").exists():
            return str(d)
    return None


def agents_get(srv, paseo, now=None, auto=False):
    """GET /api/agents[?auto=1] → {agents, current, repo, error?}. paseo 목록은 AGENTS_TTL 동안 다시 쓴다(current 는 늘 지금 값).
    auto = 캔버스가 열 때 자동으로 고를지 묻는 것 — 이미 붙어 있거나 저장소를 모르면 paseo 를 띄우지 않고 {agents:[], skipped:true}."""
    if auto and (srv.agent or not srv.repo):
        return {"agents": [], "current": srv.agent, "repo": srv.repo, "skipped": True}
    t = time.monotonic() if now is None else now
    with srv.agents_lock:
        hit = srv.agents_cache
        if hit is None or t - hit[0] >= AGENTS_TTL:
            hit = srv.agents_cache = (t, list_agents(paseo))
    return dict(hit[1], current=srv.agent, repo=srv.repo)


def watch(out, files):
    """화면 파일 바뀐 시각 보기(Q2b) — files = out 기준 상대 경로 목록 → {mtimes:{경로: st_mtime | None}}. 없거나 out 밖이면 None."""
    out = pathlib.Path(out).resolve()
    mtimes = {}
    if not isinstance(files, list):
        return {"mtimes": mtimes}
    for f in files:
        if not isinstance(f, str):
            continue
        try:
            p = out / f
            mtimes[f] = p.stat().st_mtime if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            mtimes[f] = None
    return {"mtimes": mtimes}


# ---------------------------------------------------------------- 프로젝트 상태 파일(#228): <out>/.hd-canvas.json 이 캔버스 프로젝트별 키의 진실 원천
STATE_FILE = ".hd-canvas.json"
STATE_MAX = 2 * 1024 * 1024                          # PUT 본문 한도(넘으면 413)


def _state_ok(doc):
    return isinstance(doc, dict) and type(doc.get("rev")) is int and doc["rev"] >= 0 and isinstance(doc.get("state"), dict)


def state_load(out):
    """상태 파일 → {rev, state}. 없으면 {rev:0, state:{}}. 깨졌으면 .hd-canvas.json.corrupt-<시각> 으로 옮기고 한 줄 남긴 뒤 빈 상태(도우미는 멈추지 않는다)."""
    p = pathlib.Path(out) / STATE_FILE
    if not p.is_file():
        return {"rev": 0, "state": {}}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = None
    if _state_ok(doc):
        return {"rev": doc["rev"], "state": doc["state"]}
    bad = p.with_name(STATE_FILE + ".corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    try:
        os.replace(p, bad)
        print("[hd] 깨진 상태 파일을 옮기고 빈 상태로 시작해요: " + bad.name, file=sys.stderr, flush=True)
    except OSError as e:
        print("[hd] 깨진 상태 파일을 옮기지 못했어요(빈 상태로 시작): %s" % e, file=sys.stderr, flush=True)
    return {"rev": 0, "state": {}}


def _state_write(out, doc):                          # 같은 폴더 임시 파일 → os.replace(원자적), 바로 앞 것 하나는 .bak
    p = pathlib.Path(out) / STATE_FILE
    tmp = p.with_name(STATE_FILE + ".tmp-%d" % os.getpid())
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    if p.is_file():
        shutil.copy2(p, p.with_name(STATE_FILE + ".bak"))
    for i in range(REPLACE_TRIES):                   # 읽기는 자물쇠 없이 한다(#271) — Windows 는 읽는 중인 파일을 바꾸지 못해 잠깐 기다렸다 다시
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(0.02)


REPLACE_TRIES = 25                                   # 0.02초씩 — 읽기 하나는 수 ms


def state_peek(out):
    """자물쇠 없는 읽기(GET /api/state · index.html 스냅숏, #271) → {rev, state} | None(못 읽음·깨짐 — 그때만 자물쇠 안에서 state_load).
    쓰기는 임시 파일 + os.replace 라 반쯤 쓴 파일을 읽을 일은 없다. 깨진 파일을 옮기는 일(쓰기)은 하지 않는다."""
    p = pathlib.Path(out) / STATE_FILE
    for _ in range(REPLACE_TRIES):
        if not p.is_file():
            return {"rev": 0, "state": {}}
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except PermissionError:                       # Windows: 바로 그 순간 os.replace 중
            time.sleep(0.02); continue
        except (OSError, ValueError):
            return None
        return {"rev": doc["rev"], "state": doc["state"]} if _state_ok(doc) else None
    return None


def state_put(out, body):
    """PUT 본문 {rev, state:{이름: 값 | null(지움)}} → (code, 답). rev 가 파일과 같을 때만 합쳐 rev+1 로 쓴다 · 다르면 409 {rev, state}."""
    if not isinstance(body, dict) or type(body.get("rev")) is not int or not isinstance(body.get("state"), dict):
        return 400, {"error": "{rev: 정수, state: {}} 가 아니에요"}
    cur = state_load(out)
    if body["rev"] != cur["rev"]:
        return 409, cur
    state = dict(cur["state"])
    for k, v in body["state"].items():
        if v is None:
            state.pop(k, None)
        else:
            state[k] = v
    return 200, {"rev": _state_save(out, cur["rev"] + 1, state)}


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _state_save(out, rev, state):
    _state_write(out, {"version": 1, "rev": rev, "updated": _now(), "state": state})
    return rev


def reply_post(out, body):
    """POST /api/reply 본문 {note: id | {screen, no}, reply} → (code, 답). 최신 상태 파일의 그 메모 replies 에 붙이고 rev+1."""
    if not isinstance(body, dict) or not isinstance(body.get("reply"), dict):
        return 400, {"error": "{note, reply: {kind, …}} 가 아니에요", "errors": ["reply: 객체가 아니에요"]}
    ref = body.get("note")
    if isinstance(ref, dict):
        if not isinstance(ref.get("screen"), str) or type(ref.get("no")) is not int:
            return 400, {"error": "note: {screen: 글, no: 정수} 또는 메모 id", "errors": ["note: {screen, no} 모양이 아니에요"]}
    elif not isinstance(ref, str) or not ref:
        return 400, {"error": "note: 메모 id 또는 {screen, no}", "errors": ["note: 없어요"]}
    cur = state_load(out)
    notes = cur["state"].get("notes")
    notes = notes if isinstance(notes, list) else []
    i = hd_model.find(notes, ref, cur["state"].get("note-seq"))
    if i is None:
        return 404, {"error": "없는 메모: %s" % (ref if isinstance(ref, str) else "%s#%s" % (ref["screen"], ref["no"]))}
    note = notes[i]
    if not note.get("sent"):
        return 400, {"error": "note: 아직 보내지 않은 메모(draft)에는 답하지 않아요", "errors": ["note: 보내지 않은 메모"]}
    try:
        known = {s["id"] for s in json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("screens", [])}
    except (OSError, ValueError, KeyError, TypeError):
        known = None                                  # screens.json 을 못 읽으면 화면 id 는 모양만 본다
    errs = hd_model.check_reply(body["reply"], note.get("intent"), agent=True, known_screens=known)
    if errs:
        return 400, {"error": "; ".join(errs), "errors": errs}
    note = dict(note, replies=hd_model.replies(note) + [hd_model.stamp(body["reply"], _now())])
    notes = notes[:i] + [note] + notes[i + 1:]
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], notes=notes))
    return 200, {"rev": rev, "status": hd_model.status(note), "note": note.get("id"), "screen": note.get("screen")}


def state_inject(out, lock=None):                    # 페이지에 끼워 넣을 동기 스냅숏(window.__hdState) — </script> 가 끊지 않게 < 를 이스케이프
    snap = state_peek(out)                           # 자물쇠 없이(#271) — 깨졌을 때만 자물쇠 안에서 state_load(옮기기)
    if snap is None:
        with lock or threading.Lock():
            snap = state_load(out)
    return "<script>window.__hdState=%s;</script>" % json.dumps(snap, ensure_ascii=False).replace("<", "\\u003c")


def claim_post(out, body, now_ms=None):
    """POST /api/claim 본문 {screen, by?, note?} → (code, 답). 최신 상태 파일 state.busy 에 cli 덮개를 넣고 rev+1."""
    if not isinstance(body, dict):
        return 400, {"error": "{screen, by?, note?} 가 아니에요"}
    sid, by, note = body.get("screen"), body.get("by"), body.get("note")
    err = hd_model.claim_error(sid, by, note)
    if err:
        return 400, {"error": err}
    try:
        files = _screen_files(json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 500, {"error": "screens.json 을 읽지 못했어요: %s" % e}
    if sid not in files:
        return 404, {"error": "없는 화면: %s" % sid}
    f = pathlib.Path(out).resolve() / files[sid]
    mtime = f.stat().st_mtime if _inside(pathlib.Path(out).resolve(), f) and f.is_file() else None
    cur = state_load(out)
    busy, warns = hd_model.claim(cur["state"].get("busy"), sid, files[sid], int(now_ms if now_ms is not None else datetime.datetime.now().timestamp() * 1000),
                                 mtime, by, note)
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy))
    return 200, {"rev": rev, "screen": sid, "file": files[sid]}


def release_post(out, body):
    """POST /api/release 본문 {screen} → (code, 답). 덮개가 있으면 걷고 rev+1, 없으면 released false(쓰지 않음)."""
    if not isinstance(body, dict) or not isinstance(body.get("screen"), str) or not body["screen"]:
        return 400, {"error": "screen: 화면 id 가 없어요"}
    cur = state_load(out)
    busy, gone, warns = hd_model.release(cur["state"].get("busy"), body["screen"])
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    if not gone:
        return 200, {"rev": cur["rev"], "released": False}
    return 200, {"rev": _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy)), "released": True}


# ---------------------------------------------------------------- 화면 파일 지켜보기(#254): 1초마다 mtime → 바뀐 화면마다 seq
WATCH_EVERY = 1.0


class FileWatch:
    """화면 → mtime 을 받아 바뀐 화면을 seq 로 적는다. tick 은 I/O 가 없다(unit 테스트) — 파일을 보는 일은 scan()."""
    def __init__(self):
        self.seq, self.last, self.at = 0, None, {}       # at: 화면 → 마지막으로 바뀐 seq
        self._lock = threading.Lock()

    def tick(self, mtimes):
        """mtimes = {화면: mtime|None} → 이번에 바뀐 화면 목록(처음 = 기준만, []). 생김·없어짐·시각 바뀜 = 바뀜."""
        with self._lock:
            prev, self.last = self.last, dict(mtimes)
            if prev is None:
                return []
            changed = sorted(k for k in set(prev) | set(mtimes) if prev.get(k) != mtimes.get(k) and k in mtimes)
            if changed:
                self.seq += 1
                for k in changed:
                    self.at[k] = self.seq
            return changed

    def absorb(self, mtimes):
        """도우미가 스스로 쓴 뒤(apply·delete·restore) — 지금 시각을 기준으로만 삼고 알리지 않는다(캔버스가 이미 그 카드를 다시 싣는다)."""
        with self._lock:
            self.last = dict(mtimes)

    def changes(self, since):
        """since 보다 뒤에 바뀐 화면 → {seq, changed}. since < 0 = 기준만."""
        with self._lock:
            if since is None or since < 0:
                return {"seq": self.seq, "changed": []}
            return {"seq": self.seq, "changed": sorted(k for k, s in self.at.items() if s > since)}


def scan(out, cache):
    """screens.json 에 적힌 화면 파일(out 안만) → {화면: mtime|None} | None(screens.json 을 못 읽음 — [hd] 한 줄). cache = {'sj': (mtime, files)} — screens.json 이 바뀔 때만 다시 읽는다."""
    out = pathlib.Path(out)
    sj = out / "screens.json"
    try:
        m = sj.stat().st_mtime
        if cache.get("sj", (None,))[0] != m:
            cache["sj"] = (m, _screen_files(json.loads(sj.read_text(encoding="utf-8"))))
    except (OSError, ValueError, KeyError, TypeError) as e:
        if not cache.get("warned"):
            print("[hd] 화면 지켜보기: screens.json 을 읽지 못했어요(%s)" % e, file=sys.stderr, flush=True)
            cache["warned"] = True
        return None                                   # 이번 차례는 건너뜀(쓰는 중인 screens.json 이 모든 카드를 '바뀜'으로 만들지 않게)
    cache["warned"] = False
    res = {}
    for sid, rel in cache["sj"][1].items():
        p = out / rel
        try:
            res[sid] = p.stat().st_mtime if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            res[sid] = None
    return res


def _watch_loop(srv, out, lock):
    cache = {}
    while not srv.watch_stop.wait(WATCH_EVERY if srv.watch.last is not None else 0):
        with lock:                                   # 도우미가 쓰는 중(apply 의 쓰기~빌드)에는 보지 않는다 — 다 쓴 뒤 absorb 가 기준을 옮긴다
            m = scan(out, cache)
            if m is not None:
                srv.watch.tick(m)


# ---------------------------------------------------------------- 서버
def keypath(out):                                    # file:// 로 열었을 때의 location.pathname — 캔버스 저장 키를 같게
    return urllib.parse.urlparse((pathlib.Path(out).resolve() / "index.html").as_uri()).path


def make_server(out, port=0, agent=None, paseo=None, token=None):
    out = pathlib.Path(out).resolve()
    token = token or secrets.token_urlsafe(18)
    lock = threading.Lock()
    head = '<script>window.__hdHelper=%s;window.__hdKeyPath=%s;window.__hdOut=%s;' % (json.dumps(True), json.dumps(keypath(out)),
                                                                                     json.dumps(out.as_posix()))

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(out), **k)

        def log_message(self, *a):
            pass

        def _host_ok(self):
            port_ = self.server.server_address[1]
            return (self.headers.get("Host") or "") in ("127.0.0.1:%d" % port_, "localhost:%d" % port_)

        def _json(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            if not self._host_ok():
                return self.send_error(403)
            u = urllib.parse.urlparse(self.path)
            if u.path in ("/api/state", "/api/projects", "/api/files", "/api/agents"):
                if self.headers.get("X-HD-Token") != token:
                    return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
                if u.path == "/api/files":
                    q = urllib.parse.parse_qs(u.query).get("since", ["-1"])[0]
                    try:
                        since = int(q)
                    except ValueError:
                        return self._json(400, {"error": "since: 정수가 아니에요"})
                    return self._json(200, self.server.watch.changes(since))
                if u.path == "/api/projects":
                    return self._json(200, hd_client.project_rows())
                if u.path == "/api/agents":
                    auto = urllib.parse.parse_qs(u.query).get("auto", [""])[0] == "1"
                    return self._json(200, agents_get(self.server, paseo, auto=auto))
                snap = state_peek(out)                  # 빌드 자물쇠를 기다리지 않는다(#271 — 긴 빌드 중에도 hd 핑이 1초 안에 답)
                if snap is None:
                    with lock:                          # 깨졌을 때만: 옮기는 쓰기가 들어 있어 자물쇠 안에서
                        snap = state_load(out)
                return self._json(200, snap)
            parts = [p for p in u.path.split("/") if p]
            if any(p.startswith(".") for p in parts):      # 원본 기록·대기열·상태 파일은 내주지 않는다
                return self.send_error(404)
            if u.path in ("/", "/index.html"):
                snap = state_inject(out, lock)
                inject = head + "window.__hdAgent=%s;</script>" % json.dumps(self.server.agent)   # attach 로 바뀔 수 있어 줄 때마다
                b = (out / "index.html").read_text(encoding="utf-8").replace("<head>", "<head>" + inject + snap, 1).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
                return
            return super().do_GET()

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_POST(self):
            try:                                            # 본문은 거절하기 전에도 먼저 다 읽는다 — 안 읽은 채 닫으면 Windows 가 RST 로 끊어
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))   # 상대가 403 대신 ConnectionAbortedError 를 받는다
            except ValueError:
                raw = b""
            if not self._host_ok() or self.headers.get("X-HD-Token") != token:
                return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return self._json(400, {"error": "JSON 이 아니에요"})
            if self.path == "/api/data":
                return self._json(200, build_canvas.index_data(out, json.loads((out / "screens.json").read_text(encoding="utf-8"))))
            if self.path in ("/api/apply", "/api/delete", "/api/restore"):
                with lock:                                  # 쓰기는 한 번에 하나
                    try:
                        if self.path == "/api/apply":
                            return self._json(200, apply_edits(out, body.get("edits") or []))
                        if self.path == "/api/delete":
                            return self._json(200, delete_screens(out, [str(i) for i in body.get("screens") or []]))
                        r = restore(out, str(body.get("stamp") or ""))
                    finally:
                        m = scan(out, {})                   # 스스로 쓴 화면 파일은 '바뀜'으로 알리지 않는다(캔버스가 그 카드를 이미 다시 싣는다)
                        if m is not None:
                            self.server.watch.absorb(m)
                    code = {"changed-since": 409, "missing": 404}.get(r.get("reason"), 500 if "error" in r else 200)
                    return self._json(code, r)
            if self.path in ("/api/reply", "/api/claim", "/api/release"):
                with lock:                                  # 상태 파일 쓰기는 /api/state 와 같은 자물쇠
                    code, res = {"/api/reply": reply_post, "/api/claim": claim_post, "/api/release": release_post}[self.path](out, body)
                return self._json(code, res)
            if self.path == "/api/forward":
                return self._json(200, forward(out, str(body.get("text") or ""), self.server.agent, paseo))
            if self.path == "/api/stop":
                self._json(200, {"stopping": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()   # serve_forever 를 돌리는 쪽이 정리(표지 지움)
                return None
            if self.path == "/api/attach":
                code, res = attach_post(self.server, body, lock)
                return self._json(code, res)
            if self.path == "/api/open":
                code, res = open_post(body, self.server.agent)
                return self._json(code, res)
            if self.path == "/api/watch":
                return self._json(200, watch(out, body.get("files") if isinstance(body, dict) else None))
            return self._json(404, {"error": "모르는 주소"})

        def do_PUT(self):                               # /api/state 만 — 한도를 넘어도 본문은 다 읽고 답한다(위 do_POST 와 같은 이유)
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n > STATE_MAX:
                while n > 0:
                    chunk = self.rfile.read(min(n, 65536))
                    if not chunk:
                        break
                    n -= len(chunk)
                return self._json(413, {"error": "상태가 너무 커요(2 MB 넘음)"})
            raw = self.rfile.read(n)
            if not self._host_ok() or self.headers.get("X-HD-Token") != token:
                return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
            if self.path != "/api/state":
                return self._json(404, {"error": "모르는 주소"})
            try:
                body = json.loads(raw or b"null")
            except ValueError:
                return self._json(400, {"error": "JSON 이 아니에요"})
            with lock:                                  # 쓰기는 한 번에 하나(rev 비교와 쓰기 사이에 끼어들지 않게)
                code, res = state_put(out, body)
            return self._json(code, res)

    state_load(out)                                     # 시작할 때 깨진 상태 파일을 옮겨 둔다(멈추지 않음)
    srv = bind(H, [port] if isinstance(port, int) else list(port))
    srv.watch, srv.watch_stop = FileWatch(), threading.Event()
    threading.Thread(target=_watch_loop, args=(srv, out, lock), daemon=True).start()   # server_close 가 멈춘다
    srv.token = token
    srv.agent = agent or None                           # /api/forward 가 보낼 곳 — /api/attach 로 바뀐다
    srv.marker = None                                   # main 이 표지 경로를 넣는다(attach 가 agent 를 고쳐 씀)
    srv.agents_cache, srv.agents_lock = None, threading.Lock()   # GET /api/agents 5초 캐시
    srv.repo = project_repo(out)
    srv.url = "http://127.0.0.1:%d/index.html?hd=%s" % (srv.server_address[1], token)
    return srv


def port_order(recorded, asked=0):
    """띄울 포트 차례(#270) — asked(--port, 0 아님) = 그것만 · 아니면 지난번 포트(.hd-helper.json) 먼저, 막혔으면 0(아무 빈 포트).
    포트가 같아야 캔버스 주소(origin)가 같아 localStorage 키(도크·테마·설정·보낸 것 보기·안 보낸 표시)가 이어진다."""
    if type(asked) is int and asked > 0:
        return [asked]
    if type(recorded) is int and 0 < recorded < 65536:
        return [recorded, 0]
    return [0]


def bind(handler, ports):
    """ports 차례로 127.0.0.1 에 열어 본다 → Server. 앞 것이 막히면 [hd] 한 줄 남기고 다음, 마지막도 막히면 그 OSError."""
    for i, port in enumerate(ports):
        try:
            return Server(("127.0.0.1", port), handler)
        except OSError as e:
            if i == len(ports) - 1:
                raise
            print("[hd] 지난번 포트 %d 를 쓸 수 없어 새 포트로 띄워요(%s) — 캔버스 주소가 바뀌어 창 설정이 처음으로 돌아가요" % (port, e),
                  file=sys.stderr, flush=True)


class Server(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"     # Windows 의 SO_REUSEADDR 는 쓰는 중인 포트도 다시 연다 — 지난 포트가 막혔는지 알아야 한다(#270)

    def server_close(self):
        if hasattr(self, "watch_stop"):                # 열기에 실패하면 socketserver 가 make_server 가 칸을 달기 전에 부른다
            self.watch_stop.set()
        super().server_close()


def attach_post(srv, body, lock):
    """POST /api/attach 본문 {agent: id|null} → (code, 답). 받은 agent 를 서버에 두고 표지의 agent 를 고쳐 쓴다."""
    if not isinstance(body, dict) or "agent" not in body:
        return 400, {"error": "agent: 없어요({agent: id 또는 null})"}
    err = hd_model.agent_error(body["agent"])
    if err:
        return 400, {"error": err}
    with lock:
        srv.agent = body["agent"]
        if srv.marker is not None:
            marker_agent(srv.marker, srv.agent)
    print("[hd] 보내기 → %s" % (srv.agent or "대기열 파일"), file=sys.stderr, flush=True)
    return 200, {"agent": srv.agent}


def open_post(body, agent=None):
    """POST /api/open 본문 {name, agent?} → (code, 답). hd open 과 같은 hd_client.open_project(브라우저 없음)."""
    if not isinstance(body, dict) or not isinstance(body.get("name"), str) or not body["name"].strip():
        return 400, {"error": "name: 프로젝트 이름 또는 out 경로가 없어요"}
    a = body.get("agent", agent)
    if hd_model.agent_error(a):
        return 400, {"error": hd_model.agent_error(a)}
    try:
        e, m, reused = hd_client.open_project(body["name"], a)
    except hd_client.NotFound as x:
        return 404, {"error": str(x)}
    except hd_client.HdError as x:
        return 500, {"error": str(x)}
    return 200, {"name": e["name"], "out": e["out"], "url": m["url"], "pid": m.get("pid"), "agent": m.get("agent"), "reused": reused}


def marker_agent(path, agent):
    """표지의 agent 칸만 고쳐 쓴다(임시 파일 + os.replace)."""
    p = pathlib.Path(path)
    d = json.loads(p.read_text(encoding="utf-8"))
    d["agent"] = agent or None
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def hd_home():
    return pathlib.Path(os.environ.get("HD_HOME") or pathlib.Path.home() / ".hyper-design")


def write_marker(out, srv, agent=None):
    """떠 있는 표지 ~/.hyper-design/active/<pid>.json 을 쓰고 그 경로를 돌려준다(`hd ls`·`hd notes`·`hd reply` 가 읽는다)."""
    out = pathlib.Path(out).resolve()
    d = hd_home() / "active"
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("%d.json" % os.getpid())
    p.write_text(json.dumps({"pid": os.getpid(), "project": hd_model.project_name(out.name, out.parent.name), "out": str(out),
                             "url": srv.url, "token": srv.token, "port": srv.server_address[1], "agent": agent or None,
                             "started": _now()}, ensure_ascii=False), encoding="utf-8")
    return p


RUN_FILE = ".hd-helper.json"                         # 주인 = 이 파일. 읽는 쪽: hd_client.read_record · skills go/fix


def start_check(out):
    """시작 전(#271) → (지난 포트 | None, 살아 있는 도우미 표지 | None). 표지가 있으면 같은 out 의 둘째 도우미가 되므로 띄우지 않는다."""
    rec = hd_client.read_record(out)                 # 없음·깨짐 = None(깨졌으면 [hd] 한 줄, 덮어쓴다)
    return (rec or {}).get("port"), hd_client.live_record(out, rec) if rec else None


def write_run(run, srv):
    run.write_text(json.dumps({"url": srv.url, "pid": os.getpid(), "port": srv.server_address[1], "token": srv.token}), encoding="utf-8")


def leave_run(run, port):
    """정상 종료 — 이 도우미가 쓴 기록일 때만 {port} 로 줄여 둔다(주소·pid 는 지움 → 스킬은 다시 띄우고, 다음 도우미는 같은 포트로)."""
    try:
        cur = hd_model.helper_record(json.loads(run.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        cur = None
    if cur and cur.get("pid") not in (None, os.getpid()):
        return                                        # 다른 도우미가 덮어썼다 — 그 기록은 그대로
    try:
        run.write_text(json.dumps({"port": port}), encoding="utf-8")
    except OSError as e:
        print("[hd] 도우미 기록을 고치지 못했어요(%s): %s" % (e, run), file=sys.stderr, flush=True)


def _stop(signum, frame):                              # SIGTERM·SIGBREAK → Ctrl+C 와 같은 정상 종료(finally·atexit 가 표지를 지운다)
    raise KeyboardInterrupt


def main(argv=None):
    ap = argparse.ArgumentParser(description="hyper-design 캔버스 로컬 도우미")
    ap.add_argument("out")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--paseo-agent", default=os.environ.get("HD_PASEO_AGENT"))
    ap.add_argument("--paseo-cmd", default=os.environ.get("HD_PASEO_CMD"))
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out).resolve()
    if not (out / "index.html").is_file() or not (out / "screens.json").is_file():
        sys.exit("index.html · screens.json 이 있는 out 폴더가 아니에요: %s" % out)
    last, live = start_check(out)
    if live:
        sys.exit("이 out 은 이미 도우미가 떠 있어요(pid %s): %s — 그 주소를 쓰거나 `hd stop` 으로 끈 뒤 다시 띄우세요" % (live["pid"], live["url"]))
    srv = make_server(out, port_order(last, a.port), a.paseo_agent, a.paseo_cmd)
    marker = write_marker(out, srv, a.paseo_agent)
    srv.marker = marker
    atexit.register(lambda: marker.unlink(missing_ok=True))
    try:
        hd_client.register(out)                     # 목록에 없을 때만 씀(링크 하나, 복사 없음)
    except (OSError, ValueError) as e:
        print("[hd] 프로젝트 목록에 넣지 못했어요(%s) — 캔버스는 그대로 떠요" % e, file=sys.stderr, flush=True)
    for name in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    run = out / RUN_FILE                             # 스킬이 이미 떠 있는지 보는 표지(그 url 이 응답하면 다시 띄우지 않는다) · 다음 시작의 포트
    write_run(run, srv)                              # 주소를 찍기 전에(찍힌 주소를 본 쪽이 이 파일도 보게)
    print(srv.url, flush=True)
    print("터미널 전달: " + ("Paseo 에이전트 " + a.paseo_agent if a.paseo_agent else "대기열 파일 " + str(out / ".hd-queue")), flush=True)
    if not a.no_open:
        threading.Timer(0.3, lambda: webbrowser.open(srv.url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        leave_run(run, srv.server_address[1])
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
