"""로컬 도우미 — 캔버스 편집을 화면 파일에 바로 쓴다 (docs/eungshin/canvas-edit-plan-2026-10-19.md 7단계, 결정 8B).

python3 helper.py <out> [--port 0] [--paseo-agent ID] [--no-open]

- 127.0.0.1 에만 열고, 실행마다 새 토큰을 만든다. 출력한 주소(…/index.html?hd=<토큰>)로 캔버스를 열면 '보내기'가 도우미를 쓴다.
- 쓰는 곳은 <out> 안뿐이다. 쓰기 전에 원본을 <out>/.hd-history/<시각>/ 에 남기고, 쓴 뒤 build_canvas.py 로 캔버스를 다시 만든다(실패하면 원본으로 되돌림).
- 바로 쓰는 편집(결정형): 글자(text) · 카드 이름(title) · 설명(purpose) · 정책 줄(policy, index) · 잇기/도착 바꾸기(link) · 끊기/트리거 해제(cut).
  나머지 메모(질문, 새 화면, 도착 없는 트리거 지정 등)는 요청문 그대로 <out>/.hd-queue/<시각>.txt 대기열 파일에 쓰고,
  --paseo-agent 가 있으면 그 파일을 `paseo send <agent> --prompt-file … --no-wait` 로 그 에이전트 터미널에 넣는다
  (없으면 터미널에서 /hyper-design:fix 에 그 내용을 붙여 넣는다).
- 도우미가 꺼져 있으면 캔버스는 지금처럼 요청문을 복사한다.

- 쓰기마다 <out>/.hd-history/<stamp>/manifest.json = {files:{relpath:{before, after_sha}}, changed} — 되살리기는 그 뒤 파일이 안 바뀌었을 때만.

API (모두 POST, JSON, 머리글 X-HD-Token 필수 · Host 는 127.0.0.1/localhost 의 그 포트만)
  /api/apply   {edits:[{id, screen, edit, path, value?, to?}]} → {applied:[id], failed:[{id, reason}], stamp, changed:[screen]}
  /api/delete  {screens:[id]}                                 → {deleted:[id], cut:[{screen, path, to}], failed, stamp, changed:[screen]}
  /api/restore {stamp}                                        → {restored:[relpath], changed:[screen]} | 409 {error, reason:'changed-since'}
  /api/data    {}                                             → build_canvas.index_data (index.html 의 hd-data 와 같은 객체)
  /api/forward {text}                                         → {via:'paseo'|'queue', agent?, path?}
"""
import argparse, datetime, hashlib, html, json, os, pathlib, re, secrets, shutil, subprocess, sys, threading, urllib.parse, webbrowser
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import build_canvas

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE / "build_canvas.py"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
PASEO_DEFAULT = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Paseo" / "resources" / "bin" / "paseo.cmd"


# ---------------------------------------------------------------- HTML: 원문 위치를 아는 작은 트리
class Node:
    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag, self.attrs, self.start, self.open_end, self.parent = tag, dict(attrs), start, open_end, parent
        self.children, self.texts = [], []          # texts: (원문 위치, 길이, 글) — 이 요소 바로 아래 글
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

    def handle_startendtag(self, tag, attrs):
        pos = self._pos(); raw = self.get_starttag_text() or ""
        n = Node(tag, attrs, pos, pos + len(raw), self.stack[-1])
        self.stack[-1].children.append(n); self.stack[-1].order.append(("el", n))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
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


def _first_text(n):
    for kind, x in n.order:
        if kind == "tx" and x[2].strip():
            return x
        if kind == "el" and x.tag not in ("script", "style"):
            t = _first_text(x)
            if t:
                return t
    return None


def _set_attr(tag_src, name, value):                # 시작 태그 원문에서 속성 하나 바꾸기(없으면 더하기 · None 이면 지우기)
    rx = re.compile(r'(\s' + re.escape(name) + r')(\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?', re.I)
    if value is None:
        return rx.sub("", tag_src, count=1)
    new = ' %s="%s"' % (name, html.escape(value, quote=True))
    if rx.search(tag_src):
        return rx.sub(lambda m: new, tag_src, count=1)
    end = len(tag_src) - (2 if tag_src.endswith("/>") else 1)
    return tag_src[:end].rstrip() + new + tag_src[end:]


def edit_html(src, edits):
    """edits = [(path, op, value)] — op: text | link(value=도착 id) | cut. 원문 위치 기준으로 뒤에서부터 바꾼다."""
    tree, patches = Tree(src), []
    for path, op, value in edits:
        el = select(tree, path)
        if op == "text":
            t = _first_text(el)
            if not t:
                raise ValueError("글자가 없는 요소: " + path)
            pos, ln, data = t
            lead, trail = data[: len(data) - len(data.lstrip())], data[len(data.rstrip()):]
            patches.append((pos, pos + ln, lead + html.escape(value, quote=False).replace("\n", "<br>") + trail))
        elif op in ("link", "cut"):
            patches.append(_relink(src, el, op, value, path))
        else:
            raise ValueError("모르는 편집: " + op)
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
    """요소 속성 → 가는 화면 id | None — build_canvas._Links · screen_links 와 같은 규칙(href · data-href · onclick 안 .html)."""
    h = attrs.get("href") or attrs.get("data-href")
    if not h and attrs.get("onclick"):
        m = build_canvas.GO_ONCLICK.search(attrs["onclick"]); h = m and m.group(1)
    if not h or re.match(r"^(#|javascript:|mailto:|tel:)", h, re.I) or "://" in h or h.startswith("/"):
        return None
    h = h.split("#")[0].split("?")[0]
    if "/" in h.lstrip("./") or not re.search(r"\.html?$", h, re.I):
        return None
    return re.sub(r"\.html?$", "", h.lstrip("./"), flags=re.I) or None


