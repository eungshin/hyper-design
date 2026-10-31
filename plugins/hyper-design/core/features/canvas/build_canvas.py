"""screens.json → 캔버스 (v3, docs/v13-spec.md §7 · success-criteria §9).

python3 build_canvas.py <out_dir>

출력
- out/index.html      : canvas_template.html 에 데이터 JSON(<script id="hd-data">)·도장 meta·noscript 링크만 끼우고, 셸은 참조만 —
                        <!-- hd-shell-css --> → <link rel="stylesheet" href="hd-shell.css?v=<코드 도장>"> · <!-- hd-modules -->(+ 바로 뒤 본 <script>) → <script src="hd-shell.js?v=…">
                        (hd-data 바로 뒤, defer·async 아님 — 실행 차례는 예전 인라인과 같다. 상대 주소라 file:// 로 열어도 된다).
- out/hd-shell.js     : modules/*.js(modules() 차례, 머리 주석 뗌, 앞에 /* hd-module: <이름> */ 한 줄) + 템플릿 본 스크립트(맨 뒤).
- out/hd-shell.css    : modules/shell.css 다음 motion.css(캐스케이드 차례, 머리 주석 뗌).
                        셸 파일·palette.js 는 내용이 지금 파일과 다를 때만 쓴다(데이터만 바뀐 빌드는 작은 index.html 만 새로 — 새로 쓴 큰 파일 첫 열기가 느리다).
                        셸 파일을 못 쓰면 [hd] 한 줄 뒤 예전 길(index.html 에 셸을 끼워 넣는다).
                        헤더 = 제목 · 탭[Screens|Foundation|Components] · 팔레트 점 · [전체 보기][배율%]
                        (조작 그룹 3개: data-group="tabs"/"palette"/"view", 모드 전환 없음)
                        Screens 판 = 끌어서 이동, Ctrl/⌘+휠·핀치 확대, 카드 누르면 크게 보기(크기는 표면 프로필 frame.modal, 기본 390×844).
- out/foundation.html : tokens.css 의 색 역할(쉬운 이름)·글자 단계·여백·모서리·그림자 견본. palette.js 로 즉시 전환.
- out/palette.js      : foundation/palette.js 를 복사(같으면 그대로 — 팔레트 교체 + 주석 달기 hd-pick/hd-picked + 연결 보기 hd-links).
- out/components.html : foundation/specimens.html 중 화면들이 실제로 쓴 클래스의 섹션만. 배지는 screens.json badges 로.

판 규칙(그대로 유지)
- 한 줄 = 한 흐름(group). 상태 변형(id에 --)은 원래 화면 바로 뒤에, 같은 줄에.
- 화살표는 분기(branches)에만, 둥근 직각선(꺾임 ≤ 3, 줄 위 통로). Shift+클릭한 화면은 화면 안 링크(palette.js 가 알려 줌)를
  색별 칩·화살표로(같은 카드 Shift+클릭 = 색 하나씩 → 전체), 긴 화면은 겹쳐서 펼친다.
- 화면 아래: 제목, 고르면 본문(purpose + 옛 policies 줄 '- ', R21 — caption.body). 첫 배율 0.72.

screens.json:
{"groups": [...], "story": {...}, "badges": {"뜻": "is-brand", ...},
 "screens": [{"id", "file", "title", "group", "purpose"(본문, 여러 줄), "branches": [{"to", "label"}]}]}
 file = out 안 경로(기본 screens/<id>.html) 또는 이 PC 개발 서버 주소 http(s)://127.0.0.1|localhost[:포트]/…(앱 카드 — features/app, 링크 미리 뽑기 없음)
선택: decisions.json · palettes.json · credits.json([{slot,file,author,license,url,title}]) · surface.json(표면 프로필 — 카드·모달 크기, 없으면 폰)
환경변수 HD_SPECIMENS 로 specimens.html 경로를 바꿀 수 있다(테스트용).
코드 도장(code_stamp.py): index.html 의 <head> 에 <meta name="hd-code"> — 환경변수 HD_CODE_STAMP(build_ref 가 넘기는 git 나무 도장),
없으면 빌드 입력(템플릿·모듈·shell.css·motion.css·이 파일·palette.js) 내용 해시. 열기가 지금 도장과 견줘 옛 페이지를 다시 빌드한다.
데이터 도장(figma-lite 5): <meta name="hd-inputs"> = out 의 데이터 입력 내용(board_data.input_stamp) — 도우미는 쓰기 때 데이터만 확인하고, 페이지를 줄 때 이 도장이 다르면 다시 빌드한다.
"""
import sys, os, json, re, html, pathlib, time, urllib.parse

