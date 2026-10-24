"""앱 프로젝트(#222 1–3) unit — 무대 목록 읽기(app_stages) · build_canvas 의 개발 서버 주소 규칙 · palette.js 소스 위치 · 감싸개의 무대 주소 읽기.
하위 프로세스는 node 한 번씩(캔버스 unit 과 같은 방식) — 개발 서버·브라우저 없음."""
import json, shutil, subprocess, sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HERE = Path(__file__).resolve().parent
APP = HERE.parent
CORE = APP.parents[1]
FIX = HERE / "fixtures"
NODE = shutil.which("node")
sys.path.insert(0, str(APP))
sys.path.insert(0, str(CORE / "features" / "canvas"))
import app_stages as M  # noqa: E402
import build_canvas  # noqa: E402

DEV = "http://127.0.0.1:5199"


# ---------------------------------------------------------------- app_stages (registry.js 정적 파싱)
@pytest.fixture(scope="module")
def stages():
    return M.parse_registry((FIX / "registry.js").read_text(encoding="utf-8"))


def test_registry_stages_in_order_with_groups_and_labels(stages):
    assert [s["id"] for s in stages] == ["ocr-screen", "word-header", "settings-window"]   # 주석 속 항목은 없음
    by = {s["id"]: s for s in stages}
    assert by["ocr-screen"] == {"id": "ocr-screen", "name": "OcrApp", "group": "organisms",
                                "fixture": "ui_host/popup/src/twin/fixtures/ocr-screen.json",
                                "file": "ui_host/popup/src/lookup/ocr/OcrApp.svelte", "label": "고정 화면 OCR — see http://example.com/x"}
    assert by["word-header"]["group"] == "molecules" and by["word-header"]["name"] == "WordHeader"
    assert by["settings-window"]["label"] == "설정 창 전체 — 헤더 · 레일 · it's escaped"   # 여러 줄 값 · 이스케이프


def test_registry_without_components_is_an_error():
    with pytest.raises(M.AppParseError):
        M.parse_registry("export const PROJECT = 'x';")
    with pytest.raises(M.AppParseError):
        M.parse_registry("export const TWIN_COMPONENTS = [];")


def test_settings_tabs_from_component_source():
    assert M.parse_settings_tabs((FIX / "SettingsApp.svelte").read_text(encoding="utf-8")) == ["basic", "shortcuts", "usage"]
    assert M.parse_settings_tabs("<script>let x = 1;</script>") == []


def test_screens_doc_cards_are_stage_urls_and_tabs_follow_settings(stages):
    doc = M.screens_doc(stages, ["basic", "usage"], DEV + "/")
    ids = [s["id"] for s in doc["screens"]]
    assert ids == ["ocr-screen", "word-header", "settings-window", "settings-window--basic", "settings-window--usage"]
    files = {s["id"]: s["file"] for s in doc["screens"]}
    assert files["word-header"] == DEV + "/hd-stage/word-header.html"
    assert files["settings-window--usage"] == DEV + "/hd-stage/settings-window--usage.html"
    assert all(build_canvas.is_dev_url(f) for f in files.values())
    assert doc["groups"] == ["유기체", "분자"]
    wh = doc["screens"][1]
    assert wh["title"] == "WordHeader" and wh["purpose"].startswith("단어 헤더") and wh["policies"][0] == "소스: ui_host/popup/src/lookup/WordHeader.svelte"


def test_app_doc_is_relaunchable(stages):
    d = M.app_doc("C:/r", "C:/r/ui", DEV + "/", "node vite.js --port 5199", stages)
    assert d == {"kind": "app", "repo": "C:/r", "ui_dir": "C:/r/ui", "dev_cmd": "node vite.js --port 5199", "dev_url": DEV,
                 "stages": ["ocr-screen", "word-header", "settings-window"]}
    assert M.is_dev_url(DEV) and M.is_dev_url("http://localhost:3000/") and not M.is_dev_url("http://example.com:5199")


