"""conftest SURFACES — 화면 동작마다 적은 테스트 파일이 실제로 있다(이름이 바뀌면 --surface 가 조용히 덜 고른다)."""
from pathlib import Path

from conftest import SURFACES

HERE = Path(__file__).resolve().parent


def test_every_surface_file_exists():
    missing = [f"{name}: {f}" for name, (_, files) in SURFACES.items() for f in files if not (HERE / f).is_file()]
    assert not missing, missing
