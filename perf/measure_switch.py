#!/usr/bin/env python3
"""보드(프로젝트 탭) 바꾸기 속도 재기 — 한 명령으로 임시 환경을 만들고 재고 다 치운다.

python perf/measure_switch.py [--cases normal,data,code,first|all] [--runs N] [--ref HEAD] [--json PATH]
                              [--src-runs DIR] [--port N] [--channel chrome] [--headless]

  normal = 두 번 오간 뒤(데움) 탭 누르기 N번 · data = 갈 쪽 화면 파일을 매번 고친 뒤 누르기
  code   = 두 번에 한 번 임시 worktree 안에서 버리는 커밋(view-tabs.js 한 줄) 뒤 누르기 · first = 허브를 매번 새로 띄워 첫 열기
  표 = 경우 · 지표(클릭→카드 보임 등) · n · 최소/중앙/최대 ms. 줄마다 결과는 JSON(기본 <임시 폴더>/hd-measure-switch-<시각>.json)

하는 일: 저장소(이 파일이 든 git)의 <ref> 로 임시 detached worktree → <src-runs>/dayfine-onboarding-v1·laundry-v1 를 임시로 복사
→ 임시 HD_HOME·HD_BUILD_REF_CACHE → `hd save` 로 두 프로젝트(dayfine·laundry) 링크 → `hd home --no-browser` 허브 → Playwright(Chrome)로 잼
→ 끝나면(실패·Ctrl+C 도) 허브·도우미 프로세스, worktree(`git worktree remove --force` + prune), 임시 폴더를 지운다.
저장소 작업 트리·runs 원본에는 쓰지 않는다. code 경우의 커밋은 임시 worktree 의 detached HEAD 에만 남고 worktree 와 함께 버려진다.
Playwright 가 없으면 한 줄 안내 후 끝(종료 코드 2). 순수 부분(parse_args·summarize·format_table)은
plugins/hyper-design/core/features/canvas/tests/test_canvas_unit_measure_switch.py(unit).
바탕: 2026-10-31 보드 전환 S1-S3 뒤 측정에 쓴 임시 스크립트(measure2/measure.py).
"""
import argparse, json, os, pathlib, shutil, socket, statistics, subprocess, sys, tempfile, time, urllib.request

CASES = ("normal", "data", "code", "first")
PROJECTS = {"dayfine": "dayfine-onboarding-v1", "laundry": "laundry-v1"}   # 탭 이름 → runs/ 아래 폴더
HD_REL = "plugins/hyper-design/core/features/hd/hd.py"
CODE_REL = "plugins/hyper-design/core/features/canvas/modules/view-tabs.js"   # code 경우에 한 줄 덧붙일 셸 파일

# (지표, 표 이름) — 앞 줄이 사용자가 기다린 시간
METRICS = {
    "switch": (("click_cards", "클릭→카드 보임"), ("click_nav", "클릭→새 페이지 시작"), ("api_open", "/api/open"),
               ("ttfb", "페이지 첫 바이트"), ("fcp", "첫 그림"), ("frames_done", "카드 iframe 다 뜸")),
    "first": (("goto_cards", "열기→카드 보임"), ("api_open", "/api/open(빌드 포함)"), ("goto_nav", "열기→페이지 시작"),
              ("ttfb", "페이지 첫 바이트"), ("fcp", "첫 그림"), ("frames_done", "카드 iframe 다 뜸")),
}


# ---- 순수 부분 -------------------------------------------------------------------------------------------

def _cases(s):
    if s.strip() == "all":
        return list(CASES)
    out = []
    for x in (p.strip() for p in s.split(",")):
        if x and x not in out:
            out.append(x)
    bad = [x for x in out if x not in CASES]
    if not out or bad:
        raise argparse.ArgumentTypeError("경우는 %s 또는 all (받은 것: %r)" % (",".join(CASES), s))
    return out


def _runs(s):
    try:
        n = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError("횟수는 1 이상 정수 (받은 것: %r)" % s)
    if n < 1:
        raise argparse.ArgumentTypeError("횟수는 1 이상 정수 (받은 것: %r)" % s)
    return n


