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
        {"id": "g", "screen": "job", "edit": "policy", "index": 0, "value": "새 정책"},
    ], stamp="t1")
    assert sorted(res["applied"]) == ["a", "b", "c", "g"], res
    assert {f["id"] for f in res["failed"]} == {"d", "e", "f"}, res
    after = job.read_text(encoding="utf-8")
    assert "무슨 일을 하세요?" in after and 'href="usage.html">다음으로' in after
    assert (out / ".hd-history" / "t1" / "screens" / "job.html").read_text(encoding="utf-8") == before, "쓰기 전 원본을 남긴다"
    sj = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    assert next(s for s in sj["screens"] if s["id"] == "job")["purpose"] == "새 설명"
    assert next(s for s in sj["screens"] if s["id"] == "job")["policies"][0] == "새 정책", "정책 줄도 바로 쓴다"
    assert "새 설명" in (out / "index.html").read_text(encoding="utf-8"), "다시 빌드한다"
    q = helper.forward(out, "[hyper-design 수정 요청] …")
    assert q["via"] == "queue" and pathlib.Path(q["path"]).read_text(encoding="utf-8").startswith("[hyper-design")
    if os.name == "nt":                              # Paseo 가 있으면 대기열 파일을 paseo send --prompt-file 로(가짜 명령으로 확인 — 실제 에이전트에 보내지 않는다)
        fake = out.parent / "fake-paseo.bat"
        fake.write_text('@echo %* > "%~dp0paseo-args.txt"\r\n', encoding="ascii")
        q = helper.forward(out, "두 줄\n요청", agent="abc123", paseo=str(fake))
        args = (out.parent / "paseo-args.txt").read_text(encoding="mbcs", errors="replace")
        assert q["via"] == "paseo" and "send abc123 --prompt-file" in args and "--no-wait" in args, (q, args)


def _snapshot(out):                                  # out 안 화면 파일·screens.json 바이트(되살리기 비교용)
    files = {p.relative_to(out).as_posix(): p.read_bytes() for p in (out / "screens").glob("*.html")}
    files["screens.json"] = (out / "screens.json").read_bytes()
    return files


def _links_to(out, sid):
    import build_canvas
    m = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    ids = {s["id"] for s in m["screens"]} | {sid}
    return sorted(s["id"] for s in m["screens"]
                  if any(l["to"] == sid for l in build_canvas.screen_links(out, {"id": s["id"], "file": s.get("file") or "screens/%s.html" % s["id"]}, ids)))


def test_helper_delete_cuts_incoming_and_restore_is_byte_exact(out):   # 2.2 D3·D4 — 바로 삭제 · 오는 연결도 끊김 · 되살리기
    before = _snapshot(out)
    assert _links_to(out, "keys") == ["try-copy", "try-ocr", "try-search"]
    res = helper.delete_screens(out, ["keys"], stamp="d1")
    assert res["deleted"] == ["keys"] and res["stamp"] == "d1", res
    assert {c["screen"] for c in res["cut"]} == {"try-copy", "try-ocr", "try-search"} and all(c["to"] == "keys" for c in res["cut"]), res
    assert set(res["changed"]) >= {"keys", "try-copy", "try-ocr", "try-search"}, res
    sj = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    assert "keys" not in {s["id"] for s in sj["screens"]}, "screens.json 에서 빠진다"
    assert not any(b.get("to") == "keys" for s in sj["screens"] for b in (s.get("branches") or [])), "그리로 가는 branches 도"
    assert not (out / "screens" / "keys.html").exists() and (out / ".hd-history" / "d1" / "screens" / "keys.html").read_bytes() == before["screens/keys.html"], "화면 파일은 기록으로 옮긴다"
    assert _links_to(out, "keys") == [], "다른 화면에서 오는 링크를 끊는다(E10)"
    assert '"keys"' not in (out / "index.html").read_text(encoding="utf-8").split('id="hd-data"')[1].split("</script>")[0], "다시 빌드한다"

    r = helper.restore(out, "d1")
    assert "error" not in r and set(r["changed"]) >= {"keys", "try-copy"}, r
    assert _snapshot(out) == before, "되살리기 = 바이트 그대로"


