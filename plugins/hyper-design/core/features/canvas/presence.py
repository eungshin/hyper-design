"""Model + 상태 주인 — 프로젝트 하나에 접속한 에이전트(AgentPresence, task 47-5a): hello(임대) · 맥박 · 임대 끝 = away · bye · 진행 한 줄.

순수 규칙(check_hello · lease_of · beat_of · check_progress · sweep_plan · public)은 시계·파일·네트워크를 모른다(unit 테스트).
AgentPresence = 에이전트 표(id → 항목) 하나의 주인 — 자물쇠 하나, 시계(clock, 초)와 알림(publish = 세션 EventBus.publish)은 받는다.
바깥 모양 = tests/protocol/presence.json(agent · lease) · 이벤트 agent.hello · agent.away · agent.progress(events.json).
쓰는 곳: send_queue.Queue(보낼 곳 고르기 — get) · session 의 Ticker(1초마다 sweep) · router(/hello · /beat · /bye · /progress · /agents).
"""
import pathlib, sys, threading, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_model  # noqa: E402  — 에이전트 id 규칙 하나(hd attach 와 같음)

KINDS = ("paseo", "claude", "codex", "other")
LEASE, LEASE_MIN, LEASE_MAX = 30, 1, 300             # 초 — 맥박 없이 here 로 두는 시간(요청은 이 사이로 자름)
AWAY_KEEP = 3600                                     # away 를 목록에 두는 시간(초), 지나면 잊음
MAX_AGENTS = 32                                      # 프로젝트 하나에 아는 에이전트 수
NAME_MAX, TEXT_MAX, SCREEN_MAX, SESSION_MAX, CWD_MAX = 60, 200, 80, 128, 1024
UNKNOWN = "모르는 에이전트예요: %s — hello 를 먼저 보내세요"


def _id_error(v):
    if v is None:
        return "id 가 없어요"
    return hd_model.agent_error(v)


def lease_of(v):
    """요청한 임대(초) → LEASE_MIN..LEASE_MAX 정수(반올림). 없으면 LEASE."""
    if v is None:
        return LEASE
    return max(LEASE_MIN, min(LEASE_MAX, int(round(v))))


def beat_of(lease):
    """권하는 맥박 간격(초) = 임대의 1/3 — 맥박 하나를 놓쳐도 away 가 되지 않게."""
    return lease / 3


def check_hello(body):
    """POST /hello 본문 → (who{id, name, kind, pid, listen, session, cwd}, lease, None) | (None, None, 한국어 오류).
    cwd = 에이전트의 작업 폴더(claude 대화 기록을 찾는 projects 폴더 하나 — transcripts.py). 밖으로 내지 않는다(public)."""
    if not isinstance(body, dict) or not isinstance(body.get("agent"), dict):
        return None, None, "agent: 없어요({agent: {id, name?, kind?, pid?, listen?}})"
    a = body["agent"]
    err = _id_error(a.get("id"))
    if err:
        return None, None, err
    name = a.get("name", a["id"])
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > NAME_MAX:
        return None, None, "agent.name: 1–%d자 글이어야 해요" % NAME_MAX
    kind = a.get("kind", "other")
    if kind not in KINDS:
        return None, None, "agent.kind: %s 중 하나여야 해요" % "|".join(KINDS)
    pid = a.get("pid")
    if pid is not None and (type(pid) is not int or pid <= 0):
        return None, None, "agent.pid: 양의 정수여야 해요"
    listen = a.get("listen", True)
    if type(listen) is not bool:
        return None, None, "agent.listen: true/false 여야 해요"
    session = a.get("session")
    if session is not None and (not isinstance(session, str) or not session or len(session) > SESSION_MAX or any(c.isspace() for c in session)):
        return None, None, "agent.session: 띄어쓰기 없는 1–%d자 글이어야 해요" % SESSION_MAX
    cwd = a.get("cwd")
    if cwd is not None and (not isinstance(cwd, str) or not cwd.strip() or len(cwd) > CWD_MAX or any(ord(c) < 32 for c in cwd)):
        return None, None, "agent.cwd: 1–%d자 폴더 경로 글이어야 해요" % CWD_MAX
    lease = body.get("lease")
    if lease is not None and (type(lease) not in (int, float)):
        return None, None, "lease: 초(숫자)여야 해요"
    who = {"id": a["id"], "name": name.strip(), "kind": kind, "pid": pid, "listen": listen, "session": session, "cwd": cwd}
    return who, lease_of(lease), None


def check_progress(body):
    """POST /progress 본문 → ((agent|None, text, screen|None), None) | (None, 한국어 오류). 글은 앞뒤 빈칸을 자른다."""
    if not isinstance(body, dict):
        return None, "{text, screen?, agent?} 가 아니에요"
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        return None, "text: 비었어요"
    text = text.strip()
    if len(text) > TEXT_MAX:
        return None, "text: %d자를 넘어요" % TEXT_MAX
    screen = body.get("screen")
    if screen is not None and (not isinstance(screen, str) or not screen or len(screen) > SCREEN_MAX):
        return None, "screen: 화면 id 글이어야 해요"
    agent = body.get("agent")
    if agent is not None:
        err = _id_error(agent)
        if err:
            return None, err
    return (agent, text, screen), None


