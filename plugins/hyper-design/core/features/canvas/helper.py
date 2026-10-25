"""로컬 도우미 — 캔버스 편집을 화면 파일에 바로 쓴다 (docs/eungshin/canvas-edit-plan-2026-10-19.md 7단계, 결정 8B).

python3 helper.py <out> [--port 0] [--paseo-agent ID] [--no-open]

- 포트(#270): --port 가 없으면 <out>/.hd-helper.json 의 지난 포트를 먼저, 막혔으면 빈 포트(한 줄 남김) — 주소가 같아야 캔버스 localStorage 가 이어진다.
- 한 out 에 하나(#271): .hd-helper.json 의 pid 가 살아 있고 그 주소가 답하면 띄우지 않고 종료 코드 1. 죽은 pid 면 덮어쓴다.
  .hd-helper.json = 떠 있는 동안 {url, pid, port, token} · 정상 종료 뒤 {port}.
- 읽기(GET /api/state · index.html 스냅숏)는 빌드 자물쇠를 기다리지 않는다(쓰기가 임시 파일 + os.replace) — 쓰기만 하나씩.
- 127.0.0.1 에만 열고, 실행마다 새 토큰을 만든다. 출력한 주소(…/index.html?hd=<토큰>)로 캔버스를 열면 '보내기'가 도우미를 쓴다.
- 쓰는 곳은 <out> 안뿐이다. 쓰기 전에 원본을 <out>/.hd-history/<시각>/ 에 남기고, 쓴 뒤 build_canvas.py 로 캔버스를 다시 만든다(실패하면 원본으로 되돌림).
- 바로 쓰는 편집(결정형): 글자(text — 요소 안 내용 전부, '' = 비우기) · 요소 지우기(remove) · 요소 복제(duplicate)·위/아래로 옮기기(move, op up|down — task 49a) · 카드 이름(title) · 설명(purpose) · 정책 목록(policies, task 31) · 옛 정책 줄(policy, index) · 잇기/도착 바꾸기(link) · 끊기/트리거 해제(cut).
  나머지 메모(질문, 새 화면, 도착 없는 트리거 지정 등)는 요청문 그대로 <out>/.hd-queue/<시각>.txt 대기열 파일에 쓰고,
  --paseo-agent 가 있으면 그 파일을 `paseo send <agent> --prompt-file … --no-wait` 로 그 에이전트 터미널에 넣는다
  (없으면 터미널에서 /hyper-design:fix 에 그 내용을 붙여 넣는다).
- 도우미가 꺼져 있으면 캔버스는 지금처럼 요청문을 복사한다.

- 정리(#281): 시작·쓰기마다 가장 새 200개 밖 + 30일 넘은 .hd-history/<stamp>/, 보냄·걷힘 표시(.sent·.lifted) 붙은 7일 넘은 .hd-queue 파일(prune).
- 다시 빌드: CLI(main)는 build_ref.py(hd open 과 같음 — git HEAD, #278), 같은 프로세스 테스트는 build_canvas.py.
- 쓰기마다 <out>/.hd-history/<stamp>/manifest.json = {files:{relpath:{before, after_sha}}, changed} — 되살리기는 그 뒤 파일이 안 바뀌었을 때만.

API (모두 POST, JSON, 머리글 X-HD-Token 필수 · Host 는 127.0.0.1/localhost 의 그 포트만)
  /api/apply   {edits:[{id, screen, edit, path, value?, to?}]} → {applied:[id], failed:[{id, reason}], stamp, changed:[screen]}
    edit: text(value — 요소 안 글·인라인 자식 전부를 바꿈, 안에 블록 자식이면 거절) · remove(요소 통째로, html·body·화면 뿌리 거절) · title · purpose
      · duplicate(바로 뒤에 복사본, 복사본 안 id·data-region 뺌) · move(op up|down — 앞·뒤 형제와 원문 조각 맞바꿈, 끝이면 거절)
      · attr(op = 속성 이름, value — 허용 목록 ATTR_OK 만, on*·style·javascript: 거절) · insert·replace(value = 부품 key — 뼈대는 specimen_parts 가 out/components.html 에서, task 49b)
      · 답 paths = {id: 그 요소의 새 경로}(그 화면에 요소 편집 하나일 때 — 캔버스가 쓴 뒤 같은 요소를 다시 고른다)
      · policies(value = [글] — 화면의 policies 를 통째로 바꿈, 글 목록·50줄·줄마다 500자 아니면 거절) · policy(옛 메모: index, op delete) · link · reason = 한국어
  /api/delete  {screens:[id]}                                 → {deleted:[id], cut:[{screen, path, to}], failed, stamp, changed:[screen]}
  /api/restore {stamp}                                        → {restored:[relpath], changed:[screen]} | 409 {error, reason:'changed-since'}
  /api/data    {}                                             → board_data.index_data (index.html 의 hd-data 와 같은 객체)
  /api/forward {text}                                         → {via:'paseo'|'queue', agent?, path?}
  /api/watch   {files:[relpath]}                              → {mtimes:{relpath: mtime|null}} (없거나 out 밖이면 null)
  GET /api/state[?since=rev]                                  → {rev, state} (<out>/.hd-canvas.json, 없으면 rev 0) · since == rev 면 {rev, unchanged:true}(#273)
  PUT /api/state {rev, state:{이름: 값|null}}                 → {rev} | 409 {rev, state}(rev 가 다름) · 400(JSON 아님) · 413 {error: 크기 + "완료 메모를 보관으로 옮기세요"}
  POST /api/archive {notes:[…]}                               → {ok:true, count} — <out>/.hd-notes-archive.jsonl 에 메모마다 한 줄(임시 파일 + os.replace, 자물쇠 안) · 400
  GET /api/archive                                            → {notes:[…]} (마지막 2000 줄, 새것이 뒤)
  GET /api/parts                                              → {parts:[{key, title, ok}]} (out/components.html 의 견본, ok = 뼈대를 뽑을 수 있음) · 없으면 {parts:[], error}
  POST /api/reply {note: id | {screen, no}, reply:{kind, …칸, detail?, by?}} → {rev, status} · 400 {error, errors:[칸마다 한 줄]} · 404(없는 메모)
    — 답 규칙은 ../hd/hd_model.py(tasks/PLAN-2026-10-23.md §3). 늘 최신 파일에 붙이고 rev+1(rev 를 받지 않는다). by 기본 'agent', at = 지금.
  POST /api/stop {}                                           → {stopping:true} 를 답한 뒤 서버를 정상 종료(표지 지움 · .hd-helper.json 은 {port} 만 남김) — `hd stop`
  POST /api/attach {agent: id|null}                           → {agent} — /api/forward 가 보낼 Paseo 에이전트를 바꾸고 표지의 agent 를 고쳐 씀(다시 띄우지 않음).
    id = 빈 글 아님·128자 이하·띄어쓰기 없음(hd_model.agent_error), 아니면 400 · null = 떼기(대기열 파일로) — `hd attach`
  GET /api/projects                                           → `hd projects --json` 과 같은 줄 [{name, out, state: running|off|missing, url, pid, last_opened}]
  POST /api/open {name, agent?}                               → {name, out, url, pid, agent, reused} — `hd open` 과 같은 hd_client.open_project(브라우저 없음).
  GET /api/projects · POST /api/open · /api/new · /api/project · /api/forget · /api/reveal · GET·PUT /api/tabs · GET /api/home
    = home/home_api.route(허브와 같은 JSON — 규칙은 home/contract.md). /api/home 은 허브를 띄우거나 그 주소 {url}
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

코드 도장(code_stamp.py): 뜰 때 build_ref.code_stamp() 를 표지·.hd-helper.json 의 code 에 적는다(이 프로세스 안 Python 의 판) —
  hd open·허브가 지금 도장과 견줘 옛 코드 도우미를 (쉬면) 끄고 새로 띄운다. 페이지를 줄 때마다 index.html 의 도장도 견줘 옛것이면 다시 빌드.

구조(task 47-2): 이 파일 = CLI(main) · make_server(out 하나 서버) · 예전 이름 다시 내보내기.
  html_edit.py(Model — HTML 원문 고치기) · session.py(ProjectSession 과 부품: StateStore · History · Queue · Busy · Archive · Builder)
  · router.py(Router — 주소 → 세션 메서드, SessionHandler — 토큰·Host·크기 검사와 오류 모양)
"""

