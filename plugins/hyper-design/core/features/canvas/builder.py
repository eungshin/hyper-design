"""Edge — Builder: 쓰기 확인(check — 데이터만, 프로세스 안) · 페이지 빌드 한 번에 하나(run — index.html 전체) · hd-data · 부품 견본 목록.

쓰기(figma-lite 5): 화면 파일을 쓴 뒤 데이터만 다시 뽑아(verify = board_data.index_data — 화면이 아직 읽히나) 확인하고 index.html 은 굽지 않는다.
확인이 깨지면 부르는 쪽이 되돌린다(write_record · rebuild 그대로). 전체 페이지는 줄 때 데이터 도장이 다르면 그때(session.refresh_data).
상태: 페이지 빌드 자물쇠 하나 · 페이지 빌드 함수(_run — 기본 작업 트리 build_canvas.py, CLI 도우미는 build_ref, #278) · 쓰기 확인 함수(_check — 기본 verify, 테스트가 바꿔 끼움).
부르는 곳: session.ProjectSession(check → History · Rebuilder · run → refresh · refresh_data) · router(/api/data · /api/parts).
오류 탐지: 확인·빌드 결과(returncode · stderr)를 그대로 돌려준다 — 판단(되돌리기 · build.failed)은 부르는 쪽(write_record · rebuild).
"""
import json, subprocess, threading, traceback

import board_data
from screen_edits import parts_of
from write_record import run_build


def verify(out):
    """쓰기 확인 — 지금 out 파일로 캔버스 데이터가 만들어지나(screens.json 이 읽히고 index_data 가 깨지지 않나). → CompletedProcess(0 | 1, stderr = 까닭).
    쓰기가 바꾸는 파일(screens.json · 화면 파일)에 달린 빌드 실패는 모두 여기서 난다 — 템플릿·모듈·foundation 은 쓰기가 바꾸지 않는다."""
    try:
        board_data.index_data(out, json.loads((out / "screens.json").read_text(encoding="utf-8")))
    except Exception:                                    # noqa: BLE001 — 어떤 실패든 '쓰기가 캔버스를 깨뜨림'(부르는 쪽이 되돌린다)
        return subprocess.CompletedProcess([], 1, "", traceback.format_exc(limit=4))
    return subprocess.CompletedProcess([], 0, "", "")


class Builder:
    """쓰기 확인 · 페이지 빌드 · hd-data · 부품 목록 — out 하나. run(out) = 페이지 빌드 하나(기본 작업 트리, CLI 도우미는 build_ref — helper 가 넘긴다)."""

    def __init__(self, out, run=None, check=None):
        self.out, self._run, self._check, self.lock = out, run or run_build, check or verify, threading.Lock()

    def run(self, out):                              # 페이지 빌드 하나씩(코드 도장 · 데이터 도장 다시 빌드가 같은 index.html 을 쓴다)
        with self.lock:
            return self._run(out)

    def check(self, out):                            # 쓰기 확인(데이터만 — 자물쇠 없음, 쓰기는 세션 자물쇠 · Rebuilder 가 하나씩)
        return self._check(out)

    def build(self):
        return self.run(self.out)

    def data(self):
        return board_data.index_data(self.out, json.loads((self.out / "screens.json").read_text(encoding="utf-8")))

    def parts(self):
        return parts_of(self.out)
