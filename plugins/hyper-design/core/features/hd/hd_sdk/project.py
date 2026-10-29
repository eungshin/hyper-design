"""Service — Project: 프로젝트 하나(out 폴더 + 그것을 띄운 서버 세션)에 하는 일. notes · reply · claim · release · apply · files · state ·
attach · stop · wait · events(SSE, task 47-4b — wait 도 이벤트로 깨어나고 흐름이 없으면 폴링) ·
접속(task 47-5a): hello(+ 맥박 스레드) · beat · bye · progress · agents · requests(나에게 온 request.sent 만).

상태 = 표지(marker: {pid, project, out, url, token, port, agent, prefix?, hub?}) 하나 | None(파일만 — 도우미 없음). 쓰기는 늘 서버로
(Transport), 읽기는 서버가 있으면 GET /api/state, 없으면 상태 파일(hd_client.read_state). 규칙은 hd_model(답 검사·찾기·덮개·에이전트 id).
오류는 HdError 가족만 — 서버 거절은 errors.from_status, hd_client 오류는 transport.client_errors 가 바꾼다.
"""
import os, pathlib, time
from urllib.parse import quote

import hd_client as C
import hd_model as M

from . import errors as E
from .transport import HttpTransport, client_errors
from . import sse
from .presence import Heartbeat, whoami
from .values import Note, Event

POLL = 2.0
READ = 30.0                                          # 흐름 읽기 timeout(서버 맥박 ': hb' 15초 — 그 두 배 조용하면 다시 붙음)
RETRIES = 3                                          # 연달아 붙지 못하면 Offline(wait 는 폴링으로)
BACKOFF_MAX = 10.0
WAKE = ("open", "notes.changed", "claim", "release", "reset")   # wait 가 상태를 다시 보는 이벤트
KINDS = ("paseo", "claude", "codex", "other")         # 서버 presence.KINDS 와 같게(protocol presence.json)
PROGRESS_MAX = 200
BEAT_MIN = 0.5


def check_claim(screen, by=None, note=None):
    """덮개 칸 검사(서버에 가기 전) — 틀리면 Invalid."""
    err = M.claim_error(screen, by, note)
    if err:
        raise E.Invalid(err)


def check_agent(agent):
    """보낼 에이전트 id 검사 — None = 떼기. 틀리면 Invalid."""
    err = M.agent_error(agent)
    if err:
        raise E.Invalid(err)


