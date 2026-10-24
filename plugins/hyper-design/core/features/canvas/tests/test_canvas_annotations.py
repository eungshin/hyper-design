"""메모 주석·핀(task 11) — 판 카드 위 메모 핀 · 화면마다 바뀌지 않는 번호 · 다시 찾기(hd-locate) · 완료/다시 열기 (Playwright).

작은 화면 두 장을 임시 out 에 만들어 build_canvas.py 로 빌드한다(화면 파일을 고쳐 다시 찾기를 본다 — 고정본은 건드리지 않는다).
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import fit_view, notes_of, wait_notes, el_point, frame_of

PAY = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><header><h1 class="title" style="margin:16px">결제</h1></header>
<main style="padding:16px"><p class="lead">카드를 고르세요</p>{gap}<button class="pay" style="display:block;width:240px;height:48px;font-size:16px">{label}</button>
<a href="done.html" class="go">다음</a></main></body></html>"""
DONE = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><h1 style="margin:16px">완료</h1><p>결제가 끝났어요</p></body></html>"""


def write_pay(out, gap="", label="지금 결제하기"):
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", gap).replace("{label}", label), encoding="utf-8")


@pytest.fixture(scope="module")
def apage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-annot-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    write_pay(out)
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    pg.out = out
    yield pg
    assert not errors, errors
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)


PIN = '.card[data-id="pay"] .npin'
BADGE = '.card[data-id="pay"] .nbadge'


def pins(pg):
    return pg.evaluate(f"""[...document.querySelectorAll('{PIN}')].map(p => ({{no: p.textContent, st: p.dataset.st, top: parseFloat(p.style.top),
        vis: getComputedStyle(p.parentNode).display !== 'none'}}))""")


def el_box(pg, ph, fr, sel):
    """카드 안 요소 sel 의 상자 → 화면 좌표."""
    r = fr.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card.w")
    return {"x": ph["x"] + r[0] * sc, "y": ph["y"] + r[1] * sc, "w": r[2] * sc, "h": r[3] * sc}


def show_sent(pg, on):
    """메모 패널의 '보낸 메모 보기'(task 29)를 on 으로 — 패널 탭을 앞으로 한 뒤 누른다."""
    pg.click('#dock .dk-tab[data-p="notes"]')
    if (pg.get_attribute("#nsent", "aria-pressed") == "true") != on:
        pg.click("#nsent")
    assert pg.get_attribute("#nsent", "aria-pressed") == ("true" if on else "false")


def annotate_button(pg, note):
    ph = zoom_to(pg, "pay", 420)                     # 카드 화면 ≈ 실제의 52% — 배율만으로는 핀이 안 보이는 크기
    fr = frame_of(pg, "pay")
    pg.keyboard.press("p")
    x, y = el_point(pg, ph, fr, "button.pay")
    pg.mouse.click(x, y)
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.locator('.card[data-id="pay"] .npsel').count() == 1 and pg.is_visible('.card[data-id="pay"] .npsel'), "메모 창이 열린 동안 고른 요소 테두리"
    pg.fill("#pnote", note)
    pg.click("#padd")
    assert pg.locator(".npsel").count() == 0, "창을 닫으면 테두리도"
    pg.keyboard.press("h")
    return ph, (x, y)


@pytest.mark.area("notes")
def test_board_pin_numbers_thread_and_done(apage):
    """(a) 카드 요소에 메모 → 그 요소 자리에 핀 1(다시 불러오지 않고 바로) · 핀 누르기 = 그 메모로 열린 묶음(카드 고르기 아님).
    (b) 1 을 지우고 더하면 2. 완료 → 핀·배지가 빠지고 묶음엔 '숨김' 한 줄(task 29) · 보낸 메모 보기를 켜면 '완료' 묶음에 [다시 열기] → 핀이 돌아온다."""
    pg = apage
    fit_view(pg)
    ph, (x, y) = annotate_button(pg, "버튼을 더 크게")
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["no"] == 1 and notes_of(pg)[0]["targets"][0]["quote"]["exact"] == "지금 결제하기", notes_of(pg)[0]
    pg.wait_for_selector(PIN + '[data-no="1"]', state="visible", timeout=4000)
    b, t = pg.locator(PIN).bounding_box(), el_box(pg, ph, frame_of(pg, "pay"), "button.pay")
    assert b["x"] < t["x"] + t["w"] and t["x"] < b["x"] + b["width"] and b["y"] < t["y"] + t["h"] and t["y"] < b["y"] + b["height"], ("핀은 그 요소 상자에 걸친다", b, t)
    assert pg.locator(PIN).text_content() == "1" and pins(pg)[0]["st"] == "draft"
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.locator("#rows .card.picked").count() == 0, "핀 누르기는 카드 고르기가 아니다"
    assert pg.get_attribute("#thread li.focus", "data-no") == "1"
    assert pg.text_content("#thread li.focus .thn") == "#1" and pg.get_attribute("#thread li.focus .ths", "data-st") == "draft"
    pg.hover("#thread li.focus .tht")
    assert pg.locator('.card[data-id="pay"] .npbox.hi').count() == 1, "묶음 줄에 올리면 그 요소 테두리"
    pg.click('#thread li.focus button[data-act="del"]')   # (b) 지우고 다시
    wait_notes(pg, 0)
    pg.keyboard.press("Escape")
    fit_view(pg)
    annotate_button(pg, "버튼 색")
    wait_notes(pg, 1)
    pg.wait_for_selector(PIN + '[data-no="2"]', state="visible", timeout=4000)
    assert notes_of(pg)[0]["no"] == 2 and [p["no"] for p in pins(pg)] == ["2"], "지운 번호는 다시 쓰지 않는다"
    assert pg.text_content(BADGE) == "1"
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click('#thread li.focus button[data-act="done"]')   # 완료(사람 답 '확인')
    pg.wait_for_function(f"!document.querySelector('{PIN}')")
    assert pg.locator(BADGE).count() == 0, "완료한 메모는 배지 수에서 빠진다"
    assert pg.locator("#thread details.thdone").count() == 0 and "1건 숨김" in pg.text_content("#thread .thhid"), "완료 묶음은 보낸 메모 보기를 켰을 때만(task 29)"
    assert notes_of(pg)[0]["replies"][-1]["kind"] == "확인"
    show_sent(pg, True)
    pg.click(BADGE)                                    # 켜면 완료한 메모도 배지 수에
    pg.wait_for_selector("#thread details.thdone li", state="attached")
    pg.click("#thread details.thdone summary")
    pg.click('#thread details.thdone button[data-act="reopen"]')
    pg.wait_for_selector(PIN + '[data-no="2"]', state="attached", timeout=4000)
    n = notes_of(pg)[0]
    assert [r["kind"] for r in n["replies"]] == ["확인", "다시"] and n["sent"] is False and pg.text_content(BADGE) == "1"
    show_sent(pg, False)
    pg.keyboard.press("Control+z")                     # 다시 열기 = 되돌리기 한 단계
    pg.wait_for_function(f"!document.querySelector('{PIN}')")
    pg.keyboard.press("Control+y")
    pg.wait_for_selector(PIN, state="attached", timeout=4000)
    pg.keyboard.press("Escape")


@pytest.mark.area("notes")
def test_pins_reanchor_after_screen_changes(apage):
    """(c) 화면 파일이 바뀌어 요소가 내려가도(글 그대로) 다시 불러오면 핀이 따라간다 · 글이 바뀌면 핀은 없고 묶음 줄에 '대상이 바뀌었어요'."""
    pg = apage
    if not notes_of(pg):
        fit_view(pg)
        annotate_button(pg, "버튼")
    reload(pg)
    fit_view(pg)
    pg.wait_for_selector(PIN, state="attached", timeout=5000)
    top0 = pins(pg)[0]["top"]
    write_pay(pg.out, gap='<div style="height:200px"></div>')
    reload(pg)
    fit_view(pg)
    pg.wait_for_function(f"(() => {{ const p = document.querySelector('{PIN}'); return p && parseFloat(p.style.top) > {top0} + 150; }})()", timeout=5000)
    write_pay(pg.out, gap='<div style="height:200px"></div>', label="결제 완료")
    reload(pg)
    fit_view(pg)
    pg.wait_for_function("document.querySelector('.card[data-id=\"pay\"] .phone iframe').getAttribute('src')", timeout=5000)
    pg.click(BADGE)
    pg.wait_for_selector("#thread .thlost", timeout=5000)
    assert pg.locator('#thread li[data-no] .thlost').count() == 1
    why = "화면이 바뀌어 같은 요소가 여러 개이거나 없어요"
    assert pg.text_content("#thread .thlost") == "요소를 찾을 수 없음" and pg.get_attribute("#thread .thlost", "title") == why
    assert pg.locator(PIN).count() == 0, "다시 찾지 못한 대상에는 핀이 없다"
    # 메모 목록 줄에도 같은 상태(#285) — 조용히 사라지지 않는다
    assert pg.locator("#nlist li .nlost").count() == 1 and pg.get_attribute("#nlist li .nlost", "title") == why
    pg.keyboard.press("Escape")
    write_pay(pg.out)


@pytest.mark.area("notes")
def test_answered_memo_has_no_pin_and_leaves_badge(apage):
    """(d) 반영됨 답이 달린 메모(상태 파일에 끼워 넣음) → 핀 없음, 배지 수에서 빠짐. 배율로 화면이 실제의 60% 이상이면 고르지 않아도 핀이 보인다."""
    pg = apage
    pg.evaluate("""() => { const t = {path: 'button.pay', text: '지금 결제하기', quote: {exact: '지금 결제하기', prefix: '', suffix: ''}};
        const a = [{id: 'own8', no: 8, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: null, note: '열린 메모', intent: 'change', sent: false, replies: []}];
        a.push({id: 'ans1', no: 9, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: t.rect, note: '답 받은 메모', intent: 'change', sent: true,
                replies: [{kind: '반영됨', what: '크게 했어요', screens: ['pay'], captured: true}]});
        a.push({id: 'ask1', no: 10, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: t.rect, note: '물어본 메모', intent: 'change', sent: true,
                replies: [{kind: '질문', question: '어느 색?', choices: ['파랑', '검정']}]});
        const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
        localStorage.setItem('hd-notes:' + h, JSON.stringify(a)); localStorage.setItem('hd-note-seq:' + h, JSON.stringify({pay: 10})); }""")   # 앞 테스트의 메모에 기대지 않는다
    reload(pg)
    fit_view(pg)
    pg.wait_for_selector(PIN + '[data-no="10"]', state="attached", timeout=5000)
    ps = pins(pg)
    assert "9" not in [p["no"] for p in ps], ps
    assert sorted(p["no"] for p in ps) == ["10", "8"] and [p["st"] for p in ps if p["no"] == "10"] == ["decide"], ("결정 필요 핀", ps)
    assert pg.text_content(BADGE) == "2", "배지 = 열린 메모 수"
    zoom = lambda: float(pg.evaluate("document.getElementById('stage').dataset.zoom"))
    for _ in range(20):                                # 작게(배율 0.5 아래로)
        if zoom() < 0.5:
            break
        pg.mouse.move(5, 500)
        pg.keyboard.down("Control"); pg.mouse.wheel(0, 200); pg.keyboard.up("Control")
        pg.wait_for_timeout(60)
    pg.mouse.move(5, 500)
    assert zoom() < 0.5 and not pins(pg)[0]["vis"], (zoom(), "작게 볼 때는 고르거나 올려야 보인다")
    zoom_to(pg, "pay", 0.7 * 812)
    pg.mouse.move(5, 500)
    assert pins(pg)[0]["vis"], "화면이 실제의 60% 이상이면 늘 보인다"


SEED_JS = """() => { const t = {path: 'button.pay', text: '지금 결제하기', quote: {exact: '지금 결제하기', prefix: '', suffix: ''}},
        l = {path: 'p.lead', text: '카드를 고르세요', quote: {exact: '카드를 고르세요', prefix: '', suffix: ''}};
    const a = [{id: 'm1', no: 1, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: null, note: '버튼을 더 크게', intent: 'change', sent: false, replies: []},
               {id: 'q1', no: 2, screen: 'pay', targets: [l], path: l.path, text: l.text, rect: null, note: '안내 글 색', intent: 'change', sent: true,
                replies: [{kind: '질문', question: '어느 색?', choices: ['파랑', '검정']}]}];
    const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
    localStorage.setItem('hd-notes:' + h, JSON.stringify(a)); localStorage.setItem('hd-note-seq:' + h, JSON.stringify({pay: 2})); localStorage.removeItem('hd-show-sent:' + h); }"""


@pytest.mark.area("notes")
def test_sent_memo_hidden_until_show_sent(apage):
    """task 29: 메모 둘(m1 보내기 전 · q1 질문 받음) → 보내기 = m1 이 목록·배지 수·핀에서 사라짐, 질문 받은 q1 은 그대로 ·
    '보낸 메모 보기 (1)' 켜기 = m1 이 흐리게 + 'AI 작업 중' · 새로고침해도 켜짐 그대로 · 끄면 다시 숨김."""
    pg = apage
    pg.evaluate(SEED_JS)
    reload(pg)
    fit_view(pg)
    zoom_to(pg, "pay", 0.7 * 812)                    # 화면이 실제의 60% 이상 = 핀이 늘 보임
    pg.wait_for_selector(PIN + '[data-no="1"]', state="attached", timeout=5000)
    assert sorted(p["no"] for p in pins(pg)) == ["1", "2"] and pg.text_content(BADGE) == "2"
    assert pg.get_attribute("#nsent", "aria-pressed") == "false" and pg.is_disabled("#nsent") and pg.get_attribute("#nsent", "aria-label") == "보낸 메모 보기 (0)"         and pg.get_attribute("#nsent .ncb", "data-n") == "0", "0 이면 꺼진 단추(자리 유지)"
    pg.click("#nsend")
    pg.wait_for_function("document.getElementById('nmsg').textContent.indexOf('복사') >= 0", timeout=5000)
    assert {n["id"]: n["sent"] for n in notes_of(pg)} == {"m1": True, "q1": True}
    pg.wait_for_function(f"!document.querySelector('{PIN}[data-no=\"1\"]')", timeout=4000)
    assert [p["no"] for p in pins(pg)] == ["2"], "보낸 메모 핀은 사라지고 질문 받은 메모 핀은 남는다"
    assert pg.text_content(BADGE) == "1", "배지 수 = 보이는 메모"
    pg.click('#dock .dk-tab[data-p="notes"]')
    assert pg.eval_on_selector_all("#nlist li", "ls => ls.map(l => l.dataset.id)") == ["q1"], "목록에서 보낸 메모가 빠진다"
    assert pg.get_attribute("#nsent", "aria-label") == "보낸 메모 보기 (1)" and pg.get_attribute("#nsent .ncb", "data-n") == "1" and not pg.is_disabled("#nsent")
    show_sent(pg, True)
    assert pg.eval_on_selector_all("#nlist li", "ls => ls.map(l => l.dataset.id)") == ["m1", "q1"]
    assert "nhid" in pg.get_attribute('#nlist li[data-id="m1"]', "class") and pg.text_content('#nlist li[data-id="m1"] .nsst') == "AI 작업 중", "흐리게 + 상태 말"
    assert float(pg.eval_on_selector('#nlist li[data-id="m1"]', "l => getComputedStyle(l).opacity")) < 0.7
    pg.wait_for_selector(PIN + '[data-no="1"].nhid', state="attached", timeout=4000)
    assert pg.text_content(BADGE) == "2"
    reload(pg)
    fit_view(pg)
    pg.click('#dock .dk-tab[data-p="notes"]')
    assert pg.get_attribute("#nsent", "aria-pressed") == "true", "켜짐은 새로고침 뒤에도(캔버스마다 저장)"
    assert pg.locator("#nlist li").count() == 2
    show_sent(pg, False)
    assert pg.eval_on_selector_all("#nlist li", "ls => ls.map(l => l.dataset.id)") == ["q1"]
    assert pg.text_content(BADGE) == "1"


@pytest.mark.area("notes")
def test_broken_show_sent_value_warns_and_defaults_off(apage):
    """깨진 저장값(hd-show-sent) = [hd] 경고 한 줄 + 꺼짐(오류 탐지)."""
    pg = apage
    pg.evaluate(SEED_JS)
    pg.evaluate("""() => { const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
        localStorage.setItem('hd-show-sent:' + h, 'yes please'); }""")
    warns = []
    pg.on("console", lambda m: warns.append(m.text) if m.type == "warning" else None)
    reload(pg)
    assert pg.get_attribute("#nsent", "aria-pressed") == "false"
    assert any(w.startswith("[hd] hd-show-sent:") for w in warns), warns
