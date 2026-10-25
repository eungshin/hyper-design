"""프로토콜 v1 잠금(task 47-1) — 지금 helper.py(캔버스 도우미)·home_server(허브 hd home)의 HTTP 모양을 공유 fixture 로 고정한다.

fixture = 같은 폴더 helper.json · hub.json(모양 언어는 README.md). 여기서는 진짜 자식 프로세스(helper.py <out> · hd.py home)를 빈 포트로 띄우고
임시 HD_HOME·USERPROFILE·HOME, 가짜 paseo(--paseo-cmd — 실제 에이전트에 보내지 않는다)로 줄마다 다시 보내 상태 코드와 응답 키·타입을 본다(값은 보지 않음).
47-2(서버 하나)는 이 fixture 를 그대로 다시 돌려 옛 주소가 같은 모양으로 답하는지 확인한다. 12270·12279·실제 ~/.hyper-design 은 건드리지 않는다.
"""
import http.client, json, os, pathlib, re, subprocess, sys, time, urllib.parse

import pytest

HERE = pathlib.Path(__file__).resolve().parent
FEATURES = HERE.parents[2]
HD = FEATURES / "hd"
sys.path[:0] = [str(HD), str(HD / "tests")]
import hd_client as C  # noqa: E402
import hdfix  # noqa: E402

WIN = sys.platform == "win32"
pytestmark = pytest.mark.slow                      # 하위 프로세스·서버 — unit 에서 빠진다(contract.md '테스트 층')


# ---------------------------------------------------------------- 모양 검사(README '모양 언어')
TYPES = {"str": str, "bool": bool, "null": type(None), "list": list, "dict": dict}


def _type_ok(name, v):
    if name == "any":
        return True
    if name == "int":
        return type(v) is int
    if name == "num":
        return type(v) in (int, float)
    return isinstance(v, TYPES[name]) and not (name != "bool" and type(v) is bool)


def check(shape, v, where="$"):
    """shape 와 v 가 맞는가 → 어긋난 곳 목록(빈 목록 = 맞음)."""
    if isinstance(shape, str):
        return [] if any(_type_ok(t, v) for t in shape.split("|")) else ["%s: %s 이어야 하는데 %r" % (where, shape, v)]
    if isinstance(shape, dict) and "$eq" in shape:
        return [] if v == shape["$eq"] and type(v) is type(shape["$eq"]) else ["%s: %r 이어야 하는데 %r" % (where, shape["$eq"], v)]
    if isinstance(shape, dict) and "$list" in shape:
        if not isinstance(v, list):
            return ["%s: 목록이어야 하는데 %r" % (where, v)]
        errs = [] if len(v) >= shape.get("$min", 0) else ["%s: %d개 이상이어야 하는데 %d개" % (where, shape["$min"], len(v))]
        return errs + [e for i, x in enumerate(v) for e in check(shape["$list"], x, "%s[%d]" % (where, i))]
    if isinstance(shape, dict) and "$map" in shape:
        if not isinstance(v, dict):
            return ["%s: 객체여야 하는데 %r" % (where, v)]
        return [e for k, x in v.items() for e in check(shape["$map"], x, "%s.%s" % (where, k))]
    if isinstance(shape, dict):
        if not isinstance(v, dict):
            return ["%s: 객체여야 하는데 %r" % (where, v)]
        errs = []
        for k, s in shape.items():
            if k.endswith("?"):
                if k[:-1] in v:
                    errs += check(s, v[k[:-1]], where + "." + k[:-1])
            elif k not in v:
                errs.append("%s: 키 %s 가 없어요 (있는 키 %s)" % (where, k, sorted(v)))
            else:
                errs += check(s, v[k], where + "." + k)
        return errs
    raise ValueError("모르는 모양: %r" % (shape,))


# ---------------------------------------------------------------- 보내기
def _fill(x, vars_):
    if isinstance(x, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: str(vars_[m.group(1)]), x)
    if isinstance(x, list):
        return [_fill(i, vars_) for i in x]
    if isinstance(x, dict):
        return {k: _fill(v, vars_) for k, v in x.items()}
    return x


