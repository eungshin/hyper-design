"""메모 주석·핀(task 11) — 판 카드 위 메모 핀 · 화면마다 바뀌지 않는 번호 · 다시 찾기(hd-locate) · 완료/다시 열기 (Playwright).

작은 화면 두 장을 임시 out 에 만들어 build_canvas.py 로 빌드한다(화면 파일을 고쳐 다시 찾기를 본다 — 고정본은 건드리지 않는다).
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import NOTES_JS, fit_view, notes_of, wait_notes, el_point, frame_of

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


@pytest.mark.area("notes")
def test_thread_row_actions_are_quiet_icons_with_tooltips(apage):
    """R26: 묶음 줄 동작 = 메타 줄 끝 작은 아이콘(글 단추 아님) · 올리면 #thtip 꼬리말이 이름을 말한다 · 메모 글이 메타보다 크고 진하다 ·
    머리 줄 + = 메모 추가 · 고치기(메모 창)·완료(사람 답 '확인')·지우기 그대로."""
    pg = apage
    pg.evaluate(SEED_JS)
    reload(pg)
    fit_view(pg)
    pg.click(BADGE)
    pg.wait_for_selector("#thread:not([hidden])")
    row = '#thread li[data-id="m1"]'
    acts = pg.eval_on_selector_all(row + " .thl button", "bs => bs.map(b => [b.dataset.act, b.getAttribute('aria-label'), b.textContent.trim(), !!b.querySelector('svg')])")
    assert acts == [["edit", "고치기", "", True], ["del", "지우기", "", True], ["done", "완료", "", True]], ("메타 줄 안 아이콘(글 없음)", acts)
    hb, mb = pg.locator(row + ' button[data-act="del"]').bounding_box(), pg.locator(row + " .thn").bounding_box()
    assert hb["width"] <= 28 and hb["height"] <= 28 and abs((hb["y"] + hb["height"] / 2) - (mb["y"] + mb["height"] / 2)) < 6, ("작은 아이콘이 메타와 같은 줄", hb, mb)
    assert pg.locator('#thread button[data-act="add"]').text_content().strip() == "" and pg.get_attribute('#thread button[data-act="add"]', "aria-label") == "메모 추가"
    css = lambda sel, p: pg.eval_on_selector(sel, f"e => getComputedStyle(e).{p}")
    assert float(css(row + " .tht", "fontSize")[:-2]) > float(css(row + " .the", "fontSize")[:-2]), "메모 글이 메타보다 크다"
    assert css(row + " .tht", "fontWeight") == "400" and css(row + " .tht", "color") == "rgb(28, 28, 28)"
    pg.mouse.move(5, 995)
    quiet = css('#thread li[data-id="q1"] button[data-act="del"]', "color")
    pg.hover(row + ' button[data-act="del"]')
    pg.wait_for_selector("#thtip:not([hidden])")
    assert pg.text_content("#thtip") == "지우기"
    assert css(row + ' button[data-act="del"]', "color") != quiet, "올리면 진하게(평소 흐림)"
    pg.hover(row + ' button[data-act="done"]')
    assert pg.text_content("#thtip") == "완료"
    pg.click(row + ' button[data-act="edit"]')        # 고치기 = 그 메모의 메모 창
    pg.wait_for_selector("#pop:not([hidden])")
    assert pg.input_value("#pnote") == "버튼을 더 크게" and pg.is_hidden("#thread") and pg.is_hidden("#thtip")
    pg.keyboard.press("Escape")
    pg.click(BADGE)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click(row + ' button[data-act="done"]')
    pg.wait_for_function("(() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:')); const m = JSON.parse(localStorage.getItem(k)).find(n => n.id === 'm1'); return m && (m.replies || []).some(r => r.kind === '확인'); })()", timeout=4000)
    pg.click('#thread li[data-id="q1"] button[data-act="del"]')
    pg.wait_for_function("(() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:')); return !JSON.parse(localStorage.getItem(k)).some(n => n.id === 'q1'); })()", timeout=4000)
    pg.keyboard.press("Escape")


@pytest.mark.area("notes")
def test_annotate_shift_click_adds_and_removes_elements_on_the_board(apage):
    """주석 도구(P): 메모 창이 열린 채 같은 카드 안 Shift+클릭 = 그 요소를 메모 대상에 더하기 · 다시 Shift+클릭 = 빼기(크게 보기와 같다).
    카드 고르기(Shift = 여러 장)로 가지 않는다."""
    pg = apage
    fit_view(pg)
    ph = zoom_to(pg, "pay", 420)
    fr = frame_of(pg, "pay")
    pg.keyboard.press("p")
    pg.mouse.click(*el_point(pg, ph, fr, "button.pay"))
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    lead = el_point(pg, ph, fr, "p.lead")
    pg.keyboard.down("Shift"); pg.mouse.click(*lead); pg.keyboard.up("Shift")
    pg.wait_for_function("document.querySelectorAll('.card[data-id=\"pay\"] .npsel').length === 2", timeout=3000)
    assert not pg.is_hidden("#pop") and pg.locator(".card.sel").count() == 0, "카드 고르기로 가지 않는다"
    pg.fill("#pnote", "둘 다 크게")
    pg.keyboard.down("Shift"); pg.mouse.click(*lead); pg.keyboard.up("Shift")
    pg.wait_for_function("document.querySelectorAll('.card[data-id=\"pay\"] .npsel').length === 1", timeout=3000)
    assert pg.input_value("#pnote") == "둘 다 크게", "빼도 쓰던 글은 그대로"
    pg.keyboard.down("Shift"); pg.mouse.click(*lead); pg.keyboard.up("Shift")
    pg.wait_for_function("document.querySelectorAll('.card[data-id=\"pay\"] .npsel').length === 2", timeout=3000)
    pg.click("#padd")                                       # 같은 페이지를 쓰는 앞 테스트 메모가 남아 있을 수 있다 — 이 메모만 본다
    pg.wait_for_function(f"({NOTES_JS}).some(n => n.note === '둘 다 크게')", timeout=4000)
    mine = [n for n in notes_of(pg) if n["note"] == "둘 다 크게"]
    assert len(mine) == 1 and len(mine[0]["targets"]) == 2, mine


@pytest.mark.area("notes")
def test_double_click_on_memo_text_opens_it_for_editing(apage):
    """메모 글 더블클릭 = 고치기 아이콘과 같다(메모 묶음 · 메모 패널) — 그 메모의 메모 창이 열린다."""
    pg = apage
    pg.evaluate(SEED_JS)
    reload(pg)
    fit_view(pg)
    pg.click(BADGE)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.dblclick('#thread li[data-id="m1"] .tht')
    pg.wait_for_selector("#pop:not([hidden])")
    assert pg.input_value("#pnote") == "버튼을 더 크게" and pg.is_hidden("#thread")
    pg.keyboard.press("Escape")
    pg.wait_for_selector("#pop", state="hidden")
    pg.click('#dock .dk-tab[data-p="notes"]')
    pg.dblclick('#nlist li[data-id="m1"] .nnote')
    pg.wait_for_selector("#pop:not([hidden])")
    assert pg.input_value("#pnote") == "버튼을 더 크게"
    pg.keyboard.press("Escape")


@pytest.mark.area("notes")
def test_memo_composer_is_quiet_and_opens_beside_its_target(apage):
    """R27 F09: 메모 쓰는 창 — 내부 경로 줄 없음(꼬리말만) · 의도 말은 한국어(바꾸기·질문) · 범위 = 기본이 골라진 아이콘 셋(이름은 꼬리말) ·
    의도·범위·📎·추가가 아이콘 한 줄 · × 는 머리 줄 · 글 칸이 컨트롤 글보다 크다 · 창은 누른 요소 옆(덮지 않음)."""
    pg = apage
    pg.evaluate(SEED_JS)
    reload(pg)
    ph = zoom_to(pg, "pay", 420)
    fr = frame_of(pg, "pay")
    pg.keyboard.press("p")
    x, y = el_point(pg, ph, fr, "button.pay")
    pg.mouse.click(x, y)
    pg.wait_for_selector("#pop:not([hidden])")
    assert pg.text_content("#ptitle") == "지금 결제하기" and "pay" in pg.get_attribute("#ptitle", "title") and pg.is_hidden("#ppath")
    assert pg.eval_on_selector_all("#pintent button", "bs => bs.map(b => b.textContent)") == ["바꾸기", "질문"]
    sc = pg.eval_on_selector_all("#pscope button", "bs => bs.map(b => [b.textContent.trim(), b.getAttribute('aria-label'), b.getAttribute('aria-pressed'), !!b.querySelector('svg')])")
    assert sc == [["", "이 요소", "true", True], ["", "이 화면", "false", True], ["", "모든 화면", "false", True]], sc
    mid = lambda sel: (lambda b: b["y"] + b["height"] / 2)(pg.locator(sel).bounding_box())
    row = [mid(s) for s in ("#pintent", "#pscope", "#pop .patt", "#padd")]
    assert max(row) - min(row) < 4, ("아이콘 한 줄", row)
    pb, cb, tb = pg.locator("#pop").bounding_box(), pg.locator("#pcancel").bounding_box(), pg.locator("#pnote").bounding_box()
    ab = pg.locator("#pop .patt").bounding_box()
    assert pb["x"] <= ab["x"] and ab["x"] + ab["width"] <= pb["x"] + pb["width"], "📎 는 창 안(R22)"
    assert cb["y"] + cb["height"] <= tb["y"] and pg.get_attribute("#pcancel", "aria-label") == "닫기", "× = 머리 줄"
    fs = lambda sel: float(pg.eval_on_selector(sel, "e => getComputedStyle(e).fontSize")[:-2])
    assert fs("#pnote") > fs("#pintent button") and fs("#pnote") >= fs("#ptitle")
    eb = el_box(pg, ph, fr, "button.pay")
    over = not (pb["x"] + pb["width"] <= eb["x"] or eb["x"] + eb["w"] <= pb["x"] or pb["y"] + pb["height"] <= eb["y"] or eb["y"] + eb["h"] <= pb["y"])
    assert not over, ("창이 고른 요소를 덮지 않는다", pb, eb)
    pg.hover('#pscope button[data-scope="all"]')
    pg.wait_for_selector("#poptip:not([hidden])")
    assert pg.text_content("#poptip") == "범위: 모든 화면"
    pg.click('#pintent [data-intent="question"]')
    assert pg.get_attribute("#pnote", "placeholder") == "무엇이 궁금한지 적어 주세요…"
    pg.click("#pcancel")
    assert pg.is_hidden("#pop") and pg.is_hidden("#poptip")
    pg.keyboard.press("v")


@pytest.mark.area("notes")
def test_memo_panel_groups_rows_under_screen_title(apage):
    """R27 F10: 메모 패널 — 화면 이름 머리가 화면마다 한 번 · 줄 = 작은 회색 메타(번호·의도 아이콘·대상) + 메모 글(더 크고 진함) · 화면 id·영어 의도 말 없음."""
    pg = apage
    pg.evaluate("""() => { const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
      const b = {path: 'button.pay', text: '지금 결제하기'}, body = {path: 'body', text: '결제'};
      const mk = (id, no, screen, t, note, intent) => ({id, no, screen, targets: [t], path: t.path, text: t.text, rect: null, note, intent, sent: false, replies: []});
      localStorage.setItem('hd-notes:' + h, JSON.stringify([mk('m1', 1, 'pay', b, '버튼을 더 크게', 'change'), mk('d1', 1, 'done', {path: 'body', text: '완료'}, '축하 그림 넣기', 'change'),
        mk('m2', 2, 'pay', body, '이 화면이 꼭 필요할까요?', 'question')]));
      localStorage.setItem('hd-note-seq:' + h, JSON.stringify({pay: 2, done: 1})); localStorage.removeItem('hd-show-sent:' + h); }""")
    reload(pg)
    pg.wait_for_selector("#notes:not([hidden])")
    assert pg.eval_on_selector_all("#nlist .ngh", "es => es.map(e => e.textContent)") == ["결제", "완료"], "화면 이름은 화면마다 한 번"
    assert pg.eval_on_selector_all("#nlist li", "ls => ls.map(l => l.dataset.id)") == ["m1", "m2", "d1"], "같은 화면끼리 묶임(줄 = 메모 하나)"
    meta = pg.eval_on_selector_all("#nlist li .nl", r"es => es.map(e => e.innerText.replace(/\s+/g, ' ').trim())")
    assert meta == ["#1 지금 결제하기", "#2 화면 전체", "#1 화면 전체"], meta
    txt = pg.text_content("#nlist")
    assert not any(w in txt for w in ("pay", "done", "change", "question")), ("내부 id·영어 의도 없음", txt)
    assert pg.eval_on_selector_all("#nlist li .ni", "es => es.map(e => e.getAttribute('aria-label'))") == ["바꾸기", "질문", "바꾸기"]
    css = lambda sel, p: pg.eval_on_selector(sel, f"e => getComputedStyle(e).{p}")
    row = '#nlist li[data-id="m1"]'
    assert float(css(row + " .nnote", "fontSize")[:-2]) > float(css(row + " .nl", "fontSize")[:-2]) and css(row + " .nnote", "color") == "rgb(28, 28, 28)"
    eb, nb = pg.locator(row + ' button[data-act="edit"]').bounding_box(), pg.locator(row + " .nn").bounding_box()
    assert abs((eb["y"] + eb["height"] / 2) - (nb["y"] + nb["height"] / 2)) < 6, "연필·휴지통은 메타 줄 끝(메모 묶음과 같이)"


# ---------------------------------------------------------------- 메모 도구 한 칸·두 모드(2026-10-29 브리프)
MEMO_SHOTS = Path(tempfile.gettempdir()) / "claude" / "memo-tool-shots"
MEMO_BTN = '#tools [data-tool="memo"]'


def _hover_label(pg, sel):
    pg.wait_for_function(f"(() => {{ const b = document.querySelector('{sel}'); return b && b.dataset.label; }})()", timeout=3000)
    return pg.get_attribute(sel, "data-label")


@pytest.mark.area("tools", "notes")
def test_memo_tool_is_one_slot_with_two_modes(apage):
    """메모 = 말풍선 한 칸: P = 요소 모드 · M = 화면 모드 — 귀퉁이 글·키·꼬리말 첫 줄이 지금 모드를 말하고, 같은 칸 단추 = 마지막 모드."""
    pg = apage
    fit_view(pg)
    assert pg.locator('#tools [data-tool="annotate"]').count() == 0 and pg.locator(MEMO_BTN).count() == 1
    pg.keyboard.press("m")
    assert pg.get_attribute(MEMO_BTN, "aria-pressed") == "true"
    assert pg.text_content(MEMO_BTN + " .tmode") == "화면" and pg.get_attribute(MEMO_BTN, "data-key") == "M"
    assert pg.get_attribute(MEMO_BTN, "data-tip").startswith("메모 · 화면 전체|")
    pg.keyboard.press("p")
    assert pg.text_content(MEMO_BTN + " .tmode") == "요소" and pg.get_attribute(MEMO_BTN, "aria-label") == "메모 · 요소 (P)"
    pg.keyboard.press("m"); pg.keyboard.press("h")
    pg.click(MEMO_BTN)
    assert pg.get_attribute(MEMO_BTN, "aria-pressed") == "true" and pg.text_content(MEMO_BTN + " .tmode") == "화면", "단추 = 마지막 모드"
    pg.hover(MEMO_BTN)
    pg.wait_for_selector("#ttip:not([hidden])")
    assert "메모 · 화면 전체" in pg.text_content("#ttip") and "Shift" in pg.text_content("#ttip")
    MEMO_SHOTS.mkdir(parents=True, exist_ok=True)
    pg.locator("#tools").screenshot(path=str(MEMO_SHOTS / "toolbar-memo-slot.png"))
    pg.mouse.move(600, 400)
    pg.keyboard.press("h")


@pytest.mark.area("tools", "notes")
def test_memo_hover_shows_target_before_click(apage):
    """누르기 전 미리 보이기: 요소 모드 = 그 요소 테두리 + '<종류> · 요소' · 화면 모드 = 카드 전체 테두리 + '<화면 이름> · 화면 전체' ·
    요소 모드여도 카드 제목 줄 위 = 화면 전체."""
    pg = apage
    fit_view(pg)
    ph = zoom_to(pg, "pay", 420)
    fr = frame_of(pg, "pay")
    MEMO_SHOTS.mkdir(parents=True, exist_ok=True)
    pg.keyboard.press("p")
    pg.mouse.move(*el_point(pg, ph, fr, "button.pay"))
    assert _hover_label(pg, ".elbox:not(.sel):not(.par)") == "버튼 · 요소"
    assert pg.locator(".elbox.scr").count() == 0
    pg.screenshot(path=str(MEMO_SHOTS / "hover-element.png"))
    tb = pg.locator('.card[data-id="pay"] .ftitle').bounding_box()
    pg.mouse.move(tb["x"] + 10, tb["y"] + tb["height"] / 2)
    assert _hover_label(pg, '.card[data-id="pay"] .elbox.scr') == "결제 · 화면 전체", "제목 줄 = 늘 화면 전체"
    pg.keyboard.press("m")
    pg.mouse.move(*el_point(pg, ph, fr, "p.lead"))
    assert _hover_label(pg, '.card[data-id="pay"] .elbox.scr') == "결제 · 화면 전체"
    pg.wait_for_timeout(250)                                 # 늦게 온 요소 답이 화면 테두리를 덮지 않는다
    assert pg.locator('.card[data-id="pay"] .elbox:not(.scr):not(.sel):not(.par)').count() == 0
    cb = pg.locator('.card[data-id="pay"]').bounding_box(); sb = pg.locator('.card[data-id="pay"] .elbox.scr').bounding_box()
    assert sb["x"] <= cb["x"] and sb["y"] <= cb["y"] and sb["x"] + sb["width"] >= cb["x"] + cb["width"], ("카드 전체 테두리", cb, sb)
    pg.screenshot(path=str(MEMO_SHOTS / "hover-screen.png"))
    pg.mouse.move(5, 300)
    pg.keyboard.press("h")
    assert pg.locator(".elbox.scr").count() == 0, "판 밖·도구 바꾸면 걷힌다"


@pytest.mark.area("tools", "notes")
def test_memo_click_title_is_whole_screen_and_shift_adds_screens(apage):
    """경계 = 늘 화면 전체(요소 모드에서 카드 제목을 눌러도) · 화면 모드 Shift+클릭 = 고른 화면 더하기·빼기(memo-batch), 쓰던 글 그대로."""
    pg = apage
    fit_view(pg)
    pg.keyboard.press("p")
    pg.click('.card[data-id="pay"] .ftitle')
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.text_content("#ptitle") == "결제 — 화면 전체", pg.text_content("#ptitle")
    assert pg.get_attribute('#pscope button[aria-pressed="true"]', "data-scope") == "screen"
    pg.keyboard.press("Escape")
    pg.wait_for_selector("#pop", state="hidden")
    pg.keyboard.press("m")
    cover = lambda sid: pg.locator(f'.card[data-id="{sid}"] .phone').bounding_box()
    c = cover("pay"); pg.mouse.click(c["x"] + c["width"] / 2, c["y"] + c["height"] / 2)
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.text_content("#ptitle") == "결제 — 화면 전체"
    pg.fill("#pnote", "두 화면 모두")
    d = cover("done")
    pg.keyboard.down("Shift"); pg.mouse.click(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2); pg.keyboard.up("Shift")
    pg.wait_for_function("document.getElementById('ptitle').textContent.startsWith('고른 화면 2개')", timeout=3000)
    assert pg.input_value("#pnote") == "두 화면 모두" and pg.locator(".card.sel").count() == 0, "쓰던 글 그대로 · 카드 고르기로 가지 않는다"
    pg.keyboard.down("Shift"); pg.mouse.click(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2); pg.keyboard.up("Shift")
    pg.wait_for_function("document.getElementById('ptitle').textContent === '결제 — 화면 전체'", timeout=3000)
    pg.keyboard.down("Shift"); pg.mouse.click(d["x"] + d["width"] / 2, d["y"] + d["height"] / 2); pg.keyboard.up("Shift")
    pg.wait_for_function("document.getElementById('ptitle').textContent.startsWith('고른 화면 2개')", timeout=3000)
    pg.click("#padd")
    pg.wait_for_function(f"({NOTES_JS}).filter(n => n.note === '두 화면 모두').length === 2", timeout=4000)
    mine = [n for n in notes_of(pg) if n["note"] == "두 화면 모두"]
    assert sorted(n["screen"] for n in mine) == ["done", "pay"] and all(n["path"] == "body" for n in mine), mine
    pg.keyboard.press("h")


def _open_board_memo(pg, ph, fr):
    pg.keyboard.press("p")
    pg.mouse.click(*el_point(pg, ph, fr, "button.pay"))
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)


@pytest.mark.area("notes", "tools")
def test_leaving_memo_tool_closes_an_empty_memo_popup(apage):
    """R52: 메모 요소 모드(P)로 요소를 눌러 연 빈 메모 창 → 다른 도구(키·도구 막대 단추) = 창이 닫힌다(Figma 댓글 모드와 같게) · 고른 요소 테두리도.
    글을 이미 썼으면 창이 그대로 남는다(쓴 글을 조용히 버리지 않는다) — 추가하거나 ×/Esc 로 직접 닫는다."""
    pg = apage
    fit_view(pg)
    ph = zoom_to(pg, "pay", 420)
    fr = frame_of(pg, "pay")
    _open_board_memo(pg, ph, fr)
    pg.mouse.move(5, 500)                                      # 글 칸 밖(키가 도구로 가게) — 창은 열려 있다
    pg.evaluate("document.activeElement && document.activeElement.blur()")
    pg.keyboard.press("v")
    pg.wait_for_selector("#pop", state="hidden", timeout=3000)
    assert pg.locator(".npsel").count() == 0, "창을 닫으면 고른 요소 테두리도"
    _open_board_memo(pg, ph, fr)
    pg.click('#tools [data-tool="hand"]')
    pg.wait_for_selector("#pop", state="hidden", timeout=3000)
    _open_board_memo(pg, ph, fr)
    pg.fill("#pnote", "쓰던 글")
    pg.click('#tools [data-tool="move"]')
    pg.wait_for_timeout(200)
    assert not pg.is_hidden("#pop") and pg.input_value("#pnote") == "쓰던 글", "쓴 글은 남는다"
    pg.fill("#pnote", "")                                     # 다 지우면 다시 빈 창 = 도구를 바꾸면 닫힘
    pg.click('#tools [data-tool="hand"]')
    pg.wait_for_selector("#pop", state="hidden", timeout=3000)


@pytest.mark.area("notes", "modal")
def test_leaving_memo_tool_in_large_view_closes_an_empty_memo_popup(apage):
    """R52: 크게 보기도 같은 규칙 — 메모 요소 모드(P)로 고른 요소의 빈 메모 창은 손(H)·이동 단추로 바꾸면 닫히고, 쓴 글이 있으면 남는다."""
    pg = apage
    fit_view(pg)
    pg.keyboard.press("h")
    pg.dblclick('.card[data-id="pay"] .cover')
    pg.wait_for_selector("#modal:not([hidden])", timeout=5000)
    mf = None
    for _ in range(100):
        mf = pg.query_selector("#mframe").content_frame()
        if mf and mf.query_selector("button.pay"):
            break
        pg.wait_for_timeout(100)

    def open_memo():
        pg.keyboard.press("p")
        pg.wait_for_function("document.querySelector('#tools [data-tool=\"memo\"]').getAttribute('aria-pressed') === 'true'", timeout=3000)
        mf.click("button.pay")
        pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
        pg.evaluate("document.activeElement && document.activeElement.blur()")

    open_memo()
    pg.keyboard.press("h")
    pg.wait_for_selector("#pop", state="hidden", timeout=3000)
    open_memo()
    pg.click('#tools [data-tool="move"]')
    pg.wait_for_selector("#pop", state="hidden", timeout=3000)
    open_memo()
    pg.fill("#pnote", "크게 보기 글")
    pg.click('#tools [data-tool="hand"]')
    pg.wait_for_timeout(200)
    assert not pg.is_hidden("#pop") and pg.input_value("#pnote") == "크게 보기 글", "쓴 글은 남는다"
    pg.click("#pcancel")
    pg.keyboard.press("Escape")
    pg.wait_for_selector("#modal", state="hidden", timeout=3000)