def test_helper_restore_refuses_when_files_changed_since(out):        # 2.2 D4 — 그 뒤에 바뀐 파일은 덮지 않는다
    res = helper.apply_edits(out, [{"id": "c", "screen": "job", "edit": "link", "op": "link", "to": "usage",
                                    "path": "div.btns:nth-of-type(1) > a.btn:nth-of-type(1)"}], stamp="a1")
    assert res["applied"] == ["c"] and res["stamp"] == "a1" and res["changed"] == ["job"], res
    job = out / "screens" / "job.html"
    job.write_text(job.read_text(encoding="utf-8") + "<!-- 사람이 고침 -->", encoding="utf-8")
    r = helper.restore(out, "a1")
    assert r.get("reason") == "changed-since", r
    assert "사람이 고침" in job.read_text(encoding="utf-8"), "거절하면 아무것도 바꾸지 않는다"
    assert helper.restore(out, "nope").get("error"), "없는 기록"


def test_helper_server_delete_restore_data(out):                      # 2.2 API — /api/delete · /api/restore(409) · /api/data
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = srv.url.split("/index.html")[0]
    try:
        assert _post(base + "/api/data", {})[0] == 403, "토큰 없으면 거절"
        code, data = _post(base + "/api/data", {}, srv.token)
        raw = (out / "index.html").read_text(encoding="utf-8").split('<script id="hd-data" type="application/json">')[1].split("</script>")[0]
        assert code == 200 and data == json.loads(raw), "/api/data = index.html 의 hd-data"
        code, res = _post(base + "/api/delete", {"screens": ["keys"]}, srv.token)
        assert code == 200 and res["deleted"] == ["keys"] and len(res["cut"]) >= 3, res
        code, data = _post(base + "/api/data", {}, srv.token)
        assert "keys" not in {c["id"] for r in data["rows"] for c in r["screens"]}
        (out / "screens" / "try-copy.html").write_text("<p>바뀜</p>", encoding="utf-8")
        assert _post(base + "/api/restore", {"stamp": res["stamp"]}, srv.token)[0] == 409, "그 뒤에 바뀌었으면 409"
    finally:
        srv.shutdown(); srv.server_close()


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


