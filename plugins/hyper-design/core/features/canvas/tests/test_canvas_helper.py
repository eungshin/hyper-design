"""로컬 도우미(helper.py, 7단계) — 화면 파일에 바로 쓰기 · out 안만 · 원본 남김 · 토큰/주소 검사 · 꺼지면 복사."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SAMPLE = """<main><section class="block"><h1 class="title">하는 일</h1>
<a class="row" href="a.html">가기 <b>›</b></a><p>설명 &amp; 글</p><button class="btn">시작</button><button class="btn">또</button></section></main>"""


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-helper-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def test_helper_edit_html_ops():
    s = helper.edit_html(SAMPLE, [("section.block:nth-of-type(1) > h1.title:nth-of-type(1)", "text", "바뀐 <제목>")])
    assert '<h1 class="title">바뀐 &lt;제목&gt;</h1>' in s, "글자만 바꾸고 태그는 그대로(이스케이프)"
    s = helper.edit_html(SAMPLE, [("a.row:nth-of-type(1)", "text", "새 글")])
    assert '<a class="row" href="a.html">새 글 <b>›</b></a>' in s, "첫 글자 마디만"
    s = helper.edit_html(SAMPLE, [("button.btn:nth-of-type(1)", "link", "job"), ("a.row:nth-of-type(1)", "link", "usage")])
    assert """<button class="btn" onclick="location.href=&#x27;job.html&#x27;">시작</button>""" in s and 'href="usage.html"' in s
    assert 'href="a.html"' not in s
    s = helper.edit_html(SAMPLE, [("a.row:nth-of-type(1)", "cut", None)])
    assert '<a class="row">가기' in s, "끊기 = href 지우기"
    with pytest.raises(ValueError):
        helper.edit_html(SAMPLE, [("button.btn", "text", "x")])           # 둘 다 맞음 → 모호
    with pytest.raises(ValueError):
        helper.edit_html(SAMPLE, [("p:nth-of-type(1)", "cut", None)])     # 끊을 연결 없음


def test_helper_apply_backup_rebuild_and_refusals(out):
    job = out / "screens" / "job.html"
    before = job.read_text(encoding="utf-8")
    res = helper.apply_edits(out, [
        {"id": "a", "screen": "job", "edit": "text", "path": "h1.title:nth-of-type(1)", "value": "무슨 일을 하세요?"},
        {"id": "b", "screen": "job", "edit": "purpose", "value": "새 설명"},
        {"id": "c", "screen": "job", "edit": "link", "op": "link", "to": "usage", "path": "div.btns:nth-of-type(1) > a.btn:nth-of-type(1)"},
        {"id": "d", "screen": "nope", "edit": "text", "path": "h1", "value": "x"},
        {"id": "e", "screen": "job", "edit": "link", "op": "new", "path": "h1"},
        {"id": "f", "screen": "job", "edit": "text", "path": "h9.none:nth-of-type(1)", "value": "x"},
    ], stamp="t1")
    assert sorted(res["applied"]) == ["a", "b", "c"], res
    assert {f["id"] for f in res["failed"]} == {"d", "e", "f"}, res
    after = job.read_text(encoding="utf-8")
    assert "무슨 일을 하세요?" in after and 'href="usage.html">다음으로' in after
    assert (out / ".hd-history" / "t1" / "screens" / "job.html").read_text(encoding="utf-8") == before, "쓰기 전 원본을 남긴다"
    sj = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    assert next(s for s in sj["screens"] if s["id"] == "job")["purpose"] == "새 설명"
    assert "새 설명" in (out / "index.html").read_text(encoding="utf-8"), "다시 빌드한다"
    q = helper.forward(out, "[hyper-design 수정 요청] …")
    assert q["via"] == "queue" and pathlib.Path(q["path"]).read_text(encoding="utf-8").startswith("[hyper-design")
    if os.name == "nt":                              # Paseo 가 있으면 대기열 파일을 paseo send --prompt-file 로(가짜 명령으로 확인 — 실제 에이전트에 보내지 않는다)
        fake = out.parent / "fake-paseo.bat"
        fake.write_text('@echo %* > "%~dp0paseo-args.txt"\r\n', encoding="ascii")
        q = helper.forward(out, "두 줄\n요청", agent="abc123", paseo=str(fake))
        args = (out.parent / "paseo-args.txt").read_text(encoding="mbcs", errors="replace")
        assert q["via"] == "paseo" and "send abc123 --prompt-file" in args and "--no-wait" in args, (q, args)


def _post(url, body, token=None, host=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    if token:
        req.add_header("X-HD-Token", token)
    if host:
        req.add_header("Host", host)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def test_helper_server_applies_from_canvas_and_falls_back_to_copy(ctx, out):
    srv = helper.make_server(out, 0)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = srv.url.split("/index.html")[0]
    assert _post(base + "/api/apply", {"edits": []})[0] == 403, "토큰 없으면 거절"
    assert _post(base + "/api/apply", {"edits": []}, srv.token, host="evil.example:80")[0] == 403, "다른 Host 거절"
    assert _post(base + "/api/apply", {"edits": []}, srv.token)[0] == 200
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(base + "/.hd-history/", timeout=5)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        assert pg.evaluate("window.__hdKeyPath") == helper.keypath(out), "저장 키는 file:// 로 열 때의 경로로 — 같은 out 이면 메모가 이어진다"
        pg.evaluate("""() => { const k = 'hd-notes:' + (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath);
            localStorage.setItem(k, JSON.stringify([
              {id: 'x1', screen: 'job', targets: [{path: 'h1.title:nth-of-type(1)', text: '하는 일이 무엇인가요?'}], path: 'h1.title:nth-of-type(1)', text: '하는 일이 무엇인가요?',
               note: '글자를 "도우미가 씀"(으)로 바꾸기', intent: 'change', sent: false, edit: 'text', value: '도우미가 씀'},
              {id: 'x2', screen: 'job', targets: [{path: 'h1', text: 'q'}], path: 'h1', text: 'q', note: '이건 무슨 뜻?', intent: 'question', sent: false}])); }""")
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.click("#nsend")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        last = pg.evaluate("window.__hdLastHelper")
        assert last["apply"]["applied"] == ["x1"] and last["forward"]["via"] == "queue", last
        assert "바로 반영 1건" in pg.text_content("#nmsg") and "터미널로 1건" in pg.text_content("#nmsg")
        assert "도우미가 씀" in (out / "screens" / "job.html").read_text(encoding="utf-8")
        assert "이건 무슨 뜻?" in pathlib.Path(last["forward"]["path"]).read_text(encoding="utf-8")
        pg.wait_for_function("window.__hdLastHelper === undefined", timeout=10000)   # 다시 빌드된 캔버스로 새로고침
        pg.wait_for_function("window.__hdReady !== undefined")
        left = pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]')")
        assert [n["id"] for n in left] == ["x2"] and left[0]["sent"], "바로 쓴 편집은 메모에서 빠지고, 터미널로 보낸 것은 보냄"
        srv.shutdown(); srv.server_close()                  # 도우미가 꺼지면 지금처럼 복사
        pg.click("#nsend")
        pg.wait_for_function("document.getElementById('nmsg').textContent.indexOf('도우미가 꺼져 있어 복사했어요') === 0", timeout=10000)
        assert "이건 무슨 뜻?" in pg.evaluate("window.__hdLastSend")
    finally:
        try:
            srv.shutdown(); srv.server_close()
        except Exception:
            pass
    assert not errors, errors
    pg.close()