import board_data as BD
import code_probe as CP
import code_stamp
import page_fill as PF  # hd-data 이스케이프 · noscript 링크 — 줄 때 끼우기(session.page)와 같은 규칙

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "canvas_template.html"
MODULES_DIR = HERE / "modules"
MODULES_MARKER = "<!-- hd-modules -->"                # 이 자리 + 바로 뒤 본 <script> → <script src="hd-shell.js?v=…">
CSS_MARKER = "<!-- hd-shell-css -->"                 # → <link rel="stylesheet" href="hd-shell.css?v=…">(tokens.css 뒤 — 예전 <style> 자리)
# hd-shell.css 에 싣는 차례 = 캐스케이드 차례(셸 화면 틀 CSS 가 motion.css 보다 앞)
CSS_FILES = (MODULES_DIR / "shell.css", MODULES_DIR / "motion.css")
SHELL_JS, SHELL_CSS = "hd-shell.js", "hd-shell.css"  # out 안 상대 경로(file:// 로 열어도 된다)
PALETTE_JS = HERE.parents[1] / "foundation" / "palette.js"
SPECIMENS = pathlib.Path(os.environ.get("HD_SPECIMENS") or HERE.parents[1] / "foundation" / "specimens.html")


def modules():
    """끼워 넣을 모듈 = modules/*.js 전부(손으로 적는 목록 없음 — 새 모듈은 파일만 만든다). 테스트도 이 함수를 읽는다.
    차례: view-* 가 아닌 것(Model·ViewModel·등록부 features) 먼저, 그다음 view-*, 묶음 안은 이름 차례.
    까닭: 모듈은 정의만 하고 서로를 mount 때 찾지만, View 는 읽힐 때 `HD.feature(...)` 로 자기를 등록할 수 있다 — 그때 등록부가 있어야 한다."""
    names = sorted(f.stem for f in MODULES_DIR.glob("*.js"))
    return [n for n in names if not n.startswith("view-")] + [n for n in names if n.startswith("view-")]


def build_stamp():
    """이 빌드가 index.html 에 적을 도장 — build_ref 가 넘긴 HD_CODE_STAMP, 없으면 작업 트리 내용."""
    return os.environ.get("HD_CODE_STAMP") or CP.work_stamp()


esc = lambda x: html.escape(str(x if x is not None else ""))


# ---------------------------------------------------------------- index.html
def strip_head(src):
    """파일 맨 앞 머리 주석(`/* … */` 첫 덩어리) 하나만 뗀다 — 층·책임·API 설명은 원본 파일(책임 게이트가 읽는 곳)에 남고
    index.html 에는 싣지 않는다(figma-lite 6: 바이트 약 1/5). 그 밖 주석·코드는 손대지 않는다(줄이기 아님).
    맨 앞이 주석이 아니거나 닫히지 않으면 그대로."""
    body = src.lstrip()
    if not body.startswith("/*"):
        return src
    end = body.find("*/", 2)
    return src if end < 0 else body[end + 2:].lstrip("\r\n")


