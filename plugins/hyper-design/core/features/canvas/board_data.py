"""Model + 읽기 — screens.json → 캔버스 데이터(hd-data): index.html 에 끼우는 것과 도우미 /api/data 가 같은 객체(index_data).

out 안 파일(화면 HTML · decisions.json · palettes.json · credits.json · surface.json · tokens.css)을 읽기만 한다 — 쓰기·네트워크·하위 프로세스 없음.
build_canvas(빌드 CLI)와 session(도우미 /api/data)이 함께 쓴다. 화면 안 링크 규칙은 links.
오류 탐지: 깨진 JSON · 못 읽는 tokens.css 는 멈추지 않고 기본값으로, stderr 에 '경고:' 한 줄. 없는 화면 파일은 링크 없음([]).
"""
import json
import re
import sys

import links

SCALE, CARD, MODAL, RADIUS = 0.72, {"w": 375, "h": 812}, {"w": 390, "h": 844}, 28   # surface.json이 없을 때(폰)


def frame(out):
    """out/surface.json의 frame → (scale, card, modal, radius). 없거나 빠진 칸은 폰 값."""
    f = (load(out / "surface.json", {}) or {}).get("frame") or {}
    size = lambda v, d: {"w": int(v["w"]), "h": int(v["h"])} if isinstance(v, dict) and v.get("w") and v.get("h") else d
    return (f.get("scale") or SCALE, size(f.get("card"), CARD), size(f.get("modal"), MODAL),
            RADIUS if f.get("radius") is None else f["radius"])


def load(p, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except Exception as e:
        print(f"경고: {p.name} 읽기 실패 — {e}", file=sys.stderr)
        return default


DEV_URL = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d{1,5})?/", re.I)


def is_dev_url(f):
    """화면 file 이 이 PC 의 개발 서버 주소(http(s)://127.0.0.1|localhost[:포트]/…)인가 — 앱 카드(features/app). 카드가 그 주소를 그대로 불러온다(복사·파일 검사 없음)."""
    return isinstance(f, str) and bool(DEV_URL.match(f))


def screen_links(out, card, ids):
    """카드 하나의 화면 파일에서 다른 화면으로 가는 링크 → [{to, text}] (도착 = 같은 폴더 .html 파일 이름). 개발 서버 주소 카드는 읽을 파일이 없다 → []."""
    if is_dev_url(card["file"]):
        return []
    f = out / card["file"]
    try:
        src = f.read_text(encoding="utf-8")
    except OSError:
        return []
    p = links.Links(); p.feed(src); p.close()
    res = []
    for h, text in p.out:
        to = links.link_target(h)
        if to and to != card["id"] and to in ids:
            res.append({"to": to, "text": text})
    return res


def root_vars(css):
    names = []
    for block in re.findall(r":root\s*\{(.*?)\}", css, re.S):
        for n in re.findall(r"(--[\w-]+)\s*:", re.sub(r"/\*.*?\*/", "", block, flags=re.S)):
            if n not in names:
                names.append(n)
    return names


def index_data(out, m):
    """screens.json(m) → 캔버스 hd-data 객체(index.html 에 끼우는 것 · 도우미 /api/data 도 같은 것)."""
    screens = m["screens"]
    groups = list(m.get("groups") or [])
    for s in screens:
        g = s.get("group") or "기타"
        if g not in groups:
            groups.append(g)
    rows = {g: [] for g in groups}
    for s in screens:                                   # 상태 변형은 원래 화면 바로 뒤에
        if "--" in s["id"]:
            continue
        g = s.get("group") or "기타"
        rows[g].append(s)
        rows[g].extend(v for v in screens if v["id"].startswith(s["id"] + "--"))
    placed = {s["id"] for r in rows.values() for s in r}
    for s in screens:                                   # 원래 화면이 없는 상태 변형도 버리지 않는다
        if s["id"] not in placed:
            rows[s.get("group") or "기타"].append(s)
    card = lambda s: {"id": s["id"], "file": s.get("file") or f"screens/{s['id']}.html",
                      "title": s.get("title") or s["id"], "purpose": s.get("purpose") or "",
                      "policies": [p for p in (s.get("policies") or []) if p], "state": "--" in s["id"]}
    data_rows = [{"group": g, "screens": [card(s) for s in rows[g]]} for g in groups if rows[g]]
    ids = {s["id"] for s in screens}
    arrows = [{"from": s["id"], "to": b.get("to"), "label": b.get("label") or ""}
              for s in screens for b in (s.get("branches") or [])
              if b.get("to") in ids and b.get("to") != s["id"]]
    # 화면 안 링크(판에 늘 그리는 선) — 화면 파일에서 미리 뽑는다(카드를 불러오지 않아도 모든 선이 보이게)
    links = {c["id"]: ls for r in data_rows for c in r["screens"] if (ls := screen_links(out, c, ids))}

    D = load(out / "decisions.json")
    decisions = None
    if D:
        label = {"lighten": "가볍게", "cut": "뺌", "later": "나중에"}
        items = [{"verdict": i["verdict"], "label": label[i["verdict"]], "name": i.get("name") or "",
                  "how": i.get("how") if i.get("verdict") == "lighten" else "", "why": i.get("why") or ""}
                 for i in D.get("items", []) if i.get("verdict") in label and i.get("source") != "시장"][:6]
        # 시장 관례: 벗어난 것 먼저(이유가 중요), 그다음 따른 것 — 최대 6
        mk = [i for i in D.get("items", []) if i.get("source") == "시장" and str(i.get("id", "")).startswith("M")]
        mk = sorted(mk, key=lambda i: i.get("verdict") == "keep")[:6]
        market = [{"verdict": "follow" if i.get("verdict") == "keep" else "cut", "label": "따름" if i.get("verdict") == "keep" else "벗어남",
                   "name": i.get("name") or "", "how": i.get("how") or "", "why": i.get("why") or ""} for i in mk]
        if items or D.get("core") or market:
            decisions = {"core": D.get("core") or "", "items": items, "market": market}

    pal = load(out / "palettes.json")
    if pal and pal.get("options"):
        pal = {"default": pal.get("default"),
               "options": [{k: o.get(k) for k in ("slug", "name", "brand", "source")} for o in pal["options"][:3]]}
    else:
        pal = None
    credits = load(out / "credits.json", []) or []
    tok = out / "tokens.css"                          # 판 위 디자인 시스템 카드(S6, modules/ds-card.js): tokens.css :root 변수 이름만 — 값은 카드가 같은 파일에서 읽는다
    try:
        tokens = root_vars(tok.read_text(encoding="utf-8")) if tok.exists() else None
    except (OSError, UnicodeDecodeError) as e:
        print(f"경고: tokens.css 읽기 실패 — {e}", file=sys.stderr)
        tokens = None

    scale, card_sz, modal_sz, radius = frame(out)
    data = {"title": m.get("title") or "전체 화면 한눈에 보기", "scale": scale, "card": card_sz, "modal": modal_sz, "radius": radius,
            "story": m.get("story") or None, "people": [{"name": p.get("name", ""), "why": p.get("why", ""), "win": p.get("win", ""), "core": bool(p.get("core")),
                                                     "wants": [w.get("q", "") for w in (p.get("wants") or [])][:5]} for p in (m.get("people") or [])[:4]], "decisions": decisions, "stage": m.get("stage") or "", "pending": m.get("pending_states") or 0, "rows": data_rows, "arrows": arrows, "links": links,
            "palettes": pal, "credits": credits if isinstance(credits, list) else [], "tokens": tokens}
    return data
