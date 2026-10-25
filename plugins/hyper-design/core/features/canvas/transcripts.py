"""Client 어댑터 — 고른 터미널의 대화 기록 읽기(S3b). 새 도구 = 구현 하나 + REGISTRY 한 줄(source_for 는 그대로).

  TranscriptSource     인터페이스 — kind · read(since) → (entries, cursor). since = None|'' (처음부터) · END(줄 없이 지금 끝) · 앞서 받은 커서
  ClaudeTranscript     Claude Code 세션 jsonl(<claude 집>/projects/<인코딩한 cwd>/<session>.jsonl) — 지난 바이트 자리부터 조각(CHUNK)씩
  PaseoTranscript      `paseo logs <id> --json [--since <시각> | --tail 1]` — 읽기만(보내기·만들기 없음), 창 없음(NO_WINDOW)
  NoTranscript         읽을 길이 없는 에이전트(other·codex·session 없는 claude) — 늘 빈 목록 + 이유(why)
  source_for(record, env)  presence 항목(또는 {id} — 붙인 Paseo id) → 소스. 종류 고르기 = kind_of(순수) + REGISTRY
글 해석은 transcript_parse(순수), 여기는 파일·하위 프로세스만. 상태 = 찾은 파일 경로 하나(ClaudeTranscript). 디스크에 쓰지 않는다.
읽을 수 없으면(파일 없음·CLI 실패) TranscriptUnavailable(한국어 한 줄) — 숨기지 않는다(펌프가 [hd] 한 줄, HTTP 는 error 칸).
"""
import collections, os, pathlib, re, subprocess, sys

import adapters as AD
import transcript_parse as TP

END = TP.END
CHUNK = 1 << 20                                      # read 한 번에 읽는 바이트(1 MB)
LONG_LINE_MAX = 32 << 20                             # 한 줄이 이보다 길면 읽지 않고 건너뜀([hd] — 다음 줄부터)
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")   # 세션 id = 파일 이름 — 경로 글자(/ \ ..)는 받지 않는다
PASEO_TIMEOUT = 15

SourceEnv = collections.namedtuple("SourceEnv", "claude_home cwd_hints paseo_find run")


class TranscriptUnavailable(Exception):
    """지금 읽을 수 없음(한국어 한 줄). 커서는 그대로 — 다음 차례에 다시."""


class TranscriptSource:
    """인터페이스. kind = 'claude'|'paseo'|'none'. read(since) → (entries, cursor) — 같은 cursor 로 다시 부르면 새 줄만.
    every = 펌프가 다시 읽는 간격(초, 값 칸 — 비싼 소스는 길게)."""
    kind = ""
    every = 1.0

    def read(self, since):
        raise NotImplementedError


class NoTranscript(TranscriptSource):
    kind = "none"
    every = 30.0

    def __init__(self, why="이 에이전트의 대화 기록을 읽는 길이 없어요"):
        self.why = why

    def read(self, since):
        return [], since or ""


def encode_cwd(path):
    """Claude Code 의 projects 폴더 이름 규칙: 글자·숫자 밖은 모두 '-'(C:\\Code\\hyper-design → C--Code-hyper-design)."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def cwd_chain(cwd):
    """에이전트 작업 폴더 → 그 폴더와 위 폴더들(가까운 차례, 순수). Claude 는 띄운 폴더 이름으로 기록하는데 hd 는 그 아래에서 돌 수 있어서.
    빈 값·글이 아님 = ()."""
    if not isinstance(cwd, str) or not cwd.strip():
        return ()
    path = pathlib.PurePath(cwd.strip())
    return tuple(str(x) for x in (path,) + tuple(path.parents))


def claude_home(env):
    return pathlib.Path(env.get("CLAUDE_CONFIG_DIR") or pathlib.Path.home() / ".claude")


class ClaudeTranscript(TranscriptSource):
    """session 하나의 jsonl 만 연다(다른 세션 파일은 열지 않는다). 경로: cwd 힌트 폴더 먼저, 없으면(anywhere 일 때만)
    projects/*/<session>.jsonl 이름으로만 찾기. anywhere=False = 힌트 폴더 밖은 보지 않는다(에이전트가 cwd 를 알려 준 경우)."""
    kind = "claude"

    def __init__(self, session, home, cwd_hints=(), anywhere=True):
        if not isinstance(session, str) or not SESSION_RE.match(session):
            raise ValueError("claude session id 가 아니에요")
        self.session, self.home, self.cwd_hints, self.anywhere = session, pathlib.Path(home), tuple(cwd_hints), anywhere
        self.path = None

    def locate(self):
        if self.path is not None and self.path.is_file():
            return self.path
        name, root = self.session + ".jsonl", self.home / "projects"
        for hint in self.cwd_hints:
            folder = encode_cwd(hint)                # 글자·숫자·'-' 뿐 — '..'·구분자가 남지 않아 projects 밖으로 못 나간다
            p = root / folder / name
            if p.parent.parent == root and p.is_file():
                self.path = p
                return p
        if not self.anywhere:
            raise TranscriptUnavailable("Claude 세션 기록 파일을 이 에이전트 폴더에서 찾지 못했어요(%s)" % self.session)
        hits = sorted(root.glob("*/" + name)) if root.is_dir() else []
        if not hits:
            raise TranscriptUnavailable("Claude 세션 기록 파일을 찾지 못했어요(%s)" % self.session)
        self.path = hits[0]
        return self.path

    def read(self, since):
        start = TP.claude_cursor(since)
        path = self.locate()
        try:
            with open(path, "rb") as f:
                size = os.fstat(f.fileno()).st_size
                if start == END:
                    return [], TP.claude_cursor_str(self._line_end(f, size))
                if start > size:                     # 파일이 줄었음(다른 파일로 바뀜) — 처음부터 다시
                    start = 0
                f.seek(start)
                data = f.read(CHUNK)
                entries, used = TP.parse_claude(data, TP.ENTRIES_MAX, start)
                if used == 0 and len(data) == CHUNK:  # 한 줄이 CHUNK 보다 김 — 그 줄 끝까지 이어 읽기
                    entries, used = self._long_line(f, start, data)
        except OSError as e:
            raise TranscriptUnavailable("Claude 세션 기록을 읽지 못했어요: %s" % e)
        return entries, TP.claude_cursor_str(start + used)

    @staticmethod
    def _line_end(f, size):
        """지금 끝 = 마지막 줄바꿈 바로 뒤(덜 쓴 마지막 줄은 아직 안 먹은 것으로)."""
        back = min(size, CHUNK)
        f.seek(size - back)
        tail = f.read(back)
        nl = tail.rfind(b"\n")
        return size - back + nl + 1 if nl >= 0 else (0 if back == size else size - back)

    @staticmethod
    def _long_line(f, start, data):
        """CHUNK 안에 줄바꿈이 없는 긴 줄 — 그 줄 끝까지 이어 읽는다. LONG_LINE_MAX 를 넘으면 해석하지 않고 건너뜀([hd] 한 줄)."""
        buf, n = bytearray(data), len(data)
        while True:
            more = f.read(CHUNK)
            if not more:
                return [], 0                         # 아직 덜 쓴 줄 — 다음 read 에서
            nl = more.find(b"\n")
            part = more if nl < 0 else more[:nl + 1]
            n += len(part)
            if n <= LONG_LINE_MAX:
                buf += part
            if nl >= 0:
                break
        if n > LONG_LINE_MAX:
            print("[hd] 대화 기록 한 줄이 너무 길어 건너뛰어요(%d바이트)" % n, file=sys.stderr, flush=True)
            return [], n
        return TP.parse_claude(bytes(buf), TP.ENTRIES_MAX, start)


