"""hd — 터미널 에이전트가 떠 있는 캔버스의 메모를 읽고 답한다. argparse → hd_sdk(Hub·Project — task 47-3) → 출력. 얇은 껍데기: 규칙·I/O 는 SDK 아래.

  hd ls                                   떠 있는 캔버스: project · url · agent · 열린 메모 수
  hd notes [<project>|--out PATH] [--open|--sent|--all]
                                          메모: screen #no · status · intent · target · text (답은 들여 쓴 줄)
  hd reply <screen>#<no>|<note-id> --kind 반영됨 --what … --screens a,b --captured yes|no
           (일부: --done --left · 대체됨: --where · 답변: --text · 질문: --question --choice X --choice Y · 모두: --detail|--detail-file PATH|- --by NAME)
           요약 칸은 짧게(한 줄 상태), 긴 답 전체는 detail(50000자 — 대화 패널·메모가 다 보인다). 긴 글은 --detail-file(명령줄 한도)
  hd projects                             저장한 프로젝트(링크): name · out · url|꺼짐|없음 · 연 때
  hd save [--name N] [--out PATH]         링크 넣기·고치기(기본 out = 떠 있는 캔버스 하나) — 복사하지 않는다
  hd open <name|path> [--agent ID] [--no-open]
                                          떠 있으면 그 주소, 아니면 build_ref.py 로 빌드 후 helper.py 를 떼어 띄운다
  hd forget <name>                        링크만 지운다(파일은 그대로)
  hd stop [<name|path>]                   도우미 끄기(POST /api/stop, 답이 없으면 pid 강제 종료) — 링크는 그대로
  hd attach [--agent ID|none] [<name|path>]
                                          보내기 받을 Paseo 에이전트 바꾸기(다시 띄우지 않음, 기본 env PASEO_AGENT_ID, none = 떼기)
                                          — 서버가 알면 접속 알리기(hello, listen false: 보내기는 그대로 paseo)도 한 번(47-5a)
  hd progress "<글>" [<name|path>] [--screen ID] [--agent ID]
                                          캔버스에 진행 한 줄(200자, agent 기본 env PASEO_AGENT_ID) — 접속 칩·대화창이 보여 줌
  hd wait [<name|path>] [--timeout S]     보낸(working) 메모가 생길 때까지 기다렸다가 hd notes 처럼 보여 줌 — 시간 넘으면 종료 코드 2
  hd claim <screen> [<name|path>] [--note TEXT] [--by ID]
                                          "이 화면 고치는 중" — 캔버스 그 카드에 덮개(파일이 바뀌거나 hd release 면 걷힘, by 기본 env PASEO_AGENT_ID)
  hd release <screen> [<name|path>]       덮개 걷기
  hd screens [<name|path>]                화면 목록: 줄마다 id · 제목 · 파일 · 자리 +dx,+dy · W×H(프리셋) — 떠 있지 않아도 저장한 이름·out 경로로 읽음
  hd add <file.html> [<name|path>] [--id ID] [--title T] [--group G] [--purpose P] [--after ID | --at DX,DY] [--size Desktop|WxH]
         [--asset PATH …] [--replace]
                                          HTML 화면 하나를 캔버스에 넣기: out 으로 복사 · screens.json 에 등록(새 줄이면 만듦) · 자리·크기(도우미로)
                                          · 열린 캔버스에 바로 보임(새로고침 없음). 자리 = --after 옆 | --at 제 자리에서 옮긴 거리 | 그 줄 끝
  hd home [--no-browser] [--port N] [--restart]
                                          홈(모든 캔버스) 허브를 띄우고 브라우저로 — 떠 있으면 그 주소(home_server, 옛 코드면 한 줄 알림)
                                          --restart = 떠 있는 허브를 끄고 지금 코드로 같은 포트에 다시 띄움
  hd home --shortcut [--desktop DIR]      바탕 화면에 'Hyper Design' 바로 가기(→ pythonw hd.py home)를 쓰고 끝
  hd parts [--check [<file>]] [<name|path>]
                                          앱 부품(out/parts.json): 파일 · 낡음|최신|모름 · 미커밋 변경 포함 · 빌드 시각 — 읽기만(git 나무 도장 비교)
  모든 명령 --json = 기계용 출력. 쓰기는 늘 도우미로(도우미가 없으면 hd reply 는 실패하고 띄우는 법을 알려 준다).
"""
import argparse, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hd_sdk as S  # noqa: E402  — 모든 일은 SDK(Hub·Project·Note·HdError, task 47-3). 여기는 argparse → SDK → 출력뿐

