"""파일에서 바뀐 상태를 제자리에서 받나, 판을 다시 불러오나(R57 B) — modules/state-file.js 의 LIVE·inPlace(node).

다른 AI 세션이 캔버스가 열린 동안 화면을 더하며 card-size 를 쓰면(10-31: 1분에 22번) 판이 매번 다시 불러와지고
'다른 곳에서 바뀌어 다시 불러왔어요' 토스트가 거듭 떴다. 이제 card-size 는 제자리에서(카드만 크기 바뀜) 받고,
셸이 따로 들고 있는 자리·폴더 등이 함께 바뀌었을 때만 다시 불러온다."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")
JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/state-file.js', 'utf8'), {filename: 'state-file.js'});
const S = globalThis.HD.stateFile;
console.log(JSON.stringify({live: Object.keys(S.LIVE).sort(), inPlace: [
  S.inPlace(['card-size']), S.inPlace(['notes', 'card-size', 'busy']), S.inPlace([]),
  S.inPlace(['card-size', 'card-pos']), S.inPlace(['folders']), S.inPlace(['zzz'])]}));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-state-live-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_card_size_from_elsewhere_is_taken_in_place(out):
    assert out["live"] == ["busy", "card-size", "note-seq", "notes"]
    assert out["inPlace"][:3] == [True, True, True], "card-size(메모·덮개와 함께여도) = 제자리"


def test_other_names_still_reload_the_board(out):
    assert out["inPlace"][3:] == [False, False, False], "자리·폴더·모르는 이름이 섞이면 다시 불러오기"
