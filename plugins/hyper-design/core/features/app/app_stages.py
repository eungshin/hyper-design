"""Model — 앱 저장소 글(twin registry.js · SettingsApp.svelte) → 캔버스 screens.json · app.json 데이터. 순수 함수(파일·프로세스 없음).

무대 목록은 node 에 묻지 않고 글에서 읽는다(정적 파싱): registry.js 는 import 없는 리터럴 배열·객체라 충분하고,
unit 테스트가 하위 프로세스 없이 돈다. 읽는 것 — `export const TWIN_COMPONENTS = [ {id, name, group, fixture, file}, … ]`,
`export const TWIN_LABELS = { 'id': '글', … }`, SettingsApp.svelte 의 `const tabs = ['basic', …]`.
"""
import re

STAGE_PATH = "/hd-stage/{screen}.html"                 # dayfine.vite.mjs 의 무대 페이지(경로 마지막 조각 = 캔버스 화면 id)
GROUP_NAMES = {"atoms": "원자", "molecules": "분자", "organisms": "유기체"}
SETTINGS_STAGE = "settings-window"


class AppParseError(ValueError):
    """registry.js 에서 무대 목록을 찾지 못함 — 앱 쪽 모양이 바뀌었다."""


def strip_comments(js):
    """// 와 /* */ 주석을 지운다(따옴표 안은 그대로)."""
    out, i, n, q = [], 0, len(js), None
    while i < n:
        c = js[i]
        if q:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(js[i + 1]); i += 2; continue
            if c == q:
                q = None
            i += 1; continue
        if c in "'\"`":
            q = c; out.append(c); i += 1; continue
        if js.startswith("//", i):
            j = js.find("\n", i); i = n if j < 0 else j; continue
        if js.startswith("/*", i):
            j = js.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        out.append(c); i += 1
    return "".join(out)


def _block(js, name, open_ch, close_ch):
    """`export const NAME = <open> … <close>` 의 안쪽 글(괄호 짝을 세고 따옴표 안은 건너뜀) | None."""
    m = re.search(r"\bconst\s+" + re.escape(name) + r"\s*=\s*" + re.escape(open_ch), js)
    if not m:
        return None
    depth, i, q = 1, m.end(), None
    while i < len(js):
        c = js[i]
        if q:
            if c == "\\":
                i += 2; continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return js[m.end():i]
        i += 1
    return None


STR = r"""(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")"""
KEY = r"""(?:([A-Za-z_$][\w$]*)|""" + STR + r")"


def _unq(a, b):
    v = a or b                                          # findall 은 빠진 묶음을 None 이 아니라 "" 로 준다
    return re.sub(r"\\(.)", r"\1", v or "")


def _objects(body):
    """배열 안쪽 글 → 맨 위 {…} 조각들의 안쪽 글."""
    res, depth, start, q, i = [], 0, None, None, 0
    while i < len(body):
        c = body[i]
        if q:
            if c == "\\":
                i += 2; continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c == "{":
            if depth == 0:
                start = i + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                res.append(body[start:i]); start = None
        i += 1
    return res


def _fields(obj):
    """{a:'x', 'b': "y", c: CONST} → {a:'x', b:'y', c:'CONST'}(이름만 있는 값은 그 이름 그대로)."""
    f = {}
    for m in re.finditer(KEY + r"\s*:\s*(?:" + STR + r"|([A-Za-z_$][\w$]*))", obj):
        k = m.group(1) or _unq(m.group(2), m.group(3))
        f[k] = _unq(m.group(4), m.group(5)) if (m.group(4) is not None or m.group(5) is not None) else m.group(6)
    return f