def sweep_plan(agents, now_ms):
    """에이전트 표 → (away 로 바꿀 id들 — here 이고 seen + 임대 < 지금, 잊을 id들 — away 이고 AWAY_KEEP 지남). 차례 = 표 차례."""
    away = [k for k, e in agents.items() if e["state"] == "here" and now_ms > e["seen"] + e["lease"] * 1000]
    forget = [k for k, e in agents.items() if e["state"] == "away" and now_ms > e["seen"] + AWAY_KEEP * 1000]
    return away, forget


PUBLIC = ("id", "name", "kind", "pid", "state", "listen", "since", "seen", "lease", "progress")


def public(e):
    """밖으로 내는 모양(presence.json agent) — claude 이어 받기 session 은 내지 않는다."""
    return {k: (dict(e[k]) if k == "progress" and e[k] else e[k]) for k in PUBLIC}


class AgentPresence:
    """에이전트 표의 주인. publish(type, **data) → 이벤트(dict, id 있음) | None. clock() = 초(기본 time.time)."""

    def __init__(self, publish=None, clock=time.time):
        self.publish, self.clock = publish or (lambda *a, **k: None), clock
        self.agents = {}
        self.lock = threading.Lock()

    def _now(self):
        return int(self.clock() * 1000)

    def get(self, aid):
        """id → 항목 사본(session 포함 — 어댑터가 씀) | None."""
        with self.lock:
            e = self.agents.get(aid)
            return dict(e) if e else None

    def list(self):
        with self.lock:
            return {"agents": [public(e) for e in self.agents.values()], "lease": LEASE}

    def _answer(self, e, first):
        return {"agent": public(e), "lease": e["lease"], "beat": beat_of(e["lease"]), "first": first}

    def _arrive(self, e, now):                       # 처음 · away 에서 돌아옴 → here + agent.hello
        e.update(state="here", since=now, seen=now)
        self.publish("agent.hello", agent=public(e))

    def hello(self, body):
        who, lease, err = check_hello(body)
        if err:
            return 400, {"error": err}
        now = self._now()
        with self.lock:
            e = self.agents.get(who["id"])
            if e is None:
                if len(self.agents) >= MAX_AGENTS:
                    gone = sorted((x for x in self.agents.values() if x["state"] == "away"), key=lambda x: x["seen"])
                    if not gone:
                        return 400, {"error": "이 프로젝트에 접속한 에이전트가 너무 많아요(%d) — 안 쓰는 터미널을 닫으세요" % MAX_AGENTS}
                    del self.agents[gone[0]["id"]]
                e = self.agents[who["id"]] = dict(who, state="away", since=now, seen=now, lease=lease, progress=None)
            else:
                e.update(who, lease=lease)
            first = e["state"] != "here"
            if first:
                self._arrive(e, now)
            else:
                e["seen"] = now
            return 200, self._answer(e, first)

    def _known(self, body):
        if not isinstance(body, dict):
            return None, (400, {"error": "{id} 가 아니에요"})
        err = _id_error(body.get("id"))
        if err:
            return None, (400, {"error": err})
        e = self.agents.get(body["id"])
        if e is None:
            return None, (404, {"error": UNKNOWN % body["id"], "reason": "unknown"})
        return e, None

    def beat(self, body):
        """맥박 {id} — here 면 seen 만, away 면 돌아옴(agent.hello, first true). 모르는 id = 404 unknown(hello 를 다시)."""
        now = self._now()
        with self.lock:
            e, bad = self._known(body)
            if bad:
                return bad
            first = e["state"] != "here"
            if first:
                self._arrive(e, now)
            else:
                e["seen"] = now
            return 200, self._answer(e, first)

    def bye(self, body):
        with self.lock:
            e, bad = self._known(body)
            if bad:
                return bad
            if e["state"] == "here":
                e["state"] = "away"
                self.publish("agent.away", agent=e["id"], name=e["name"], reason="bye")
            return 200, {"agent": public(e)}

    def progress(self, body):
        """진행 한 줄 → agent.progress. agent 를 주면 그 에이전트의 맥박도 된다(모르는 id = 404)."""
        got, err = check_progress(body)
        if err:
            return 400, {"error": err}
        aid, text, screen = got
        now = self._now()
        with self.lock:
            if aid is not None:
                e = self.agents.get(aid)
                if e is None:
                    return 404, {"error": UNKNOWN % aid, "reason": "unknown"}
                if e["state"] != "here":
                    self._arrive(e, now)
                e["seen"], e["progress"] = now, {"text": text, "screen": screen, "at": now}
            ev = self.publish("agent.progress", agent=aid, text=text, screen=screen)
        return 200, {"event": ev["id"] if ev else None}

    def sweep(self):
        """임대가 끝난 here → away(agent.away reason lease) · 오래된 away 잊기 → away 로 바꾼 id들. Ticker 가 1초마다."""
        now = self._now()
        with self.lock:
            away, forget = sweep_plan(self.agents, now)
            for k in away:
                e = self.agents[k]
                e["state"] = "away"
                self.publish("agent.away", agent=k, name=e["name"], reason="lease")
            for k in forget:
                del self.agents[k]
        return away