class Project:
    def __init__(self, marker=None, out=None, transport=None, finder=None):
        """marker = 살아 있는 표지 | None(out 만 — 읽기만). transport = 가짜를 끼울 자리(기본 HttpTransport(marker)).
        finder(out) → 새 표지 | None = 서버가 다시 떴을 때 다시 찾기(기본 hd_client.serving; 가짜 transport 면 쓰지 않음)."""
        if marker is None and out is None:
            raise ValueError("marker 나 out 이 있어야 해요")
        self.marker = marker
        self.out = pathlib.Path(out if out is not None else marker["out"])
        self._own_transport = transport is None
        self.transport = transport if transport is not None else (HttpTransport(marker) if marker else None)
        self.finder = finder if finder is not None else (C.serving if self._own_transport else (lambda out: None))
        self.me, self.heartbeat, self._hello_body = None, None, None   # 47-5a: hello 한 에이전트 id · 맥박 · 다시 보낼 hello 몸통

    # ------------------------------------------------------------ 누구
    @property
    def online(self):
        return self.marker is not None

    @property
    def name(self):
        return (self.marker or {}).get("project") or M.project_name(self.out.name, self.out.parent.name)

    @property
    def url(self):
        return (self.marker or {}).get("url")

    @property
    def agent(self):
        return (self.marker or {}).get("agent")

    @property
    def pid(self):
        return (self.marker or {}).get("pid")

    @property
    def port(self):
        return (self.marker or {}).get("port")

    def __repr__(self):
        return "Project(%r, %s)" % (self.name, self.url or "파일만")

    # ------------------------------------------------------------ 서버에 말 걸기
    def _need(self):
        if not self.online:
            raise E.Offline("이 out 을 띄운 도우미가 없어요 — 먼저 띄우세요: python \"%s\" \"%s\" --no-open" % (C.HELPER, self.out),
                            next="")                    # 메시지가 다음 행동을 이미 말한다
        return self.transport

    def _call(self, method, path, body=None, timeout=10):
        code, res = self._need().request(method, path, body, timeout=timeout)
        if code != 200:
            raise E.from_status(code, res)
        return res

    # ------------------------------------------------------------ 읽기
    def state(self):
        """→ {rev, state}. 서버가 있으면 GET /api/state, 없으면 상태 파일(없으면 rev 0 · 깨졌으면 HdError)."""
        if not self.online:
            with client_errors():
                return C.read_state(self.out)
        res = self._call("GET", "/api/state")
        if not isinstance(res, dict) or not isinstance(res.get("state"), dict):
            raise E.HdError("상태를 읽지 못했어요(모양이 아님): %s" % self.url)
        return {"rev": res.get("rev", 0), "state": res["state"]}

    def notes(self, which="open", state=None):
        """→ Note 목록(which = open|sent|all). state 를 주면 다시 읽지 않는다."""
        st = state if state is not None else self.state()
        return Note.from_state(st["state"], which)

    def screens(self):
        """screens.json 의 화면 id 집합 | None(못 읽음)."""
        return C.screen_ids(self.out)

    def groups(self):
        """screens.json 의 {화면 id: 줄 이름} — 정보 카드(R47, hd_info_card) 의 줄 카드. 못 읽으면 {}."""
        return C.screen_groups(self.out)

    def files(self, since=None):
        """GET /api/files[?since=seq] → {seq, changed:[screen]} — 디스크에서 바뀐 화면 파일."""
        return self._call("GET", "/api/files" + ("" if since is None else "?since=%s" % quote(str(since))))

    def layout(self):
        """화면 목록 + 자리·크기(hd screens) → {project, out, helper, title, groups, screens:[{id, title, group, file, purpose, pos, size}]} — place.layout."""
        from . import place
        return place.layout(self)

    def add(self, src, **opts):
        """HTML 화면 하나를 이 캔버스에 놓기(hd add) — place.add(id · title · group · purpose · after · at · size · assets · replace)."""
        from . import place
        return place.add(self, src, **opts)

    # ------------------------------------------------------------ 쓰기(늘 서버로)
    def reply(self, ref, reply):
        """메모에 답 하나. ref = '<screen>#<no>' | 메모 id. 규칙(hd_model.check_reply)으로 먼저 보고 POST /api/reply → {rev, status, note, screen}."""
        self._need()
        r = M.parse_ref(ref)
        st = self.state()
        notes = st["state"].get("notes") if isinstance(st["state"].get("notes"), list) else []
        i = M.find(notes, r, st["state"].get("note-seq"))
        if i is None:
            raise E.NotFound("없는 메모: %s — hd notes --all 로 번호를 보세요" % ref)
        errs = M.check_reply(reply, notes[i].get("intent"), agent=True, known_screens=self.screens())
        if errs:
            raise E.Invalid("답이 규칙에 맞지 않아요:\n  " + "\n  ".join(errs))
        return self._call("POST", "/api/reply", {"note": r, "reply": reply})

    def _known_screen(self, screen):
        ids = self.screens()
        if ids is not None and screen not in ids:
            raise E.NotFound("없는 화면이에요: %s — 있는 화면: %s" % (screen, ", ".join(sorted(ids)) or "없음"))

    def claim(self, screen, by=None, note=None):
        """'이 화면 고치는 중' 덮개 → {rev, screen, file}."""
        check_claim(screen, by, note)
        self._need()
        self._known_screen(screen)
        body = {"screen": screen}
        if by:
            body["by"] = by
        if note is not None:
            body["note"] = note
        return self._call("POST", "/api/claim", body)

    def release(self, screen):
        """덮개 걷기 → {rev, released}(없었으면 released false)."""
        self._need()
        self._known_screen(screen)
        return self._call("POST", "/api/release", {"screen": screen})

    def apply(self, edits, **opts):
        """화면 파일에 바로 쓰기 POST /api/apply {edits, …opts} → {applied, failed, stamp, changed, history?}(모양 = protocol helper.json)."""
        return self._call("POST", "/api/apply", dict(opts, edits=list(edits)), timeout=120)

    def attach(self, agent):
        """보내기 받을 에이전트 바꾸기(None = 떼기) → 서버가 받은 agent. 표지의 agent 도 고친다."""
        check_agent(agent)
        got = self._call("POST", "/api/attach", {"agent": agent}).get("agent")
        self.marker = dict(self.marker, agent=got)
        return got

    def stop(self):
        """서버 세션 끄기 → 'route' | 'kill' | 'gone' | 'other'(hd_client.stop — 허브 세션이면 그 세션만)."""
        self._need()
        with client_errors():
            return C.stop(self.marker)

    # ------------------------------------------------------------ 접속(task 47-5a, protocol presence.json)
    def hello(self, id=None, name=None, kind=None, pid=None, listen=True, session=None, lease=None, beat=True, cwd=None):
        """이 프로젝트에 접속 알리기 POST /hello → {agent, lease, beat, first}. id 를 안 주면 whoami(PASEO_AGENT_ID · CLAUDECODE · pid).
        listen = request.sent 이벤트를 읽는다(requests()) — False 면 보이기만 하고 보내기는 어댑터(paseo 등)로.
        session = claude 세션 id(대화 패널이 그 jsonl 을 읽음 · 서버가 HD_CLAUDE_WAKE=1 일 때 claude -p --resume 으로 깨움). beat = 데몬 맥박 스레드(간격 = 서버가 권한 beat).
        kind claude 면 session 기본 = CLAUDE_CODE_SESSION_ID(whoami), cwd 기본 = os.getcwd()(서버가 그 projects 폴더에서만 찾는다).
        옛 서버(접속 라우트 없음) = NotYet."""
        who = whoami(os.environ, os.getpid(), os.getcwd())
        if id is None:
            id, name, kind, pid = who["id"], name or who["name"], kind or who["kind"], pid if pid is not None else who["pid"]
        if kind == "claude":
            session = session if session is not None else who.get("session") if who["kind"] == "claude" else None
            cwd = cwd if cwd is not None else os.getcwd()
        if id is None or M.agent_error(id):
            raise E.Invalid(M.agent_error(id) or "에이전트 id 가 없어요")
        kind = kind or "other"
        if kind not in KINDS:
            raise E.Invalid("kind: %s 중 하나여야 해요" % "|".join(KINDS))
        agent = {"id": id, "name": name or id, "kind": kind}
        if pid is not None:
            agent["pid"] = pid
        agent["listen"] = bool(listen)
        if session is not None:
            agent["session"] = session
        if cwd is not None:
            agent["cwd"] = str(cwd)
        body = {"agent": agent}
        if lease is not None:
            body["lease"] = lease
        res = self._hello(body)
        self.me, self._hello_body = id, body
        if self.heartbeat is not None:
            self.heartbeat.stop()
            self.heartbeat = None
        if beat:
            self.heartbeat = Heartbeat(self, max(BEAT_MIN, float(res.get("beat") or 10))).start()
        return res

    def _hello(self, body):
        code, res = self._need().request("POST", "/hello", body)
        if code == 404 and not (isinstance(res, dict) and res.get("reason")):
            raise E.NotYet("이 서버는 접속 알리기를 몰라요(옛 도우미) — 서버를 다시 띄우면 돼요")
        if code != 200:
            raise E.from_status(code, res)
        return res

    def beat(self):
        """맥박 한 번 POST /beat {id} → 답. 서버가 이 id 를 잊었으면(다시 떴음 — 404 unknown) hello 를 다시 보낸다."""
        if not self.me:
            raise E.HdError("먼저 hello 를 보내세요")
        code, res = self._need().request("POST", "/beat", {"id": self.me})
        if code == 404 and isinstance(res, dict) and res.get("reason") == "unknown":
            return self._hello(self._hello_body)
        if code != 200:
            raise E.from_status(code, res)
        return res

    def bye(self):
        """맥박을 멈추고 POST /bye {id} → {agent}(state away). hello 를 안 했으면 None."""
        if self.heartbeat is not None:
            self.heartbeat.stop()
            self.heartbeat = None
        if not self.me:
            return None
        return self._call("POST", "/bye", {"id": self.me})

    def progress(self, text, screen=None, agent=None):
        """진행 한 줄 POST /progress {text, agent?, screen?} → 이벤트 id. agent 기본 = hello 한 id(있으면 맥박도 됨).
        서버가 그 id 를 모르면(hello 안 함) 보이기만 하는 hello(listen false, 맥박 없음) 뒤 한 번 더."""
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > PROGRESS_MAX:
            raise E.Invalid("진행 글은 1–%d자여야 해요" % PROGRESS_MAX)
        body = {"text": text.strip()}
        aid = agent or self.me
        if aid:
            body["agent"] = aid
        if screen:
            body["screen"] = screen
        code, res = self._need().request("POST", "/progress", body)
        if code == 404 and isinstance(res, dict) and res.get("reason") == "unknown" and aid:
            self._hello({"agent": {"id": aid, "name": aid, "kind": "other", "listen": False}})
            code, res = self._need().request("POST", "/progress", body)
        if code == 404 and not (isinstance(res, dict) and res.get("reason")):
            raise E.NotYet("이 서버는 진행 알리기를 몰라요(옛 도우미)")
        if code != 200:
            raise E.from_status(code, res)
        return res.get("event")

    def agents(self):
        """접속한 에이전트 GET /agents → [{id, name, kind, pid, state, listen, since, seen, lease, progress}]."""
        code, res = self._need().request("GET", "/agents")
        if code == 404:
            raise E.NotYet("이 서버는 접속한 에이전트 목록을 몰라요(옛 도우미)")
        if code != 200:
            raise E.from_status(code, res)
        return res.get("agents") or []

    def requests(self, since=None, timeout=None, retries=RETRIES, clock=time.time, sleep=time.sleep):
        """나에게 온 요청(request.sent, to = 내 id, via 'event') → Event generator(data: notes · text · path). 먼저 hello(listen true)."""
        if not self.me:
            raise E.HdError("먼저 hello 를 보내세요(받을 id 가 없어요)")
        me = self.me
        return (e for e in self.events(since, timeout, retries, clock, sleep)
                if e.type == "request.sent" and e.data.get("to") == me and e.data.get("via") == "event")

    # ------------------------------------------------------------ 기다리기
    def wait(self, timeout, poll=POLL, clock=time.time, sleep=time.sleep):
        """보낸(working) 메모가 생길 때까지 → ({rev, state}, [Note]). 시간 넘으면 TimedOut(종료 코드 2).
        이벤트(47-4b): 흐름이 열릴 때마다와 notes.changed·claim·release·reset 마다 상태를 다시 본다(타이머 없이 깨어남).
        흐름이 없거나(옛 서버 · 가짜 transport) 끊겨 다시 붙지 못하면 남은 시간 동안 poll 초마다 GET /api/state —
        서버에 닿지 않으면 finder 로 그 out 의 새 표지를 찾아 이어 간다([hd] 경고는 한 줄만)."""
        self._need()
        end = clock() + timeout
        try:
            found = self._pending()
        except E.HdError:                              # 닿지 않음 = 폴링 길(표지를 다시 찾는다)
            return self._wait_poll(end, timeout, poll, clock, sleep, failed=True)
        if found:
            return found
        if hasattr(self.transport, "stream"):
            try:
                for ev in self._events(None, end - clock(), RETRIES, clock, sleep, opens=True):
                    if ev.type in WAKE:
                        found = self._pending()
                        if found:
                            return found
                if clock() >= end:
                    raise E.TimedOut("%g초 동안 보낸 메모가 없어요(%s)" % (timeout, self.marker["out"]))
            except (E.NotYet, E.Offline, E.Unauthorized):
                pass                                   # 폴링으로(남은 시간)
        return self._wait_poll(end, timeout, poll, clock, sleep)

    def _pending(self):
        st = self.state()
        rs = [Note.from_row(r) for r in M.pending(st["state"])]
        return (st, rs) if rs else None

    def _wait_poll(self, end, timeout, poll, clock, sleep, failed=False):
        warned = False
        while True:
            try:
                if failed:
                    failed = False
                    raise E.Offline("앞서 닿지 않았어요")
                found = self._pending()
                if found:
                    return found
            except E.HdError:
                if not warned:
                    C.warn("도우미에 닿지 않아요 — 표지를 다시 읽으며 기다려요(%s)" % self.marker["out"]); warned = True
                again = self.finder(self.marker["out"])
                if again and again.get("token") != self.marker.get("token"):
                    self.marker = again
                    if self._own_transport:
                        self.transport = HttpTransport(again)
                    continue
            left = end - clock()
            if left <= 0:
                raise E.TimedOut("%g초 동안 보낸 메모가 없어요(%s)" % (timeout, self.marker["out"]))
            sleep(min(poll, left))

    # ------------------------------------------------------------ 이벤트(SSE, task 47-4b)
    def events(self, since=None, timeout=None, retries=RETRIES, clock=time.time, sleep=time.sleep):
        """서버 이벤트 흐름 GET <세션>/api/events(protocol events.json) → Event 차례로(generator).
        since = 이 id 다음부터(이어 받기, None = 지금부터). 흐름이 끊기면 마지막 id 를 Last-Event-ID 로 다시 붙는다(0.5·1·2…초, retries 번 넘게
        연달아 실패 = Offline). reset(이어 받을 수 없음 — 서버가 다시 떴거나 너무 오래됨)은 Event(type='reset', data {reason, last})로 내고 last 부터 이어 간다
        — 받는 쪽은 상태를 다시 읽는다. timeout 초가 지나면 끝(오류 없음, None = 끝없이). 흐름이 없는 옛 서버(404) = NotYet."""
        if not hasattr(self._need(), "stream"):
            raise E.NotYet("이 연결에는 이벤트 흐름이 없어요")
        return (e for e in self._events(since, timeout, retries, clock, sleep) if e.type != "open")

    def _events(self, since, timeout, retries, clock, sleep, opens=False):
        end = None if timeout is None else clock() + timeout
        last, fails = since, 0
        while end is None or clock() < end:
            wait = READ if end is None else max(0.1, min(READ, end - clock()))
            try:
                lines = self.transport.stream("/api/events", last=last, timeout=wait)
            except E.NotFound as e:
                raise E.NotYet("이 서버에는 이벤트 흐름이 없어요(옛 도우미): %s" % e) from e
            except E.Offline:
                fails += 1
                if fails > retries:
                    raise
                sleep(min(BACKOFF_MAX, 0.5 * 2 ** (fails - 1)))
                continue
            fails = 0
            if opens:
                yield Event(0, "open")
            for fr in sse.frames(lines):
                ev = sse.event_of(fr)
                if ev is None:
                    C.warn("이벤트가 깨져 건너뛰어요: %s" % str(fr.get("data"))[:80])
                    continue
                last = ev.data.get("last", ev.id) if ev.type == "reset" else ev.id
                yield ev
                if end is not None and clock() >= end:
                    return