HOME_DIR = HERE.parent / "home"


def _hub():
    return S.Hub()


def cmd_ls(a):
    rows = []
    for p in _hub().canvases():
        try:
            n = len(p.notes("open"))
        except S.HdError:
            n = None
        m = p.marker
        rows.append({"project": m.get("project"), "out": m["out"], "url": m.get("url"), "agent": m.get("agent"),
                     "pid": m.get("pid"), "port": m.get("port"), "started": m.get("started"), "open": n})
    return rows, S.text.canvases(rows)


def cmd_notes(a):
    p = _hub().project(a.project, a.out)
    st = p.state()
    ns = p.notes(a.which, state=st)
    head = "%s · rev %s · %s · %d개%s" % (p.name, st["rev"], a.which, len(ns), "" if p.online else " · 도우미 꺼짐(읽기만)")
    return ({"project": p.name, "out": str(p.out), "rev": st["rev"], "helper": p.online, "which": a.which, "notes": [n.as_dict() for n in ns]},
            head + "\n" + S.text.notes(ns))


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


def read_detail(a):
    """--detail-file PATH|- → a.detail(R26: 긴 답은 파일·표준 입력으로 — Windows 명령줄은 약 32000자). --detail 과 함께면 오류."""
    if a.detail_file is None:
        return
    if a.detail is not None:
        raise SystemExit("--detail 과 --detail-file 중 하나만 쓰세요")
    try:
        raw = sys.stdin.buffer.read() if a.detail_file == "-" else pathlib.Path(a.detail_file).read_bytes()
        a.detail = raw.decode("utf-8-sig").replace("\r\n", "\n")   # Windows 에서 쓴 파일도 같은 줄바꿈
    except (OSError, UnicodeDecodeError) as e:
        raise SystemExit("--detail-file 을 읽지 못했어요(UTF-8 글이어야 해요): %s" % e)


def cmd_reply(a):
    read_detail(a)
    p = _hub().project(a.project, a.out, need_helper=True)
    res = p.reply(a.note, build_reply(a))
    r = S.parse_ref(a.note)
    label = "%s#%s" % (r["screen"], r["no"]) if isinstance(r, dict) else a.note
    return res, "%s → %s (rev %s)" % (label, res.get("status"), res.get("rev"))


def cmd_projects(a):
    rs = _hub().projects()
    return rs, S.text.projects(rs)


def cmd_save(a):
    e, added, old = _hub().save(a.out, a.name)
    how = "새로 저장" if added else ("이름 바꿈, 전: %s" % old["name"] if old["name"] != e["name"] else "이미 있음")
    return dict(e, added=added), "%s (%s)" % (S.text.link(e), how)


def cmd_open(a):
    agent = a.agent or os.environ.get("PASEO_AGENT_ID") or None
    e, p, reused = _hub().open(a.target, agent)
    if not a.no_open:
        import webbrowser
        webbrowser.open(p.url)
    data = {"name": e["name"], "out": e["out"], "url": p.url, "pid": p.pid, "agent": p.agent, "reused": reused}
    how = "이미 떠 있음" if reused else "새로 띄움"
    note = ""
    if reused and agent and p.agent != agent:
        note = " · 떠 있는 도우미는 %s 로 보내요(바꾸려면 hd attach --agent %s %s)" % (p.agent or "대기열 파일", agent, e["name"])
    return data, "%s · %s · %s · pid %s · 보내기 → %s%s" % (e["name"], p.url, how, p.pid, p.agent or "대기열 파일", note)


def cmd_forget(a):
    hit = _hub().forget(a.name)
    return hit, "링크를 지웠어요: %s (파일은 그대로)" % S.text.link(hit)


