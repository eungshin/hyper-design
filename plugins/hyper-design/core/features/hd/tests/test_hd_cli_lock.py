"""hd CLI 잠금(task 47-3 1단계) — SDK 로 옮기기 전 지금 출력·종료 코드를 글자 그대로 고정한다(최상위 싼 층 = 자식 프로세스 hd.py).

두 가지 서버에서 같은 대본을 돌린다: 옛 도우미(helper.py <out>) · 허브 안 세션(hd.py home → POST /api/open, task 47-2 '서버 하나').
값이 실행마다 바뀌는 것(주소·out 경로·pid·port·시각)만 <URL> 같은 이름으로 바꿔 비교한다. 임시 HD_HOME·HOME, 가짜 paseo, 빈 포트 — 12270·12279·실제
~/.hyper-design 은 건드리지 않는다. SDK 로 옮긴 뒤 바뀌어도 되는 것은 오류의 '다음:' 꼬리뿐(이 파일의 NEXT_OK).
"""
import json, os, re, subprocess, sys, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"
WIN = sys.platform == "win32"


def child_env(home, user, paseo):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        e.pop(k, None)
    e.update(USERPROFILE=str(user), HOME=str(user), HD_HUB_PORT="0", HD_PASEO_CMD=paseo)
    return e


def fake_paseo(d):
    d.mkdir(parents=True, exist_ok=True)
    if WIN:
        p = d / "paseo.bat"
        p.write_text("@echo []\r\n", encoding="ascii")
    else:
        p = d / "paseo"
        p.write_text("#!/bin/sh\necho '[]'\n", encoding="ascii")
        p.chmod(0o755)
    return str(p)


def start_hub(env, log):
    err = open(log, "w", encoding="utf-8")
    try:
        p = subprocess.Popen([sys.executable, str(HD_PY), "home", "--no-browser", "--port", "0"], stdout=subprocess.PIPE, stderr=err,
                             text=True, encoding="utf-8", env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if WIN else 0)
    finally:
        err.close()
    url = p.stdout.readline().strip()
    assert url.startswith("http://127.0.0.1:") and "/?hd=" in url, (url, Path(log).read_text(encoding="utf-8", errors="replace"))
    return p, url