# ---------------------------------------------------------------- build_canvas: 개발 서버 주소 카드
@pytest.mark.parametrize("f, ok", [
    ("http://127.0.0.1:5173/hd-stage/a.html", True), ("https://localhost/x.html", True), ("http://LOCALHOST:80/", True),
    ("http://127.0.0.1.evil.com/x.html", False), ("http://example.com/x.html", False), ("screens/a.html", False),
    ("file:///C:/x.html", False), ("//127.0.0.1:5173/x", False), (None, False)])
def test_build_dev_url_rule(f, ok):
    assert build_canvas.is_dev_url(f) is ok


def test_build_keeps_dev_url_file_and_reads_no_file(tmp_path):
    m = {"screens": [{"id": "word-header", "file": DEV + "/hd-stage/word-header.html", "title": "WordHeader", "group": "분자"},
                     {"id": "local", "file": "screens/local.html", "group": "분자"}]}
    (tmp_path / "screens").mkdir()
    (tmp_path / "screens" / "local.html").write_text('<a href="word-header.html">go</a>', encoding="utf-8")
    d = build_canvas.index_data(tmp_path, m)
    cards = {c["id"]: c for r in d["rows"] for c in r["screens"]}
    assert cards["word-header"]["file"] == DEV + "/hd-stage/word-header.html"
    assert "word-header" not in d["links"]                       # 주소 카드는 링크를 미리 뽑지 않는다
    assert d["links"]["local"] == [{"to": "word-header", "text": "go"}]   # 파일 카드는 지금 규칙 그대로