STOP_WORD = {"route": "도우미가 스스로 껐어요", "kill": "답이 없어 pid 를 강제로 껐어요", "gone": "프로세스가 이미 없어 표지만 지웠어요",
             "other": "그 pid 는 다른 프로그램이라 끄지 않고 표지만 지웠어요"}


def cmd_stop(a):
    p = _hub().pick(a.target, stale_ok=True)
    how = p.stop()
    return ({"project": p.name, "out": str(p.marker["out"]), "pid": p.pid, "port": p.port, "how": how},
            "%s · pid %s · %s (링크는 그대로)" % (p.name, p.pid, STOP_WORD[how]))


def cmd_attach(a):
    agent = a.agent if a.agent is not None else os.environ.get("PASEO_AGENT_ID")
    if agent is None:
        raise S.Invalid("보낼 에이전트가 없어요 — --agent ID 를 주거나(PASEO_AGENT_ID 도 없음), 떼려면 --agent none")
    agent = None if agent == "none" else agent
    S.check_agent(agent)
    p = _hub().pick(a.target)
    was = p.agent
    got = p.attach(agent)
    if got:                                          # 47-5a: 접속 칩에 보이기(맥박 없음 — 임대가 끝나면 away). 옛 서버·실패는 조용히(attach 는 됐다)
        try:
            p.hello(got, kind="paseo", listen=False, beat=False)
        except S.HdError:
            pass
    return ({"project": p.name, "out": p.marker["out"], "pid": p.pid, "agent": got, "was": was},
            "%s · 보내기 → %s (전: %s)" % (p.name, got or "대기열 파일", was or "대기열 파일"))


def cmd_wait(a):
    p = _hub().pick(a.target)
    st, ns = p.wait(a.timeout)
    head = "%s · rev %s · working · %d개" % (p.name, st["rev"], len(ns))
    return ({"project": p.name, "out": p.marker["out"], "rev": st["rev"], "helper": True, "which": "working", "notes": [n.as_dict() for n in ns]},
            head + "\n" + S.text.notes(ns))


def cmd_claim(a):
    by = a.by if a.by is not None else os.environ.get("PASEO_AGENT_ID") or None
    S.check_claim(a.screen, by, a.note)
    p = _hub().pick(a.target)
    res = p.claim(a.screen, by, a.note)
    return (dict(res, project=p.name, by=by, note=a.note),
            "%s · %s 덮개 씌움%s (rev %s) — 파일이 바뀌거나 hd release %s 면 걷혀요" % (
                p.name, a.screen, " · " + a.note if a.note else "", res.get("rev"), a.screen))


def cmd_release(a):
    p = _hub().pick(a.target)
    res = p.release(a.screen)
    return (dict(res, project=p.name, screen=a.screen),
            "%s · %s %s" % (p.name, a.screen, "덮개 걷음 (rev %s)" % res.get("rev") if res.get("released") else "덮개가 없어요(그대로)"))


def cmd_progress(a):
    p = _hub().pick(a.target)
    ev = p.progress(a.text, screen=a.screen, agent=a.agent or os.environ.get("PASEO_AGENT_ID") or None)
    return ({"project": p.name, "text": a.text.strip(), "screen": a.screen, "event": ev},
            "%s · 진행: %s%s" % (p.name, a.text.strip(), " (%s)" % a.screen if a.screen else ""))


def cmd_screens(a):
    p = _hub().target(a.target)
    d = p.layout()
    head = "%s · 화면 %d개 · 줄 %d개%s" % (p.name, len(d["screens"]), len({r["group"] for r in d["screens"]}),
                                     "" if p.online else " · 도우미 꺼짐(읽기만)")
    return d, head + "\n" + S.place_text(d["screens"], d["groups"])


def cmd_add(a):
    p = _hub().target(a.target)
    r = p.add(a.file, sid=a.id, title=a.title, group=a.group, purpose=a.purpose, after=a.after, at=a.at, size=a.size,
              assets=a.asset or (), replace=a.replace)
    where = "%s 옆" % r["after"] if r["after"] else ("'%s' 줄 끝" % r["group"] if r["group"] else "끝")
    bits = [x for x in (S.place_pos(r["pos"]), S.place_size(r["size"])) if x]
    live = "캔버스에 바로 보여요" if r["live"] else "도우미 꺼짐 — index.html 다시 빌드(다음에 열면 보여요)"
    return r, "%s · %s %s (%s · %s%s%s) · %s" % (p.name, r["id"], "바꿈" if r["replaced"] else "넣음", r["file"], where,
                                               " · 새 줄" if r["group_added"] else "", "".join(" · " + b for b in bits), live)


