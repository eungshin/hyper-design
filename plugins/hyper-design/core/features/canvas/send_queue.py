"""Edge — 보낸 메모(#214 · 47-5a): 보낼 곳(agent · Paseo 목록 5초 캐시 · 저장소) · 요청문 대기열 파일 <out>/.hd-queue + 받는 곳 고르기 · 에이전트 답(reply).

상태: 붙은 에이전트(agent) · Paseo 목록 캐시(agents_cache) · 어댑터 셋 — 주인 = Queue. 대기열 파일은 늘 쓴다(어디로 보내든 기록).
받는 곳(adapters.choose): 접속 중이고 이벤트를 읽는 에이전트 = request.sent 이벤트(터미널 없음) · 아니면 어댑터(paseo · claude · queue).
부르는 곳: session.ProjectSession(Queue) · router(/api/forward · /api/agents · /api/attach · /api/reply) · helper(예전 이름 forward · list_agents …).
오류 탐지: paseo 가 없거나 실패하면 {agents:[], error:한국어} · 넘기기 실패는 [hd] 한 줄 뒤 대기열 파일로 · 모양이 틀린 본문은 400, 없는 메모는 404.
"""
import datetime, json, os, pathlib, shutil, subprocess, sys, threading, time

import adapters as AD  # 받는 곳 고르기 · Paseo/Claude/None 어댑터(task 47-5a)
import attach_rules as AR  # 요청 글의 '첨부 이미지:' 경로 · 보낼 이미지 고르기(R28)
import chat_log as CL  # 답 글(reply_text — 대화 패널)
import events as EV  # 바뀐 것 알림(request.sent · notes.changed · agent.reply)
from adapters import _paseo_args, _paseo_cmd
from out_io import _now  # out_io 가 hd 폴더를 sys.path 에 넣는다
from state_store import _state_save, state_load

import hd_model  # noqa: E402  — 답 검사 · 메모 찾기 · 에이전트 id 검사

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: paseo 가 콘솔 창을 띄웠다 닫지 않게


def _str(v):
    return v if isinstance(v, str) else None


def queue_file(out, text):
    """요청문 대기열 파일 <out>/.hd-queue/<stamp>.txt 하나(늘 씀 — 어디로 보내든 기록) → 경로."""
    q = pathlib.Path(out).resolve() / ".hd-queue"
    q.mkdir(exist_ok=True)
    p = q / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
    p.write_text(text, encoding="utf-8")
    return p



def mark_sent(p):                                    # 보냄 표시 — 7일 뒤 정리(#281). 어댑터(paseo·claude)가 받았을 때만
    try:
        p.with_suffix(".sent").write_text("", encoding="utf-8")
    except OSError as e:
        print("[hd] 대기열 보냄 표시를 쓰지 못했어요(%s): %s" % (e, p), file=sys.stderr, flush=True)



def forward(out, text, agent=None, paseo=None):
    """결정형이 아닌 메모 → 터미널(옛 이름 — 받는 곳 고르기는 Queue.send). 늘 대기열 파일에 쓰고, Paseo 에이전트가 있으면 PaseoAdapter(paseo send)로 넘긴다."""
    p = queue_file(out, text)
    if agent and AD.PaseoAdapter(lambda: _paseo_cmd(paseo)).send(p, text, agent)[0]:
        mark_sent(p)
        return {"via": "paseo", "agent": agent, "path": str(p)}
    return {"via": "queue", "path": str(p)}



AGENTS_TTL = 5.0                                     # GET /api/agents 답을 이만큼(초) 다시 쓴다 — 메뉴를 열 때마다 paseo 를 띄우지 않게



NO_PASEO = "Paseo 를 찾을 수 없어요"



