"""hd — 터미널 에이전트가 떠 있는 캔버스의 메모를 읽고 답한다. argparse → hd_client(I/O) → hd_model(규칙) → 출력.

  hd ls                                   떠 있는 캔버스: project · url · agent · 열린 메모 수
  hd notes [<project>|--out PATH] [--open|--sent|--all]
                                          메모: screen #no · status · intent · target · text (답은 들여 쓴 줄)
  hd reply <screen>#<no>|<note-id> --kind 반영됨 --what … --screens a,b --captured yes|no
           (일부: --done --left · 대체됨: --where · 답변: --text · 질문: --question --choice X --choice Y · 모두: --detail --by NAME)
  hd projects                             저장한 프로젝트(링크): name · out · url|꺼짐|없음 · 연 때
  hd save [--name N] [--out PATH]         링크 넣기·고치기(기본 out = 떠 있는 캔버스 하나) — 복사하지 않는다
  hd open <name|path> [--agent ID] [--no-open]
                                          떠 있으면 그 주소, 아니면 build_ref.py 로 빌드 후 helper.py 를 떼어 띄운다
  hd forget <name>                        링크만 지운다(파일은 그대로)
  모든 명령 --json = 기계용 출력. 쓰기는 늘 도우미로(도우미가 없으면 hd reply 는 실패하고 띄우는 법을 알려 준다).
"""
import argparse, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hd_client as C  # noqa: E402
import hd_model as M  # noqa: E402
import hd_projects as P  # noqa: E402

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


def cmd_projects(a):
    reg = C.load_projects()
    rs = P.rows(reg, C.running(), C.exists_map(reg))
    return rs, P.format_rows(rs)


def cmd_save(a):
    if a.out:
        o = pathlib.Path(C.abs_out(a.out))
        if not C.is_out(o):
            raise C.HdError("screens.json 이 있는 out 폴더가 아니에요: %s" % o)
    else:
        alive = C.running()
        if len(alive) != 1:
            raise C.HdError(("떠 있는 캔버스가 없어요" if not alive else "캔버스가 여럿이에요(%s)" % _listing(alive)) + " — --out PATH 로 고르세요")
        o = pathlib.Path(C.abs_out(alive[0]["out"]))
    reg = C.load_projects()
    old = P.by_out(reg, str(o))
    try:
        reg, e, added = P.save(reg, str(o), C.now(), a.name, default_name=C.project_from(o))
    except P.ProjectError as x:
        raise C.HdError(str(x))
    C.save_projects(reg)
    how = "새로 저장" if added else ("이름 바꿈, 전: %s" % old["name"] if old["name"] != e["name"] else "이미 있음")
    return dict(e, added=added), "%s (%s)" % (P.link_line(e), how)


def cmd_open(a):
    reg = C.load_projects()
    e = P.find(reg, a.target)
    if e is None and C.is_out(a.target):
        o = C.abs_out(a.target)
        reg, e, _ = P.save(reg, o, C.now(), default_name=C.project_from(o))
        C.save_projects(reg)
    if e is None:
        raise C.HdError("모르는 프로젝트예요: %s — hd projects 로 이름을 보거나 out 경로를 주세요" % a.target)
    o = pathlib.Path(e["out"])
    if not C.is_out(o):
        raise C.HdError("'%s' 의 out 폴더가 없어요(없음): %s — 링크만 지우려면 hd forget %s" % (e["name"], o, e["name"]))
    agent = a.agent or os.environ.get("PASEO_AGENT_ID") or None
    m = C.serving(o)
    reused = m is not None
    if not reused:
        code, tail = C.build(o)
        if code != 0:
            if not (o / "index.html").is_file():
                raise C.HdError("빌드 실패(build_ref.py %d): %s" % (code, " / ".join(tail.splitlines())))
            C.warn("빌드 실패(%d) — 있던 index.html 로 띄워요: %s" % (code, tail.splitlines()[-1] if tail else ""))
        proc, log = C.spawn_helper(o, agent)
        m = C.wait_serving(o, proc)
        if m is None:
            raise C.HdError("도우미가 %d초 안에 뜨지 않았어요 — 로그 %s: %s" % (C.START_WAIT, log, " / ".join(C.log_tail(log).splitlines())))
    C.save_projects(P.touch(C.load_projects(), e["out"], C.now()))   # 도우미가 그 사이 목록을 썼을 수 있어 다시 읽는다
    if not a.no_open:
        C.open_browser(m["url"])
    data = {"name": e["name"], "out": e["out"], "url": m["url"], "pid": m.get("pid"), "agent": m.get("agent"), "reused": reused}
    how = "이미 떠 있음" if reused else "새로 띄움"
    note = ""
    if reused and agent and m.get("agent") != agent:
        note = " · 떠 있는 도우미는 %s 로 보내요(바꾸려면 그 도우미를 끄고 다시 open)" % (m.get("agent") or "대기열 파일")
    return data, "%s · %s · %s · pid %s · 보내기 → %s%s" % (e["name"], m["url"], how, m.get("pid"), m.get("agent") or "대기열 파일", note)


def cmd_forget(a):
    reg, hit = P.forget(C.load_projects(), a.name)
    if hit is None:
        raise C.HdError("저장한 프로젝트에 '%s' 이 없어요 — hd projects" % a.name)
    C.save_projects(reg)
    return hit, "링크를 지웠어요: %s (파일은 그대로)" % P.link_line(hit)


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
    sub.add_parser("projects", parents=[common], help="저장한 프로젝트(링크)").set_defaults(fn=cmd_projects)
    v = sub.add_parser("save", parents=[common], help="프로젝트 링크 넣기·고치기")
    v.add_argument("--name"); v.add_argument("--out")
    v.set_defaults(fn=cmd_save)
    o = sub.add_parser("open", parents=[common], help="프로젝트 열기(떠 있으면 그 주소, 아니면 빌드 후 도우미 띄움)")
    o.add_argument("target", help="이름 또는 out 경로")
    o.add_argument("--agent", help="보내기 받을 Paseo 에이전트(기본 env PASEO_AGENT_ID)")
    o.add_argument("--no-open", action="store_true", help="브라우저를 열지 않음")
    o.set_defaults(fn=cmd_open)
    f = sub.add_parser("forget", parents=[common], help="링크만 지움(파일은 그대로)")
    f.add_argument("name")
    f.set_defaults(fn=cmd_forget)
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
