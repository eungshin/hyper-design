"""Client — ProjectRegistry(task 47-2 '서버 하나'): 허브 프로세스 하나가 프로젝트마다 ProjectSession 을 열고 닫는다(도우미를 따로 띄우지 않음).

- 프로젝트 목록·탭·별표·휴지통 파일은 그대로 hd_client · home_client 가 주인(여기는 부르기만). 여기 상태 = 열린 세션들(이름 → 세션).
- 열기 open(이름|out, agent) → (항목, 표지 모양, reused) — hd_client.open_project 와 같은 답(home_api ctx.opener).
  이 허브에 열려 있으면 그것 · 따로 떠 있는 옛 도우미(helper.py)가 있으면 그것(한 out 에 쓰는 프로세스 하나) · 아니면 build_ref 로 빌드한 뒤 세션.
- 세션 주소 = http://127.0.0.1:<허브 포트>/v1/p/<이름>/index.html?hd=<세션 토큰>(출처 하나 — 탭 사이를 오가도 같은 주소).
- <out>/.hd-helper.json = {url, pid(허브), port, token} — 옛 helper.py 시작 검사·hd_client.live_record 가 이 세션을 '떠 있음'으로 본다.
  닫을 때 처음 것으로 되돌린다({port} 만 — 다음 helper.py 가 같은 포트로).
- 옛 포트 별칭: 그 기록의 지난 도우미 포트를 열 수 있으면 같은 세션을 그 포트에서도 낸다(옛 주소·스킬의 curl 이 계속 닿게). 못 열면 [hd] 한 줄.
- 표지 markers() = hd_client 의 표지 모양 + prefix(/v1/p/<이름>) · hub:true — hd ls·notes·reply·claim 이 허브를 거쳐 찾는다(hd_client.hub_markers).
- 코드 도장(canvas/code_stamp.py): code = 이 허브가 뜬 코드. 열 때마다 지금 도장과 견줘 — 열린 세션의 옛 index.html = 다시 빌드(세션 refresh,
  페이지를 줄 때도), 따로 떠 있는 옛 코드 도우미 = 쉬면 끄고 이 허브 세션으로(hd_client.freshen), 허브 자신이 옛것이면 답에 notice 한 줄
  (허브는 스스로 끄지 않는다 — 홈 화면의 '다시 켜기' · hd home --restart).
  R34: 같은 판단을 프로젝트 화면에도 — stale_info() = code_stamp.hub_stale(뜬 도장, 지금 도장, 뜬 시각) → 세션의 hub_stale(GET /api/state 의 hubStale ·
  페이지의 window.__hdHubStale). 지금 도장(git)은 STALE_TTL 초에 한 번만 잰다(2초 읽기마다 git 을 부르지 않게). restarter() = 프로젝트 화면의
  [다시 켜기](세션 토큰 POST /api/hub/restart — 홈 화면과 같은 spawn_restart).
- 지금 도장 재기는 한 자리(보드 전환 S1): current_code(max_age) = 이 허브의 기억 하나(잰 시각 · 값) — STAMP_TTL(2초) 안이면 git 을 다시 부르지 않는다.
  열기(open) · 세션 페이지(page 의 code) · 옛 코드 칩(stale_info, STALE_TTL) 이 같은 기억을 쓴다 → 전환 한 번에 git rev-parse 한 번.
  커밋 뒤 2초 안 전환은 옛 도장으로 볼 수 있다(다음 전환에서 바로잡힘). 규칙은 stamp_fresh(순수 — 시계를 넘겨받는다).
- 공용 셸 미리 만들기(1단계 P1a): current_code 가 git 으로 새로 잴 때마다 prebuild.want(도장) — 처음 보는 도장이면 뒤 스레드 하나가
  그 도장의 셸을 만든다(canvas/shell_store.Prebuilder — 허브 make_hub 가 넘김 · 같은 도장 두 번 안 함). 뜰 때 · 커밋 뒤(열기·페이지 2초 · 옛 코드 칩 30초) 알아챈다.
"""
import json, os, pathlib, sys, threading, time, urllib.parse
from http.server import ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
CANVAS = HERE.parent / "canvas"
sys.path[:0] = [str(HERE), str(HERE.parent / "hd"), str(CANVAS)]
import code_stamp as CS  # noqa: E402
import hd_client as C  # noqa: E402
import hd_projects as P  # noqa: E402
import home_api as A  # noqa: E402
import router as R  # noqa: E402
import write_record  # noqa: E402
import session as S  # noqa: E402