def _parts_args(a):
    """--check/--rebuild 뒤 값 하나만 있으면 out 경로·저장한 이름일 때 그것이 대상(hd parts --rebuild <out>), 아니면 부품 고르기."""
    sel = a.rebuild if a.rebuild is not None else a.check
    sel = None if sel == "*" else sel
    if sel and a.target is None:
        import hd_client, hd_projects
        if hd_client.is_out(sel) or ("/" not in sel and "\\" not in sel and "." not in sel and hd_projects.find(hd_client.load_projects(), sel)):
            return None, sel
    return sel, a.target


def cmd_parts(a):
    """앱 부품 보기(기본 · --check) — parts.json 은 읽기만. 대상 고르기는 hd screens 와 같음(떠 있지 않아도 out 경로·저장한 이름)."""
    import hd_parts
    sel, target = _parts_args(a)
    p = _hub().target(target)
    with S.client_errors():
        rows = hd_parts.check(p.out, sel)
    stale = sum(1 for r in rows if r["stale"])
    head = "%s · 앱 부품 %d개 · 낡음 %d개%s" % (p.name, len(rows), stale, " — 다시 빌드: hd parts --rebuild %s" % p.name if stale else "")
    return {"project": p.name, "out": str(p.out), "parts": rows}, head + "\n" + hd_parts.format_rows(rows)