def _consts(js):
    """const NAME = 'value'; → {NAME: value}(그룹 이름 상수용)."""
    return {m.group(1): _unq(m.group(2), m.group(3)) for m in re.finditer(r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*" + STR + r"\s*;", js)}


def parse_registry(js):
    """registry.js 글 → [{id, name, group, fixture, file, label}](차례 그대로). 무대 배열이 없으면 AppParseError."""
    js = strip_comments(js)
    body = _block(js, "TWIN_COMPONENTS", "[", "]")
    if body is None:
        raise AppParseError("registry.js 에 TWIN_COMPONENTS = [ … ] 가 없어요")
    consts = _consts(js)
    labels = parse_labels(js)
    stages = []
    for o in _objects(body):
        f = _fields(o)
        sid = f.get("id")
        if not sid:
            continue
        g = f.get("group") or ""
        stages.append({"id": sid, "name": f.get("name") or sid, "group": consts.get(g, g),
                       "fixture": f.get("fixture") or "", "file": f.get("file") or "", "label": labels.get(sid, "")})
    if not stages:
        raise AppParseError("TWIN_COMPONENTS 에 무대가 하나도 없어요")
    return stages


def parse_labels(js):
    """TWIN_LABELS = {'id': '글', …} → {id: 글}(여러 줄에 걸친 값 포함). 없으면 {}."""
    body = _block(strip_comments(js), "TWIN_LABELS", "{", "}")
    if body is None:
        return {}
    return {m.group(1) or _unq(m.group(2), m.group(3)): _unq(m.group(4), m.group(5))
            for m in re.finditer(KEY + r"\s*:\s*" + STR, body)}


def parse_settings_tabs(svelte):
    """SettingsApp.svelte 의 `const tabs = ['basic', …]` → ['basic', …](없으면 [])."""
    m = re.search(r"\bconst\s+tabs\s*=\s*\[([^\]]*)\]", strip_comments(svelte))
    return [_unq(a, b) for a, b in re.findall(STR, m.group(1))] if m else []


def is_dev_url(u):
    """http(s)://127.0.0.1|localhost[:포트] — canvas/build_canvas.py is_dev_url 과 같은 규칙(카드가 그 주소를 그대로 불러온다)."""
    return isinstance(u, str) and bool(re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d{1,5})?/?$", u, re.I))


def stage_url(dev_url, screen):
    return dev_url.rstrip("/") + STAGE_PATH.format(screen=screen)


def screens_doc(stages, tabs, dev_url, title="Dayfine — 앱 화면(twin 무대)"):
    """무대 + 설정 탭 → screens.json 객체. 설정 탭 카드 id = settings-window--<탭>(캔버스가 상태 변형으로 그 무대 바로 뒤에 둔다)."""
    groups, screens = [], []
    for s in stages:
        g = GROUP_NAMES.get(s["group"], s["group"] or "기타")
        if g not in groups:
            groups.append(g)
        pol = [p for p in (f"소스: {s['file']}" if s["file"] else "", f"픽스처: {s['fixture']}" if s["fixture"] else "") if p]
        screens.append({"id": s["id"], "file": stage_url(dev_url, s["id"]), "title": s["name"], "group": g,
                        "purpose": s["label"] or s["name"], "policies": pol, "branches": []})
        if s["id"] == SETTINGS_STAGE:
            for t in tabs:
                screens.append({"id": f"{s['id']}--{t}", "file": stage_url(dev_url, f"{s['id']}--{t}"), "title": f"{s['name']} · {t}",
                                "group": g, "purpose": f"설정 창 — {t} 탭", "policies": pol[:1], "branches": []})
    return {"title": title, "groups": groups, "screens": screens}


def app_doc(repo, ui_dir, dev_url, dev_cmd, stages):
    """app.json 객체 — 다시 띄우는 데 드는 것(저장소 · 앱 폴더 · 개발 서버 명령·주소 · 무대 id)."""
    return {"kind": "app", "repo": repo, "ui_dir": ui_dir, "dev_cmd": dev_cmd, "dev_url": dev_url.rstrip("/"),
            "stages": [s["id"] for s in stages]}


SURFACE = {"frame": {"card": {"w": 520, "h": 640}, "modal": {"w": 960, "h": 720}, "radius": 12, "scale": 0.6}}
