"""표면 프로필 읽기 — out/surface.json(setup_out.py가 복사), 없으면 mobile.json(오늘의 기본값).

    from surface import load, resolve
    P = load(out)            # dict, 슬롯은 README.md
    P = resolve("desktop-dashboard")   # 프로필 파일이 없는 데스크톱 레이아웃 → 데스크톱 기본(마법사 창 크기 + 모바일 흐름 고리)
"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = "mobile"
DESKTOP_DEFAULT = "desktop-wizard"


def _read(name):
    return json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))


def names():
    return sorted(p.stem for p in HERE.glob("*.json"))


def resolve(name):
    """이름 → 프로필. 파일이 있으면 그대로. 없는 desktop-* 레이아웃은 데스크톱 기본으로 짓는다:
    창 크기·뷰포트·감사·이미지·작성 안내는 desktop-wizard, 흐름 고리·화면 종류·상태는 mobile(일반 앱 흐름)."""
    name = (name or DEFAULT).strip()
    if (HERE / f"{name}.json").exists():
        return _read(name)
    if not name.startswith("desktop"):
        raise SystemExit(f"표면 프로필 없음: {name} (있는 것: {', '.join(names())})")
    d, m = _read(DESKTOP_DEFAULT), _read(DEFAULT)
    p = {**d, "name": name, "label": f"데스크톱 ({name[len('desktop-'):] or '기본'})", "fallback_of": DESKTOP_DEFAULT}
    for k in ("flow", "kinds", "states"):
        p[k] = m[k]
    p["market"] = d["market"]
    return p


def load(out):
    f = pathlib.Path(out) / "surface.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _read(DEFAULT)