import argparse, atexit, json, os, pathlib, signal, subprocess, sys, threading, webbrowser  # noqa: F401 — subprocess: 예전 이름(helper.subprocess)
from http.server import ThreadingHTTPServer

import build_canvas  # noqa: F401  — 예전 이름(helper.build_canvas)
import build_ref
import html_edit
import router as R
import safe_port
import session as S
from html_edit import *  # noqa: F401,F403  — 예전 이름(helper.select · edit_html · edit_one · Tree …)
from html_edit import (_after, _attr_patch, _block_ok, _dup_patch, _end, _has_text, _inline_only, _insert_patch, _is_root, _lead,  # noqa: F401
                       _link_to, _move_patch, _op_patch, _part, _patch, _path_of, _relink, _remove_patch, _replace_patch, _seg_ok,
                       _set_attr, _strip_ids, _text_patch, _unesc)
from session import (AGENTS_TTL, ARCHIVE_FILE, NO_PASEO, NO_WINDOW, PASEO_DEFAULT, POLICY_MAX_CHARS, POLICY_MAX_LINES,  # noqa: F401
                     REPLACE_TRIES, STATE_FILE, STATE_MAX, WATCH_EVERY, FileWatch, ProjectSession, _inside, _now, _parts_html,
                     _paseo_args, _paseo_cmd, _policies, _replace, _screen_files, _sha, _stamp, _state_ok, _state_save, _state_write,
                     _write_json, _Writes, agents_get, archive_get, archive_post, claim_post, keypath, list_agents, parts_of,
                     project_repo, prune, release_post, reply_post, scan, state_inject, state_load, state_peek, state_put, watch)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_model  # noqa: E402