BUILD_REF = CANVAS / "build_ref.py"
STALE_TTL = 30.0                                     # 프로젝트 화면의 '허브 옛 코드' 판단 — 지금 도장을 이만큼마다 한 번 잰다
STAMP_TTL = 2.0                                      # 열기 · 페이지 — 이 안에 다시 재면 기억한 도장(전환 한 번에 git 한 번)


def stamp_fresh(taken, now, ttl):
    """잰 시각 taken 의 도장을 now 에 다시 써도 되나 — ttl 초 안(0 <= now-taken < ttl). 잰 적 없음 · 시계가 뒤로 감 = 아니(다시 잰다)."""
    return taken is not None and 0 <= now - taken < ttl


def ref_build(out):                                  # 허브의 다시 빌드 = hd open 과 같은 build_ref(저장소면 git HEAD 코드, #278)
    return write_record.run_build(out, BUILD_REF)


def prefix(name):
    return "/v1/p/%s" % urllib.parse.quote(name, safe="")


class _Alias(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True
    request_queue_size = 64                           # 허브와 같은 연결 대기 줄(W10)


class ProjectRegistry:
    """열린 세션들(이름 → ProjectSession). hub_port()·hub_url() = 허브 주소, picker = 폴더 고르기, build = 다시 빌드(테스트가 바꿔 끼움)."""

    def __init__(self, hub_port, hub_url, picker=None, paseo=None, build=None, after_rows=None, restarter=None, prebuild=None, shells=None):
        self.hub_port, self.hub_url, self.picker, self.paseo = hub_port, hub_url, picker, paseo
        self.build, self.after_rows, self.restarter = build or ref_build, after_rows, restarter
        self.shells = shells                         # 공용 셸 저장소(1단계) — 세션 페이지가 뼈대 + 지금 데이터로(허브가 SS.STORE 를 넘김, 없으면 예전 길)
        self.prebuild = prebuild                     # 새 도장의 공용 셸을 뒤에서 만든다 — 허브(make_hub)가 SS.PREBUILD 를 넘김, 없으면 안 함(unit 은 I/O 없이)
        self.clock = time.monotonic                  # 도장 기억의 시계(테스트가 바꿔 끼움)
        self._probe, self._probe_lock = None, threading.Lock()   # (잰 때 clock, 지금 도장) — current_code 의 기억 하나
        self.code = self.current_code()              # 이 허브 프로세스가 뜬 코드 도장
        self.started = C.now()                       # 이 허브가 뜬 시각(프로젝트 화면 칩의 '켠 시각')
        self.sessions = {}
        self.lock = threading.RLock()

    # ------------------------------------------------------------ 찾기
    def get(self, name):
        with self.lock:
            return self.sessions.get(name)

    def by_token(self, token):
        if not token:
            return None
        with self.lock:
            return next((s for s in self.sessions.values() if s.token == token), None)

    def _by_out(self, out):
        k = P.key(C.abs_out(out))
        with self.lock:
            return next((s for s in self.sessions.values() if P.key(str(s.out)) == k), None)

    def url(self, sess):
        return "http://127.0.0.1:%d%s/index.html?hd=%s" % (self.hub_port(), prefix(sess.name), sess.token)

    def marker(self, sess):
        """hd_client 표지 모양 — prefix 가 있어 그 세션 주소로 부른다. local = 이 프로세스 안(핑 없이 살아 있음)."""
        return {"pid": os.getpid(), "project": sess.name, "out": str(sess.out), "url": self.url(sess), "token": sess.token,
                "port": self.hub_port(), "agent": sess.queue.agent, "started": sess.started, "prefix": prefix(sess.name), "hub": True,
                "code": self.code}

    def current_code(self, max_age=STAMP_TTL, now=None):
        """지금 코드 도장 | None — 허브가 재는 유일한 곳. 기억이 max_age 초 안이면 그것(git 을 부르지 않음), 아니면 재고 기억한다.
        자물쇠 안에서 잰다 — 같이 온 요청(열기 · 페이지)이 따로 재지 않게."""
        t = self.clock() if now is None else now
        with self._probe_lock:
            fresh = self._probe is not None and stamp_fresh(self._probe[0], t, max_age)
            if not fresh:
                self._probe = (t, C.code_stamp())
            stamp = self._probe[1]
        if not fresh and self.prebuild is not None:
            self.prebuild.want(stamp)                # 처음 보는 도장만 뒤에서 만든다(기다리지 않음)
        return stamp

    def stale(self, current=None):
        """이 허브가 옛 코드로 떠 있나(지금 도장을 모르면 아니라고)."""
        return CS.stale(self.code, self.current_code() if current is None else current)

    def stale_info(self, now=None):
        """프로젝트 화면에 실을 판단 → {sha, since} | None(새것 · 지금 도장을 모름). 지금 도장은 STALE_TTL 안이면 기억한 것(열기·페이지와 같은 기억)."""
        return CS.hub_stale(self.code, self.current_code(STALE_TTL, now), self.started)

    def _noticed(self, m, current):
        return dict(m, notice=CS.HUB_NOTICE) if self.stale(current) else m

    def markers(self):
        with self.lock:
            return [self.marker(s) for s in self.sessions.values()]

    # ------------------------------------------------------------열기·닫기
    def ctx(self, sess):
        """세션 토큰으로 온 프로젝트·탭·홈 주소(캔버스의 /api/projects · open · tabs · home …) — 도우미 때와 같은 JSON, 열기는 이 허브 안에서."""
        return A.Ctx(hub=False, agent=lambda: sess.queue.agent, port=self.hub_port, picker=self.picker,
                     opener=self.open, home_url=self.hub_url, closer=self.close)

    def open(self, target, agent=None):
        e, o = C.resolve(target)
        current = self.current_code()                # 바로 뒤 page() 도 이 기억을 쓴다(전환 한 번에 git 한 번)
        with self.lock:
            sess = self._by_out(o)
            if sess is not None:
                sess.refresh(current)                # 옛 코드로 구운 페이지 = 다시 빌드(허브 프로세스는 그대로 — 옛것이면 notice)
                C.save_projects(P.touch(C.load_projects(), e["out"], C.now()))
                return e, self._noticed(self.marker(sess), current), True
            m = C.serving(o) or C.live_record(o)     # 따로 떠 있는 옛 도우미 — 같은 out 에 쓰는 프로세스를 둘로 만들지 않는다
            if m is not None:
                m = C.freshen(o, m, current)         # 옛 코드로 뜬 쉬는 도우미면 끄고(None) 아래에서 이 허브 세션으로
            if m is not None:
                C.save_projects(P.touch(C.load_projects(), e["out"], C.now()))
                return e, m, True
            code, tail = C.build(o)
            if code != 0:
                if not (pathlib.Path(o) / "index.html").is_file():
                    raise C.HdError("빌드 실패(build_ref.py %d): %s" % (code, " / ".join(tail.splitlines())))
                C.warn("빌드 실패(%d) — 있던 index.html 로 열어요: %s" % (code, tail.splitlines()[-1] if tail else ""))
            sess = self._start(e["name"], o, agent)
        C.save_projects(P.touch(C.load_projects(), e["out"], C.now()))
        return e, self._noticed(self.marker(sess), current), False

    def _start(self, name, out, agent):
        sess = S.ProjectSession(out, agent=agent, paseo=self.paseo, build=self.build, name=name,
                                code=self.current_code,
                                shell=self.shells.get if self.shells is not None else None).open()   # name = 이벤트의 project · code = 페이지를 줄 때 견줄 지금 도장 · shell = 공용 셸(1단계)
        sess.name, sess.started = name, C.now()
        sess.hub_stale = self.stale_info             # R34 프로젝트 화면의 '허브 옛 코드' 칩(GET /api/state · 페이지)
        sess.router = R.Router(home_ctx=self.ctx(sess), on_stop=lambda: threading.Thread(target=self.close, args=(name,), daemon=True).start(),
                               on_restart=self.restarter)
        sess.record_before = self._read_record(sess.out)
        sess.alias = self._alias(sess, (sess.record_before or {}).get("port"))
        sess.start()
        self.sessions[name] = sess
        self._write_record(sess)
        print("[hd] 프로젝트를 열었어요: %s → %s" % (name, self.url(sess)), file=sys.stderr, flush=True)
        return sess

    def _alias(self, sess, port):
        """옛 도우미 포트에서도 같은 세션을 낸다(옛 주소의 /api/* · 화면 파일). 못 열면 None."""
        if not isinstance(port, int) or not 0 < port < 65536 or port == self.hub_port():
            return None

        class H(R.SessionHandler):
            router = sess.router

            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(sess.out), **k)

            def target(self, path):
                return sess, path
        try:
            srv = _Alias(("127.0.0.1", port), H)
        except OSError as e:
            print("[hd] 지난 도우미 포트 %d 를 열지 못해 별칭 없이 열어요(%s)" % (port, e), file=sys.stderr, flush=True)
            return None
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def close(self, name):
        """세션 닫기 → 닫았나. 지켜보기를 멈추고 별칭 포트를 닫고 .hd-helper.json 을 처음 것으로."""
        with self.lock:
            sess = self.sessions.pop(name, None)
        if sess is None:
            return False
        sess.close()
        if sess.alias is not None:
            sess.alias.shutdown(); sess.alias.server_close()
        self._restore_record(sess)
        print("[hd] 프로젝트를 닫았어요: %s" % name, file=sys.stderr, flush=True)
        return True

    def close_out(self, name):                       # 휴지통·잊기 — 그 이름의 세션이 열려 있으면 닫는다
        return self.close(name)

    def close_all(self):
        with self.lock:
            names = list(self.sessions)
        for n in names:
            self.close(n)

    # ------------------------------------------------------------ <out>/.hd-helper.json
    def _read_record(self, out):
        p = pathlib.Path(out) / C.HELPER_FILE
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
        except (OSError, ValueError):
            return None

    def _write_record(self, sess):
        port = sess.alias.server_address[1] if sess.alias is not None else self.hub_port()
        doc = {"url": self.url(sess), "pid": os.getpid(), "port": port, "token": sess.token, "code": self.code, "hub": True}
        try:
            (sess.out / C.HELPER_FILE).write_text(json.dumps(doc), encoding="utf-8")
        except OSError as e:
            print("[hd] 도우미 기록을 쓰지 못했어요(%s): %s" % (e, sess.out), file=sys.stderr, flush=True)

    def _restore_record(self, sess):
        p = sess.out / C.HELPER_FILE
        cur = self._read_record(sess.out) or {}
        if cur.get("pid") not in (None, os.getpid()) or cur.get("token") not in (None, sess.token):
            return                                    # 그 사이 다른 도우미가 덮어썼다 — 그대로
        before = sess.record_before or {}
        try:
            if isinstance(before.get("port"), int):
                p.write_text(json.dumps({"port": before["port"]}), encoding="utf-8")
            else:
                p.unlink(missing_ok=True)
        except OSError as e:
            print("[hd] 도우미 기록을 되돌리지 못했어요(%s): %s" % (e, p), file=sys.stderr, flush=True)
