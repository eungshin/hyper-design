"""Service — Project: 프로젝트 하나(out 폴더 + 그것을 띄운 서버 세션)에 하는 일. notes · reply · claim · release · apply · files · state ·
attach · stop · wait. events 는 아직(task 47-4b — 부르면 NotYet).

상태 = 표지(marker: {pid, project, out, url, token, port, agent, prefix?, hub?}) 하나 | None(파일만 — 도우미 없음). 쓰기는 늘 서버로
(Transport), 읽기는 서버가 있으면 GET /api/state, 없으면 상태 파일(hd_client.read_state). 규칙은 hd_model(답 검사·찾기·덮개·에이전트 id).
오류는 HdError 가족만 — 서버 거절은 errors.from_status, hd_client 오류는 transport.client_errors 가 바꾼다.
"""
import pathlib, time
from urllib.parse import quote

import hd_client as C
import hd_model as M

from . import errors as E
from .transport import HttpTransport, client_errors
from .values import Note

POLL = 2.0


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

    def files(self, since=None):
        """GET /api/files[?since=seq] → {seq, changed:[screen]} — 디스크에서 바뀐 화면 파일."""
        return self._call("GET", "/api/files" + ("" if since is None else "?since=%s" % quote(str(since))))

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

    # ------------------------------------------------------------ 기다리기
    def wait(self, timeout, poll=POLL, clock=time.time, sleep=time.sleep):
        """보낸(working) 메모가 생길 때까지 poll 초마다 GET /api/state → ({rev, state}, [Note]). 시간 넘으면 TimedOut(종료 코드 2).
        서버에 닿지 않으면 finder 로 그 out 의 새 표지를 찾아 이어 간다([hd] 경고는 한 줄만). 47-4b 가 events 로 바꾼다."""
        self._need()
        end, warned = clock() + timeout, False
        while True:
            try:
                st = self.state()
                rs = [Note.from_row(r) for r in M.pending(st["state"])]
                if rs:
                    return st, rs
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

    def events(self, since=None):
        """서버 이벤트 흐름(SSE /v1/p/<이름>/events, protocol events.json) — 아직 없음: task 47-4b 가 만든다."""
        raise E.NotYet("project.events() 는 아직 없어요(task 47-4b)")