import hd_client  # noqa: E402  — 프로젝트 목록(링크) 쓰기는 CLI 와 같은 Client 하나로
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "home"))
import home_api  # noqa: E402
import home_client  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE / "build_canvas.py"
BUILD_REF = HERE / "build_ref.py"                    # hd open 과 같은 빌더 — 저장소면 git HEAD 코드로(#278), 아니면 작업 트리
CODE = None                                          # 이 도우미가 뜬 코드 도장(main 이 잰다 — 같은 프로세스 테스트는 None)
BUILDER = BUILD                                      # 다시 빌드에 쓰는 것 — CLI(main)는 use_ref_build() 로 BUILD_REF. 같은 프로세스에서 make_server 를 쓰는 테스트는 작업 트리
VOID = html_edit.VOID


def use_ref_build():
    """CLI 로 뜬 도우미(실사용)는 hd open 과 같은 build_ref.py 로 다시 빌드한다 — 다른 세션이 고치는 중인 작업 트리가 떠 있는 캔버스에 들어가지 않게(#278)."""
    global BUILDER
    BUILDER = BUILD_REF


def _build(out):
    return S.run_build(out, BUILDER)


def _run(out):                                       # 세션·아래 함수가 부르는 빌드 — 부를 때마다 helper._build 를 찾는다(테스트가 바꿔 끼움)
    return _build(out)


def apply_edits(out, edits, stamp=None):
    return S.apply_edits(out, edits, stamp, build=_run)


def delete_screens(out, ids, stamp=None):
    return S.delete_screens(out, ids, stamp, build=_run)


def restore(out, stamp):
    return S.restore(out, stamp, build=_run)


def forward(out, text, agent=None, paseo=None):
    return S.forward(out, text, agent, paseo)


# ---------------------------------------------------------------- 서버(out 하나)
class Server(ThreadingHTTPServer):
    """out 하나를 내는 서버 — srv.session(ProjectSession). 예전 칸(srv.agent · agents_cache · repo · watch · token)은 세션 부품으로 넘긴다."""
    allow_reuse_address = sys.platform != "win32"     # Windows 의 SO_REUSEADDR 는 쓰는 중인 포트도 다시 연다 — 지난 포트가 막혔는지 알아야 한다(#270)

    def server_close(self):
        if getattr(self, "session", None) is not None:   # 열기에 실패하면 socketserver 가 make_server 가 칸을 달기 전에 부른다
            self.session.close()
        super().server_close()

    agent = property(lambda s: s.session.queue.agent, lambda s, v: setattr(s.session.queue, "agent", v))
    agents_cache = property(lambda s: s.session.queue.agents_cache, lambda s, v: setattr(s.session.queue, "agents_cache", v))
    agents_lock = property(lambda s: s.session.queue.agents_lock)
    repo = property(lambda s: s.session.queue.repo, lambda s, v: setattr(s.session.queue, "repo", v))
    watch = property(lambda s: s.session.busy.watch)
    watch_stop = property(lambda s: s.session.busy.stop)
    token = property(lambda s: s.session.token)