def send(port, token, req, vars_):
    """req(fixture 의 request) → (status | 'dropped'(답 없이 끊김) | 'timeout', content-type, 몸통 bytes)."""
    method = req.get("method", "GET")
    path = _fill(req["path"], vars_)
    if "size" in req:
        data = b"x" * req["size"]
    elif "raw" in req:
        data = req["raw"].encode("utf-8")
    elif "body" in req:
        data = json.dumps(_fill(req["body"], vars_), ensure_ascii=False).encode("utf-8")
    else:
        data = None
    h = {"Host": req.get("host", "127.0.0.1:%d" % port)}
    tok = req.get("token", True)
    if tok is True:
        h["X-HD-Token"] = token
    elif isinstance(tok, str):
        h["X-HD-Token"] = tok
    if data is not None:
        h["Content-Type"] = "application/json"
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        return r.status, r.getheader("Content-Type") or "", r.read()
    except TimeoutError:
        return "timeout", "", b""
    except (ConnectionError, http.client.HTTPException, OSError):
        return "dropped", "", b""
    finally:
        c.close()


def replay(name, port, token, vars_):
    """fixture 한 파일을 차례로 다시 보낸다 → 어긋난 줄 목록. save 칸은 답의 값을 다음 줄의 ${이름} 으로."""
    doc = json.loads((HERE / name).read_text(encoding="utf-8"))
    errs, seen = [], 0
    for route in doc["routes"]:
        for case in route["cases"]:
            if "skip" in case:
                continue
            seen += 1
            label = "%s %s [%s]" % (route["method"], route["path"], case["name"])
            exp = case["expect"]
            status, ctype, raw = send(port, token, case["request"], vars_)
            if status != exp["status"]:
                errs.append("%s: 상태 %s 이어야 하는데 %s — %s" % (label, exp["status"], status, raw[:200].decode("utf-8", "replace")))
                continue
            if "ctype" in exp and not ctype.startswith(exp["ctype"]):
                errs.append("%s: Content-Type %s 이어야 하는데 %s" % (label, exp["ctype"], ctype))
            text = raw.decode("utf-8", "replace")
            for s in exp.get("contains", []):
                if _fill(s, vars_) not in text:
                    errs.append("%s: 몸통에 %r 가 없어요" % (label, s))
            if "json" in exp:
                try:
                    body = json.loads(raw)
                except ValueError:
                    errs.append("%s: JSON 이 아니에요: %r" % (label, text[:200]))
                    continue
                errs += ["%s: %s" % (label, e) for e in check(exp["json"], body)]
                for var, key in case.get("save", {}).items():
                    vars_[var] = body[key]
    assert seen, "fixture 에 줄이 없어요: " + name
    return errs


# ---------------------------------------------------------------- 띄우기(임시 HOME · 빈 포트 · 가짜 paseo)
def fake_paseo(d):
    """ls → '[]' · send → 종료 0(아무 데도 보내지 않음). 경로를 돌려준다."""
    d.mkdir(parents=True, exist_ok=True)
    if WIN:
        p = d / "paseo.bat"
        p.write_text("@echo []\r\n", encoding="ascii")
    else:
        p = d / "paseo"
        p.write_text("#!/bin/sh\necho '[]'\n", encoding="ascii")
        p.chmod(0o755)
    return str(p)


def child_env(home, user, paseo):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        e.pop(k, None)
    e.update(USERPROFILE=str(user), HOME=str(user), HD_HUB_PORT="0", HD_PASEO_CMD=paseo)
    return e


def start(args, env, log, mark):
    """자식 서버 → (proc, 찍은 주소). stderr 는 파일로 — 읽지 않는 PIPE 는 버퍼(Windows 약 4 KB)가 차면 서버의 다음 [hd] 줄에서 요청이 멈춘다."""
    err = open(log, "w", encoding="utf-8")
    try:
        p = subprocess.Popen([sys.executable] + args, stdout=subprocess.PIPE, stderr=err, text=True, encoding="utf-8", env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if WIN else 0)
    finally:
        err.close()                                  # 자식이 자기 핸들을 가진다
    url = p.stdout.readline().strip()
    assert url.startswith("http://127.0.0.1:") and mark in url, (url, pathlib.Path(log).read_text(encoding="utf-8", errors="replace"))
    return p, url


