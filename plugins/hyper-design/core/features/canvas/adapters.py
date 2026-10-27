"""AgentAdapter — 접속하지 않은(이벤트를 읽지 않는) 에이전트에게 요청문을 넘기는 길(task 47-5a). 새 도구 = 구현 하나 더.

  choose(target, entry, ready)   순수 규칙: 받는 곳 → 'event' | 'paseo' | 'claude' | 'queue'
  config_from_env(env)           순수: HD_CLAUDE_WAKE · HD_ALLOW_SPAWN · HD_CLAUDE_CMD (모두 기본 꺼짐)
  NoneAdapter                    대기열 파일만(파일은 부르는 쪽이 이미 씀 — 오늘 동작)
  PaseoAdapter                   `paseo send <id> --prompt-file <파일> [--image <절대 경로>]… --no-wait`(R28: 첨부 이미지를 진짜 이미지로) ·
                                 update_thinking = `paseo agent update <id> --thinking <opt>` · read_json = 읽기만 하는 `paseo … --json`(R28 모델 선택지)
  ClaudeCliAdapter               `claude -p --resume <session>` — 표준 입력 = 요청문 파일, 출력 = 대기열 옆 .claude.log. 기다리지 않음. 기본 꺼짐
  PaseoSpawner                   새 터미널 에이전트 열기 `paseo run --no-wait …` — HD_ALLOW_SPAWN=1 이 아니면 403 disabled(밖으로 나가는 일 — 캔버스가 먼저 사용자에게 묻는다)
자식 프로세스는 모두 creationflags=NO_WINDOW(창 없이 뜬 서버에서 콘솔이 깜빡이지 않게). run·popen 은 테스트가 가짜로 바꿔 끼운다.
상태 없음(어댑터는 찾는 법 find 와 켜짐 enabled 만 안다). 쓰는 곳 = send_queue.Queue.send · send_queue.forward(옛 이름).
"""
import json, os, pathlib, shutil, subprocess

import agent_meta as AM  # paseo 인자 모양(send_argv · update_argv, R28)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PASEO_DEFAULT = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Paseo" / "resources" / "bin" / "paseo.cmd"
SPAWN_KINDS = ("claude", "codex")                    # Paseo provider 이름 그대로
NO_PASEO = "Paseo 를 찾을 수 없어요"


def _paseo_cmd(paseo=None):
    """Paseo CLI 경로 — 넘긴 것(--paseo-cmd·HD_PASEO_CMD, 테스트의 가짜) > 설치 위치(PASEO_DEFAULT) > PATH. 없으면 None."""
    return paseo or (str(PASEO_DEFAULT) if PASEO_DEFAULT.exists() else shutil.which("paseo"))


def _paseo_args(cmd, rest):
    args = [cmd] + rest
    return ["cmd", "/c"] + args if cmd.lower().endswith((".cmd", ".bat")) else args


def config_from_env(env):
    """환경 → {claude_wake, allow_spawn, claude_cmd}. 켜기는 정확히 '1' 만(기본 모두 꺼짐)."""
    return {"claude_wake": env.get("HD_CLAUDE_WAKE") == "1", "allow_spawn": env.get("HD_ALLOW_SPAWN") == "1",
            "claude_cmd": env.get("HD_CLAUDE_CMD") or None}


def choose(target, entry, ready):
    """받는 곳 고르기(순수). target = 보낼 에이전트 id | None, entry = AgentPresence 항목 | None, ready = {'paseo': bool, 'claude': bool}.
    접속 중(here)이고 이벤트를 읽음(listen) = 'event' · claude 이고 이어 받을 session 이 있고 깨우기가 켜짐 = 'claude' ·
    모르는 id(오늘의 Paseo id) 또는 kind paseo 이고 Paseo 가 있음 = 'paseo' · 그 밖 = 'queue'(대기열 파일만)."""
    if not target:
        return "queue"
    if entry and entry.get("state") == "here" and entry.get("listen"):
        return "event"
    if entry and entry.get("kind") == "claude":
        return "claude" if entry.get("session") and ready.get("claude") else "queue"
    if (entry is None or entry.get("kind") == "paseo") and ready.get("paseo"):
        return "paseo"
    return "queue"


class AgentAdapter:
    """인터페이스 — name · ready() → 쓸 수 있나 · send(path, text, target, images=()) → (넘겼나, 못 넘긴 이유 | None).
    target = id 또는 presence 항목 · images = 첨부 이미지 절대 경로(진짜 이미지로 넘길 수 있는 어댑터만 쓴다 — 글의 '첨부 이미지:' 줄은 그대로)."""
    name = ""

    def ready(self):
        raise NotImplementedError

    def send(self, path, text, target, images=()):
        raise NotImplementedError


class NoneAdapter(AgentAdapter):
    name = "queue"

    def ready(self):
        return True

    def send(self, path, text, target, images=()):
        return True, None


def _run(args, **kw):                                # 기본 실행기 — 늘 창 없이
    kw["creationflags"] = NO_WINDOW
    return subprocess.run(args, **kw)


