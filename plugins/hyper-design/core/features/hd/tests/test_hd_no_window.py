"""창 없이 뜬 허브·도우미(pythonw)의 자식 프로세스는 콘솔 창을 띄우지 않는다 — hd_client 의 빌드·pid 보기·끄기, 세션의 다시 빌드·paseo. 브라우저 없음."""
import subprocess, sys
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HD), str(HD.parent / "canvas")]
import hd_client  # noqa: E402
import send_queue  # noqa: E402
import write_record  # noqa: E402

FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _fake(seen):
    def run(args, **kw):
        seen.append(kw.get("creationflags", 0))
        return subprocess.CompletedProcess(args, 0, "" if kw.get("text") or kw.get("encoding") else b"", "")
    return run


def test_hd_client_children_open_no_console_window(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(hd_client.subprocess, "run", _fake(seen))
    hd_client.build(tmp_path)
    if sys.platform == "win32":
        hd_client._image(4242)
    assert seen and all(f == FLAG for f in seen), seen


def test_session_children_open_no_console_window(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(write_record.subprocess, "run", _fake(seen))
    write_record.run_build(tmp_path)
    send_queue.forward(tmp_path, "메모", agent="a1", paseo="paseo.exe")
    send_queue.list_agents(paseo="paseo.exe")
    assert len(seen) == 3 and all(f == FLAG for f in seen), seen


# ---------------------------------------------------------------- 저장소 전체 지킴이(47-5a): 편집할 때 콘솔이 깜빡이던 일이 돌아오지 않게
SPAWN = {"run", "Popen", "call", "check_call", "check_output"}


def _spawn_calls_without_flags(path):
    """subprocess.run/Popen/… 부르기 중 creationflags 를 넘기지 않는 줄 번호. **kw 로 넘기면 같은 함수 안에 creationflags 를 정하는 글이 있어야 한다."""
    import ast
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    bad = []

    def visit(node, fn_src):
        for ch in ast.iter_child_nodes(node):
            sub = ast.get_source_segment(src, ch) if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn_src
            if isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute) and ch.func.attr in SPAWN \
                    and isinstance(ch.func.value, ast.Name) and ch.func.value.id == "subprocess":
                kws = [k.arg for k in ch.keywords]
                if "creationflags" not in kws and not (None in kws and "creationflags" in (fn_src or "")):
                    bad.append(ch.lineno)
            visit(ch, sub)
    visit(tree, None)
    return bad


def test_every_child_process_in_canvas_hd_home_passes_creationflags():
    features = HD.parent
    files = [p for d in ("canvas", "hd", "home") for p in (features / d).rglob("*.py")
             if "tests" not in p.relative_to(features).parts and "__pycache__" not in p.parts]
    assert len(files) > 20
    bad = ["%s:%d" % (p.relative_to(features).as_posix(), n) for p in files for n in _spawn_calls_without_flags(p)]
    assert not bad, "creationflags(NO_WINDOW) 없이 자식 프로세스를 띄우는 곳: %s" % bad


def test_the_guard_sees_a_missing_flag(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("import subprocess\ndef a():\n    subprocess.run(['x'])\ndef b():\n    kw = {}\n    subprocess.Popen(['x'], **kw)\n"
                 "def c():\n    kw = {'creationflags': 0}\n    subprocess.Popen(['x'], **kw)\ndef d():\n    subprocess.run(['x'], creationflags=0)\n", encoding="utf-8")
    assert _spawn_calls_without_flags(f) == [3, 6]
