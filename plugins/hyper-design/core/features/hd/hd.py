"""hd — 터미널 에이전트가 떠 있는 캔버스의 메모를 읽고 답한다. argparse → hd_client(I/O) → hd_model(규칙) → 출력.

  hd ls                                   떠 있는 캔버스: project · url · agent · 열린 메모 수
  hd notes [<project>|--out PATH] [--open|--sent|--all]
                                          메모: screen #no · status · intent · target · text (답은 들여 쓴 줄)
  hd reply <screen>#<no>|<note-id> --kind 반영됨 --what … --screens a,b --captured yes|no
           (일부: --done --left · 대체됨: --where · 답변: --text · 질문: --question --choice X --choice Y · 모두: --detail --by NAME)
  모든 명령 --json = 기계용 출력. 쓰기는 늘 도우미로(도우미가 없으면 hd reply 는 실패하고 띄우는 법을 알려 준다).
"""
import argparse, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hd_client as C  # noqa: E402
import hd_model as M  # noqa: E402

HELPER = HERE.parent / "canvas" / "helper.py"


def _same(a, b):
    return pathlib.Path(a).resolve() == pathlib.Path(b).resolve()


def _listing(alive):
    return "; ".join("%s (%s)" % (m.get("project"), m.get("out")) for m in alive) or "없음"


def resolve(project=None, out=None, need_helper=False):
    """→ (out 경로, 살아 있는 표지 | None). 고를 수 없으면 HdError(떠 있는 것 목록을 붙여)."""
    alive = C.running()
    if out:
        o = pathlib.Path(out).resolve()
        if not (o / "screens.json").is_file():
            raise C.HdError("screens.json 이 있는 out 폴더가 아니에요: %s" % o)
        m = next((m for m in alive if _same(m["out"], o)), None)
    else:
        pool = [m for m in alive if m.get("project") == project or _same(m["out"], project)] if project else alive
        if not pool:
            raise C.HdError(("'%s' 캔버스가 떠 있지 않아요" % project if project else "떠 있는 캔버스가 없어요") +
                            " — 떠 있는 것: %s. 파일만 읽으려면 --out PATH" % _listing(alive))
        if len(pool) > 1:
            raise C.HdError("캔버스가 여럿이에요 — 하나를 고르세요(project 또는 --out): %s" % _listing(pool))
        m = pool[0]; o = pathlib.Path(m["out"])
    if need_helper and not m:
        raise C.HdError("이 out 을 띄운 도우미가 없어요 — 먼저 띄우세요: python \"%s\" \"%s\" --no-open" % (HELPER, o))
    return o, m


def _seq(st):
    return st["state"].get("note-seq")


def _notes(st):
    n = st["state"].get("notes")
    return n if isinstance(n, list) else []


def cmd_ls(a):
    rows = []
    for m in C.running():
        try:
            st = C.read_state(m["out"]); n = len(M.pick(M.rows(_notes(st), _seq(st))))
        except C.HdError:
            n = None
        rows.append({"project": m.get("project"), "out": m["out"], "url": m.get("url"), "agent": m.get("agent"),
                     "pid": m.get("pid"), "port": m.get("port"), "started": m.get("started"), "open": n})
    return rows, M.format_canvases(rows)


def cmd_notes(a):
    o, m = resolve(a.project, a.out)
    st = C.read_state(o)
    rs = M.pick(M.rows(_notes(st), _seq(st)), a.which)
    proj = m.get("project") if m else M.project_name(o.name, o.parent.name)
    head = "%s · rev %s · %s · %d개%s" % (proj, st["rev"], a.which, len(rs), "" if m else " · 도우미 꺼짐(읽기만)")
    return {"project": proj, "out": str(o), "rev": st["rev"], "helper": bool(m), "which": a.which, "notes": rs}, head + "\n" + M.format_rows(rs)


def build_reply(a):
    r = {"kind": a.kind}
    for k in ("what", "done", "left", "where", "text", "question", "detail", "by"):
        v = getattr(a, k)
        if v is not None:
            r[k] = v
    if a.screens is not None:
        r["screens"] = [s.strip() for s in a.screens.split(",") if s.strip()]
    if a.captured is not None:
        r["captured"] = a.captured == "yes"
    if a.choice:
        r["choices"] = a.choice
    return r


def cmd_reply(a):
    o, m = resolve(a.project, a.out, need_helper=True)
    ref = M.parse_ref(a.note)
    st = C.read_state(o)
    notes = _notes(st)
    i = M.find(notes, ref, _seq(st))
    if i is None:
        raise C.HdError("없는 메모: %s — hd notes --all 로 번호를 보세요" % a.note)
    reply = build_reply(a)
    errs = M.check_reply(reply, notes[i].get("intent"), agent=True, known_screens=C.screen_ids(o))
    if errs:
        raise C.HdError("답이 규칙에 맞지 않아요:\n  " + "\n  ".join(errs))
    code, res = C.post_reply(m, {"note": ref, "reply": reply})
    if code != 200:
        raise C.HdError("도우미가 거절했어요(%d): %s" % (code, "\n  ".join(res.get("errors") or [res.get("error", "")])))
    label = "%s#%s" % (ref["screen"], ref["no"]) if isinstance(ref, dict) else a.note
    return res, "%s → %s (rev %s)" % (label, res.get("status"), res.get("rev"))


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    ap = argparse.ArgumentParser(prog="hd", description="hyper-design 캔버스 메모 — 읽기·답하기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ls", parents=[common], help="떠 있는 캔버스").set_defaults(fn=cmd_ls)
    n = sub.add_parser("notes", parents=[common], help="메모 보기")
    n.add_argument("project", nargs="?")
    n.add_argument("--out")
    w = n.add_mutually_exclusive_group()
    w.add_argument("--open", dest="which", action="store_const", const="open", help="보냈고 끝나지 않은 것(기본)")
    w.add_argument("--sent", dest="which", action="store_const", const="sent", help="보낸 것 전부")
    w.add_argument("--all", dest="which", action="store_const", const="all", help="보내기 전 것까지 전부")
    n.set_defaults(fn=cmd_notes, which="open")
    r = sub.add_parser("reply", parents=[common], help="메모에 답하기(도우미로 씀)")
    r.add_argument("note", help="<screen>#<no> 또는 메모 id")
    r.add_argument("--project"); r.add_argument("--out")
    r.add_argument("--kind", required=True, choices=M.AGENT_KINDS)
    for k in ("what", "done", "left", "where", "text", "question", "detail", "by"):
        r.add_argument("--" + k)
    r.add_argument("--screens", help="쉼표로: a,b")
    r.add_argument("--captured", choices=("yes", "no"))
    r.add_argument("--choice", action="append", help="질문의 고를 것(2–4번)")
    r.set_defaults(fn=cmd_reply)
    return ap


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    a = parser().parse_args(argv)
    try:
        data, text = a.fn(a)
    except C.HdError as e:
        if a.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        print("hd: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=1) if a.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
