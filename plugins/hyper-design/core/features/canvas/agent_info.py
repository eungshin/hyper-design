"""Edge — 고른 Paseo 터미널의 모델·생각 깊이·컨텍스트 사용량(R28): GET /api/agents/info · POST /api/agents/effort.

읽는 곳(모두 읽기만, 바꾸는 것은 effort 하나):
  `paseo ls -g --json`            Queue.agents() 의 5초 캐시 그대로 — provider('claude/claude-opus-5-5')·thinking
  `paseo provider models <p> --thinking --json`   생각 깊이 선택지(MODELS_TTL 캐시, 실패 = agent_meta.DEFAULT_EFFORTS)
  <PASEO_HOME|~/.paseo>/agents/*/<id>.json         runtimeInfo.sessionId · cwd(Claude 세션 파일 찾기 — SESSION_TTL 캐시)
  <CLAUDE_CONFIG_DIR|~/.claude>/projects/<cwd>/<session>.jsonl 꼬리(TAIL)  마지막 usage → 컨텍스트(Claude 만, 모르면 null)
바꾸기: `paseo agent update <id> --thinking <opt>` — PaseoAdapter.update_thinking(선택지로 먼저 검사), 성공하면 ls 캐시를 비우고 새 답.
대상은 늘 붙은 받는 곳(Queue.agent) 하나 — 다른 에이전트의 기록은 열지 않는다(transcripts 와 같은 사생활 규칙).
규칙(모양·합·최대·반올림·선택지)은 agent_meta(Model). 상태 = 선택지 캐시 · 세션 파일 캐시(자물쇠 하나).
오류 탐지: 받는 곳 없음·Paseo 목록에 없음 = 200 {agent, paseo:false}(대화창 줄을 숨김) · 기록을 못 읽음 = context null + [hd] 한 줄(같은 이유는 한 번) ·
  effort 모양·선택지 밖 = 400 · Paseo 가 거절 = 502 {error: 그 까닭}.
"""
import json, os, pathlib, re, sys, threading, time

import agent_meta as AM
import transcripts as TR

MODELS_TTL = 300.0
SESSION_TTL = 30.0
TAIL = 512 * 1024                                    # jsonl 끝에서 이만큼만 읽는다(마지막 usage 는 끝 가까이)
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def paseo_home(env):
    return pathlib.Path(env.get("PASEO_HOME") or pathlib.Path.home() / ".paseo")


class AgentInfo:
    def __init__(self, queue, adapter, paseo_dir=None, claude_dir=None, clock=time.monotonic):
        self.queue, self.adapter, self.clock = queue, adapter, clock
        self.paseo_dir = pathlib.Path(paseo_dir) if paseo_dir else paseo_home(os.environ)
        self.claude_dir = pathlib.Path(claude_dir) if claude_dir else TR.claude_home(os.environ)
        self.lock = threading.Lock()
        self.models = {}                             # provider → (시각, 줄 | None)
        self.sessions = {}                           # agent id → (시각, (session, cwd) | None)
        self.warned = set()

    def _warn(self, why):
        if why in self.warned:
            return
        self.warned.add(why)
        print("[hd] 에이전트 정보: %s" % why, file=sys.stderr, flush=True)

    def _row(self):
        aid = self.queue.agent
        if not aid:
            return None, None
        res = self.queue.agents()
        for r in res.get("agents") or ():
            if r.get("id") == aid:
                return aid, r
        return aid, None

    def _options(self, provider, model):
        if not provider:
            return list(AM.DEFAULT_EFFORTS)
        t = self.clock()
        with self.lock:
            hit = self.models.get(provider)
        if hit is None or t - hit[0] >= MODELS_TTL:
            rows, why = self.adapter.read_json(["provider", "models", provider, "--thinking", "--json"])
            if why:
                self._warn("모델 선택지를 읽지 못했어요(%s) — 기본 선택지로" % why)
            hit = (t, rows if isinstance(rows, list) else None)
            with self.lock:
                self.models[provider] = hit
        return AM.effort_options(hit[1], model)

    def _session(self, aid):
        """Paseo 기록 파일 → (session, cwd) | None."""
        if not ID_RE.match(aid):
            return None
        t = self.clock()
        with self.lock:
            hit = self.sessions.get(aid)
        if hit is not None and t - hit[0] < SESSION_TTL:
            return hit[1]
        got = None
        root = self.paseo_dir / "agents"
        for p in sorted(root.glob("*/" + aid + ".json")) if root.is_dir() else ():
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                self._warn("Paseo 기록 파일을 읽지 못했어요(%s): %s" % (e, p.name))
                continue
            ri = doc.get("runtimeInfo") if isinstance(doc, dict) else None
            sid = ri.get("sessionId") if isinstance(ri, dict) else None
            if isinstance(sid, str) and TR.SESSION_RE.match(sid):
                got = (sid, doc.get("cwd") if isinstance(doc.get("cwd"), str) else None)
                break
        with self.lock:
            self.sessions[aid] = (t, got)
        return got

    def _usage(self, aid, row):
        found = self._session(aid)
        if not found:
            return None
        sid, cwd = found
        src = TR.ClaudeTranscript(sid, self.claude_dir, TR.cwd_chain(cwd or row.get("cwd")), anywhere=False)
        try:
            path = src.locate()
            with open(path, "rb") as f:
                size = os.fstat(f.fileno()).st_size
                start = max(0, size - TAIL)
                f.seek(start)
                data = f.read(TAIL)
        except (TR.TranscriptUnavailable, OSError) as e:
            self._warn("컨텍스트 사용량을 읽지 못했어요: %s" % e)
            return None
        return AM.last_usage(data, whole=(start == 0))

    def get(self, q=None):
        """GET /api/agents/info → 200 {agent:null} | {agent, paseo:false} | {agent, paseo:true, name, provider, model, modelLabel, effort, effortOptions, context}."""
        aid, row = self._row()
        if not aid:
            return 200, {"agent": None, "paseo": False}
        if row is None:
            return 200, {"agent": aid, "paseo": False}
        provider, model = AM.split_provider(row.get("provider"))
        usage = self._usage(aid, row) if provider == "claude" else None
        return 200, dict(AM.info(row, self._options(provider, model), usage), paseo=True)

    def effort(self, body):
        """POST /api/agents/effort {effort} → 200 새 정보 | 400 | 409(받는 곳이 Paseo 에이전트가 아님) | 502 {error}."""
        opt = body.get("effort") if isinstance(body, dict) else None
        aid, row = self._row()
        if row is None:
            return 409, {"error": "받는 곳이 Paseo 에이전트가 아니에요 — 생각 깊이를 바꿀 수 없어요"}
        provider, model = AM.split_provider(row.get("provider"))
        err = AM.check_effort(opt, self._options(provider, model))
        if err:
            return 400, {"error": err}
        ok, why = self.adapter.update_thinking(aid, opt)
        if not ok:
            print("[hd] 생각 깊이를 바꾸지 못했어요(%s): %s" % (aid, why), file=sys.stderr, flush=True)
            return 502, {"error": "생각 깊이를 바꾸지 못했어요 — %s" % why}
        with self.queue.agents_lock:
            self.queue.agents_cache = None           # 다음 ls 는 새로(바뀐 thinking)
        return self.get()