class PaseoAdapter(AgentAdapter):
    name = "paseo"

    def __init__(self, find, run=None):
        self.find, self.run = find, run or _run

    @property
    def cmd(self):
        return self.find()

    def ready(self):
        return bool(self.find())

    def send(self, path, text, target, images=()):
        cmd = self.find()
        aid = target.get("id") if isinstance(target, dict) else target
        if not cmd or not aid:
            return False, NO_PASEO if not cmd else "받을 에이전트가 없어요"
        try:
            r = self.run(_paseo_args(cmd, AM.send_argv(aid, path, images)),
                         capture_output=True, timeout=60, creationflags=NO_WINDOW)   # 바이트로(cmd 오류 글은 UTF-8 이 아닐 수 있음 — 종료 코드만 본다)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, "paseo send 실패: %s" % e
        return (True, None) if r.returncode == 0 else (False, "paseo send 종료 코드 %d" % r.returncode)

    def _call(self, rest, timeout):
        """paseo 한 번 → (종료 코드, stdout 글, stderr 마지막 줄) | 오류 글(문자열). 바이트로 받아 UTF-8 로 푼다(한글)."""
        cmd = self.find()
        if not cmd:
            return NO_PASEO
        try:
            r = self.run(_paseo_args(cmd, rest), capture_output=True, timeout=timeout, creationflags=NO_WINDOW,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1"))
        except (OSError, subprocess.TimeoutExpired) as e:
            return "paseo 실행 실패: %s" % e
        dec = lambda b: b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")
        err = [x for x in dec(r.stderr).strip().splitlines() if x.strip()]
        return r.returncode, dec(r.stdout), (err[-1][:200] if err else "")

    def update_thinking(self, aid, opt):
        """생각 깊이 바꾸기(R28) → (바꿨나, 이유 | None). 부르는 쪽이 선택지로 먼저 검사한다(agent_meta.check_effort)."""
        if not aid:
            return False, "받을 에이전트가 없어요"
        got = self._call(AM.update_argv(aid, opt), 30)
        if isinstance(got, str):
            return False, got
        code, out, err = got
        return (True, None) if code == 0 else (False, err or out.strip()[-200:] or "paseo agent update 종료 코드 %d" % code)

    def read_json(self, rest, timeout=20):
        """읽기만 하는 `paseo … --json` → (값, None) | (None, 이유)."""
        got = self._call(list(rest), timeout)
        if isinstance(got, str):
            return None, got
        code, out, err = got
        if code != 0:
            return None, err or "종료 코드 %d" % code
        try:
            return json.loads(out), None
        except ValueError:
            return None, "JSON 이 아니에요"


def _popen(args, **kw):
    kw["creationflags"] = NO_WINDOW
    return subprocess.Popen(args, **kw)


class ClaudeCliAdapter(AgentAdapter):
    """잠든 Claude Code 세션 깨우기 — `claude -p --resume <session>`(요청문 = 표준 입력). enabled(HD_CLAUDE_WAKE=1)가 아니면 쓰지 않는다."""
    name = "claude"

    def __init__(self, find, enabled=False, popen=None, cwd=None):
        self.find, self.enabled, self.popen, self.cwd = find, enabled, popen or _popen, cwd

    def ready(self):
        return bool(self.enabled and self.find())

    def send(self, path, text, target, images=()):        # 이미지는 글의 '첨부 이미지:' 줄로만(claude -p 표준 입력은 글)
        session = target.get("session") if isinstance(target, dict) else None
        if not self.ready():
            return False, "claude 깨우기가 꺼져 있어요(HD_CLAUDE_WAKE=1)"
        if not session:
            return False, "이어 받을 claude 세션이 없어요"
        path = pathlib.Path(path)
        try:
            with open(path, "rb") as stdin, open(path.with_suffix(".claude.log"), "ab") as log:
                self.popen([self.find(), "-p", "--resume", session], stdin=stdin, stdout=log, stderr=subprocess.STDOUT,
                           cwd=self.cwd, creationflags=NO_WINDOW)
        except OSError as e:
            return False, "claude 를 띄우지 못했어요: %s" % e
        return True, None


class PaseoSpawner:
    """새 터미널 에이전트 열기(POST /agents/spawn {kind}). enabled(HD_ALLOW_SPAWN=1)가 아니면 403 disabled — 실제 에이전트를 만드는 일이라 기본 꺼짐."""

    def __init__(self, find, enabled=False, run=None):
        self.find, self.enabled, self.run = find, enabled, run or _run

    def spawn(self, body, cwd, project):
        kind = body.get("kind") if isinstance(body, dict) else None
        if kind not in SPAWN_KINDS:
            return 400, {"error": "kind: %s 중 하나여야 해요" % "|".join(SPAWN_KINDS)}
        if not self.enabled:
            return 403, {"error": "새 에이전트 열기는 꺼져 있어요(서버를 HD_ALLOW_SPAWN=1 로 띄워야 해요)", "reason": "disabled"}
        cmd = self.find()
        if not cmd:
            return 503, {"error": NO_PASEO}
        prompt = ("Hyper Design 캔버스 '%s' 의 요청을 받는 에이전트예요. hd attach 로 접속한 뒤 hd wait 로 보낸 메모를 받아 처리하고 hd reply 로 답하세요." % project)
        args = _paseo_args(cmd, ["run", "--no-wait", "--json", "--provider", kind, "--cwd", str(cwd), "--title", "hd · %s" % project, prompt])
        try:
            r = self.run(args, capture_output=True, timeout=60, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 502, {"error": "paseo run 실패: %s" % e}
        if r.returncode != 0:
            return 502, {"error": "paseo run 종료 코드 %d" % r.returncode}
        try:
            out = r.stdout.decode("utf-8") if isinstance(r.stdout, bytes) else (r.stdout or "")
            doc = json.loads(out)
            aid = doc.get("id") if isinstance(doc, dict) and isinstance(doc.get("id"), str) else None
        except ValueError:
            aid = None
        return 200, {"spawned": True, "via": "paseo", "agent": aid}
