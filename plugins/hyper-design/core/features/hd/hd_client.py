"""Client — I/O 만: 떠 있는 표지 읽기 · 도우미 살아 있나 보기 · 상태 파일·screens.json 읽기 · 답 보내기. 규칙은 hd_model.

표지 = <HD_HOME | ~/.hyper-design>/active/<pid>.json (helper.py 가 쓰고 지운다). 죽은 표지(강제 종료)는 1초 핑으로 걸러 내고 지우지 않는다.
상태 파일은 읽기만 한다 — 쓰기는 늘 도우미(POST /api/reply)로(쓰는 곳 하나).
"""
import json, os, pathlib, urllib.error, urllib.request

STATE_FILE = ".hd-canvas.json"
PING_TIMEOUT = 1.0


class HdError(Exception):
    """사용자에게 그대로 보일 한 줄 오류."""


def home():
    return pathlib.Path(os.environ.get("HD_HOME") or pathlib.Path.home() / ".hyper-design")


def markers():
    """표지 전부(읽을 수 없는 것은 건너뜀) — 살아 있는지는 모른다."""
    d = home() / "active"
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(m, dict) and m.get("port") and m.get("token") and m.get("out"):
            out.append(m)
    return out


def _base(m):
    return "http://127.0.0.1:%d" % int(m["port"])


def ping(m, timeout=PING_TIMEOUT):
    req = urllib.request.Request(_base(m) + "/api/state", headers={"X-HD-Token": m["token"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False


def running():
    """살아 있는 도우미의 표지만."""
    return [m for m in markers() if ping(m)]


def read_state(out):
    """<out>/.hd-canvas.json → {rev, state}. 없으면 rev 0 · 깨졌으면 HdError."""
    p = pathlib.Path(out) / STATE_FILE
    if not p.is_file():
        return {"rev": 0, "state": {}}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HdError("상태 파일을 읽지 못했어요(%s): %s" % (e, p))
    if not isinstance(doc, dict) or not isinstance(doc.get("state"), dict):
        raise HdError("상태 파일 모양이 아니에요: %s" % p)
    return {"rev": doc.get("rev", 0), "state": doc["state"]}


def screen_ids(out):
    """screens.json 의 화면 id 집합 | None(못 읽음)."""
    try:
        return {s["id"] for s in json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("screens", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def post_reply(m, body, timeout=10):
    """POST /api/reply → (code, 답 객체). 닿지 않으면 HdError."""
    req = urllib.request.Request(_base(m) + "/api/reply", data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"X-HD-Token": m["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {"error": "HTTP %d" % e.code}
    except (OSError, ValueError) as e:
        raise HdError("도우미에 닿지 않아요(%s): %s" % (e, _base(m)))
