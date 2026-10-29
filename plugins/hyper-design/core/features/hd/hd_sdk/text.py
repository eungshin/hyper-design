"""View — 사람이 읽는 줄(터미널). 규칙과 글은 hd_model · hd_projects 의 format 함수 하나 — 여기는 SDK 값(Note·줄 객체)을 넘길 뿐."""
import hd_model as M
import hd_projects as P


CARD_PAD = "    "


def notes(ns, cards=None):
    """Note 목록 → 줄(답은 들여 쓴 줄). cards = {화면 id: 정보 카드 글}(R47, hd_info_card.cards_for) — 그 화면의 첫 메모 아래 네 칸 들여 한 번.
    cards 가 없거나 비면 예전과 같은 글."""
    if not cards:
        return M.format_rows([n.as_dict() for n in ns])
    out, seen = [], set()
    for n in ns:
        out.append(M.format_rows([n.as_dict()]))
        t = cards.get(n.screen)
        if t and n.screen not in seen:
            seen.add(n.screen)
            out.append("\n".join(CARD_PAD + l for l in t.split("\n")))
    return "\n".join(out) if out else M.format_rows([])


def canvases(rows):
    return M.format_canvases(rows)


def projects(rows):
    return P.format_rows(rows)


def link(entry):
    return P.link_line(entry)