@pytest.fixture(params=["helper", "hub"])
def served(request, tmp_path):
    """→ {home, out, url, env}. helper = 옛 도우미 자식 프로세스 · hub = 허브 자식 프로세스 안 세션(out 을 목록에 넣고 POST /api/open)."""
    home, user = tmp_path / "home", tmp_path / "user"
    user.mkdir()
    env = child_env(home, user, fake_paseo(tmp_path / "fake-paseo"))
    out = hdfix.make_out(tmp_path / "w")
    procs = []
    try:
        if request.param == "helper":
            p, url = hdfix.start_helper(out, home, extra_env={"USERPROFILE": str(user), "HOME": str(user)})
            procs.append(p)
        else:
            hub, hub_url = start_hub(env, tmp_path / "hub.log")
            procs.append(hub)
            assert subprocess.run([sys.executable, str(HD_PY), "save", "--out", str(out)], env=env, capture_output=True, timeout=30).returncode == 0
            base, token = hub_url.split("/?hd=")
            req = urllib.request.Request(base + "/api/open", data=json.dumps({"name": "proj-a"}).encode(), method="POST",
                                         headers={"X-HD-Token": token, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                url = json.loads(r.read())["url"]
            assert "/v1/p/proj-a/index.html?hd=" in url
        yield {"home": home, "out": out, "url": url, "env": env, "kind": request.param}
    finally:
        for p in reversed(procs):
            hdfix.stop_helper(p)


def norm(s, d):
    """실행마다 바뀌는 값 → 이름. out 은 JSON 안(역슬래시 두 번)과 글(한 번) 둘 다."""
    out = str(d["out"])
    s = s.replace(d["url"], "<URL>").replace(json.dumps(out)[1:-1], "<OUT>").replace(out, "<OUT>")
    s = re.sub(r'"(pid|port)": \d+', r'"\1": 0', s)
    s = re.sub(r'"started": "[^"]*"', '"started": "<T>"', s)
    s = re.sub(r"\(rev \d+\)", "(rev N)", s)
    s = re.sub(r"^(proj-a · rev )\d+( · working)", r"\1N\2", s)
    s = re.sub(r'"rev": \d+', '"rev": 0', s)
    return s


def run(d, *args):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=d["env"], timeout=60)
    return r.returncode, norm(r.stdout, d), norm(r.stderr, d)


NEXT_OK = re.compile(r" — 다음: [^\n]*")   # SDK 오류가 덧붙여도 되는 꼬리(같은 줄, 한 줄 유지)


def err_of(e):
    return NEXT_OK.sub("", e)


NOTES_OPEN = """proj-a · rev 3 · open · 3개
home #1 · working · change · button:nth-of-type(1) "다음" · 버튼 문구를 '계속'으로
home #2 · working · question · h1 "제목" · 이 색은 토큰인가요?
list #1 · working · change · ul · 목록 간격 줄이기
"""

NOTE_KEYS = ["id", "screen", "no", "status", "intent", "sent", "edit", "scope", "target", "text", "replies"]


def test_cli_output_is_locked(served):
    d = served
    assert run(d, "ls") == (0, "proj-a · <URL> · - · 열린 메모 3\n", "")
    code, o, e = run(d, "ls", "--json")
    assert code == 0 and json.loads(o) == [{"project": "proj-a", "out": "<OUT>", "url": "<URL>", "agent": None, "pid": 0, "port": 0,
                                            "started": "<T>", "open": 3}], o
    assert list(json.loads(o)[0]) == ["project", "out", "url", "agent", "pid", "port", "started", "open"], "키 순서도 그대로"

    assert run(d, "notes") == (0, NOTES_OPEN, "")
    code, o, e = run(d, "notes", "--json")
    doc = json.loads(o)
    assert code == 0 and list(doc) == ["project", "out", "rev", "helper", "which", "notes"] and doc["helper"] is True
    assert [list(n) for n in doc["notes"]] == [NOTE_KEYS] * 3
    assert doc["notes"][0] == {"id": "n1", "screen": "home", "no": 1, "status": "working", "intent": "change", "sent": True, "edit": None,
                               "scope": "element", "target": {"path": "body > button:nth-of-type(1)", "quote": "다음", "count": 1},
                               "text": "버튼 문구를 '계속'으로", "replies": []}
    code, o, e = run(d, "notes", "--all")
    assert code == 0 and o.endswith("list #2 · draft · change · ul · 아직 안 보냄\n") and o.startswith("proj-a · rev 3 · all · 4개\n")

    code, o, e = run(d, "notes", "zz")
    assert (code, o) == (1, "") and err_of(e) == "hd: 'zz' 캔버스가 떠 있지 않아요 — 떠 있는 것: proj-a (<OUT>). 파일만 읽으려면 --out PATH\n"
    code, o, e = run(d, "notes", "zz", "--json")
    assert code == 1 and json.loads(o)["error"] == "'zz' 캔버스가 떠 있지 않아요 — 떠 있는 것: proj-a (<OUT>). 파일만 읽으려면 --out PATH"

    code, o, e = run(d, "reply", "home#1", "--kind", "반영됨", "--what", "x", "--screens", "ghost")
    assert (code, o, err_of(e)) == (1, "", "hd: 답이 규칙에 맞지 않아요:\n  screens: 없는 화면 ghost\n  captured: 없어요\n")
    code, o, e = run(d, "reply", "home#9", "--kind", "대체됨", "--where", "x")
    assert (code, err_of(e)) == (1, "hd: 없는 메모: home#9 — hd notes --all 로 번호를 보세요\n")
    assert run(d, "reply", "home#1", "--kind", "반영됨", "--what", "버튼", "--screens", "home", "--captured", "yes") == (0, "home#1 → done (rev N)\n", "")
    code, o, e = run(d, "reply", "n2", "--kind", "답변", "--text", "네", "--json")
    assert code == 0 and json.loads(o) == {"rev": 0, "status": "done", "note": "n2", "screen": "home"} and list(json.loads(o)) == ["rev", "status", "note", "screen"]
    code, o, e = run(d, "notes", "--sent")
    assert code == 0 and "home #1 · done · change" in o and "    ↳ 반영됨 — 버튼" in o and "    ↳ 답변 — 네" in o, o

    assert run(d, "claim", "home", "--note", "n", "--by", "a1") == (0, "proj-a · home 덮개 씌움 · n (rev N) — 파일이 바뀌거나 hd release home 면 걷혀요\n", "")
    code, o, e = run(d, "claim", "list", "--json")
    assert code == 0 and json.loads(o) == {"rev": 0, "screen": "list", "file": "screens/list.html", "project": "proj-a", "by": None, "note": None}
    assert run(d, "release", "home") == (0, "proj-a · home 덮개 걷음 (rev N)\n", "")
    code, o, e = run(d, "release", "home", "--json")
    assert code == 0 and json.loads(o) == {"rev": 0, "released": False, "project": "proj-a", "screen": "home"}
    assert run(d, "release", "home") == (0, "proj-a · home 덮개가 없어요(그대로)\n", "")
    code, o, e = run(d, "claim", "ghost", "--json")
    assert code == 1 and json.loads(o)["error"] == "없는 화면이에요: ghost — 있는 화면: home, list" and err_of(e) == "hd: 없는 화면이에요: ghost — 있는 화면: home, list\n"
    code, o, e = run(d, "attach", "--agent", "a b")
    assert (code, err_of(e)) == (1, "hd: agent: 띄어쓰기·줄바꿈 없는 id 여야 해요\n")
    code, o, e = run(d, "attach", "--agent", "ag-1", "--json")
    assert code == 0 and json.loads(o) == {"project": "proj-a", "out": "<OUT>", "pid": 0, "agent": "ag-1", "was": None}
    assert run(d, "attach", "--agent", "none") == (0, "proj-a · 보내기 → 대기열 파일 (전: ag-1)\n", "")

    assert run(d, "wait", "--timeout", "5") == (0, "proj-a · rev N · working · 1개\nlist #1 · working · change · ul · 목록 간격 줄이기\n", ""), "있으면 바로"
    code, o, e = run(d, "stop", "--json")
    assert code == 0 and json.loads(o) == {"project": "proj-a", "out": "<OUT>", "pid": 0, "port": 0, "how": "route"}
    code, o, e = run(d, "notes")
    assert (code, err_of(e)) == (1, "hd: 떠 있는 캔버스가 없어요 — 떠 있는 것: 없음. 파일만 읽으려면 --out PATH\n")
    code, o, e = run(d, "reply", "home#2", "--out", str(d["out"]), "--kind", "대체됨", "--where", "x")
    assert code == 1 and err_of(e).startswith("hd: 이 out 을 띄운 도우미가 없어요 — 먼저 띄우세요: python ") and "helper.py" in e
