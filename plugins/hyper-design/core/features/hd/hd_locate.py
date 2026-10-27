"""Client — hd locate: 캔버스 '주소 복사'(R30) 줄 → 화면 파일 · 요소 경로 · 그 요소의 지금 바깥 HTML 앞 300자. 읽기만.

주소 읽기 = hd_address(순수), 요소 찾기 = canvas html_edit.select(palette.js 경로 규칙 — 도우미 편집과 같은 것).
화면 파일: 줄에 적힌 절대 경로가 있으면 그것, 없거나 사라졌으면 프로젝트 이름 → out(부르는 쪽이 준 out_of — hd 대상 고르기와 같음) → screens.json 의 그 화면 file.
부르는 곳: hd.py(cmd_locate).
오류 탐지: 주소가 아님 · 화면이 없음 · 파일을 못 읽음 · 경로에 맞는 요소가 0개이거나 여럿 = HdError 한 줄(종료 코드 1). 적힌 파일이 없어 프로젝트로 찾았으면 [hd] 한 줄(stderr).
"""
import pathlib, re, sys

import hd_address as A
import hd_client as C  # noqa: F401  — canvas 폴더를 sys.path 에 넣는다(html_edit)
import html_edit  # noqa: E402

SNIPPET = 300


def _snippet(src, el):
    end = el.close[1] if el.close else el.open_end
    s = re.sub(r"\s+", " ", src[el.start:end]).strip()
    return s if len(s) <= SNIPPET else s[:SNIPPET] + "…"


def _screen_file(a, out_of):
    """주소 → (화면 파일 Path, 프로젝트 out|None)."""
    if a["file"]:
        f = pathlib.Path(a["file"])
        if f.is_file():
            return f, None
        print("[hd] 적힌 화면 파일이 없어 프로젝트에서 찾아요: %s" % a["file"], file=sys.stderr, flush=True)
    out = pathlib.Path(out_of(a["project"]))
    data, _ = C.read_manifest(out)
    for s in data.get("screens") or []:
        if isinstance(s, dict) and s.get("id") == a["screen"] and isinstance(s.get("file"), str):
            f = out / s["file"]
            if not f.is_file():
                raise C.HdError("화면 파일이 없어요: %s" % f)
            return f, out
    raise C.HdError("그 화면이 없어요: %s (프로젝트 %s · %s)" % (a["screen"], a["project"], out))


def locate(line, out_of):
    """주소 줄 하나 → {project, screen, path, file, text, html, tag}. out_of(project) → out 경로(못 찾으면 HdError)."""
    a = A.parse(line)
    if not a:
        raise C.HdError("hd:// 주소가 아니에요: %s" % str(line).strip()[:120])
    f, _ = _screen_file(a, out_of)
    try:
        src = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise C.HdError("화면 파일을 읽지 못했어요(%s): %s" % (e, f))
    tree = html_edit.Tree(src)
    if a["path"]:
        try:
            el = html_edit.select(tree, a["path"])
        except ValueError as e:
            raise C.HdError("%s — 파일: %s" % (e, f))
    else:
        el = next((n for n in tree.walk() if n.tag == "body"), None)
    return {"project": a["project"], "screen": a["screen"], "path": a["path"], "file": str(f), "text": a["text"],
            "tag": el.tag if el else None, "html": _snippet(src, el) if el else re.sub(r"\s+", " ", src).strip()[:SNIPPET]}


def format_item(r):
    return "\n".join(["%s · %s · %s" % (r["project"], r["screen"], r["file"]),
                      "경로: %s" % (r["path"] or "(화면 전체 — 카드)"),
                      r["html"]])
