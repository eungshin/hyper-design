"""Session — 프로젝트(out) 하나의 조립 지점: 부품 객체를 만들고 잇는다 · 쓰기 자물쇠 하나 · 토큰 하나 · 페이지(index.html + window.__hdState) · 코드 도장 다시 빌드.

부품(모듈 하나씩 — canvas contract.md 책임 게이트):
  StateStore     — state_store.py: <out>/.hd-canvas.json rev · 합쳐 쓰기(409) · 자물쇠 없는 읽기(#271) · 깨진 파일 옮기기
  History        — history.py: 화면 파일 쓰기 하나씩 + 이벤트 · 쓰기 기록 .hd-history = write_record.py · 편집 적용(EDIT_OPS) = screen_edits.py · 줄 = board_rows.py
  Queue          — send_queue.py: 보낸 메모 · 보낼 곳(agent · Paseo 목록 5초 캐시 · 저장소) · 대기열 파일 + 받는 곳 고르기 · 에이전트 답
  AgentPresence  — presence.py(47-5a): hello·맥박·임대 끝 = away·진행 한 줄
  Ticker         — ticker.py(47-5a): 세션 시계 — 간격(PRESENCE_EVERY · ARCHIVE_EVERY · TRP.EVERY)은 여기서 정한다
  Busy · AiUndo  — busy.py · ai_undo.py: AI 작업 덮개 + 화면 파일 지켜보기 · 덮개 동안 AI 가 쓴 화면 되돌리기(48c)
  AgentInfo      — agent_info.py(R28): 붙은 Paseo 터미널의 모델·생각 깊이(바꾸기)·컨텍스트 사용량(규칙 agent_meta.py)
  Attachments    — attach_store.py(R22): <out>/.hd-attach/ 첨부 이미지 저장·읽기(규칙 attach_rules.py)
  ChatLog        — chat_store.py: <out>/.hd-chat.jsonl 대화 기록(S3, 버스 탭)
  Archive        — note_archive.py: <out>/.hd-notes-archive.jsonl 완료 메모 보관(sweep)
  Builder        — builder.py: 쓰기 확인(데이터만) · 페이지 빌드 하나씩 · hd-data · 부품 견본 목록
  PartsWatch     — parts_file.py(R30): <out>/parts.json 앱 부품 낡음 보기(읽기만 · 60초 캐시 · 빌드하지 않음)
  EventBus       — events.py(47-4a): 부품이 바뀔 때 publish → SSE /events · Rebuilder(rebuild.py) = async apply 의 뒤 빌드
상태: 토큰 · 붙은 코드 도장 함수(code) · 포기한 도장(_gave_up · _data_gave_up) — 나머지 상태는 부품마다 주인 하나.
페이지(figma-lite 5): 쓰기는 데이터만 확인하고 index.html 을 굽지 않는다 — page() 가 줄 때 데이터 도장(code_stamp.page_inputs)이 지금 out 파일과 다르면 다시 빌드(refresh_data), 닫을 때도 한 번.
부르는 곳: helper.make_server(CLI 도우미) · home.registry(허브) · router(주소 → 부품 메서드). 모듈 함수 예전 이름은 helper.py 가 부품 모듈에서 다시 내보낸다.
오류 탐지: 시작 정리·도장 재기·다시 빌드가 실패해도 [hd] 한 줄 뒤 있던 index.html 로 보인다(페이지를 못 주지는 않는다).
"""
import json, os, pathlib, secrets, sys, threading, urllib.parse

