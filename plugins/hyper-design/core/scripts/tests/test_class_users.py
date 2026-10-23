"""class_users.py(R9) — 바뀐 클래스를 쓰는 화면 찾기. 순수 함수 + 명령 한 번. 브라우저 없음."""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
sys.path.insert(0, str(SCRIPTS))
import class_users as CU  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def test_class_tokens_reads_only_class_attributes():
    html = '<main class="auth  wrap"><p class="row">.auth 와 class="divider" 는 글자일 뿐</p><img class="icon"/></main>'
    assert CU.class_tokens(html) == {"auth", "wrap", "row", "icon"}


def test_users_any_of_many_classes_in_order_and_text_ignored():
    pages = [("a", '<div class="row">x</div>'),
             ("b", '<p>auth 를 쓰는 화면이 아님 .auth</p>'),
             ("c", '<section class="block auth">y</section>'),
             ("d", '<div class="author">z</div>')]                          # 낱말 일부만 같음 → 아님
    assert CU.users(pages, ["auth", ".row"]) == ["a", "c"]
    assert CU.users(pages, ["divider"]) == []


def test_changed_classes_from_css_diff():
    old = "/* c */ .auth { display:flex; }\n.row{gap:4px}\n.btn, .btn--primary { color: red }\n"
    new = ".auth { display:flex; align-items:center }\n.row { gap: 4px }\n.btn, .btn--primary { color: red }\n.divider{height:1px}\n"
    assert CU.changed_classes(old, new) == {"auth", "divider"}                  # 공백만 다른 .row 는 그대로
    assert CU.changed_classes(old, old) == set()


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "class_users.py"), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", env=ENV)


def test_cli_skips_missing_files_with_warning(tmp_path):
    (tmp_path / "screens").mkdir()
    (tmp_path / "screens.json").write_text(json.dumps({"screens": [
        {"id": "login", "file": "screens/login.html"}, {"id": "login--done"}, {"id": "gone"}]}), encoding="utf-8")
    (tmp_path / "screens" / "login.html").write_text('<main class="auth"></main>', encoding="utf-8")
    (tmp_path / "screens" / "login--done.html").write_text('<main class="auth row"></main>', encoding="utf-8")
    r = run(tmp_path, "--classes", "auth", "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"classes": ["auth"], "screens": ["login", "login--done"], "missing": ["gone"]}
    assert "gone" in r.stderr
    old, new = tmp_path / "old.css", tmp_path / "new.css"
    old.write_text(".row{gap:4px}", encoding="utf-8")
    new.write_text(".row{gap:8px}", encoding="utf-8")
    r = run(tmp_path, "--css-old", old, "--css-new", new)
    assert r.returncode == 0 and r.stdout.split() == ["login--done"]
