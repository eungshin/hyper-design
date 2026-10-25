"""View — 사람이 읽는 줄(터미널). 규칙과 글은 hd_model · hd_projects 의 format 함수 하나 — 여기는 SDK 값(Note·줄 객체)을 넘길 뿐."""
import hd_model as M
import hd_projects as P


def notes(ns):
    """Note 목록 → 줄(답은 들여 쓴 줄)."""
    return M.format_rows([n.as_dict() for n in ns])


def canvases(rows):
    return M.format_canvases(rows)


def projects(rows):
    return P.format_rows(rows)


def link(entry):
    return P.link_line(entry)