def split_shell(tpl):
    """템플릿 글 → (셸 자리를 비운 템플릿, 본 스크립트 글). 순수.
    본 스크립트 = <!-- hd-modules --> 바로 뒤 <script>…</script>(인라인 스크립트라 안에 `</script>` 가 없다). 그 자리는 표시 하나로 줄인다."""
    at = tpl.find(MODULES_MARKER)
    assert at >= 0, f"canvas_template.html 에 {MODULES_MARKER} 자리가 없다"
    start = at + len(MODULES_MARKER)
    m = re.match(r"\s*<script>", tpl[start:])
    assert m, f"canvas_template.html 의 {MODULES_MARKER} 바로 뒤에 본 <script> 가 없다"
    end = tpl.find("</script>", start + m.end())
    assert end >= 0, "canvas_template.html 의 본 <script> 가 닫히지 않았다"
    main = tpl[start + m.end():end].lstrip("\r\n")
    return tpl[:at] + MODULES_MARKER + tpl[end + len("</script>"):], main


def shell_js(sources, main):
    """[(모듈 이름, 원문)] · 본 스크립트 → hd-shell.js 글. 순수. 모듈마다 머리 주석을 떼고 앞에 `/* hd-module: <이름> */` 한 줄, 본 스크립트는 맨 뒤.
    모듈마다 try 로 감싼다 — 예전 <script> 하나씩과 같게: 앞 모듈이 `;` 없이 끝나도 다음 `(function` 과 붙지 않고(ASI),
    읽다 던지면 그 모듈만 빠진다([hd] console.error 뒤 같은 오류를 다시 던져 pageerror 로도 보인다). 모듈은 모두 IIFE 라 감싸도 이름 범위가 같다."""
    parts = [f"/* hd-module: {name} */\ntry {{\n{strip_head(src)}\n}} catch (e) {{ console.error('[hd] 모듈 {name} 을 읽다 멈췄어요', e); "
             f"setTimeout(function () {{ throw e; }}); }}" for name, src in sources]
    parts.append(f"/* hd-shell: canvas_template.html 본 스크립트 */\n{main}")
    return "\n".join(p if p.endswith("\n") else p + "\n" for p in parts)


def shell_css(sources):
    """[원문] → hd-shell.css 글(주어진 차례 = 캐스케이드 차례, 머리 주석 뗌). 순수."""
    return "\n".join(strip_head(src) for src in sources)


def shell_refs(stamp, js, css):
    """(index.html 의 CSS 자리 글, 스크립트 자리 글) — 상대 주소 + ?v=<코드 도장>(옛 캐시 막기). 순수.
    도장이 없으면 셸 내용 해시. file:// 로 열어도 같은 폴더 파일이라 그대로 된다."""
    v = urllib.parse.quote(stamp or code_stamp.content_stamp([("hd-shell.js", js.encode("utf-8")), ("hd-shell.css", css.encode("utf-8"))]), safe=":")
    return f'<link rel="stylesheet" href="{SHELL_CSS}?v={v}">', f'<script src="{SHELL_JS}?v={v}"></script>'


def shell_inline(js, css):
    """예전 길(셸 파일을 못 쓸 때) — (CSS 자리 글, 스크립트 자리 글)을 index.html 안에 끼울 글로. 순수."""
    css = css.replace("</", "<\\/")
    js = js.replace("</", "<\\/").replace("<!--", "<\\!--")
    return f"<style>\n{css}</style>", f"<script>\n{js}</script>"