# ---------------------------------------------------------------- 편집 적용(out 안만 · 원본 남김 · 다시 빌드)
def _inside(out, p):
    p = p.resolve()
    return p == out or out in p.parents


def _sha(p):                                         # 파일 sha256 | None(없음)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _build(out):
    return subprocess.run([sys.executable, str(BUILD), str(out)], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


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
            if kind in ("title", "purpose", "policy"):
                if kind == "policy" and not isinstance(e.get("index"), int):
                    raise ValueError("정책 줄 번호가 없어요")
                json_ops.append((eid, sid, kind if kind != "policy" else ("policy", e["index"]), str(e.get("value", ""))))
                continue
            if kind == "text":
                op = ("text", str(e.get("value", "")))
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
        for o in ops:
            try:
                edit_html(src, [(o[1], o[2], o[3])]); good.append(o)
            except ValueError as err:
                failed.append({"id": o[0], "reason": str(err)})
        if good:
            new = edit_html(src, [(o[1], o[2], o[3]) for o in good])
            w.keep(f); f.write_text(new, encoding="utf-8", newline="")
            applied += [o[0] for o in good]; changed.add(owner[f])
    if json_ops:
        by = {s["id"]: s for s in data["screens"]}
        for eid, sid, kind, v in json_ops:
            if isinstance(kind, tuple):                 # 정책 줄 i
                pol = by[sid].setdefault("policies", [])
                if not 0 <= kind[1] < len(pol):
                    failed.append({"id": eid, "reason": "없는 정책 줄: %d" % kind[1]}); continue
                pol[kind[1]] = v
            else:
                by[sid][kind] = v
            applied.append(eid); changed.add(sid)
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


def forward(out, text, agent=None, paseo=None):
    """결정형이 아닌 메모 → 터미널. 늘 대기열 파일에 쓰고, Paseo 에이전트가 있으면 그 파일을 paseo send 로 넘긴다."""
    q = pathlib.Path(out).resolve() / ".hd-queue"
    q.mkdir(exist_ok=True)
    p = q / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
    p.write_text(text, encoding="utf-8")
    if agent:
        cmd = paseo or (str(PASEO_DEFAULT) if PASEO_DEFAULT.exists() else shutil.which("paseo"))
        if cmd:
            args = [cmd, "send", agent, "--prompt-file", str(p), "--no-wait"]
            if cmd.lower().endswith((".cmd", ".bat")):
                args = ["cmd", "/c"] + args
            try:
                r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=60)
                if r.returncode == 0:
                    return {"via": "paseo", "agent": agent, "path": str(p)}
            except (OSError, subprocess.TimeoutExpired):
                pass
    return {"via": "queue", "path": str(p)}


# ---------------------------------------------------------------- 서버
def keypath(out):                                    # file:// 로 열었을 때의 location.pathname — 캔버스 저장 키를 같게
    return urllib.parse.urlparse((pathlib.Path(out).resolve() / "index.html").as_uri()).path


def make_server(out, port=0, agent=None, paseo=None, token=None):
    out = pathlib.Path(out).resolve()
    token = token or secrets.token_urlsafe(18)
    lock = threading.Lock()
    inject = ('<script>window.__hdHelper=%s;window.__hdKeyPath=%s;window.__hdOut=%s;</script>'
              % (json.dumps(True), json.dumps(keypath(out)), json.dumps(out.as_posix())))

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
            parts = [p for p in u.path.split("/") if p]
            if any(p.startswith(".") for p in parts):      # 원본 기록·대기열은 내주지 않는다
                return self.send_error(404)
            if u.path in ("/", "/index.html"):
                b = (out / "index.html").read_text(encoding="utf-8").replace("<head>", "<head>" + inject, 1).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
                return
            return super().do_GET()

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_POST(self):
            if not self._host_ok() or self.headers.get("X-HD-Token") != token:
                return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except ValueError:
                return self._json(400, {"error": "JSON 이 아니에요"})
            if self.path == "/api/data":
                return self._json(200, build_canvas.index_data(out, json.loads((out / "screens.json").read_text(encoding="utf-8"))))
            if self.path in ("/api/apply", "/api/delete", "/api/restore"):
                with lock:                                  # 쓰기는 한 번에 하나
                    if self.path == "/api/apply":
                        return self._json(200, apply_edits(out, body.get("edits") or []))
                    if self.path == "/api/delete":
                        return self._json(200, delete_screens(out, [str(i) for i in body.get("screens") or []]))
                    r = restore(out, str(body.get("stamp") or ""))
                    code = {"changed-since": 409, "missing": 404}.get(r.get("reason"), 500 if "error" in r else 200)
                    return self._json(code, r)
            if self.path == "/api/forward":
                return self._json(200, forward(out, str(body.get("text") or ""), agent, paseo))
            return self._json(404, {"error": "모르는 주소"})

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.token = token
    srv.url = "http://127.0.0.1:%d/index.html?hd=%s" % (srv.server_address[1], token)
    return srv


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
    srv = make_server(out, a.port, a.paseo_agent, a.paseo_cmd)
    print(srv.url, flush=True)
    run = out / ".hd-helper.json"                    # 스킬이 이미 떠 있는지 보는 표지(그 url 이 응답하면 다시 띄우지 않는다)
    run.write_text(json.dumps({"url": srv.url, "pid": os.getpid()}), encoding="utf-8")
    print("터미널 전달: " + ("Paseo 에이전트 " + a.paseo_agent if a.paseo_agent else "대기열 파일 " + str(out / ".hd-queue")), flush=True)
    if not a.no_open:
        threading.Timer(0.3, lambda: webbrowser.open(srv.url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        run.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