def list_agents(paseo=None):
    """`paseo ls -g --json`(읽기만) → {agents:[{id, name, status, cwd, provider, thinking}]} | {agents:[], error:한국어}(thinking = 생각 깊이, R28).
    보관(archived)된 것은 뺀다. 출력은 바이트로 받아 UTF-8 로 푼다(Windows 기본 코드 페이지로 풀면 한글 이름이 깨진다)."""
    cmd = _paseo_cmd(paseo)
    if not cmd or (("/" in cmd or "\\" in cmd) and not pathlib.Path(cmd).exists()):
        return {"agents": [], "error": NO_PASEO}
    try:
        r = subprocess.run(_paseo_args(cmd, ["ls", "-g", "--json"]), capture_output=True, timeout=30, creationflags=NO_WINDOW,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1"))
    except FileNotFoundError:
        return {"agents": [], "error": NO_PASEO}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요: %s" % e}
    if r.returncode != 0:
        why = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요" + (": " + why[-1][:200] if why else " (종료 코드 %d)" % r.returncode)}
    try:
        rows = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return {"agents": [], "error": "Paseo 목록이 JSON 이 아니에요"}
    if not isinstance(rows, list):
        return {"agents": [], "error": "Paseo 목록이 목록이 아니에요"}
    agents = []
    for a in rows:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"]:
            continue
        if a.get("archived") or a.get("status") == "archived" or a.get("archivedAt"):
            continue
        agents.append({k: (a.get(k) if isinstance(a.get(k), str) else None) for k in ("id", "name", "status", "cwd", "provider", "thinking")})
    return {"agents": agents}



def project_repo(out):
    """이 캔버스의 저장소 뿌리 — 앱 프로젝트면 app.json 의 repo, 아니면 out 위로 처음 만나는 .git 이 있는 폴더. 없으면 None."""
    out = pathlib.Path(out).resolve()
    try:
        app = json.loads((out / "app.json").read_text(encoding="utf-8"))
        if isinstance(app, dict) and isinstance(app.get("repo"), str) and app["repo"]:
            return str(pathlib.Path(app["repo"]))
    except (OSError, ValueError):
        pass                                          # app.json 이 없거나 깨짐 = 정적 프로젝트로 본다
    for d in [out] + list(out.parents):
        if (d / ".git").exists():
            return str(d)
    return None



def agents_get(srv, paseo, now=None, auto=False):
    """GET /api/agents[?auto=1] → {agents, current, repo, error?}. paseo 목록은 AGENTS_TTL 동안 다시 쓴다(current 는 늘 지금 값).
    auto = 캔버스가 열 때 자동으로 고를지 묻는 것 — 이미 붙어 있거나 저장소를 모르면 paseo 를 띄우지 않고 {agents:[], skipped:true}."""
    if auto and (srv.agent or not srv.repo):
        return {"agents": [], "current": srv.agent, "repo": srv.repo, "skipped": True}
    t = time.monotonic() if now is None else now
    with srv.agents_lock:
        hit = srv.agents_cache
        if hit is None or t - hit[0] >= AGENTS_TTL:
            hit = srv.agents_cache = (t, list_agents(paseo))
    connected = srv.presence.list()["agents"] if getattr(srv, "presence", None) is not None else []   # 47-5a: 접속한 에이전트(AgentPresence)
    return dict(hit[1], current=srv.agent, repo=srv.repo, connected=connected)



def reply_post(out, body):
    """POST /api/reply 본문 {note: id | {screen, no}, reply} → (code, 답). 최신 상태 파일의 그 메모 replies 에 붙이고 rev+1."""
    if not isinstance(body, dict) or not isinstance(body.get("reply"), dict):
        return 400, {"error": "{note, reply: {kind, …}} 가 아니에요", "errors": ["reply: 객체가 아니에요"]}
    ref = body.get("note")
    if isinstance(ref, dict):
        if not isinstance(ref.get("screen"), str) or type(ref.get("no")) is not int:
            return 400, {"error": "note: {screen: 글, no: 정수} 또는 메모 id", "errors": ["note: {screen, no} 모양이 아니에요"]}
    elif not isinstance(ref, str) or not ref:
        return 400, {"error": "note: 메모 id 또는 {screen, no}", "errors": ["note: 없어요"]}
    cur = state_load(out)
    notes = cur["state"].get("notes")
    notes = notes if isinstance(notes, list) else []
    i = hd_model.find(notes, ref, cur["state"].get("note-seq"))
    if i is None:
        return 404, {"error": "없는 메모: %s" % (ref if isinstance(ref, str) else "%s#%s" % (ref["screen"], ref["no"]))}
    note = notes[i]
    if not note.get("sent"):
        return 400, {"error": "note: 아직 보내지 않은 메모(draft)에는 답하지 않아요", "errors": ["note: 보내지 않은 메모"]}
    try:
        known = {s["id"] for s in json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("screens", [])}
    except (OSError, ValueError, KeyError, TypeError):
        known = None                                  # screens.json 을 못 읽으면 화면 id 는 모양만 본다
    errs = hd_model.check_reply(body["reply"], note.get("intent"), agent=True, known_screens=known)
    if errs:
        return 400, {"error": "; ".join(errs), "errors": errs}
    note = dict(note, replies=hd_model.replies(note) + [hd_model.stamp(body["reply"], _now())])
    notes = notes[:i] + [note] + notes[i + 1:]
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], notes=notes))
    return 200, {"rev": rev, "status": hd_model.status(note), "note": note.get("id"), "screen": note.get("screen")}




NOTES_MAX = 200                                      # /api/forward notes(메모 id) 개수 한도



def check_send(body):
    """POST /api/forward 본문 {text, to?, notes?, images?} → ((text, to | None, notes, images | None), None) | (None, 한국어 오류).
    images(R28) = 첨부 이미지 절대 경로 글 목록 — 없으면 None(그때는 글의 '첨부 이미지:' 줄에서 읽는다)."""
    to = body.get("to")
    err = hd_model.agent_error(to)
    if err:
        return None, "to: " + err
    notes = body.get("notes", [])
    if not isinstance(notes, list) or len(notes) > NOTES_MAX or not all(isinstance(n, str) and n for n in notes):
        return None, "notes: 메모 id 글 목록(%d개까지)이어야 해요" % NOTES_MAX
    images = body.get("images")
    if images is not None and (not isinstance(images, list) or len(images) > AR.IMAGES_MAX * 2 or not all(isinstance(x, str) and x for x in images)):
        return None, "images: 첨부 이미지 절대 경로 글 목록이어야 해요"
    return (str(body.get("text") or ""), to, list(notes), list(images) if images is not None else None), None