def test_helper_server_reads_the_body_before_refusing(out):
    """거절(403)도 요청 본문을 다 읽은 뒤에 답한다 — 안 읽고 닫으면 Windows 가 연결을 RST 로 끊어
    클라이언트가 403 대신 ConnectionAbortedError(10053)를 받는다(-n 4 에서 가끔 보이던 흔들림의 원인)."""
    import socket
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    body = json.dumps({"edits": []}).encode()
    try:
        for token in (None, "wrong"):
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            lines = ["POST /api/apply HTTP/1.1", "Host: 127.0.0.1:%d" % port, "Content-Type: application/json", "Content-Length: %d" % len(body)]
            if token:
                lines.append("X-HD-Token: " + token)
            s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())          # 머리만 먼저 — 본문은 답이 오는지 본 뒤에
            s.settimeout(0.4)
            try:
                early = s.recv(4096)
            except socket.timeout:
                early = b""
            assert early == b"", "본문이 오기 전에 답하고 닫으면 안 된다(본문이 닫힌 소켓에 닿아 RST)"
            s.settimeout(5)
            s.sendall(body)
            got = b""
            while not got.endswith(b"}"):
                chunk = s.recv(4096)
                if not chunk:
                    break
                got += chunk
            assert got.startswith(b"HTTP/1.0 403") or got.startswith(b"HTTP/1.1 403"), got[:60]
            s.close()
    finally:
        srv.shutdown(); srv.server_close()


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
        assert pg.text_content("#mode") == "파일에 바로 씀", "모드 칩(E9)"
        assert pg.text_content("#aichip") == "AI 없음" and pg.is_visible("#aichip"), "보내기가 AI 로 가는지 위쪽 줄에 늘 보인다"
        pg.evaluate("window.__hdStay = 1")               # 새로고침하면 사라지는 표지
        pg.click("#nsend")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        last = pg.evaluate("window.__hdLastHelper")
        assert last["apply"]["applied"] == ["x1"] and last["forward"]["via"] == "queue", last
        assert "바로 반영 1건" in pg.text_content("#nmsg") and "AI 터미널이 연결돼 있지 않아요" in pg.text_content("#nmsg")
        assert "대기열 파일" in pg.text_content("#toast") and pg.is_visible("#toast"), "보낸 뒤 어디로 갔는지 알림"
        assert "도우미가 씀" in (out / "screens" / "job.html").read_text(encoding="utf-8")
        assert "이건 무슨 뜻?" in pathlib.Path(last["forward"]["path"]).read_text(encoding="utf-8")
        assert pg.evaluate("window.__hdStay") == 1, "쓴 뒤 페이지 전체를 새로고침하지 않는다(E17)"
        job_src = pg.evaluate("(() => { const f = document.querySelector('.card[data-id=\"job\"] .phone iframe'); return f.getAttribute('src') || f.getAttribute('data-src') || ''; })()")   # 한 번에 읽는다(따로 읽으면 그 사이 data-src → src 로 옮겨 가 둘 다 비어 보인다)
        assert "?v=" in job_src, "바뀐 카드만 다시 싣는다"
        left = pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]')")
        assert [n["id"] for n in left] == ["x2"] and left[0]["sent"], "바로 쓴 편집은 메모에서 빠지고, 터미널로 보낸 것은 보냄"
        srv.shutdown(); srv.server_close()                  # 도우미가 꺼지면 지금처럼 복사
        pg.click("#nsend")
        pg.wait_for_function("document.getElementById('nmsg').textContent.indexOf('파일에 바로 쓰기가 꺼져 있어 복사했어요') === 0", timeout=10000)
        assert "이건 무슨 뜻?" in pg.evaluate("window.__hdLastSend")
    finally:
        try:
            srv.shutdown(); srv.server_close()
        except Exception:
            pass
    assert not errors, errors
    pg.close()