import adapters as AD  # 받는 곳 고르기 · Paseo/Claude/None 어댑터(task 47-5a)
import board_data as BD  # 데이터 도장 재기(input_stamp)
import code_stamp as CS  # 코드 도장 — 옛 코드로 구운 index.html 알아보기(순수 Model)
import events as EV  # 바뀐 것 알림(Model, task 47-4a)
import presence as PR  # 접속한 에이전트(task 47-5a)
import rebuild as RB  # async apply 뒤 빌드 차례(task 47-4a)
import transcript_pump as TRP  # 터미널 대화 펌프(S3b — 출처는 transcripts.py, 해석은 transcript_parse.py)
from adapters import _paseo_cmd
from agent_info import AgentInfo  # R28 고른 Paseo 터미널의 모델·생각 깊이·컨텍스트
from attach_store import Attachments  # R22 첨부 이미지 <out>/.hd-attach
from ai_undo import AiUndo  # 48c AI 반영 되돌리기
from builder import Builder  # 다시 빌드 하나씩 · hd-data · 부품 목록
from busy import Busy  # AI 덮개 + 화면 파일 지켜보기
from chat_store import ChatLog  # <out>/.hd-chat.jsonl 대화 기록(S3)
from history import History  # 화면 파일 쓰기(apply · delete · 줄 · 되살리기)
from note_archive import Archive  # <out>/.hd-notes-archive.jsonl
from parts_file import PartsWatch  # <out>/parts.json 앱 부품 낡음(R30)
from send_queue import Queue  # 보낸 메모 · 보낼 곳 · 에이전트 답
from state_store import StateStore, state_load  # <out>/.hd-canvas.json — out_io 가 hd 폴더를 sys.path 에 넣는다
from ticker import Ticker  # 세션 시계

import hd_model  # noqa: E402  — 프로젝트 이름(project_name)


def keypath(out):                                    # file:// 로 열었을 때의 location.pathname — 캔버스 저장 키를 같게
    return urllib.parse.urlparse((pathlib.Path(out).resolve() / "index.html").as_uri()).path


PRESENCE_EVERY = 1.0                                 # 접속 임대 끝 보기(초)
ARCHIVE_EVERY = 3600.0                               # 완료 메모 보관(초) — 캔버스 탭의 '한 시간에 한 번'과 같은 규칙, 탭이 없어도
PAGE_WAIT = 0.25                                     # 페이지를 줄 때 쓰기 자물쇠를 이만큼만 기다린다 — 쓰기 중이면 있던 index.html 로(읽기는 쓰기를 기다리지 않는다)


