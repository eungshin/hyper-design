"""Session — 프로젝트(out) 하나의 서버 쪽(task 47-2 에서 helper.py 를 쪼갬). 파일 I/O 는 여기, 규칙은 hd_model · helper_model, HTML 고치기는 html_edit.

객체(책임 하나씩 — canvas contract.md 책임 게이트):
  ProjectSession — out 하나: 아래 부품을 만들고 잇는다 · 쓰기 자물쇠 하나 · 토큰 하나 · 페이지(index.html + window.__hdState)
  StateStore     — <out>/.hd-canvas.json: rev · 합쳐 쓰기(409) · 자물쇠 없는 읽기(#271) · 깨진 파일 옮기기
  History        — <out>/.hd-history: 쓰기마다 원본 + manifest(apply · delete) · 되살리기(restore, 409 changed-since) · 정리(prune)
  Queue          — 보낸 메모: 보낼 곳(agent · Paseo 목록 5초 캐시 · 저장소) · 요청문 대기열 파일 + 받는 곳 고르기(send — 접속 중이면 request.sent 이벤트,
                   아니면 AgentAdapter: adapters.py) · 에이전트 답(reply → agent.reply)
  AgentPresence  — 접속한 에이전트(presence.py, 47-5a): hello·맥박·임대 끝 = away·진행 한 줄
  Ticker         — 세션 시계 스레드 하나(47-5a): 1초마다 presence.sweep · 한 시간마다 Archive.sweep(완료 메모 보관)
  Busy           — AI 작업 덮개 state.busy(claim · release) + 화면 파일 지켜보기(1초 mtime → seq — /api/files · /api/watch)
  AiUndo         — 덮개 동안 AI 가 쓴 화면 = 기록 한 줄 'AI 반영 · <화면>' + 되살리기 stamp(48c, GET /api/ai-writes)
  ChatLog        — <out>/.hd-chat.jsonl 대화 기록(S3): 버스 탭으로 이벤트 → 기록 한 줄(모양·턴·한도 = chat_log.py) · GET/POST /api/chat
  Archive        — <out>/.hd-notes-archive.jsonl 완료 메모 보관(sweep = 서버가 고르고 옮김, 고르기 = memo_archive.py)
  Builder        — 다시 빌드(한 번에 하나 — 동기 apply 의 빌드와 뒤 빌드가 겹치지 않게) · hd-data · 부품 견본 목록
  EventBus       — 바뀐 것 알림(events.py, 47-4a): 부품이 바뀔 때 publish → SSE /events · Rebuilder(rebuild.py) = async apply 의 뒤 빌드
모듈 함수(apply_edits · restore · state_put …)는 helper.py 가 예전 이름 그대로 다시 내보낸다(테스트·hd 가 부름).
"""
import json, os, pathlib, secrets, sys, threading, time, urllib.parse

import adapters as AD  # 받는 곳 고르기 · Paseo/Claude/None 어댑터(task 47-5a)
import board_data
import code_stamp as CS  # 코드 도장 — 옛 코드로 구운 index.html 알아보기(순수 Model)
import events as EV  # 바뀐 것 알림(Model, task 47-4a)
import presence as PR  # 접속한 에이전트(task 47-5a)
import rebuild as RB  # async apply 뒤 빌드 차례(task 47-4a)
import transcript_pump as TRP  # 터미널 대화 펌프(S3b — 출처는 transcripts.py, 해석은 transcript_parse.py)
from adapters import _paseo_cmd
from ai_undo import AiUndo  # 48c AI 반영 되돌리기
from busy import Busy  # AI 덮개 + 화면 파일 지켜보기
from chat_store import ChatLog  # <out>/.hd-chat.jsonl 대화 기록(S3)
from history import History  # 화면 파일 쓰기(apply · delete · 줄 · 되살리기)
from note_archive import Archive  # <out>/.hd-notes-archive.jsonl
from screen_edits import parts_of
from send_queue import Queue  # 보낸 메모 · 보낼 곳 · 에이전트 답
from state_store import StateStore, state_load  # <out>/.hd-canvas.json — out_io 가 hd 폴더를 sys.path 에 넣는다
from write_record import run_build

import hd_model  # noqa: E402  — 프로젝트 이름(project_name)


def keypath(out):                                    # file:// 로 열었을 때의 location.pathname — 캔버스 저장 키를 같게
    return urllib.parse.urlparse((pathlib.Path(out).resolve() / "index.html").as_uri()).path