def test_helper_canvas_writes_delete_and_link_without_reload(ctx, out):   # 2.2 — 바로 삭제·오는 연결 끊김·되돌리기 = 되살리기 · 잇기 바로 씀 · 새로고침 없음
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    keys = (out / "screens" / "keys.html").read_bytes()
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("window.__hdStay = 1")
        from test_canvas_edit import fit_view
        fit_view(pg)
        pick = lambda sid: pg.evaluate("(id) => { const r = document.querySelector('.card[data-id=\"' + id + '\"] .cover').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", sid)
        pg.mouse.click(*pick("keys")); pg.wait_for_timeout(150)
        pg.keyboard.press("Delete")                                  # 고른 카드 삭제 = 파일에서 바로(E1)
        pg.wait_for_function("!document.querySelector('.card[data-id=\"keys\"]')", timeout=20000)
        assert "오는 연결 3개도 끊김" in pg.text_content("#toast"), pg.text_content("#toast")
        assert not (out / "screens" / "keys.html").exists() and _links_to(out, "keys") == []
        assert pg.locator("#hlist li.now .hs").text_content() == "파일에 씀", "기록 한 줄 · 파일에 씀"
        pg.click("#undo")
        pg.wait_for_function("!!document.querySelector('.card[data-id=\"keys\"]')", timeout=20000)
        assert (out / "screens" / "keys.html").read_bytes() == keys and _links_to(out, "keys") == ["try-copy", "try-ocr", "try-search"], "되돌리기 = 되살리기"
        assert _links_to(out, "language") == ["job", "usage"]
        pg.mouse.click(*pick("job")); pg.wait_for_timeout(150)       # 연결 패널 휴지통 = 그 방향 연결 끊기 → 파일에 바로
        pg.locator('#legend .lgrow[data-from="job"][data-to="language"] .lgcut').click()
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀' && document.querySelector('#hlist li.now .hl').textContent === '선 자르기'", timeout=20000)
        assert _links_to(out, "language") == ["usage"], "끊기는 파일에 바로"
        assert pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]').length") == 0, "반영 대기로 남지 않는다"
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음(E17)"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def test_helper_canvas_busy_overlay_lifts_on_file_change(ctx, out):   # Q2b — 터미널로 넘긴 화면에 덮개 · 새로고침해도 남음 · 파일이 바뀌면 걷힘 · [걷기]
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    busy = '.card[data-id="job"] .busy'
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("""() => { const k = 'hd-notes:' + (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath);
            localStorage.setItem(k, JSON.stringify([{id: 'm1', screen: 'job', targets: [{path: 'h1', text: 'q'}], path: 'h1', text: 'q', note: '제목을 더 짧게', intent: 'change', sent: false}])); }""")
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        assert pg.locator(busy).count() == 0
        pg.click("#nsend")
        pg.wait_for_selector(busy)
        assert pg.get_attribute(busy, "data-via") == "queue" and pg.get_attribute(busy, "role") == "status"
        assert pg.text_content(busy + " .busy-txt") == "대기열에 있음" and pg.locator(busy + " [data-act=lift]").text_content() == "걷기"
        assert pg.locator(".busy").count() == 1, "넘긴 화면에만"
        from test_canvas_v2 import zoom_to
        zoom_to(pg, "job", 420)
        from test_canvas_edit import ESHOTS
        ESHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(ESHOTS / "q2b-busy.png"))
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector(busy + '[data-via="queue"]')       # 새로고침해도 남는다
        pg.wait_for_function("Object.keys(localStorage).some(k => k.startsWith('hd-busy:') && /\"mtime\":[0-9]/.test(localStorage.getItem(k)))", timeout=5000)
        f = out / "screens" / "job.html"
        f.write_text(f.read_text(encoding="utf-8") + "\n<!-- AI 가 고침 -->\n", encoding="utf-8")
        pg.wait_for_selector(busy, state="detached", timeout=6000)  # 화면 파일이 바뀌면 걷힌다
        assert "?v=" in (pg.get_attribute('.card[data-id="job"] .phone iframe', "src") or pg.get_attribute('.card[data-id="job"] .phone iframe', "data-src") or ""), "그 카드만 다시 싣는다"
        pg.click("#nsend")                                       # 다시 넘김 → [걷기] = 손으로 바로 걷기
        pg.wait_for_selector(busy)
        pg.locator(busy + " [data-act=lift]").click()
        assert pg.locator(busy).count() == 0
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


SEED = """(notes) => { const k = 'hd-notes:' + (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath || location.pathname);
    localStorage.setItem(k, JSON.stringify(notes)); }"""
NOTES_NOW = "JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]')"
QUESTION = {"id": "q1", "screen": "job", "targets": [{"path": "h1", "text": "q"}], "path": "h1", "text": "q", "note": "이건 무슨 뜻?", "intent": "question", "sent": False}


