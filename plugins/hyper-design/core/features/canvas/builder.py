"""Edge — Builder: 다시 빌드를 한 번에 하나(동기 apply 의 빌드 · 뒤 빌드 · 되돌린 뒤 빌드가 같은 index.html 을 쓴다) · hd-data · 부품 견본 목록.

상태: 빌드 자물쇠 하나 · 빌드 함수(run — 기본 작업 트리 build_canvas.py, CLI 도우미는 build_ref 를 넘긴다, #278).
부르는 곳: session.ProjectSession(Builder → History · Rebuilder · refresh) · router(/api/data · /api/parts).
오류 탐지: 빌드 결과(returncode · stderr)를 그대로 돌려준다 — 판단(되돌리기 · build.failed)은 부르는 쪽(write_record · rebuild).
"""
import json, threading

import board_data
from screen_edits import parts_of
from write_record import run_build


class Builder:
    """다시 빌드 · hd-data · 부품 목록 — out 하나. run(out) = 빌드 하나(기본 작업 트리, CLI 도우미는 build_ref — helper 가 넘긴다)."""

    def __init__(self, out, run=None):
        self.out, self._run, self.lock = out, run or run_build, threading.Lock()

    def run(self, out):                              # 빌드 하나씩(동기 apply 의 빌드 · 뒤 빌드 · 되돌린 뒤 빌드가 같은 index.html 을 쓴다)
        with self.lock:
            return self._run(out)

    def build(self):
        return self.run(self.out)

    def data(self):
        return board_data.index_data(self.out, json.loads((self.out / "screens.json").read_text(encoding="utf-8")))

    def parts(self):
        return parts_of(self.out)