def write_if_changed(path, content):
    """내용(str = utf-8 · bytes)이 지금 파일과 다를 때만 쓴다 → 썼나. Edge.
    같으면 손대지 않는다(mtime 그대로 — 데이터만 바뀐 빌드가 큰 셸 파일을 새로 쓰지 않게, 새로 쓴 큰 파일 첫 열기가 느리다).
    쓰기 = 임시 파일 + os.replace(Windows 에서 읽는 중이라 막히면 잠깐 다시). 끝내 못 쓰면 OSError."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    path = pathlib.Path(path)
    try:
        if path.read_bytes() == data:
            return False
    except OSError:                                    # 없음·못 읽음 = 다르다고 보고 쓴다
        pass
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_bytes(data)
    for i in range(5):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            if i == 4:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (i + 1))
    return True


def copy_palette(out):
    """foundation/palette.js → out/palette.js(화면 쪽 스크립트를 최신으로) — 내용이 같으면 쓰지 않는다."""
    if PALETTE_JS.exists():
        write_if_changed(out / "palette.js", PALETTE_JS.read_bytes())


def build_shell(out, tpl, stamp):
    """셸(modules/*.js + 템플릿 본 스크립트 · shell.css + motion.css)을 out/hd-shell.js·hd-shell.css 로 쓰고(같으면 그대로)
    셸 자리를 참조로 채운 템플릿을 돌려준다. 셸 파일을 못 쓰면 [hd] 한 줄 뒤 예전 길 — index.html 에 끼워 넣는다(판은 열린다)."""
    tpl, main = split_shell(tpl)
    assert CSS_MARKER in tpl, f"canvas_template.html 에 {CSS_MARKER} 자리가 없다"
    sources = []
    for name in modules():
        f = MODULES_DIR / f"{name}.js"
        assert f.exists(), f"캔버스 모듈이 없다: {f}"
        sources.append((name, f.read_text(encoding="utf-8")))
    js, css = shell_js(sources, main), shell_css([f.read_text(encoding="utf-8") for f in CSS_FILES])
    try:
        write_if_changed(out / SHELL_JS, js)          # index.html 보다 먼저 — 페이지가 없는 셸 파일을 가리키지 않게
        write_if_changed(out / SHELL_CSS, css)
        link, script = shell_refs(stamp, js, css)
    except OSError as e:
        print(f"[hd] 셸 파일({SHELL_JS}·{SHELL_CSS})을 쓰지 못했어요({e}) — 이번 index.html 에는 셸을 끼워 넣어요", file=sys.stderr, flush=True)
        link, script = shell_inline(js, css)
    return tpl.replace(CSS_MARKER, link, 1).replace(MODULES_MARKER, script, 1)


def build_index(out, m):
    inputs = BD.input_stamp(out)                       # 데이터보다 먼저 잰다 — 그 사이 쓰기가 들면 도장이 옛것이 되어 다음 페이지에서 다시 빌드(안전한 쪽)
    data = BD.index_data(out, m)
    data_rows = data["rows"]
    tpl = TEMPLATE.read_text(encoding="utf-8")
    PF.need(tpl, PF.DATA_SLOT, PF.LINKS_SLOT)          # 셸 파일을 쓰기 전에 자리 검사(없으면 SlotMissing)
    tpl = PF.put_links(tpl, data_rows)                 # 스크립트 없이도(그리고 도달성 검사가) 따라갈 수 있는 화면 링크 목록
    stamp = build_stamp()
    tpl = code_stamp.stamp_inputs(code_stamp.stamp_page(build_shell(out, tpl, stamp), stamp), inputs)
    # hd-data 는 맨 끝에 — 이스케이프 = page_fill.data_json(줄 때 session.page 와 같은 규칙)
    (out / "index.html").write_text(PF.put_data(tpl, data), encoding="utf-8")
    return len(m["screens"]), len(data["arrows"]), len(data_rows)


# ---------------------------------------------------------------- foundation.html
# 쉬운 이름 표는 token_edit(토큰 Model) 하나에 — 부품 고치기 창(R55 phase C)도 같은 이름을 쓴다
from token_edit import COLOR_GROUPS, COLOR_NAMES, FS_NAMES, SPACE_NAMES, R_NAMES, SH_NAMES  # noqa: E402

FOUNDATION_CSS = """
*{box-sizing:border-box} body{margin:0;background:#F6F6F3;color:#1c1c1c;font-family:-apple-system,BlinkMacSystemFont,'Pretendard',sans-serif;word-break:keep-all;padding:24px 24px 64px}
.wrap{max-width:1200px;margin:0 auto} h1{font-size:24px;margin:0 0 4px} .lead{color:#666;margin:0 0 28px;font-size:15px}
h2{font-size:20px;margin:36px 0 12px} h3{font-size:15px;color:#555;margin:20px 0 10px;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.sw{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.sw .chip{height:72px;border-bottom:1px solid rgba(0,0,0,.06)}
.sw .meta{padding:10px 12px 12px} .sw .nm{font-size:16px;font-weight:700;line-height:1.35}
.tok{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#777;word-break:break-all} .val{color:#333}
.type{background:#fff;border-radius:14px;padding:4px 16px} .type .ln{display:flex;align-items:baseline;gap:16px;padding:12px 0;border-bottom:1px solid #eee}
.type .ln:last-child{border:0} .type .lb{flex:none;width:150px} .type .lb b{display:block;font-size:14px}
.type .sample{font-family:var(--font);letter-spacing:var(--tracking);min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.box{background:#fff;border-radius:14px;padding:16px} .bar{height:20px;background:var(--c-brand,#2563eb);border-radius:3px;margin:8px 0 6px}
.rad{width:100%;height:72px;background:var(--c-brand-tint,#e7f0ff);border:2px solid var(--c-brand,#2563eb);margin-bottom:10px}
.shd{height:72px;background:#fff;border-radius:12px;margin:8px 4px 14px}
.box b{font-size:15px}
"""
FOUNDATION_JS = """
(function(){
  function read(){ var cs=getComputedStyle(document.documentElement);
    document.querySelectorAll('[data-var]').forEach(function(el){ var v=cs.getPropertyValue(el.getAttribute('data-var')).trim();
      var o=el.querySelector('.val'); if(o) o.textContent=v||'(없음)'; }); }
  var l=document.getElementById('tokens'); if(l) l.addEventListener('load',read);
  addEventListener('message',function(e){ var t=e.data&&e.data.type; if(t==='hd-palette'||t==='hd-tokens-reload'||t==='hd-css-reload'){ [30,150,500,1200].forEach(function(t){setTimeout(read,t)}); } });
  addEventListener('DOMContentLoaded',read); addEventListener('load',read);
})();
"""


def build_foundation(out):
    tok = out / "tokens.css"
    names = BD.root_vars(tok.read_text(encoding="utf-8")) if tok.exists() else []
    tokcell = lambda n: f'<div class="tok">{esc(n)} · <span class="val"></span></div>'
    parts = []
    colors = [n for n in names if n.startswith("--c-")]
    by = {k: [] for k, _ in COLOR_GROUPS}
    for n in colors:
        g, nm = COLOR_NAMES.get(n, ("etc", n))
        by[g].append((n, nm))
    parts.append("<h2>색</h2>")
    for k, title in COLOR_GROUPS:
        if not by[k]:
            continue
        cells = "".join(f'<div class="sw" data-var="{esc(n)}" data-role="{k}"><div class="chip" style="background:var({esc(n)})"></div>'
                        f'<div class="meta"><div class="nm">{esc(nm)}</div>{tokcell(n)}</div></div>' for n, nm in by[k])
        parts.append(f'<h3>{esc(title)}</h3><div class="grid colors">{cells}</div>')
    fs = [n[5:] for n in names if n.startswith("--fs-")]
    if fs:
        lines = []
        for f in fs:
            style = f"font-size:var(--fs-{f});" + (f"font-weight:var(--fw-{f});" if f"--fw-{f}" in names else "") + (f"line-height:var(--lh-{f});" if f"--lh-{f}" in names else "")
            lines.append(f'<div class="ln" data-var="--fs-{esc(f)}"><div class="lb"><b>{esc(FS_NAMES.get(f, "--fs-" + f))}</b>{tokcell("--fs-" + f)}</div>'
                         f'<div class="sample" style="{style}">가나다 Aa 123 — 모임 날짜를 정해요</div></div>')
        parts.append(f'<h2>글자 단계</h2><div class="type">{"".join(lines)}</div>')
    sp = [n for n in names if n.startswith("--stack-") or n in SPACE_NAMES]
    if sp:
        cells = "".join(f'<div class="box" data-var="{esc(n)}"><b>{esc(SPACE_NAMES.get(n, n))}</b><div class="bar" style="width:var({esc(n)})"></div>{tokcell(n)}</div>' for n in sp)
        parts.append(f'<h2>여백</h2><div class="grid">{cells}</div>')
    rr = [n for n in names if n.startswith("--r-")]
    if rr:
        cells = "".join(f'<div class="box" data-var="{esc(n)}"><div class="rad" style="border-radius:var({esc(n)})"></div><b>{esc(R_NAMES.get(n, n))}</b>{tokcell(n)}</div>' for n in rr)
        parts.append(f'<h2>모서리</h2><div class="grid">{cells}</div>')
    sh = [n for n in names if n.startswith("--shadow-")]
    if sh:
        cells = "".join(f'<div class="box" data-var="{esc(n)}" style="background:#F1F1EE"><div class="shd" style="box-shadow:var({esc(n)})"></div><b>{esc(SH_NAMES.get(n, n))}</b>{tokcell(n)}</div>' for n in sh)
        parts.append(f'<h2>그림자</h2><div class="grid">{cells}</div>')
    if not names:
        parts.append('<p class="lead">tokens.css 가 없어 보여줄 토큰이 없어요.</p>')
    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Foundation — 색·글자·여백</title>
<link id="tokens" rel="stylesheet" href="tokens.css"><script src="palette.js"></script>
<style>{FOUNDATION_CSS}</style></head><body><div class="wrap">
<h1>Foundation</h1><p class="lead">이 앱의 모든 화면이 쓰는 색·글자·여백. 위의 색 점을 누르면 여기도 바로 바뀌어요.</p>
{"".join(parts)}
</div><script>{FOUNDATION_JS}</script></body></html>"""
    (out / "foundation.html").write_text(doc, encoding="utf-8")
    return len(colors)


# ---------------------------------------------------------------- components.html
def used_classes(out):
    used = set()
    for f in (out / "screens").glob("*.html"):
        for v in re.findall(r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)')""", f.read_text(encoding="utf-8", errors="ignore")):
            used.update((v[0] or v[1]).split())
    return used


def spec_sections(body):
    """<section class="spec" …>…</section> 을 중첩 section 까지 세어 잘라낸다 → [(start, end, open_tag, inner)]."""
    res, i = [], 0
    opener = re.compile(r"<section\b[^>]*>", re.I)
    tag = re.compile(r"<(/?)section\b[^>]*>", re.I)
    while True:
        mo = opener.search(body, i)
        if not mo:
            break
        if not re.search(r"""class\s*=\s*["'][^"']*\bspec\b""", mo.group(0)):
            i = mo.end(); continue
        depth, j = 1, mo.end()
        while depth:
            t = tag.search(body, j)
            if not t:
                j = len(body); break
            depth += -1 if t.group(1) else 1
            j = t.end()
        res.append((mo.start(), j, mo.group(0), body[mo.end():j - len("</section>")]))
        i = j
    return res


def attr(tag, name):
    mo = re.search(rf"""\b{name}\s*=\s*["']([^"']*)["']""", tag)
    return mo.group(1) if mo else ""


def badge_section(open_tag, inner, badges):
    cls = lambda c: ".badge" + ("." + esc(c) if c else "")
    if "spec-cell" in inner:                            # specimens.html 의 칸 모양을 그대로 따른다
        cells = "".join(f'<div class="spec-cell"><p class="spec-cap">{esc(k)} · {cls(c)}</p>'
                        f'<div class="spec-stage"><span class="badge {esc(c)}">{esc(k)}</span></div></div>' for k, c in badges.items())
        return f"{open_tag}{cells}</section>"
    head = re.match(r"\s*(<h[1-6]\b[^>]*>.*?</h[1-6]>)", inner, re.S)
    rows = "".join(f'<tr><td style="padding:8px 16px 8px 0"><span class="badge {esc(c)}">{esc(k)}</span></td>'
                   f'<td style="padding:8px 16px 8px 0">{esc(k)}</td><td style="padding:8px 0"><code>.badge{("." + esc(c)) if c else ""}</code></td></tr>'
                   for k, c in badges.items())
    table = (f'<table style="border-collapse:collapse;font-size:14px"><thead><tr style="text-align:left;color:#777">'
             f'<th style="padding:0 16px 6px 0;font-weight:600">모습</th><th style="padding:0 16px 6px 0;font-weight:600">뜻</th>'
             f'<th style="padding:0 0 6px;font-weight:600">클래스</th></tr></thead><tbody>{rows}</tbody></table>')
    return f'{open_tag}{head.group(1) if head else ""}{table}</section>'


def build_components(out, m):
    used = used_classes(out)
    badges = m.get("badges") or {}
    if not SPECIMENS.exists():
        sec = badge_section('<section class="spec" data-key="badge" data-title="배지">', "<h2>배지</h2>", badges) if badges else ""
        doc = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>Components</title><link id="tokens" rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="components.css">'
               f'<script src="palette.js"></script></head><body style="padding:24px;font-family:-apple-system,sans-serif">'
               f'<p>부품 견본 파일(foundation/specimens.html)이 아직 없어요.</p>{sec}</body></html>')
        (out / "components.html").write_text(doc, encoding="utf-8")
        print(f"경고: {SPECIMENS} 없음 — components.html 은 배지만", file=sys.stderr)
        return 0
    src = SPECIMENS.read_text(encoding="utf-8")
    # 링크 경로를 out/ 기준으로
    src = re.sub(r"""(<link\b[^>]*\bid\s*=\s*["']tokens["'][^>]*\bhref\s*=\s*["'])[^"']*(["'])""", r"\1tokens.css\2", src)
    src = re.sub(r"""(<link\b[^>]*\bhref\s*=\s*["'])[^"']*\btokens\.css(["'][^>]*\bid\s*=\s*["']tokens["'])""", r"\1tokens.css\2", src)
    src = re.sub(r"""(\bhref\s*=\s*["'])[^"']*components\.css(["'])""", r"\1components.css\2", src)
    src = re.sub(r"""(\bsrc\s*=\s*["'])[^"']*palette\.js(["'])""", r"\1palette.js\2", src)
    out_parts, last, kept = [], 0, 0
    for s, e, open_tag, inner in spec_sections(src):
        out_parts.append(src[last:s]); last = e
        key = attr(open_tag, "data-key")
        if key not in used:
            continue
        kept += 1
        out_parts.append(badge_section(open_tag, inner, badges) if key == "badge" and badges else src[s:e])
    out_parts.append(src[last:])
    (out / "components.html").write_text("".join(out_parts), encoding="utf-8")
    return kept


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 build_canvas.py <out_dir>")
    out = pathlib.Path(sys.argv[1])
    m = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    copy_palette(out)                                   # 화면 쪽 스크립트(주석 달기·연결 보기)를 최신으로(같으면 그대로)
    n, na, ng = build_index(out, m)
    nc = build_foundation(out)
    nk = build_components(out, m)
    print(f"canvas v3: {n} screens, {na} branch arrows, {ng} groups, scale {BD.frame(out)[0]} · foundation {nc} colors · components {nk} sections")


if __name__ == "__main__":
    main()
