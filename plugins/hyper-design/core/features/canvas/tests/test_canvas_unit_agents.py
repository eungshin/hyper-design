"""보낼 곳 고르기(#214) Model — modules/agents.js 순수 함수 단위 테스트(node). 브라우저 없음.

rank: 이 저장소(cwd = repo 또는 그 아래) 먼저 → running < idle < 그 밖 → 이름. suggest: 저장소 안 running 이 정확히 하나일 때만.
rows: 닫힌·모양 틀린 줄 빼기, 지금 보낼 곳 표시, 이름 40자, 폴더 이름, error 그대로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/agents.js', 'utf8'), {filename: 'agents.js'});
const A = globalThis.HD.agents, out = {};
const repo = 'C:\\Code\\proj';
const list = [
  {id: 'o1', name: '다른 저장소 실행', status: 'running', cwd: 'C:\\Code\\other'},
  {id: 'i1', name: 'b 쉬는 중', status: 'idle', cwd: 'c:/code/proj/'},
  {id: 'r1', name: '하나 실행', status: 'running', cwd: 'C:\\Code\\proj\\sub'},
  {id: 'i0', name: 'a 쉬는 중', status: 'idle', cwd: 'C:\\Code\\proj'},
  {id: 'x1', name: 'proj2 아님', status: 'running', cwd: 'C:\\Code\\proj2'},
];
out.rank = A.rank(list, repo).map(a => a.id);
out.one = (A.suggest(list, repo) || {}).id || null;
out.two = A.suggest(list.concat([{id: 'r2', status: 'running', cwd: 'C:/Code/proj'}]), repo);
out.none = A.suggest(list, 'D:\\elsewhere');
out.noRepo = A.suggest(list, null);
out.idleOnly = A.suggest([{id: 'i', status: 'idle', cwd: repo}], repo);
const long = 'ㄱ'.repeat(60);
const r = A.rows({agents: [{id: 'c', name: '닫힘', status: 'closed', cwd: repo}, {id: 'r1', name: long, status: 'running', cwd: repo + '\\'},
                           {name: 'id 없음'}, 'junk', {id: 'n', status: 'idle', cwd: '/home/me/app'}], current: 'r1', repo: repo});
out.rows = r;
out.err = A.rows({agents: [], error: 'Paseo 를 찾을 수 없어요'});
out.bodyNull = A.rows(null);
out.labelLen = A.label({id: 'z', name: long}).length;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-agents-js-"))
    try:
        (tmp / "a.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "a.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rank_repo_first_then_running_then_name(out):
    assert out["rank"] == ["r1", "i0", "i1", "x1", "o1"], "저장소 안(아래 폴더 포함, 대소문자·역슬래시 무시) 먼저 · running 먼저 · 이름 · proj2 는 proj 가 아님"


def test_suggest_only_single_running_in_repo(out):
    assert out["one"] == "r1", "저장소 안 running 하나 → 그것"
    assert out["two"] is None, "둘이면 고르지 않는다"
    assert out["none"] is None and out["noRepo"] is None, "저장소 안에 없으면(또는 저장소 모름) 없음"
    assert out["idleOnly"] is None, "쉬는 것만 있으면 없음"


def test_rows_drop_closed_and_bad_mark_current(out):
    r = out["rows"]
    assert [x["id"] for x in r["rows"]] == ["r1", "n"], "닫힌 것·모양 틀린 줄은 빠지고 저장소 안 먼저"
    assert r["bad"] == 2, "틀린 줄 수(View 가 [hd] 경고)"
    top = r["rows"][0]
    assert top["current"] and top["mine"] and top["folder"] == "proj" and len(top["label"]) == 40 and top["label"].endswith("…")
    assert r["rows"][1]["folder"] == "app" and r["rows"][1]["name"] == "n", "이름이 없으면 id"
    assert r["current"] == "r1" and r["error"] is None
    assert out["err"]["error"] == "Paseo 를 찾을 수 없어요" and out["err"]["rows"] == []
    assert out["bodyNull"]["rows"] == [] and out["bodyNull"]["current"] is None
    assert out["labelLen"] == 40