class Queue:
    """보낸 메모 — 보낼 곳(agent, attach 로 바뀜 · Paseo 목록 5초 캐시 · 저장소 repo) · 요청문 보내기(send: 대기열 파일 + 받는 곳 고르기) · 에이전트 답(reply).
    받는 곳(adapters.choose): 접속 중이고 이벤트를 읽는 에이전트 = request.sent 이벤트(터미널 없음) · 아니면 어댑터(paseo · claude · queue).
    칸 이름 agent · repo · agents_cache · agents_lock · presence 는 agents_get 이 읽는다."""

    def __init__(self, out, lock, agent=None, paseo=None, on_attach=None, bus=None, presence=None, config=None):
        self.out, self.lock, self.paseo, self.on_attach, self.bus, self.presence = out, lock, paseo, on_attach, bus, presence
        self.agent = agent or None
        self.repo = project_repo(out)
        self.agents_cache, self.agents_lock = None, threading.Lock()
        cfg = config or {}
        self.adapters = {"paseo": AD.PaseoAdapter(lambda: _paseo_cmd(self.paseo)),
                         "claude": AD.ClaudeCliAdapter(lambda: cfg.get("claude_cmd") or shutil.which("claude"),
                                                       enabled=bool(cfg.get("claude_wake")), cwd=self.repo or str(out)),
                         "queue": AD.NoneAdapter()}

    def forward(self, text):                         # 옛 이름(받는 곳 = 붙은 에이전트, 메모 id 없음)
        return self.send({"text": text})[1]

    def send(self, body):
        """POST /api/forward {text, to?, notes?} → (code, {via, path, agent?, event}). 늘 대기열 파일을 쓰고 request.sent 를 낸다."""
        got, err = check_send(body)
        if err:
            return 400, {"error": err}
        text, to, notes, images = got
        target = to or self.agent
        entry = self.presence.get(target) if (target and self.presence is not None) else None
        how = AD.choose(target, entry, {k: a.ready() for k, a in self.adapters.items()})
        p = queue_file(self.out, text)
        via = how
        if how in ("paseo", "claude"):
            ok, why = self.adapters[how].send(p, text, entry or target, images=self.images(text, images) if how == "paseo" else ())
            if ok:
                mark_sent(p)
            else:
                print("[hd] %s 로 넘기지 못해 대기열 파일로 남겨요(%s): %s" % (how, why, p.name), file=sys.stderr, flush=True)
                via = "queue"
        ev = EV.emit(self.bus, "request.sent", to=target, via=via, notes=notes, text=text, path=str(p))
        res = {"via": via, "path": str(p)}
        if via != "queue":
            res["agent"] = target
        if ev is not None:
            res["event"] = ev["id"]
        return 200, res

    def images(self, text, given=None):
        """보낼 첨부 이미지(R28) — given(본문 images) 또는 글의 '첨부 이미지:' 줄 → <out>/.hd-attach 안 · 규칙 이름 · 있는 파일만.
        뺀 것은 [hd] 한 줄(글의 경로 줄은 그대로 가므로 받는 쪽은 경로로라도 본다)."""
        folder = str((pathlib.Path(self.out) / AR.FOLDER).resolve())
        ok, bad = AR.pick_images(folder, given if given is not None else AR.paths_in(text))
        have = [x for x in ok if pathlib.Path(x).is_file()]
        drop = bad + [x for x in ok if x not in have]
        if drop:
            print("[hd] 첨부 이미지 %d장은 이미지로 넘기지 않아요(.hd-attach 밖·없는 파일·한도): %s" % (len(drop), ", ".join(str(x) for x in drop)[:300]),
                  file=sys.stderr, flush=True)
        return have

    def agents(self, auto=False):
        return agents_get(self, self.paseo, auto=auto)

    def attach(self, body):
        """{agent: id|null} → (code, 답). 받은 agent 를 두고 on_attach(agent)(표지 고쳐 쓰기)."""
        if not isinstance(body, dict) or "agent" not in body:
            return 400, {"error": "agent: 없어요({agent: id 또는 null})"}
        err = hd_model.agent_error(body["agent"])
        if err:
            return 400, {"error": err}
        with self.lock:
            self.agent = body["agent"]
            if self.on_attach:
                self.on_attach(self.agent)
        print("[hd] 보내기 → %s" % (self.agent or "대기열 파일"), file=sys.stderr, flush=True)
        return 200, {"agent": self.agent}

    def reply(self, body):
        with self.lock:
            code, res = reply_post(self.out, body)
            if code == 200:
                EV.emit(self.bus, "notes.changed", rev=res["rev"])
                by = body["reply"].get("by")                # 47-5a: 에이전트가 답했다(캔버스 대화창 · 접속 칩)
                EV.emit(self.bus, "agent.reply", note=_str(res.get("note")), kind=str(body["reply"].get("kind")), screen=_str(res.get("screen")),
                      agent=_str(by), status=res["status"], text=CL.reply_text(body["reply"]))   # text = 대화 패널에 보일 답(S3)
            return code, res