def parse_args(argv):
    p = argparse.ArgumentParser(prog="measure_switch.py", description="보드(프로젝트 탭) 바꾸기 속도 재기 — 임시 worktree·허브에서")
    p.add_argument("--cases", type=_cases, default=["normal"], help="쉼표로 normal,data,code,first 또는 all (기본 normal)")
    p.add_argument("--runs", type=_runs, default=3, help="경우마다 잴 횟수(기본 3)")
    p.add_argument("--ref", default="HEAD", help="잴 코드의 git ref(기본 HEAD)")
    p.add_argument("--json", default=None, help="결과 JSON 경로(기본 <임시 폴더>/hd-measure-switch-<시각>.json)")
    p.add_argument("--src-runs", default=None, help="dayfine-onboarding-v1·laundry-v1 가 든 폴더(기본 <저장소>/runs) — 읽기만")
    p.add_argument("--port", type=int, default=0, help="허브 포트(기본 0 = 빈 포트)")
    p.add_argument("--channel", default="chrome", help="Playwright 브라우저 채널(기본 chrome, '' = 내장 chromium)")
    p.add_argument("--headless", action="store_true", help="창 없이(기본은 10-31 측정처럼 창을 띄움)")
    return p.parse_args(argv)


def summarize(results):
    """{경우: [줄 dict]} → [{case, metric, label, n, min, med, max}] — 값이 없는(None) 줄은 빼고 센다."""
    rows = []
    for case, items in results.items():
        mine = []
        for key, label in METRICS["first" if case == "first" else "switch"]:
            v = [r[key] for r in items if isinstance(r.get(key), (int, float))]
            if v:
                mine.append({"case": case, "metric": key, "label": label, "n": len(v),
                             "min": min(v), "med": round(statistics.median(v)), "max": max(v)})
        rows.extend(mine or [{"case": case, "metric": None, "label": "결과 없음", "n": 0, "min": None, "med": None, "max": None}])
    return rows


def _w(s):                                            # 한글·한자는 두 칸(→ 같은 기호는 한 칸)
    wide = lambda o: 0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFF60
    return sum(2 if wide(ord(c)) else 1 for c in s)


def format_table(rows):
    head = ("경우", "지표", "n", "최소", "중앙", "최대")
    body = [(r["case"], r["label"]) + tuple("-" if r[k] is None else str(r[k]) for k in ("n", "min", "med", "max")) for r in rows]
    ws = [max(_w(x[i]) for x in [head] + body) for i in range(len(head))]
    line = lambda xs: "  ".join((x + " " * (ws[i] - _w(x))) if i < 2 else (" " * (ws[i] - _w(x)) + x) for i, x in enumerate(xs)).rstrip()
    out = [line(head), "  ".join("-" * w for w in ws)] + [line(x) for x in body]
    return "\n".join(out + ["(ms)"])


# ---- 브라우저 쪽(10-31 측정 그대로) ------------------------------------------------------------------------

INIT = r"""
(() => {
  const E = () => performance.timeOrigin + performance.now();
  const R = window.__m = {lt: [], frames: 0, lastFrame: 0, cards: 0, fcp: 0};
  try { new PerformanceObserver(l => l.getEntries().forEach(e => R.lt.push([e.startTime, e.duration]))).observe({type: 'longtask', buffered: true}); } catch (e) {}
  try { new PerformanceObserver(l => l.getEntries().forEach(e => { if (e.name === 'first-contentful-paint') R.fcp = e.startTime; })).observe({type: 'paint', buffered: true}); } catch (e) {}
  document.addEventListener('load', ev => { const t = ev.target; if (t && t.tagName === 'IFRAME' && t.closest && t.closest('.card')) { R.frames++; R.lastFrame = performance.now(); } }, true);
  const poll = () => {
    if (!R.cards) {
      const c = [...document.querySelectorAll('.card')].find(c => { const r = c.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth; });
      if (c) R.cards = performance.now();
    }
    if (!R.cards) requestAnimationFrame(poll);
  };
  requestAnimationFrame(poll);
  const of = window.fetch;
  window.fetch = function (u, o) {
    const s = String(u && u.url || u);
    if (s.indexOf('/api/open') < 0) return of.apply(this, arguments);
    const t0 = E();
    return of.apply(this, arguments).then(r => { sessionStorage.setItem('m_open', JSON.stringify([t0, E()])); return r; });
  };
})();
"""