# ---------------------------------------------------------------- 객체(task 47-2): out 하나 = ProjectSession 하나


class Builder:
    """다시 빌드 · hd-data · 부품 목록 — out 하나. run(out) = 빌드 하나(기본 작업 트리, CLI 도우미는 build_ref — helper 가 넘긴다)."""

    def __init__(self, out, run=None):
        self.out, self._run, self.lock = out, run or run_build, threading.Lock()

    def run(self, out):                              # 빌드 하나씩(동기 apply 의 빌드 · 뒤 빌드 · 되돌린 뒤 빌드가 같은 index.html 을 쓴다)
        with self.lock:
            return self._run(out)

    def build(self):
        return self.run(self.out)

    def data(self):
        return board_data.index_data(self.out, json.loads((self.out / "screens.json").read_text(encoding="utf-8")))

    def parts(self):
        return parts_of(self.out)


PRESENCE_EVERY = 1.0                                 # 접속 임대 끝 보기(초)
ARCHIVE_EVERY = 3600.0                               # 완료 메모 보관(초) — 캔버스 탭의 '한 시간에 한 번'과 같은 규칙, 탭이 없어도
TICK = 0.5


class Ticker:
    """세션 시계 — 일(간격 초, fn)마다 처음 한 번, 그 뒤 간격마다. step(now) 는 I/O 가 없다(unit), 스레드는 start()·close().
    한 일이 실패해도 [hd] 한 줄 뒤 다른 일은 계속."""

    def __init__(self, tasks, clock=time.monotonic):
        self.tasks, self.clock = list(tasks), clock
        self.next = [None] * len(self.tasks)
        self.stop = threading.Event()

    def step(self, now):
        for i, (every, fn) in enumerate(self.tasks):
            if self.next[i] is None or now >= self.next[i]:
                self.next[i] = now + every
                try:
                    fn()
                except Exception as e:                # noqa: BLE001 — 세션 시계는 멈추지 않는다(한 줄 남김)
                    print("[hd] 세션 시계 일이 실패했어요(%s): %s" % (getattr(fn, "__name__", fn), e), file=sys.stderr, flush=True)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self.stop.set()

    def _loop(self):
        while not self.stop.is_set():
            self.step(self.clock())
            self.stop.wait(TICK)


