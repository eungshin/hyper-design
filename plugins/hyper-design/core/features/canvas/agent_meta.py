"""Model — 고른 Paseo 터미널의 모델·생각 깊이(effort)·컨텍스트 사용량(R28) 규칙. I/O 없음(바이트·dict 를 받아 값을 낸다).

  split_provider(s)            'claude/claude-opus-5-5' → ('claude', 'claude-opus-5-5') · 'codex' → ('codex', None)
  model_label(model)           표(MODELS, Paseo model-manifest 와 같은 값) → 'Opus 5.5' · 모르면 모델 id 그대로
  context_max(model)           표 → 최대 토큰 · '[1m]' 붙은 id = 1M · 모르면 DEFAULT_MAX(200k — 작게 잡아 넘치면 100%)
  usage_sum(u)                 Claude usage → input + cache_creation + cache_read + output(Paseo streamUsedTokens 와 같은 식) | None
  last_usage(data, whole)      Claude 세션 jsonl 꼬리 바이트 → 마지막 assistant(옆 대화·<synthetic> 빼고)의 usage | None
  context(used, max)           → {used, max, pct}(pct = 반올림 정수, 0..100) | None(모름 — 고리를 숨긴다, 0% 가 아니다)
  effort_options(rows, model)  `paseo provider models <p> --thinking --json` 줄 → 그 모델의 thinkingOptionIds | 없으면 DEFAULT_EFFORTS
  check_effort(opt, options)   → None | 한국어 이유
  info(row, options, usage)    `paseo ls -g --json` 한 줄(provider·thinking) + 선택지 + usage → 답 모양 {agent, name, provider, model, modelLabel, effort, effortOptions, context}
  send_argv · update_argv      paseo 인자(--image 마다 하나 · agent update --thinking)
상태 없음. 부르는 곳: agent_info.AgentInfo(Edge) · adapters.PaseoAdapter.
"""
import json

# Paseo model-manifest(claude provider)의 id → (보이는 이름, contextWindowMaxTokens). 새 모델이 오면 한 줄.
MODELS = {
    "claude-opus-5-5": ("Opus 5.5", 1000000),
    "claude-opus-5": ("Opus 5", 1000000),
    "claude-mythos-5-1": ("Mythos 5.1", 1000000),
    "claude-fable-5-1": ("Fable 5.1", 1000000),
    "claude-fable-5": ("Fable 5", 1000000),
    "claude-opus-4-8[1m]": ("Opus 4.8 1M", 1000000),
    "claude-opus-4-8": ("Opus 4.8", 200000),
    "claude-sonnet-5-5": ("Sonnet 5.5", 1000000),
    "claude-sonnet-5": ("Sonnet 5", 200000),
    "claude-sonnet-5[1m]": ("Sonnet 5 1M", 1000000),
    "claude-opus-4-7[1m]": ("Opus 4.7 1M", 1000000),
    "claude-opus-4-7": ("Opus 4.7", 200000),
    "claude-opus-4-6[1m]": ("Opus 4.6 1M", 1000000),
    "claude-opus-4-6": ("Opus 4.6", 200000),
    "claude-sonnet-4-6[1m]": ("Sonnet 4.6 1M", 1000000),
    "claude-sonnet-4-6": ("Sonnet 4.6", 200000),
    "claude-haiku-5-5": ("Haiku 5.5", 1000000),
    "claude-haiku-4-5": ("Haiku 4.5", 200000),
}
DEFAULT_MAX = 200000
DEFAULT_EFFORTS = ("low", "medium", "high", "xhigh", "max")
OPT_MAX = 32                                         # 생각 깊이 id 길이 한도(인자로 넘기므로 모양도 본다)


def split_provider(s):
    if not isinstance(s, str) or not s.strip():
        return None, None
    p, _, m = s.strip().partition("/")
    return p or None, m or None


def model_label(model):
    if not isinstance(model, str) or not model:
        return None
    hit = MODELS.get(model)
    return hit[0] if hit else model


def context_max(model):
    if not isinstance(model, str) or not model:
        return DEFAULT_MAX
    hit = MODELS.get(model)
    if hit:
        return hit[1]
    return 1000000 if model.endswith("[1m]") else DEFAULT_MAX


def _n(v):
    return v if type(v) is int and v >= 0 else 0


def usage_sum(u):
    if not isinstance(u, dict):
        return None
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    if not any(type(u.get(k)) is int for k in keys):
        return None
    return sum(_n(u.get(k)) for k in keys)


def last_usage(data, whole=True):
    """jsonl 바이트(파일 꼬리) → 마지막 usage dict | None. whole=False 면 첫 줄은 잘린 줄이라 버린다. 깨진 줄·덜 쓴 마지막 줄은 건너뛴다."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        return None
    lines = bytes(data).split(b"\n")
    if not whole:
        lines = lines[1:]
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw or b'"usage"' not in raw:
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(row, dict) or row.get("type") != "assistant" or row.get("isSidechain"):
            continue
        msg = row.get("message")
        if not isinstance(msg, dict) or msg.get("model") == "<synthetic>":
            continue
        if usage_sum(msg.get("usage")) is not None:
            return msg["usage"]
    return None


def context(used, mx):
    if type(used) is not int or used < 0 or type(mx) is not int or mx <= 0:
        return None
    return {"used": used, "max": mx, "pct": max(0, min(100, int(used * 100 / mx + 0.5)))}


def effort_options(rows, model):
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict) and r.get("id") == model and isinstance(r.get("thinkingOptionIds"), list):
                opts = [o for o in r["thinkingOptionIds"] if isinstance(o, str) and o and len(o) <= OPT_MAX]
                if opts:
                    return opts
    return list(DEFAULT_EFFORTS)


def check_effort(opt, options):
    if not isinstance(opt, str) or not opt:
        return "effort: 생각 깊이 이름이 없어요"
    if opt not in (options or ()):
        return "effort: '%s' 는 이 모델에서 고를 수 없어요(%s)" % (opt[:OPT_MAX], " · ".join(options or ()))
    return None


def info(row, options, usage):
    """ls 한 줄 → 답. row 가 없으면 None. thinking 'auto'·없음 = effort None(알약은 '자동')."""
    if not isinstance(row, dict) or not isinstance(row.get("id"), str):
        return None
    provider, model = split_provider(row.get("provider"))
    effort = row.get("thinking") if isinstance(row.get("thinking"), str) and row.get("thinking") not in ("", "auto") else None
    used = usage_sum(usage)
    return {"agent": row["id"], "name": row.get("name") if isinstance(row.get("name"), str) else None,
            "provider": provider, "model": model, "modelLabel": model_label(model) or provider,
            "effort": effort, "effortOptions": list(options or ()),
            "context": context(used, context_max(model)) if provider == "claude" and used is not None else None}


def send_argv(aid, path, images=()):
    args = ["send", aid, "--prompt-file", str(path)]
    for p in images or ():
        args += ["--image", str(p)]
    return args + ["--no-wait"]


def update_argv(aid, opt):
    return ["agent", "update", aid, "--thinking", opt]