class PaseoTranscript(TranscriptSource):
    """Paseo 에이전트 하나의 기록 — `paseo logs <id> --json`(읽기만). run = 테스트의 가짜 실행기."""
    kind = "paseo"
    every = 3.0                                      # paseo CLI 를 띄우는 값이 커서(node) 3초마다

    def __init__(self, agent, find, run=None):
        self.agent, self.find, self.run = agent, find, run or AD._run

    def _logs(self, extra):
        cmd = self.find()
        if not cmd:
            raise TranscriptUnavailable(AD.NO_PASEO)
        args = AD._paseo_args(cmd, ["logs", self.agent, "--json"] + extra)
        try:
            r = self.run(args, capture_output=True, text=True, encoding="utf-8", timeout=PASEO_TIMEOUT, creationflags=AD.NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise TranscriptUnavailable("paseo logs 실패: %s" % e)
        if r.returncode != 0:
            raise TranscriptUnavailable("paseo logs 종료 코드 %d" % r.returncode)
        return TP.parse_paseo(r.stdout if isinstance(r.stdout, str) else (r.stdout or b"").decode("utf-8", "replace"))

    def read(self, since):
        cur = TP.paseo_cursor(since)
        if cur == END:
            last = self._logs(["--tail", "1"])
            return [], TP.paseo_cursor_str(last[-1]["at"], [last[-1]["id"]]) if last else ""
        at, seen = cur
        entries = self._logs(["--since", at] if at else [])
        return TP.paseo_after(entries, at, seen)


# ---------------------------------------------------------------- 고르기(OCP: 새 도구 = 클래스 하나 + 여기 한 줄)
def kind_of(record):
    """presence 항목 → 소스 종류(순수). kind 가 없으면(붙이기만 한 id = 오늘의 Paseo id — adapters.choose 와 같은 규칙) 'paseo'."""
    if not isinstance(record, dict) or not record.get("id"):
        return None
    return record.get("kind") or "paseo"


def _claude(record, env):
    """session(SDK = CLAUDE_CODE_SESSION_ID) 의 jsonl. hello 에 cwd 가 있으면 그 폴더(와 위 폴더)의 projects 폴더에서만, 없으면(옛 SDK) 캔버스 힌트 + 이름 찾기."""
    if not record.get("session"):
        return NoTranscript("이 Claude 터미널이 세션 id 를 알려 주지 않았어요(hello 의 session)")
    chain = cwd_chain(record.get("cwd"))
    try:
        if chain:
            return ClaudeTranscript(record["session"], env.claude_home, chain, anywhere=False)
        return ClaudeTranscript(record["session"], env.claude_home, env.cwd_hints)
    except ValueError as e:
        return NoTranscript(str(e))


def _paseo(record, env):
    return PaseoTranscript(record["id"], env.paseo_find, env.run)


REGISTRY = {"claude": _claude, "paseo": _paseo}


def default_env(cwd_hints=(), paseo=None, environ=None):
    environ = os.environ if environ is None else environ
    return SourceEnv(claude_home(environ), tuple(str(h) for h in cwd_hints if h), lambda: AD._paseo_cmd(paseo), None)


def source_for(record, env=None):
    """presence 항목 → TranscriptSource. 모르는 종류 = NoTranscript."""
    make = REGISTRY.get(kind_of(record))
    return make(record, env or default_env()) if make else NoTranscript()
