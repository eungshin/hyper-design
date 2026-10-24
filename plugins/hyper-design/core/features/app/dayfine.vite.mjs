/* Dayfine 앱 카드용 Vite 감싸개 — 앱 저장소(ui_host/popup)를 한 줄도 고치지 않고 twin 무대 하나만 띄우는 페이지를 더한다.

   실행(앱 폴더에서, 또는 HD_APP_DIR=<앱 폴더>):
     node <앱>/node_modules/vite/bin/vite.js --mode twin --config <이 파일> --host 127.0.0.1 --port <빈 포트> --strictPort
   (= npx vite --mode twin --config <이 파일> --port <빈 포트>)

   - 앱의 vite.config.js 를 그대로 읽고 플러그인 하나(hd-stage, 개발 서버에서만)를 더한다. 빌드·평소 dev 는 이 파일을 거치지 않으므로 그대로다.
   - GET /hd-stage/<화면>.html — <화면> = <무대 id> 또는 <무대 id>--<설정 탭>(settings-window--basic). 무대 하나를 그 fixture 로 붙인다
     (src/twin/stages.js 의 STAGES·stageProps, 설정 스토어는 twin 페이지처럼 usage-tab 스냅샷). 탭은 window.__dictSettingsTab 로 건넨다.
     /hd-stage.html?id=<무대>&tab=<탭> 도 같은 페이지(캔버스 화면 id 는 경로 마지막 조각에서 읽으므로 카드는 앞의 모양을 쓴다).
   - 그 페이지에만 hyper-design foundation/palette.js 를 /@hd/palette.js 로 끼운다(고르기·hd-hit-at·hd-locate + 소스 위치).
     window.__hdSrc = {root: 저장소 뿌리, base: 저장소 안 앱 폴더} — palette.js 가 __svelte_meta.loc.file 을 저장소 기준 경로로 바꾸는 데 쓴다.
   - Vite 캐시(cacheDir)는 OS 임시 폴더로 — 앱 저장소 안에 아무 파일도 만들지 않는다.
   bare import 를 쓰지 않는다(이 파일은 hyper-design 쪽에 있어 vite·svelte 를 여기서 찾을 수 없다 — 앱 설정이 자기 자리에서 불러온다). */
import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';

const HERE = dirname(fileURLToPath(import.meta.url));
const PALETTE = resolve(HERE, '..', '..', 'foundation', 'palette.js');
const APP = resolve(process.env.HD_APP_DIR || process.cwd());
const ENTRY_URL = '/@hd/stage-entry.js';
const ENTRY_ID = '\0hd-stage-entry.js';
const SCREEN_RE = /^[a-z0-9][a-z0-9-]*$/i;

const slash = (p) => p.replace(/\\/g, '/');

function repoRoot(dir) {                                // .git 이 있는 가장 가까운 위 폴더(없으면 앱 폴더)
  for (let d = dir; ; d = dirname(d)) {
    if (existsSync(join(d, '.git'))) return d;
    if (dirname(d) === d) return dir;
  }
}

/* 요청 → {screen, id, tab} | null. 화면 = 무대[--탭]. 캔버스가 다시 실을 때 붙이는 ?v= 는 무시한다 */
export function parseStage(url) {
  const u = new URL(url, 'http://x');
  let screen = null;
  const m = u.pathname.match(/^\/hd-stage\/([^/]+)\.html$/);
  if (m) screen = decodeURIComponent(m[1]);
  else if (u.pathname === '/hd-stage.html') {
    const id = (u.searchParams.get('id') || '').split('?')[0], tab = (u.searchParams.get('tab') || '').split('?')[0];
    screen = id + (tab ? '--' + tab : '');
  }
  if (screen == null) return null;
  const [id, tab = '', ...rest] = screen.split('--');
  if (rest.length || !SCREEN_RE.test(id) || (tab && !SCREEN_RE.test(tab))) return {screen, id: null, tab: null};
  return {screen, id, tab: tab || null};
}