class ProjectSession:
    """프로젝트(out) 하나 — 부품 객체를 만들고 잇는다. 쓰기 자물쇠 하나(상태 파일·화면 파일·보관 파일 쓰기는 한 번에 하나) · 토큰 하나.
    open() = 시작 정리(깨진 상태 파일 옮기기 · 오래된 기록 정리) · start() = 지켜보기 시작 · close() = 멈춤."""

    def __init__(self, out, token=None, agent=None, paseo=None, build=None, on_attach=None, name=None, config=None, code=None):
        self.out = pathlib.Path(out).resolve()
        self.code = code                             # () → 지금 코드 도장 | None — 있으면 페이지를 줄 때 옛 도장 index.html 을 다시 빌드(CLI 도우미·허브가 넘김)
        self._gave_up = None                         # 다시 빌드해도 그 도장이 안 나온 도장 — 같은 도장으로 매번 빌드하지 않게
        self._data_gave_up = None                    # 데이터 도장도 같은 규칙(그 빌드가 도장을 못 적는 옛 코드 · 실패)
        self.token = token or secrets.token_urlsafe(18)
        self.lock = threading.Lock()
        self.events = EV.EventBus(name or hd_model.project_name(self.out.name, self.out.parent.name))
        self.builder = Builder(self.out, build)
        self.store = StateStore(self.out, self.lock, self.events)
        self.ai = AiUndo(self.out)
        self.busy = Busy(self.out, self.lock, self.ai, self.events)
        self.history = History(self.out, self.lock, self.builder, self.busy.absorb, self.events, lambda: self.busy.watch.seq)
        self.rebuilder = RB.Rebuilder(lambda: self.builder.check(self.out), self.history.revert_writes, self.events.publish)
        self.history.rebuilder = self.rebuilder
        self.config = config if config is not None else AD.config_from_env(os.environ)   # 47-5a: claude 깨우기 · 새 에이전트 열기(기본 꺼짐)
        self.presence = PR.AgentPresence(self.events.publish)
        self.queue = Queue(self.out, self.lock, agent, paseo, on_attach, self.events, self.presence, self.config)
        self.agent_info = AgentInfo(self.queue, self.queue.adapters["paseo"])   # R28 — paseo 는 Queue 와 같은 어댑터 하나로
        self.spawner = AD.PaseoSpawner(lambda: _paseo_cmd(paseo), enabled=bool(self.config.get("allow_spawn")))
        self.archive = Archive(self.out, self.lock, self.events)
        self.images = Attachments(self.out)          # R22 첨부 이미지 — 붙인 이미지를 out 안에 두고 절대 경로를 요청 글에
        self.parts = PartsWatch(self.out)            # R30 앱 부품 낡음 — GET /api/app-parts(읽기만, git 은 60초에 한 번까지)
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
        else:
            try:
                self.refresh_data(wait=5.0)          # 디스크의 index.html 도 마지막 쓰기까지(도우미 없이 file:// 로 열어도)
            except Exception as e:                    # noqa: BLE001 — 닫기는 멈추지 않는다
                print("[hd] 닫으며 캔버스를 다시 빌드하지 못했어요(%s)" % e, file=sys.stderr, flush=True)
        self.events.close()                           # 열린 흐름(SSE)이 끝난다

    def _head(self):
        """index.html 앞 8 KB(도장 meta 는 <head> 바로 뒤) | None(없음 · 못 읽음)."""
        try:
            with open(self.out / "index.html", encoding="utf-8", errors="replace") as f:
                return f.read(8192)
        except OSError:
            return None

    def page_code(self):
        """index.html 이 품은 코드 도장 | None(도장 전 빌드 · 못 읽음)."""
        return CS.page_stamp(self._head())

    def page_inputs(self):
        """index.html 이 품은 데이터 도장 | None(도장 전 빌드 · 가짜 페이지 · 못 읽음)."""
        return CS.page_inputs(self._head())

    def refresh_data(self, wait=PAGE_WAIT):
        """index.html 을 구운 뒤 out 의 데이터 입력이 바뀌었으면(쓰기 · AI 수정) 다시 빌드 → 'fresh' | 'rebuilt' | 'failed' | 'busy'.
        쓰기 중이면(자물쇠를 wait 안에 못 잡음 · 뒤 확인을 기다리는 쓰기) 기다리지 않고 있던 페이지('busy' — 다음 페이지에서).
        자물쇠 안에서 굽는다 — 확인 안 된 쓰기가 페이지에 들지 않게. 도장 없는 페이지는 견주지 않는다(code_stamp.data_stale)."""
        if not self.lock.acquire(timeout=wait):
            return "busy"
        try:
            if self.rebuilder.pending():
                return "busy"
            have = self.page_inputs()
            want = BD.input_stamp(self.out) if have else None
            if not CS.data_stale(have, want) or want == self._data_gave_up:
                return "fresh"
            r = self.builder.run(self.out)
            if getattr(r, "returncode", 1) == 0 and self.page_inputs() == want:
                return "rebuilt"
            self._data_gave_up = want
            tail = ((getattr(r, "stdout", "") or "") + (getattr(r, "stderr", "") or "")).strip().splitlines()[-1:]
            print("[hd] 바뀐 화면으로 캔버스를 다시 빌드하지 못했어요 — 있던 index.html 로 보여요%s" % (": " + tail[0] if tail else ""),
                  file=sys.stderr, flush=True)
            return "failed"
        finally:
            self.lock.release()

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
        code 가 있으면 주기 전에 옛 도장 index.html 을 다시 빌드(F5 · 즐겨찾기로 열어도 지금 코드), 그다음 데이터가 옛것이면 다시 빌드(refresh_data)."""
        if self.code is not None:
            try:
                self.refresh(self.code())
            except Exception as e:                    # noqa: BLE001 — 도장 재기·빌드 실패로 페이지를 못 주지는 않는다(한 줄 남김)
                print("[hd] 코드 도장을 견주지 못했어요(%s) — 있던 index.html 로 보여요" % e, file=sys.stderr, flush=True)
        try:
            self.refresh_data()
        except Exception as e:                        # noqa: BLE001 — 데이터 도장 재기·빌드 실패로 페이지를 못 주지는 않는다
            print("[hd] 데이터 도장을 견주지 못했어요(%s) — 있던 index.html 로 보여요" % e, file=sys.stderr, flush=True)
        snap = self.store.inject()
        inject = '<script>window.__hdHelper=%s;window.__hdKeyPath=%s;window.__hdOut=%s;' % (
            json.dumps(True), json.dumps(keypath(self.out)), json.dumps(self.out.as_posix()))
        inject += "window.__hdAgent=%s;</script>" % json.dumps(self.queue.agent)
        return (self.out / "index.html").read_text(encoding="utf-8").replace("<head>", "<head>" + inject + snap, 1).encode("utf-8")