def start_hub(env, log):
    return start([str(HD / "hd.py"), "home", "--no-browser", "--port", "0"], env, log, "/?hd=")


def start_helper(out, env, log):
    return start([str(hdfix.HELPER), str(out), "--no-open"], env, log, "/index.html?hd=")


def port_token(url):
    u = urllib.parse.urlparse(url)
    return u.port, urllib.parse.parse_qs(u.query)["hd"][0]


@pytest.fixture
def servers(tmp_path, monkeypatch):
    """허브 + 도우미(proj-a) + 링크만 있는 proj-b(index.html 없음 — 썸네일을 그리지 않음). 모두 임시 HOME 안."""
    home, user = tmp_path / "hd-home", tmp_path / "user"
    user.mkdir()
    monkeypatch.setenv("HD_HOME", str(home))         # 이 프로세스의 hd_client(proj-b 등록 · 끝 정리)도 같은 임시 HD_HOME
    env = child_env(home, user, fake_paseo(tmp_path / "fake-paseo"))
    out = hdfix.make_out(tmp_path / "w")
    b = tmp_path / "w" / "proj-b" / "out"
    b.mkdir(parents=True)
    (b / "screens.json").write_text(json.dumps({"screens": []}), encoding="utf-8")
    C.register(C.abs_out(b))
    thumbs = home / "thumbs"                         # proj-a 썸네일을 미래 시각으로 — 허브가 진짜 브라우저로 다시 그리지 않게
    thumbs.mkdir(parents=True)
    png = thumbs / "proj-a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    far = time.time() + 100 * 365 * 86400
    os.utime(png, (far, far))
    procs = []
    try:
        hub, hub_url = start_hub(env, tmp_path / "hub.log"); procs.append(hub)
        helper, helper_url = start_helper(out, env, tmp_path / "helper.log"); procs.append(helper)
        yield {"hub": port_token(hub_url), "helper": port_token(helper_url), "out": out, "home": home}
    finally:
        for m in C.markers():                        # 이 임시 HD_HOME 에 혹시 떼어 띄운 도우미가 있으면
            if m.get("pid") not in [p.pid for p in procs]:
                C.stop(m)
        for p in reversed(procs):
            hdfix.stop_helper(p)
        rec = home / "home.json"
        if rec.is_file():                            # /api/home 이 다른 허브를 띄웠다면 그것도
            pid = json.loads(rec.read_text(encoding="utf-8")).get("pid")
            if pid and pid not in [p.pid for p in procs]:
                C.kill_pid(pid)


def test_hub_protocol_v1(servers):
    port, token = servers["hub"]
    errs = replay("hub.json", port, token, {"project": "proj-a", "other": "proj-b"})
    assert not errs, "\n".join(errs)


def test_helper_protocol_v1(servers):
    port, token = servers["helper"]
    errs = replay("helper.json", port, token, {"project": "proj-a", "other": "proj-b"})
    assert not errs, "\n".join(errs)


def test_fixtures_name_every_route():
    """fixture 의 라우트 목록 = helper.py · home_api · home_server 가 아는 주소 전부(새 주소를 더하면 여기서 걸린다)."""
    src = (FEATURES / "canvas" / "helper.py").read_text(encoding="utf-8") + (FEATURES / "home" / "home_api.py").read_text(encoding="utf-8")
    known = set(re.findall(r'"(/api/[a-z-]+)"', src))
    named = set()
    for name in ("helper.json", "hub.json"):
        for r in json.loads((HERE / name).read_text(encoding="utf-8"))["routes"]:
            named.add(r["path"].split("?")[0])
    assert known <= named, "fixture 에 없는 주소: %s" % sorted(known - named)
