"""Model + 맥박 — 접속 알리기(task 47-5a). whoami(env, pid) = 나는 누구(순수) · Heartbeat = Project.hello 뒤 맥박 스레드 하나(데몬).

whoami 규칙: PASEO_AGENT_ID 가 있으면 그 id·kind paseo(Paseo 안의 어떤 도구든 Paseo 로 깨운다) · CLAUDECODE=1 이면 claude-<pid> · 그 밖 agent-<pid>(other).
Heartbeat.tick() = 맥박 한 번(스레드 없이 부를 수 있음 — unit): POST /beat, 서버가 잊었으면(404 unknown — 서버가 다시 떴음) hello 를 다시.
닿지 않으면 False 를 내고 다음 차례에 다시(멈추지 않음). 상태 = 간격(every) · 연달아 실패 수(fails) · 스레드 · 멈춤 깃발.
"""
import threading

from .errors import HdError


def whoami(env, pid):
    """환경 사전 + pid → {id, name, kind, pid}(hello 의 기본값)."""
    if env.get("PASEO_AGENT_ID"):
        aid = env["PASEO_AGENT_ID"]
        return {"id": aid, "name": aid, "kind": "paseo", "pid": pid}
    if env.get("CLAUDECODE") == "1":
        return {"id": "claude-%d" % pid, "name": "Claude Code", "kind": "claude", "pid": pid}
    return {"id": "agent-%d" % pid, "name": "agent-%d" % pid, "kind": "other", "pid": pid}


class Heartbeat:
    """project 의 맥박. every = 초(서버가 권한 beat). start() = 데몬 스레드, stop() = 멈춤(기다리지 않음)."""

    def __init__(self, project, every):
        self.project, self.every = project, every
        self.fails = 0
        self._stop = threading.Event()
        self.thread = None

    def tick(self):
        try:
            self.project.beat()
        except HdError:
            self.fails += 1
            return False
        self.fails = 0
        return True

    def start(self):
        self.thread = threading.Thread(target=self._loop, name="hd-heartbeat", daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.every):
            self.tick()
