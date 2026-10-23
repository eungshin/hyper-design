"""앱 프로젝트 테스트 표시 — 캔버스와 같은 이름: unit(I/O 없음, 수 초) · slow(개발 서버·브라우저가 드는 것).
고치는 동안: `pytest <이 폴더> -m unit` · 커밋 전: `pytest <이 폴더>`(slow 포함, dictionary 의 node_modules 가 없으면 건너뜀)."""


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: 순수 함수(python·node) — 늘 같이 돌린다")
    config.addinivalue_line("markers", "slow: vite 개발 서버 + 브라우저(Playwright) — 앱 저장소의 node_modules 가 있어야")