const MIME = {woff2: 'font/woff2', woff: 'font/woff', ttf: 'font/ttf', otf: 'font/otf', svg: 'image/svg+xml', png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp', gif: 'image/gif'};

/* /hd-stage/<상대 경로>(.html 아님) → 앱 public/ 안의 있는 파일 | null(밖으로 나가는 경로는 null) */
export function publicFile(app, path) {
  const m = /^\/hd-stage\/(.+)$/.exec(path || '');
  if (!m || /\.html$/i.test(m[1])) return null;
  let rel; try { rel = decodeURIComponent(m[1]); } catch { return null; }
  const pub = resolve(app, 'public'), f = resolve(pub, rel);
  const r = relative(pub, f);
  if (!r || r.startsWith('..') || isAbsolute(r)) return null;
  return existsSync(f) && statSync(f).isFile() ? f : null;
}

/* 무대 페이지가 읽는 앱의 비공개 모듈(app 계약 '아직/의존' 에 같은 목록) — 하나라도 못 읽으면 페이지에 한 줄 + 부모 창에 hd-here {error} (#280) */
export const ENTRY_DEPS = ['/src/styles/theme.css', '/src/twin/stages.js', '/src/settings/store.js'];

/* 무대 페이지 진입 모듈. import 는 하나씩 동적으로 — 실패하면 그 모듈 이름 + 메시지 한 줄(빈 페이지 대신).
   HMR: 개발 서버가 바꾼 뒤(vite:afterUpdate) 부모 창에 hd-here {hmr:true} — 캔버스가 그 카드의 "AI 수정 중" 칩을 걷는다(#272) */
export const ENTRY = `const q = window.__hdStage || {};
const root = document.getElementById('hd-stage-root');
function tell(m) {
  try { parent.postMessage(Object.assign({type: 'hd-here', screen: q.screen || ''}, m), '*'); } catch (e) { console.error('[hd] postMessage', e); }
}
function fail(msg) {
  root.textContent = '[hd] ' + msg;
  console.error('[hd] twin stage', msg);
  tell({error: msg});
}
function why(e) { return String((e && e.message) || e).split('\\n')[0]; }
async function need(name, load, keys) {
  let m;
  try { m = await load(); } catch (e) { throw Object.assign(new Error(name + ': ' + why(e)), {hd: true}); }
  for (const k of keys || []) if (m[k] == null) throw Object.assign(new Error(name + ': ' + k + ' 를 내보내지 않아요'), {hd: true});
  return m;
}
if (import.meta.hot) import.meta.hot.on('vite:afterUpdate', () => tell({hmr: true}));
try {
  await need('/src/styles/theme.css', () => import('/src/styles/theme.css'));
  const { mount } = await need('svelte', () => import('svelte'), ['mount']);
  const { STAGES, STAGE_FIXTURES, stageProps } = await need('/src/twin/stages.js', () => import('/src/twin/stages.js'), ['STAGES', 'stageProps']);
  const { applyConfigSnapshot } = await need('/src/settings/store.js', () => import('/src/settings/store.js'), ['applyConfigSnapshot']);
  const stage = q.id && STAGES[q.id];
  if (!stage) {
    fail('이 무대가 없어요: ' + (q.screen || '') + ' — 있는 무대: ' + Object.keys(STAGES).join(', '));
  } else {
    // twin 페이지(TwinApp.svelte)와 같게: 설정 스토어는 usage-tab 스냅샷으로 채운다
    const fx = STAGE_FIXTURES || {};
    applyConfigSnapshot(fx['usage-tab'] || fx[q.id] || {});
    if (q.tab) window.__dictSettingsTab = q.tab;
    document.documentElement.style.setProperty('--popup-font-size', '14px');
    root.style.cssText = 'background:var(--popup-bg);color:var(--popup-text);font-size:var(--popup-font-size);min-height:100vh;box-sizing:border-box;padding:16px';
    mount(stage.component, { target: root, props: stageProps(q.id) });
  }
} catch (e) {
  fail(e && e.hd ? e.message : '무대 ' + (q.id || '') + ': ' + why(e));
}
`;

function stageHtml(st, src) {
  const data = JSON.stringify({screen: st.screen, id: st.id, tab: st.tab}).replace(/</g, '\\u003c');
  const srcData = JSON.stringify(src).replace(/</g, '\\u003c');
  const title = String(st.screen).replace(/[<&]/g, '');
  return `<!doctype html>
<html lang="ko" class="theme-light">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${title} — hd stage</title>
    <script>window.__hdStage = ${data}; window.__hdSrc = ${srcData};</script>
    <script src="/@hd/palette.js"></script>
  </head>
  <body style="margin:0">
    <div id="hd-stage-root"></div>
    <script type="module" src="${ENTRY_URL}"></script>
  </body>
</html>
`;
}

export function hdStage(app = APP) {
  const root = repoRoot(app);
  const src = {root: slash(root), base: slash(relative(root, app))};
  return {
    name: 'hd-stage',
    apply: 'serve',                                     // 개발 서버에서만 — 빌드는 그대로
    resolveId(id) { return id === ENTRY_URL ? ENTRY_ID : null; },
    load(id) { return id === ENTRY_ID ? ENTRY : null; },
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        try {
          const path = (req.url || '').split('?')[0];
          if (path === '/@hd/palette.js') {               // 늘 지금 파일(palette.js 를 고치면 다시 실을 때 바로)
            res.setHeader('Content-Type', 'text/javascript; charset=utf-8');
            res.setHeader('Cache-Control', 'no-store');
            res.end(readFileSync(PALETTE, 'utf-8'));
            return;
          }
          const pub = publicFile(app, path);
          if (pub) {                                      // 무대 페이지의 상대 경로(fonts/… · flags/…) = 앱 public/ (twin 모드는 publicDir 이 꺼져 있다)
            res.setHeader('Content-Type', MIME[pub.split('.').pop().toLowerCase()] || 'application/octet-stream');
            res.end(readFileSync(pub));
            return;
          }
          const st = parseStage(req.url || '/');
          if (!st) return next();
          if (!st.id) {
            res.statusCode = 400; res.setHeader('Content-Type', 'text/plain; charset=utf-8');
            res.end(`[hd] 화면 이름이 틀렸어요: ${st.screen} (무대 또는 무대--탭)`);
            return;
          }
          const html = await server.transformIndexHtml(req.url, stageHtml(st, src), req.originalUrl);
          res.setHeader('Content-Type', 'text/html; charset=utf-8');
          res.setHeader('Cache-Control', 'no-store');
          res.end(html);
        } catch (e) {
          console.error('[hd] hd-stage', e);
          next(e);
        }
      });
    },
  };
}

export default async (env) => {
  const mod = await import(pathToFileURL(join(APP, 'vite.config.js')).href);
  const base = typeof mod.default === 'function' ? await mod.default(env) : mod.default;
  const hash = createHash('sha1').update(APP.toLowerCase()).digest('hex').slice(0, 10);
  return {
    ...base,
    root: base.root || APP,
    cacheDir: join(tmpdir(), 'hd-vite-' + hash),
    plugins: [...(base.plugins || []), hdStage(APP)],
  };
};