class ProjectSession:
    """프로젝트(out) 하나 — 부품 객체를 만들고 잇는다. 쓰기 자물쇠 하나(상태 파일·화면 파일·보관 파일 쓰기는 한 번에 하나) · 토큰 하나.
    open() = 시작 정리(깨진 상태 파일 옮기기 · 오래된 기록 정리) · start() = 지켜보기 시작 · close() = 멈춤."""

    def __init__(self, out, token=None, agent=None, paseo=None, build=None, on_attach=None, name=None, config=None, code=None):
        self.out = pathlib.Path(out).resolve()
        self.code = code                             # () → 지금 코드 도장 | None — 있으면 페이지를 줄 때 옛 도장 index.html 을 다시 빌드(CLI 도우미·허브가 넘김)
        self._gave_up = None                         # 다시 빌드해도 그 도장이 안 나온 도장 — 같은 도장으로 매번 빌드하지 않게
        self.token = token or secrets.token_urlsafe(18)
        self.lock = threading.Lock()
        self.events = EV.EventBus(name or hd_model.project_name(self.out.name, self.out.parent.name))
        self.builder = Builder(self.out, build)
        self.store = StateStore(self.out, self.lock, self.events)
        self.ai = AiUndo(self.out)
        self.busy = Busy(self.out, self.lock, self.ai, self.events)
        self.history = History(self.out, self.lock, self.builder, self.busy.absorb, self.events, lambda: self.busy.watch.seq)
        self.rebuilder = RB.Rebuilder(lambda: self.builder.run(self.out), self.history.revert_writes, self.events.publish)
        self.history.rebuilder = self.rebuilder
        self.config = config if config is not None else AD.config_from_env(os.environ)   # 47-5a: claude 깨우기 · 새 에이전트 열기(기본 꺼짐)
        self.presence = PR.AgentPresence(self.events.publish)
        self.queue = Queue(self.out, self.lock, agent, paseo, on_attach, self.events, self.presence, self.config)
        self.spawner = AD.PaseoSpawner(lambda: _paseo_cmd(paseo), enabled=bool(self.config.get("allow_spawn")))
        self.archive = Archive(self.out, self.lock, self.events)
        self.chat = ChatLog(self.out)                # S3 대화 기록 — 이미 내는 이벤트를 탭으로 받아 한 줄씩
        self.events.taps.append(self.chat.tap)
        self.transcripts = TRP.pump_for(self, paseo)  # S3b 터미널 대화 — 고른·접속한 에이전트만, 'agent.transcript' 를 publish
        self.ticker = Ticker([(PRESENCE_EVERY, self.presence.sweep), (ARCHIVE_EVERY, self.archive.sweep), (TRP.EVERY, self.transcripts.tick)])

    def open(self):
        state_load(self.out)                         # 깨진 상태 파일을 옮겨 둔다(멈추지 않음)
        self.history.prune()                         # 오래된 기록·처리된 대기열 정리(#281, 실패해도 한 줄)
        return self

    def start(self):
        self.busy.start()
        self.ticker.start()
        return self

    def spawn(self, body):
        """POST /agents/spawn {kind} — 기본 꺼짐(HD_ALLOW_SPAWN=1). 일하는 폴더 = 저장소(없으면 out)."""
        return self.spawner.spawn(body, self.queue.repo or str(self.out), self.events.project)

    def close(self):
        self.ticker.close()
        self.busy.close()
        self.rebuilder.close()                        # 다음 뒤 빌드는 시작하지 않는다(돌고 있는 것은 끝까지) — 남은 쓰기는 다음 열기의 빌드가 담는다
        if self.rebuilder.pending():
            print("[hd] 닫는 중 — 아직 빌드하지 않은 쓰기 %d개(화면 파일에는 있어요)" % self.rebuilder.pending(), file=sys.stderr, flush=True)
        self.events.close()                           # 열린 흐름(SSE)이 끝난다

    def page_code(self):
        """index.html 이 품은 코드 도장 | None(도장 전 빌드 · 못 읽음)."""
        try:
            with open(self.out / "index.html", encoding="utf-8", errors="replace") as f:
                return CS.page_stamp(f.read(8192))       # 도장은 <head> 바로 뒤
        except OSError:
            return None

    def refresh(self, current):
        """index.html 이 지금 코드(current)로 구운 것이 아니면 다시 빌드 → 'fresh' | 'rebuilt' | 'failed'.
        다시 빌드해도 그 도장이 안 나오면(빌드 실패 · 다른 빌더) 그 도장으로는 다시 하지 않는다 — [hd] 한 줄."""
        if not current or current == self._gave_up or self.page_code() == current:
            return "fresh"
        r = self.builder.run(self.out)
        if getattr(r, "returncode", 1) == 0 and self.page_code() == current:
            print("[hd] 옛 코드로 구운 캔버스를 지금 코드로 다시 빌드했어요: %s" % self.out, file=sys.stderr, flush=True)
            return "rebuilt"
        self._gave_up = current
        tail = ((getattr(r, "stdout", "") or "") + (getattr(r, "stderr", "") or "")).strip().splitlines()[-1:]
        print("[hd] 캔버스를 지금 코드로 다시 빌드하지 못했어요 — 있던 index.html 로 보여요%s" % (": " + tail[0] if tail else ""),
              file=sys.stderr, flush=True)
        return "failed"

    def page(self):
        """index.html + <head> 에 window.__hdHelper·__hdKeyPath·__hdOut·__hdAgent(attach 로 바뀌므로 줄 때마다)·__hdState → bytes.
        code 가 있으면 주기 전에 옛 도장 index.html 을 다시 빌드(F5 · 즐겨찾기로 열어도 지금 코드)."""
        if self.code is not None:
            try:
                self.refresh(self.code())
            except Exception as e:                    # noqa: BLE001 — 도장 재기·빌드 실패로 페이지를 못 주지는 않는다(한 줄 남김)
                print("[hd] 코드 도장을 견주지 못했어요(%s) — 있던 index.html 로 보여요" % e, file=sys.stderr, flush=True)
        snap = self.store.inject()
        inject = '<script>window.__hdHelper=%s;window.__hdKeyPath=%s;window.__hdOut=%s;' % (
            json.dumps(True), json.dumps(keypath(self.out)), json.dumps(self.out.as_posix()))
        inject += "window.__hdAgent=%s;</script>" % json.dumps(self.queue.agent)
        return (self.out / "index.html").read_text(encoding="utf-8").replace("<head>", "<head>" + inject + snap, 1).encode("utf-8")