def cmd_home(a):
    """홈 서버 띄우기 · 바로 가기 — 서버를 띄우는 일이라 SDK(서버에 말 걸기) 밖: home_server · shortcut 을 부를 뿐."""
    sys.path.insert(0, str(HOME_DIR))
    import hd_client
    if a.shortcut:
        import shortcut
        try:
            lnk = shortcut.write_shortcut(hd_client.home(), a.desktop)
        except shortcut.ShortcutError as e:
            raise S.HdError(str(e))
        return {"shortcut": str(lnk)}, "바로 가기를 만들었어요: %s" % lnk
    import home_server
    with S.client_errors():
        res = home_server.serve(a.port, a.no_browser, on_url=lambda u: print(u, flush=True) if sys.stdout else None, restart=a.restart)
    if res["reused"]:
        stale = " · 새 버전이 있어요 — hd home --restart 로 다시 켜면 반영돼요" if res.get("stale") else ""
        return res, res["url"] + " (이미 떠 있음)" + stale
    return res, "홈을 껐어요"


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
    r.add_argument("--kind", required=True, choices=S.AGENT_KINDS)
    for k in ("what", "done", "left", "where", "text", "question", "detail", "by"):
        r.add_argument("--" + k)
    r.add_argument("--detail-file", help="긴 답 본문(detail, 50000자까지)을 UTF-8 파일에서 · - = 표준 입력")
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
    s = sub.add_parser("stop", parents=[common], help="도우미 끄기(링크는 그대로)")
    s.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    s.set_defaults(fn=cmd_stop)
    t = sub.add_parser("attach", parents=[common], help="보내기 받을 Paseo 에이전트 바꾸기(다시 띄우지 않음)")
    t.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    t.add_argument("--agent", help="에이전트 id(기본 env PASEO_AGENT_ID) · none = 떼기(대기열 파일로)")
    t.set_defaults(fn=cmd_attach)
    w = sub.add_parser("wait", parents=[common], help="보낸 메모가 생길 때까지 기다림(시간 넘으면 종료 코드 2)")
    w.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    w.add_argument("--timeout", type=float, default=600.0, help="초(기본 600)")
    w.set_defaults(fn=cmd_wait)
    c = sub.add_parser("claim", parents=[common], help="이 화면을 고치는 중 — 캔버스 카드에 덮개")
    c.add_argument("screen", help="화면 id")
    c.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    c.add_argument("--note", help="하는 일 한 줄(덮개에 보임, 140자까지)")
    c.add_argument("--by", help="누가(기본 env PASEO_AGENT_ID)")
    c.set_defaults(fn=cmd_claim)
    rl = sub.add_parser("release", parents=[common], help="덮개 걷기")
    rl.add_argument("screen", help="화면 id")
    rl.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    rl.set_defaults(fn=cmd_release)
    pg = sub.add_parser("progress", parents=[common], help="캔버스에 진행 한 줄(접속 칩·대화창)")
    pg.add_argument("text", help="한 줄(200자까지)")
    pg.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    pg.add_argument("--screen", help="화면 id")
    pg.add_argument("--agent", help="누가(기본 env PASEO_AGENT_ID)")
    pg.set_defaults(fn=cmd_progress)
    sc = sub.add_parser("screens", parents=[common], help="화면 목록(id · 제목 · 줄 · 파일 · 자리 · 크기)")
    sc.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    sc.set_defaults(fn=cmd_screens)
    ad = sub.add_parser("add", parents=[common], help="HTML 화면 하나를 캔버스에 넣기(복사 · 등록 · 자리 · 바로 보임)")
    ad.add_argument("file", help="넣을 HTML 파일")
    ad.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    ad.add_argument("--id", help="화면 id(기본 = 파일 이름)")
    ad.add_argument("--title", help="제목(기본 = HTML <title> | id)")
    ad.add_argument("--group", help="줄 이름(없으면 새 줄 · 기본 = --after 의 줄 | 마지막 화면의 줄)")
    ad.add_argument("--purpose", help="목적 한 줄")
    pl = ad.add_mutually_exclusive_group()
    pl.add_argument("--after", help="이 화면 바로 옆에(같은 줄 · 그 화면이 옮긴 거리 · 크기를 따름)")
    pl.add_argument("--at", help="제 자리에서 옮긴 거리 DX,DY(판 px, hd screens 의 '자리' 와 같은 값 · 음수는 --at=-200,40)")
    ad.add_argument("--size", help="카드 크기: 프리셋 이름(Desktop · iPhone 16 …) 또는 WxH")
    ad.add_argument("--asset", action="append", help="같이 복사할 파일(여러 번) — 화면 폴더 안이면 그 상대 경로로, 아니면 이름만")
    ad.add_argument("--replace", action="store_true", help="같은 id 화면·같은 이름 파일을 바꿈")
    ad.set_defaults(fn=cmd_add)
    pa = sub.add_parser("parts", parents=[common], help="앱 부품(out/parts.json) 보기 — 낡음 · 미커밋 변경 포함")
    pk = pa.add_mutually_exclusive_group()
    pk.add_argument("--check", nargs="?", const="*", default=None, metavar="FILE", help="보기만(기본) — FILE = 부품 파일·이름")
    pa.add_argument("target", nargs="?", help="이름 또는 out 경로(떠 있는 것이 하나면 생략)")
    pa.set_defaults(fn=cmd_parts, rebuild=None)
    hm = sub.add_parser("home", parents=[common], help="홈(모든 캔버스) 허브 띄우기 · 바탕 화면 바로 가기")
    hm.add_argument("--no-browser", action="store_true", help="브라우저를 열지 않음")
    hm.add_argument("--shortcut", action="store_true", help="바탕 화면에 바로 가기를 쓰고 끝")
    hm.add_argument("--desktop", help="바로 가기를 쓸 폴더(기본 사용자 바탕 화면)")
    hm.add_argument("--restart", action="store_true", help="떠 있는 허브를 끄고 지금 코드로 다시 띄움(같은 포트)")
    hm.add_argument("--port", type=int, default=None, help="허브 포트(기본 env HD_HUB_PORT | 12270, 막혔으면 빈 포트, 0 = 아무 빈 포트)")
    hm.set_defaults(fn=cmd_home)
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
    except S.HdError as e:
        if a.json:
            print(json.dumps(e.as_dict(), ensure_ascii=False))
        print("hd: %s" % e.line(), file=sys.stderr)
        return e.code
    print(json.dumps(data, ensure_ascii=False, indent=1) if a.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