def _serve(out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_helper_send_double_click_sends_once(ctx, out):   # S1 — 보내기를 두 번 눌러도 AI 에게는 한 번
    srv = _serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate(SEED, [QUESTION])
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.dblclick("#nsend")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        pg.wait_for_timeout(800)                                 # 두 번째 요청이 있었다면 이 사이에 대기열에 닿는다
        q = out / ".hd-queue"
        assert len(list(q.iterdir())) == 1, "두 번 눌러도 대기열 파일은 하나"
        assert not pg.is_disabled("#nsend"), "보낸 뒤 버튼은 다시 켜진다(다시 보내기)"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def test_card_reload_posts_pending_once_per_load(ctx, out):   # S4 — 카드를 여러 번 다시 실어도 실을 때마다 메시지는 한 번
    srv = _serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script("""if (window !== window.top) { let n = 0; addEventListener('message', e => {
        if (e.data && e.data.type === 'hd-pending') { n++; try { (top.__hdPendN = top.__hdPendN || {})[location.pathname + location.search] = n; } catch (_) {} } }); }""")
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        from test_canvas_v2 import zoom_to
        zoom_to(pg, "job", 420)
        pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"] .phone iframe').hasAttribute('data-src')", timeout=10000)
        counts = []
        for i in range(1, 4):
            key = pg.evaluate("""(i) => { const f = document.querySelector('.card[data-id="job"] .phone iframe'), b = document.querySelector('.card[data-id="job"] .cover');
                f.removeAttribute('src'); f.setAttribute('data-src', b.dataset.file + '?v=t' + i); dispatchEvent(new Event('resize'));
                return '/' + b.dataset.file.replace(/^[.]?[/]/, '') + '?v=t' + i; }""", i)
            pg.wait_for_function("(k) => window.__hdPendN && window.__hdPendN[k] >= 1", arg=key, timeout=10000)
            pg.wait_for_timeout(300)
            counts.append(pg.evaluate("(k) => window.__hdPendN[k]", key))
        assert counts == [1, 1, 1], f"다시 실을 때마다 hd-pending 한 번: {counts}"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def test_copy_failure_keeps_notes_unsent_and_storage_failure_warns(ctx, out):   # S3 · S7 — 복사가 안 되면 '보냄'이 아니다 · 저장이 안 되면 알린다
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto((out / "index.html").resolve().as_uri())
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate(SEED, [QUESTION])
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("""() => { navigator.clipboard.writeText = () => Promise.reject(new Error('denied')); document.execCommand = () => false; }""")
        pg.click("#nsend")
        pg.wait_for_function("document.getElementById('toast').textContent.indexOf('복사하지 못했어요') >= 0", timeout=5000)
        assert "복사했어요" not in pg.text_content("#nmsg")
        assert [n["sent"] for n in pg.evaluate(NOTES_NOW)] == [False], "복사 실패 → 보내지 않은 그대로"
        assert pg.text_content("#nsendc") == "1"
        pg.evaluate("""() => { Storage.prototype.setItem = function () { throw new DOMException('full', 'QuotaExceededError'); }; }""")
        pg.click('#nlist li[data-id="q1"] button[data-act="del"]')
        pg.wait_for_function("document.getElementById('toast').textContent.indexOf('저장하지 못했어요') >= 0", timeout=5000)
    finally:
        pg.close()
    assert not errors, errors