def settle(page, timeout=40):
    t = time.time()
    while time.time() - t < timeout:
        m = page.evaluate("window.__m && {cards: __m.cards, frames: __m.frames, last: __m.lastFrame, now: performance.now()}")
        if m and m["cards"] and m["now"] - max(m["last"], m["cards"]) > 2500:
            break
        time.sleep(0.25)
    return page.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0];
      const m = __m; const lt = m.lt.filter(x => x[0] < (m.lastFrame || m.cards) + 500);
      return {origin: performance.timeOrigin, ttfb: n.responseStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd, fcp: m.fcp,
              cards: m.cards, frames: m.frames, lastFrame: m.lastFrame, ltN: lt.length, ltSum: Math.round(lt.reduce((a, x) => a + x[1], 0)),
              ltMax: Math.round(lt.reduce((a, x) => Math.max(a, x[1]), 0)), open: sessionStorage.getItem('m_open')}; }""")


def _page_row(r):
    return {"ttfb": round(r["ttfb"]), "fcp": round(r["fcp"]), "cards": round(r["cards"]),
            "frames_done": round(r["lastFrame"]) if r["lastFrame"] else None, "frames": r["frames"],
            "lt": "%d/%d/%d" % (r["ltN"], r["ltSum"], r["ltMax"])}


def click_switch(page, name):
    page.evaluate("sessionStorage.removeItem('m_open')")
    sel = '#ptabs .pt-tab[data-name="%s"]' % name
    page.wait_for_selector(sel, timeout=20000)
    with page.expect_navigation(timeout=120000):
        click = page.evaluate("(s) => { const t = performance.timeOrigin + performance.now(); document.querySelector(s).click(); return t; }", sel)
    r = settle(page)
    o = json.loads(r["open"]) if r["open"] else None
    row = {"to": name, "click_nav": round(r["origin"] - click), "api_open": round(o[1] - o[0]) if o else None}
    row.update(_page_row(r))
    row["click_cards"] = round(r["origin"] + r["cards"] - click)
    return row


def goto_measure(page, url):
    t = time.time() * 1000
    page.goto(url, wait_until="commit", timeout=120000)
    r = settle(page)
    row = {"goto_nav": round(r["origin"] - t)}
    row.update(_page_row(r))
    row["goto_cards"] = round(r["origin"] + r["cards"] - t)
    return row


# ---- 임시 환경 ---------------------------------------------------------------------------------------------

def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True, encoding="utf-8", check=check)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _kill_tree(pid):
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _rmtree(p):
    for _ in range(10):                               # Windows: 막 죽인 프로세스가 파일을 잠깐 쥐고 있다
        if not p.exists():
            return True
        shutil.rmtree(p, ignore_errors=True)
        time.sleep(0.5)
    return not p.exists()


class Env:
    """임시 worktree · runs 사본 · HD_HOME · 허브. close() 는 몇 번 불러도 되고, 무엇이 남았는지 줄로 돌려준다."""

    def __init__(self, repo, ref, src_runs, port):
        self.repo, self.ref = repo, ref
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-measure-"))
        self.wt = self.tmp / "wt"
        self.hdhome = self.tmp / "hdhome"
        self.port = port or _free_port()
        self.hub = None
        self.wt_added = False
        _git(repo, "worktree", "add", "--detach", str(self.wt), ref)
        self.wt_added = True
        self.sha = _git(self.wt, "rev-parse", "--short", "HEAD").stdout.strip()
        self.outs = {}
        for name, folder in PROJECTS.items():
            src = src_runs / folder
            if not (src / "out").is_dir():
                raise RuntimeError("측정할 프로젝트가 없어요: %s/out" % src)
            shutil.copytree(src, self.tmp / "runs" / folder)
            self.outs[name] = self.tmp / "runs" / folder / "out"
        self.env = dict(os.environ, HD_HOME=str(self.hdhome), HD_BUILD_REF_CACHE=str(self.tmp / "refcache"),
                        PYTHONIOENCODING="utf-8", HD_HUB_PORT=str(self.port))
        self.env.pop("HD_CODE_STAMP", None)
        for name, out in self.outs.items():
            r = subprocess.run([sys.executable, str(self.wt / HD_REL), "save", "--name", name, "--out", str(out)],
                               env=self.env, capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                raise RuntimeError("hd save %s 실패: %s" % (name, (r.stderr or r.stdout).strip()[-300:]))

    # 허브
    def _rec(self):
        p = self.hdhome / "home.json"
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def start_hub(self):
        log = open(self.tmp / "hub.log", "a", encoding="utf-8")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        t0 = time.time()
        self.hub = subprocess.Popen([sys.executable, str(self.wt / HD_REL), "home", "--no-browser", "--port", str(self.port)],
                                    env=self.env, stdout=log, stderr=log, creationflags=flags)
        log.close()
        for _ in range(600):
            r = self._rec()
            if r and r.get("pid") == self.hub.pid:
                print("허브 %.2fs pid %s port %s" % (time.time() - t0, self.hub.pid, self.port), flush=True)
                return r
            if self.hub.poll() is not None:
                break
            time.sleep(0.05)
        raise RuntimeError("허브가 뜨지 않았어요 — %s" % (self.tmp / "hub.log"))

    def stop_hub(self):
        p, self.hub = self.hub, None
        if p is None:
            return
        r = self._rec()
        if r and p.poll() is None:
            try:
                req = urllib.request.Request("http://127.0.0.1:%d/api/hub/stop" % self.port, data=b"{}", method="POST",
                                             headers={"X-HD-Token": r["token"], "Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5).read()
            except Exception as e:  # noqa: BLE001 — 아래에서 강제 종료
                print("허브 끄기 요청 실패(강제 종료): %s" % e, flush=True)
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            _kill_tree(p.pid)
        self._kill_helpers()

    def _kill_helpers(self):                          # 허브가 띄운 프로젝트 도우미 중 남은 것(표지 = HD_HOME/active/<pid>.json)
        for f in (self.hdhome / "active").glob("*.json") if (self.hdhome / "active").is_dir() else ():
            try:
                pid = int(json.loads(f.read_text(encoding="utf-8")).get("pid") or f.stem)
            except (OSError, ValueError):
                continue
            _kill_tree(pid)

    def api_open(self, rec, name):
        t = time.time()
        req = urllib.request.Request("http://127.0.0.1:%d/api/open" % self.port, data=json.dumps({"name": name}).encode(), method="POST",
                                     headers={"X-HD-Token": rec["token"], "Content-Type": "application/json"})
        b = json.loads(urllib.request.urlopen(req, timeout=120).read())
        return b, (time.time() - t) * 1000

    # 경우별 바꾸기
    def touch_screen(self, name, n):
        out = self.outs[name]
        scr = json.loads((out / "screens.json").read_text(encoding="utf-8"))
        items = scr if isinstance(scr, list) else scr.get("screens", [])
        f = next((out / it["file"] for it in items if isinstance(it, dict) and it.get("file") and (out / it["file"]).is_file()), None)
        if f is None:
            f = sorted((out / "screens").glob("*.html"))[0]
        with open(f, "a", encoding="utf-8") as h:
            h.write("\n<!-- measure %d %f -->\n" % (n, time.time()))
        return f.name

    def code_commit(self, n):
        with open(self.wt / CODE_REL, "a", encoding="utf-8") as h:
            h.write("\n// measure %d\n" % n)
        _git(self.wt, "-c", "user.name=hd-measure", "-c", "user.email=hd-measure@localhost", "-c", "commit.gpgsign=false",
             "commit", "-q", "--no-verify", "-am", "measure throwaway %d" % n)
        return _git(self.wt, "rev-parse", "--short", "HEAD").stdout.strip()

    def close(self):
        left = []
        try:
            self.stop_hub()
        except Exception as e:  # noqa: BLE001
            left.append("허브: %s" % e)
        if self.wt_added:
            r = _git(self.repo, "worktree", "remove", "--force", str(self.wt), check=False)
            if r.returncode:
                left.append("worktree remove: %s" % r.stderr.strip())
            self.wt_added = False
        _rmtree(self.wt)
        _git(self.repo, "worktree", "prune", check=False)
        if not _rmtree(self.tmp):
            left.append("임시 폴더: %s" % self.tmp)
        return left


def _browser(p, a, env):
    kw = {"channel": a.channel} if a.channel else {}
    ctx = p.chromium.launch_persistent_context(str(env.tmp / ("profile-%d" % int(time.time() * 1000))), headless=a.headless,
                                               viewport={"width": 1440, "height": 1000}, args=["--window-size=1460,1100"], **kw)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(INIT)
    return ctx, page


def run_first(p, a, env):
    res = []
    for i in range(a.runs):
        rec = env.start_hub()
        ctx = None
        try:
            name = ["dayfine", "laundry"][i % 2]
            ctx, page = _browser(p, a, env)
            b, ms = env.api_open(rec, name)
            row = {"to": name, "api_open": round(ms), "reused": b.get("reused")}
            row.update(goto_measure(page, b["url"]))
            print(json.dumps(row, ensure_ascii=False), flush=True)
            res.append(row)
        finally:
            if ctx:
                ctx.close()
            env.stop_hub()
    return res


def run_switch(p, a, env, case):
    res = []
    rec = env.start_hub()
    ctx = None
    try:
        ctx, page = _browser(p, a, env)
        b1, _ = env.api_open(rec, "dayfine")
        env.api_open(rec, "laundry")
        page.goto(b1["url"], wait_until="commit", timeout=120000)   # load 는 카드 iframe·바깥 글꼴을 기다려 늦다 — 카드가 보이면 settle 이 잡는다
        settle(page)
        for tgt in ("laundry", "dayfine"):            # 데움: 두 쪽 한 번씩
            click_switch(page, tgt)
        cur = "dayfine"
        for i in range(a.runs):
            tgt = "laundry" if cur == "dayfine" else "dayfine"
            extra = {}
            if case == "data":
                extra["edited"] = env.touch_screen(tgt, i)
            elif case == "code" and i % 2 == 0:
                extra["commit"] = env.code_commit(i)
                time.sleep(2.5)                      # 코드 도장 기억(2초)을 넘기게
            row = click_switch(page, tgt)
            row.update(extra)
            cur = tgt
            print(json.dumps(row, ensure_ascii=False), flush=True)
            res.append(row)
            time.sleep(1)
    finally:
        if ctx:
            ctx.close()
        env.stop_hub()
    return res


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)
    for f in (sys.stdout, sys.stderr):              # Windows 콘솔(cp949)에서도 표·한글이 깨지지 않게
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8", errors="replace")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright 가 없어요 — `pip install playwright` 뒤 다시 실행하세요(Chrome 이 없으면 --channel '' + `playwright install chromium`).")
        return 2
    here = pathlib.Path(__file__).resolve().parent
    r = _git(here, "rev-parse", "--show-toplevel", check=False)
    if r.returncode:
        print("git 저장소를 못 찾았어요: %s" % r.stderr.strip())
        return 2
    repo = pathlib.Path(r.stdout.strip())
    src_runs = pathlib.Path(a.src_runs) if a.src_runs else repo / "runs"
    out_json = pathlib.Path(a.json) if a.json else pathlib.Path(tempfile.gettempdir()) / ("hd-measure-switch-%s.json" % time.strftime("%Y%m%d-%H%M%S"))
    results, errors, env = {}, {}, None
    try:
        env = Env(repo, a.ref, src_runs, a.port)
        print("잴 코드 %s(%s) · 임시 %s" % (a.ref, env.sha, env.tmp), flush=True)
        with sync_playwright() as p:
            for case in a.cases:
                print("== %s × %d" % (case, a.runs), flush=True)
                try:
                    results[case] = run_first(p, a, env) if case == "first" else run_switch(p, a, env, case)
                except Exception as e:  # noqa: BLE001 — 한 경우가 깨져도 다음 경우·정리는 한다
                    errors[case] = "%s: %s" % (type(e).__name__, e)
                    results.setdefault(case, [])
                    print("[%s 실패] %s" % (case, errors[case]), flush=True)
    except subprocess.CalledProcessError as e:
        errors["setup"] = "%s → %s" % (" ".join(e.cmd), (e.stderr or "").strip())
    except Exception as e:  # noqa: BLE001
        errors["setup"] = "%s: %s" % (type(e).__name__, e)
    finally:
        left = env.close() if env else []
    rows = summarize(results)
    out_json.write_text(json.dumps({"ref": a.ref, "commit": env.sha if env else None, "runs": a.runs, "cases": results,
                                    "summary": rows, "errors": errors, "left": left}, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(format_table(rows))
    for k, v in errors.items():
        print("[실패] %s — %s" % (k, v))
    for x in left:
        print("[남음] %s" % x)
    print("JSON: %s" % out_json)
    return 1 if errors or left else 0


if __name__ == "__main__":
    sys.exit(main())