# ---------------------------------------------------------------- palette.js: __svelte_meta → src·comp
PALETTE_JS = r"""
const fs = require('fs'), vm = require('vm');
const noop = () => {};
const win = {addEventListener: noop, parent: null, CSS: null};
win.window = win; win.parent = win;
const ctx = Object.assign(win, {
  document: {addEventListener: noop, documentElement: {style: {}, appendChild: noop}, getElementById: () => null},
  location: {search: '', pathname: '/hd-stage/word-header.html', href: 'http://127.0.0.1:5199/hd-stage/word-header.html'},
  localStorage: {getItem: () => null}, URLSearchParams, NodeFilter: {}, console});
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx, {filename: 'palette.js'});
const el = (meta, parent) => ({nodeType: 1, __svelte_meta: meta, parentElement: parent || null});
const comp = {type: 'component', file: 'C:/Code/d/ui_host/popup/src/welcome/tutorial/replicas/PopupReplica.svelte', line: 499, parent: null};
const ifb = {type: 'if', file: 'C:/Code/d/ui_host/popup/src/lookup/SourceTabs.svelte', line: 272, parent: comp};
const owner = el({parent: ifb, loc: {file: 'C:/Code/d/ui_host/popup/src/lookup/SourceTabs.svelte', line: 273, column: 2}});
const plain = {nodeType: 1, parentElement: owner};          // 메타 없는 자식 → 가장 가까운 조상
const out = {};
out.noCfg = ctx.__hdSrcOf(plain);
ctx.__hdSrc = {root: 'C:\\Code\\d', base: 'ui_host/popup'};
out.abs = ctx.__hdSrcOf(plain);
out.rel = ctx.__hdSrcOf(el({parent: null, loc: {file: 'src/App.svelte', line: 3, column: 1}}));
out.outside = ctx.__hdSrcOf(el({parent: null, loc: {file: 'D:/other/X.svelte', line: 1, column: 0}}));
out.none = ctx.__hdSrcOf({nodeType: 1, parentElement: {nodeType: 1, parentElement: null}});
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def pal(tmp_path_factory):
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    t = tmp_path_factory.mktemp("hd-app-pal") / "pal.js"
    t.write_text(PALETTE_JS, encoding="utf-8")
    r = subprocess.run([NODE, str(t), str(CORE / "foundation" / "palette.js")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_palette_src_from_nearest_svelte_meta(pal):
    assert pal["noCfg"] == {"src": {"file": "C:/Code/d/ui_host/popup/src/lookup/SourceTabs.svelte", "line": 273, "column": 2},
                            "comp": ["SourceTabs", "PopupReplica"]}
    assert pal["abs"]["src"]["file"] == "ui_host/popup/src/lookup/SourceTabs.svelte"     # 저장소 기준(드라이브 대소문자·역슬래시 무시)
    assert pal["rel"]["src"] == {"file": "ui_host/popup/src/App.svelte", "line": 3, "column": 1}
    assert pal["outside"]["src"]["file"] == "D:/other/X.svelte"


def test_palette_no_meta_no_src(pal):
    assert pal["none"] is None                                   # 정적 화면: src·comp 칸 자체가 없다(withSrc 가 붙이지 않음)


# ---------------------------------------------------------------- dayfine.vite.mjs: 무대 주소 읽기 · public 파일
WRAP_JS = r"""
const {pathToFileURL} = require('url');
import(pathToFileURL(process.argv[2]).href).then((m) => {
  const urls = ['/hd-stage/word-header.html', '/hd-stage/settings-window--voice.html?v=3', '/hd-stage.html?id=usage-tab',
                '/hd-stage.html?id=settings-window&tab=basic?v=2', '/hd-stage/a--b--c.html', '/hd-stage/..%2Fx.html', '/twin.html', '/src/x.js'];
  const out = {parse: urls.map((u) => m.parseStage(u))};
  out.pub = ['/hd-stage/fonts/a.woff2', '/hd-stage/../package.json', '/hd-stage/fonts/../../package.json', '/hd-stage/x.html', '/hd-stage/missing.png']
    .map((p) => { const f = m.publicFile(process.argv[3], p); return f && f.replace(/\\/g, '/').split('/').slice(-3).join('/'); });
  console.log(JSON.stringify(out));
});
"""


def test_wrapper_stage_urls_and_public_files(tmp_path):
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    app = tmp_path / "app"
    (app / "public" / "fonts").mkdir(parents=True)
    (app / "public" / "fonts" / "a.woff2").write_bytes(b"x")
    (app / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "w.cjs").write_text(WRAP_JS, encoding="utf-8")
    r = subprocess.run([NODE, str(tmp_path / "w.cjs"), str(APP / "dayfine.vite.mjs"), str(app)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o["parse"] == [
        {"screen": "word-header", "id": "word-header", "tab": None},
        {"screen": "settings-window--voice", "id": "settings-window", "tab": "voice"},
        {"screen": "usage-tab", "id": "usage-tab", "tab": None},
        {"screen": "settings-window--basic", "id": "settings-window", "tab": "basic"},   # 캔버스가 붙인 ?v= 는 버림
        {"screen": "a--b--c", "id": None, "tab": None},
        {"screen": "../x", "id": None, "tab": None},
        None, None]
    assert o["pub"] == ["public/fonts/a.woff2", None, None, None, None]


# ---------------------------------------------------------------- dayfine.vite.mjs ENTRY: 앱 비공개 모듈이 깨져도 카드에 한 줄(#280)
# 가짜 앱 나무(src/twin/stages.js · src/settings/store.js · src/styles/theme.css + 가짜 svelte)를 node 모듈 훅으로 '/src/…'·'svelte' 에 잇고
# ENTRY 를 그대로 돌린다 — 개발 서버·브라우저 없음. 부모 창으로 간 postMessage 와 무대 뿌리 글을 본다.
ENTRY_RUN = r"""
const {registerHooks} = require('module'), {pathToFileURL} = require('url'), path = require('path'), fs = require('fs');
const [wrapper, fake, screen] = process.argv.slice(2);
registerHooks({
  resolve(spec, ctx, next) {
    if (spec.startsWith('/src/')) return {url: pathToFileURL(path.join(fake, spec)).href, shortCircuit: true};
    if (spec === 'svelte') return {url: pathToFileURL(path.join(fake, 'svelte.mjs')).href, shortCircuit: true};
    return next(spec, ctx);
  },
  load(url, ctx, next) {
    if (url.endsWith('.css')) { fs.statSync(new URL(url)); return {format: 'module', source: 'export default ""', shortCircuit: true}; }
    return next(url, ctx);
  },
});
const posts = [], root = {textContent: '', style: {}};
globalThis.window = globalThis;
globalThis.__hdStage = {screen, id: screen.split('--')[0], tab: screen.split('--')[1] || null};
globalThis.document = {getElementById: () => root, documentElement: {style: {setProperty() {}}}};
globalThis.parent = {postMessage: (m) => posts.push(m)};
console.error = () => {};
import(pathToFileURL(wrapper).href).then(async (m) => {
  const f = path.join(fake, 'entry.mjs');
  fs.writeFileSync(f, m.ENTRY);
  await import(pathToFileURL(f).href);
  await new Promise((r) => setTimeout(r, 50));
  console.log(JSON.stringify({posts, text: root.textContent, mounted: globalThis.__mounted || null, deps: m.ENTRY_DEPS}));
});
"""

GOOD_STAGES = "export const STAGES = {'word-header': {component: 'WH'}}; export const STAGE_FIXTURES = {}; export function stageProps(id) { return {id}; }\n"


def _fake_app(root, stages=GOOD_STAGES, store="export function applyConfigSnapshot() {}\n"):
    (root / "src" / "twin").mkdir(parents=True)
    (root / "src" / "settings").mkdir(parents=True)
    (root / "src" / "styles").mkdir(parents=True)
    (root / "src" / "styles" / "theme.css").write_text("", encoding="utf-8")
    (root / "svelte.mjs").write_text("export function mount(c, o) { globalThis.__mounted = {c, props: o.props}; }\n", encoding="utf-8")
    if stages is not None:
        (root / "src" / "twin" / "stages.js").write_text(stages, encoding="utf-8")
    if store is not None:
        (root / "src" / "settings" / "store.js").write_text(store, encoding="utf-8")
    return root


def _run_entry(tmp_path, fake, screen="word-header"):
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    run = tmp_path / "run.cjs"
    run.write_text(ENTRY_RUN, encoding="utf-8")
    r = subprocess.run([NODE, str(run), str(APP / "dayfine.vite.mjs"), str(fake), screen], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_entry_mounts_stage_from_fake_app(tmp_path):
    o = _run_entry(tmp_path, _fake_app(tmp_path / "app"))
    assert o["mounted"] == {"c": "WH", "props": {"id": "word-header"}}
    assert not [p for p in o["posts"] if p.get("error")], o["posts"]


def test_entry_failing_private_module_posts_one_readable_line(tmp_path):
    o = _run_entry(tmp_path, _fake_app(tmp_path / "app", stages="throw new Error('boom');\n"))
    errs = [p for p in o["posts"] if p.get("error")]
    assert len(errs) == 1 and errs[0]["type"] == "hd-here" and errs[0]["screen"] == "word-header", o["posts"]
    assert errs[0]["error"] == "/src/twin/stages.js: boom"
    assert "/src/twin/stages.js: boom" in o["text"] and o["mounted"] is None, "카드에도 같은 한 줄(빈 페이지가 아님)"


def test_entry_missing_module_and_missing_export_name_the_module(tmp_path):
    o = _run_entry(tmp_path, _fake_app(tmp_path / "a", store=None))
    errs = [p["error"] for p in o["posts"] if p.get("error")]
    assert len(errs) == 1 and errs[0].startswith("/src/settings/store.js: "), errs
    o = _run_entry(tmp_path, _fake_app(tmp_path / "b", store="export const other = 1;\n"))
    errs = [p["error"] for p in o["posts"] if p.get("error")]
    assert errs == ["/src/settings/store.js: applyConfigSnapshot 를 내보내지 않아요"], errs


def test_entry_unknown_stage_posts_error(tmp_path):
    o = _run_entry(tmp_path, _fake_app(tmp_path / "app"), screen="nope")
    errs = [p["error"] for p in o["posts"] if p.get("error")]
    assert len(errs) == 1 and "nope" in errs[0] and "word-header" in errs[0], errs


def test_entry_private_deps_are_listed_in_contract(tmp_path):
    o = _run_entry(tmp_path, _fake_app(tmp_path / "app"))
    doc = (CORE / "features" / "canvas" / "contract" / "app.md").read_text(encoding="utf-8")
    assert o["deps"] and all(d in doc for d in o["deps"]), "ENTRY 가 읽는 앱 비공개 모듈은 app 계약 '아직/의존' 에 적는다"