def make_server(out, port=0, agent=None, paseo=None, token=None):
    out = pathlib.Path(out).resolve()
    holder = {}
    sess = ProjectSession(out, token, agent, paseo, build=_run,
                          on_attach=lambda a: holder["srv"].marker is not None and marker_agent(holder["srv"].marker, a))
    sess.open()
    home_ctx = home_api.Ctx(hub=False, agent=lambda: sess.queue.agent, port=home_client.hub_port, picker=home_client.pick_folder)   # 폴더 열기 — 캔버스 선택 창도
    router = R.Router(home_ctx=home_ctx, on_stop=lambda: threading.Thread(target=holder["srv"].shutdown, daemon=True).start())   # serve_forever 를 돌리는 쪽이 정리(표지 지움)

    class H(R.SessionHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(out), **k)

        def target(self, path):
            return sess, path

    H.router = router
    srv = bind(H, [port] if isinstance(port, int) else list(port))
    holder["srv"] = srv
    srv.session = sess.start()
    srv.home_ctx = home_ctx
    srv.marker = None                                   # main 이 표지 경로를 넣는다(attach 가 agent 를 고쳐 씀)
    srv.url = "http://127.0.0.1:%d/index.html?hd=%s" % (srv.server_address[1], sess.token)
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
            return safe_port.open_server(Server, "127.0.0.1", port, handler)   # 빈 포트가 브라우저가 막는 포트면 다시
        except OSError as e:
            if i == len(ports) - 1:
                raise
            print("[hd] 지난번 포트 %d 를 쓸 수 없어 새 포트로 띄워요(%s) — 캔버스 주소가 바뀌어 창 설정이 처음으로 돌아가요" % (port, e),
                  file=sys.stderr, flush=True)


def open_post(body, agent=None):
    """POST /api/open 본문 {name, agent?} → (code, 답). 본체는 home_api.open_post(허브와 같은 것)."""
    return home_api.open_post(body, agent)


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
                             "started": _now(), "code": CODE}, ensure_ascii=False), encoding="utf-8")
    return p


RUN_FILE = ".hd-helper.json"                         # 주인 = 이 파일. 읽는 쪽: hd_client.read_record · skills go/fix


def start_check(out):
    """시작 전(#271) → (지난 포트 | None, 살아 있는 도우미 표지 | None). 표지가 있으면 같은 out 의 둘째 도우미가 되므로 띄우지 않는다."""
    rec = hd_client.read_record(out)                 # 없음·깨짐 = None(깨졌으면 [hd] 한 줄, 덮어쓴다)
    return (rec or {}).get("port"), hd_client.live_record(out, rec) if rec else None


def write_run(run, srv):
    run.write_text(json.dumps({"url": srv.url, "pid": os.getpid(), "port": srv.server_address[1], "token": srv.token, "code": CODE}),
                   encoding="utf-8")


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
    global CODE
    use_ref_build()                                  # 실사용: hd open 과 같은 빌더(#278)
    CODE = build_ref.code_stamp()                    # 이 프로세스가 뜬 코드 — 표지에 적어 옛 도우미를 알아보게
    out = pathlib.Path(a.out).resolve()
    if not (out / "index.html").is_file() or not (out / "screens.json").is_file():
        sys.exit("index.html · screens.json 이 있는 out 폴더가 아니에요: %s" % out)
    last, live = start_check(out)
    if live:
        sys.exit("이 out 은 이미 도우미가 떠 있어요(pid %s): %s — 그 주소를 쓰거나 `hd stop` 으로 끈 뒤 다시 띄우세요" % (live["pid"], live["url"]))
    srv = make_server(out, port_order(last, a.port), a.paseo_agent, a.paseo_cmd)
    srv.session.code = build_ref.code_stamp          # 페이지를 줄 때 지금 코드와 견줌(옛 도장 index.html 이면 다시 빌드)
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


def attach_post(srv, body, lock=None):
    """POST /api/attach 본문 {agent: id|null} → (code, 답) — 예전 이름(본체는 session.Queue.attach)."""
    return srv.session.queue.attach(body)


if __name__ == "__main__":
    main()