def test_helper_redo_failure_tells_the_user(ctx, out):   # S5 — 다시 하기가 파일에 못 쓰면 알린다
    srv = _serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        from test_canvas_edit import fit_view
        fit_view(pg)
        c = pg.evaluate("() => { const r = document.querySelector('.card[data-id=\"job\"] .cover').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
        pg.mouse.click(*c); pg.wait_for_timeout(150)
        pg.locator('#legend .lgrow[data-from="job"][data-to="language"] .lgcut').click()
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hl').textContent === '선 자르기'", timeout=20000)
        pg.click("#undo")
        pg.wait_for_function("() => !document.getElementById('redo').disabled", timeout=20000)
        pg.wait_for_timeout(500)
        pg.route("**/api/apply", lambda r: r.fulfill(status=500, content_type="application/json", body="{}"))
        pg.click("#redo")
        pg.wait_for_function("document.getElementById('toast').textContent.indexOf('다시 하지 못했어요') >= 0", timeout=10000)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def test_helper_written_edit_is_not_requeued_when_reload_fails(ctx, out):   # S2 — 파일에 쓴 편집은 판 다시 불러오기가 실패해도 반영 대기로 돌아가지 않는다
    srv = _serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    calls = []

    def flaky(route):                                            # 쓴 뒤 첫 /api/data 한 번만 실패
        calls.append(1)
        if len(calls) == 1:
            route.fulfill(status=500, content_type="application/json", body="{}")
        else:
            route.continue_()
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        from test_canvas_edit import fit_view
        fit_view(pg)
        pg.route("**/api/data", flaky)
        c = pg.evaluate("() => { const r = document.querySelector('.card[data-id=\"job\"] .cover').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }")
        pg.mouse.click(*c); pg.wait_for_timeout(150)
        pg.locator('#legend .lgrow[data-from="job"][data-to="language"] .lgcut').click()
        pg.wait_for_function("() => document.querySelector('#hlist li.now .hl') && document.querySelector('#hlist li.now .hl').textContent === '선 자르기'", timeout=20000)
        assert _links_to(out, "language") == ["usage"], "파일에는 썼다"
        pg.wait_for_timeout(2500)                                # 다시 불러오기(재시도)까지
        assert pg.evaluate(NOTES_NOW) == [], "이미 쓴 편집을 반영 대기로 다시 넣지 않는다(다음 보내기에서 두 번 쓰임)"
        assert len(calls) >= 2, "판 데이터를 다시 불러온다"
        assert pg.locator("#hlist li.now .hs").text_content() == "파일에 씀"
        assert "?v=" in (pg.get_attribute('.card[data-id="job"] .phone iframe', "src") or pg.get_attribute('.card[data-id="job"] .phone iframe', "data-src") or ""), "다시 불러오기가 되어 바뀐 카드를 다시 싣는다"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def _req(url, method, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("X-HD-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, None


def test_helper_state_file_put_rev_conflict_and_limits(out):   # #228 — rev 가 맞을 때만 rev+1 로 쓰고 .bak · 다르면 409 · 2 MB 넘으면 413 · 깨진 JSON 400
    srv = _serve(out)
    api = srv.url.split("/index.html")[0] + "/api/state"
    f = out / ".hd-canvas.json"
    try:
        assert _req(api, "GET")[0] == 403, "토큰 없으면 거절"
        assert _req(api, "GET", token=srv.token) == (200, {"rev": 0, "state": {}}), "파일이 없으면 rev 0"
        assert _req(api, "PUT", {"rev": 0, "state": {"notes": [{"id": "n1"}]}})[0] == 403
        assert _req(api, "PUT", {"rev": 0, "state": {"notes": [{"id": "n1"}], "future": {"x": 1}}}, srv.token) == (200, {"rev": 1})
        doc = json.loads(f.read_text(encoding="utf-8"))
        assert doc["version"] == 1 and doc["rev"] == 1 and doc["updated"] and doc["state"] == {"notes": [{"id": "n1"}], "future": {"x": 1}}, "값은 풀어 둔 JSON"
        assert _req(api, "PUT", {"rev": 1, "state": {"hidden": ["job"], "notes": None}}, srv.token) == (200, {"rev": 2})
        doc = json.loads(f.read_text(encoding="utf-8"))
        assert doc["state"] == {"future": {"x": 1}, "hidden": ["job"]}, "바뀐 키만 합치고 null = 지움, 모르는 키는 그대로"
        assert json.loads((out / ".hd-canvas.json.bak").read_text(encoding="utf-8"))["rev"] == 1, "앞 것 하나를 .bak 으로"
        code, res = _req(api, "PUT", {"rev": 1, "state": {"hidden": []}}, srv.token)
        assert code == 409 and res == {"rev": 2, "state": doc["state"]}, "rev 가 다르면 409 + 지금 상태"
        assert json.loads(f.read_text(encoding="utf-8"))["rev"] == 2, "거절하면 파일 그대로"
        assert _req(api, "PUT", token=srv.token, raw=b"{nope")[0] == 400
        assert _req(api, "PUT", {"rev": "2", "state": {}}, srv.token)[0] == 400
        big = json.dumps({"rev": 2, "state": {"notes": "x" * (2 * 1024 * 1024)}}).encode()
        assert _req(api, "PUT", token=srv.token, raw=big)[0] == 413, "2 MB 넘으면 413"
        assert _req(api, "GET", token=srv.token)[1]["rev"] == 2
        assert not list(out.glob(".hd-canvas.json.tmp-*")), "임시 파일이 남지 않는다"
        page = urllib.request.urlopen(srv.url, timeout=10).read().decode("utf-8")
        assert 'window.__hdState={"rev": 2' in page, "index.html 에 상태 스냅숏을 끼워 넣는다"
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(srv.url.split("/index.html")[0] + "/.hd-canvas.json", timeout=5)
    finally:
        srv.shutdown(); srv.server_close()


def test_helper_state_corrupt_file_on_start_is_moved_aside(out, capfd):   # #228 — 깨진 상태 파일: 옮기고 한 줄 남기고 빈 상태로 · 도우미는 뜬다
    (out / ".hd-canvas.json").write_text('{"rev": 3, "state": {"notes": [', encoding="utf-8")
    srv = _serve(out)
    try:
        bad = list(out.glob(".hd-canvas.json.corrupt-*"))
        assert len(bad) == 1 and bad[0].read_text(encoding="utf-8").startswith('{"rev": 3'), "깨진 파일은 지우지 않고 옮긴다"
        assert not (out / ".hd-canvas.json").exists()
        assert "[hd]" in capfd.readouterr().err, "한 줄 남긴다"
        assert _req(srv.url.split("/index.html")[0] + "/api/state", "GET", token=srv.token) == (200, {"rev": 0, "state": {}})
        assert urllib.request.urlopen(srv.url, timeout=10).status == 200, "도우미는 그대로 페이지를 준다"
    finally:
        srv.shutdown(); srv.server_close()


def test_helper_memo_lives_in_state_file_across_browsers(browser, out):   # #228 — 도우미로 열면 메모가 <out>/.hd-canvas.json 에 · 다른 브라우저(빈 저장소)에서도 그대로 · 다른 곳에서 바뀌면 알리고 다시 불러옴
    from test_canvas_edit import fit_view, visible_cover
    srv = _serve(out)
    f = out / ".hd-canvas.json"
    errors = []

    def state():
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def open_fresh():
        c = browser.new_context(viewport={"width": 1440, "height": 1000})
        pg = c.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        return c, pg
    c1 = c2 = None
    try:
        c1, pg = open_fresh()
        fit_view(pg)
        pg.keyboard.press("m")
        cov = visible_cover(pg)
        pg.mouse.click(cov["x"], cov["y"])
        pg.wait_for_selector("#pop:not([hidden])")
        pg.fill("#pnote", "파일에 남는 메모")
        pg.click("#padd")
        import time
        t0 = time.time()
        while time.time() - t0 < 5 and not any(n.get("note") == "파일에 남는 메모" for n in (state().get("state") or {}).get("notes") or []):
            time.sleep(0.1)
        doc = state()
        assert [n["note"] for n in doc["state"]["notes"]] == ["파일에 남는 메모"] and doc["state"]["notes"][0]["screen"] == cov["id"], doc
        assert doc["rev"] >= 1 and doc["version"] == 1
        assert "hd-dock" not in json.dumps(doc) and "dock" not in doc["state"], "전역 설정 키는 파일로 가지 않는다"
        c1.close(); c1 = None

        c2, pg = open_fresh()                                        # 다른 브라우저 = 빈 저장소
        assert pg.evaluate("Object.keys(window.__hdState.state)").count("notes") == 1
        assert pg.locator("#nlist li").count() == 1 and "파일에 남는 메모" in pg.text_content("#nlist"), "파일 상태로 메모가 보인다"
        assert "파일에 남는 메모" in pg.evaluate("localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:')))"), "파일이 이기고 캐시에도 쓴다"

        rev = state()["rev"]                                         # 다른 곳(터미널 에이전트)에서 바뀜 → 이 페이지의 다음 쓰기 = 409
        code, _ = _req(srv.url.split("/index.html")[0] + "/api/state", "PUT", {"rev": rev, "state": {"hidden": ["job"]}}, srv.token)
        assert code == 200
        pg.evaluate("window.__hdStay = 1")
        pg.click('#nlist li button[data-act="del"]')
        pg.wait_for_function("document.getElementById('toast').textContent.indexOf('다른 곳에서 바뀌어 다시 불러왔어요') >= 0", timeout=5000)
        pg.wait_for_function("window.__hdStay === undefined && window.__hdReady !== undefined", timeout=10000)
        assert pg.locator("#nlist li").count() == 1, "이번 변경(지우기)은 버리고 파일 상태로 다시"
        assert state()["state"]["hidden"] == ["job"] and len(state()["state"]["notes"]) == 1, "다른 곳의 변경을 덮어쓰지 않는다"
    finally:
        for c in (c1, c2):
            if c:
                c.close()
        srv.shutdown(); srv.server_close()
    assert not errors, errors
