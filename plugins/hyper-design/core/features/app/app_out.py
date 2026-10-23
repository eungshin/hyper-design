"""앱 프로젝트 out 폴더 만들기 — 앱 저장소의 twin 무대를 캔버스 카드로(카드 = 개발 서버의 무대 페이지 주소).

python3 app_out.py <app_dir> <out> --dev-url http://127.0.0.1:<port> [--build]

- 읽기만: <app_dir>/src/twin/registry.js(무대·이름·그룹·TWIN_LABELS) · <app_dir>/src/settings/SettingsApp.svelte(설정 탭 — 탭마다 카드 하나).
  앱 저장소에는 아무것도 쓰지 않는다.
- 쓰기: <out>/screens.json · <out>/app.json {kind:'app', repo, ui_dir, dev_cmd, dev_url, stages} · <out>/surface.json(카드·크게 보기 크기 — 이미 있으면 그대로).
- --build 면 이어서 canvas/build_canvas.py <out>. 그다음 `hd save --out <out>` / `hd open` 은 그대로 쓴다.
개발 서버는 이 스크립트가 띄우지 않는다 — app.json 의 dev_cmd(cwd = ui_dir)로 띄운다.
"""
import argparse, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import app_stages as M  # noqa: E402

WRAPPER = HERE / "dayfine.vite.mjs"
BUILD = HERE.parent / "canvas" / "build_canvas.py"


def repo_root(d):
    """.git 이 있는 가장 가까운 위 폴더(없으면 d)."""
    for p in [d, *d.parents]:
        if (p / ".git").exists():
            return p
    return d


def dev_cmd(ui_dir, port):
    """개발 서버 명령(문자열, cwd = ui_dir). npx 와 같고 앱의 node_modules 의 vite 를 바로 부른다."""
    vite = (ui_dir / "node_modules" / "vite" / "bin" / "vite.js").as_posix()
    return f'node "{vite}" --mode twin --config "{WRAPPER.as_posix()}" --host 127.0.0.1 --port {port} --strictPort'


def port_of(url):
    tail = url.rstrip("/").rsplit(":", 1)
    return tail[1] if len(tail) == 2 and tail[1].isdigit() else "5173"


def write_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="앱 twin 무대 → 캔버스 out 폴더")
    ap.add_argument("app_dir")
    ap.add_argument("out")
    ap.add_argument("--dev-url", required=True, help="개발 서버 주소 http://127.0.0.1:<port>")
    ap.add_argument("--build", action="store_true", help="이어서 build_canvas.py <out>")
    a = ap.parse_args(argv)
    ui = pathlib.Path(a.app_dir).resolve()
    out = pathlib.Path(a.out).resolve()
    if not M.is_dev_url(a.dev_url):
        sys.exit(f"[app_out] --dev-url 은 http://127.0.0.1:<port> 또는 http://localhost:<port> 여야 해요: {a.dev_url}")
    reg = ui / "src" / "twin" / "registry.js"
    if not reg.is_file():
        sys.exit(f"[app_out] 무대 목록이 없어요: {reg}")
    try:
        stages = M.parse_registry(reg.read_text(encoding="utf-8"))
    except M.AppParseError as e:
        sys.exit(f"[app_out] {reg}: {e}")
    sa = ui / "src" / "settings" / "SettingsApp.svelte"
    tabs = M.parse_settings_tabs(sa.read_text(encoding="utf-8")) if sa.is_file() else []
    if not tabs:
        print(f"[app_out] 설정 탭을 찾지 못했어요({sa}) — 설정 탭 카드 없이", file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    doc = M.screens_doc(stages, tabs, a.dev_url)
    write_json(out / "screens.json", doc)
    write_json(out / "app.json", M.app_doc(repo_root(ui).as_posix(), ui.as_posix(), a.dev_url, dev_cmd(ui, port_of(a.dev_url)), stages))
    if not (out / "surface.json").exists():
        write_json(out / "surface.json", M.SURFACE)
    print(f"app_out: {len(stages)} stages + {len(doc['screens']) - len(stages)} settings tabs → {out}")
    if a.build:
        r = subprocess.run([sys.executable, str(BUILD), str(out)], env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
