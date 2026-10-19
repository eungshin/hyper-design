"""캔버스 테스트 영역 표시(marker) — 고친 곳에 맞는 테스트만 골라 돌리려고(contract.md '테스트 층').

test_canvas_modules.py 는 통째로 unit(node, 약 1초). 브라우저 테스트는 아래 표에서 영역을 받는다.
표에 없는 브라우저 테스트가 생기면 수집 단계에서 실패한다 — 새 테스트는 여기에 한 줄을 더한다.
"""
import pytest

AREAS = {
    "input": "이동·확대·끌기·클릭·단축키(판 조작)",
    "modal": "크게 보기·주석 달기(P)",
    "notes": "메모 패널·저장·보내기",
    "tools": "도구 막대·카드 옮기기·우클릭 메뉴·숨기기·되돌리기",
    "flow": "주요 흐름 화살표(회색 점선)",
    "links": "연결 보기(Shift+클릭): 길·태그·색·범례·태그 이름",
    "motion": "카메라·전환 메뉴·움직임 끄기",
    "helper": "로컬 도우미(helper.py): 바로 반영·out 안만·원본 남김·토큰·대기열",
}

BROWSER = {
    # test_canvas_baseline.py — 0단계 고정
    "test_wheel_pans_ctrl_wheel_zooms": ("input",),
    "test_left_drag_pans_even_from_a_card": ("input", "modal"),
    "test_right_button_menu_middle_pans": ("input",),
    "test_click_opens_modal_and_esc_order": ("input", "modal", "links"),
    "test_p_picks_only_inside_modal": ("modal",),
    "test_typing_guard_blocks_shortcuts": ("input",),
    "test_notes_roundtrip_same_key": ("notes",),
    # test_canvas_edit.py — 편집 기능
    "test_notes_dropdown_scrolls_and_collapses": ("notes",),
    "test_toolbar_default_hand_and_keys": ("tools", "input"),
    "test_move_tool_moves_card_and_persists": ("tools", "flow"),
    "test_fit_includes_moved_card_and_drops_stale": ("tools", "input"),
    "test_card_drag_has_no_long_tasks": ("tools",),
    "test_moved_card_paints_above_its_new_neighbours": ("tools",),
    "test_straight_neighbour_back_faint_and_under_cards": ("links",),
    "test_tags_never_on_cards_gap_tag_ellipsis_then_full": ("links",),
    "test_tag_rename_keeps_button_text": ("links",),
    "test_context_menu_by_target": ("input", "tools"),
    "test_hide_screen_and_hidden_list": ("tools", "flow"),
    "test_undo_redo_card_moves_capped_at_50": ("tools",),
    "test_link_menu_rename_undo_and_go": ("links", "motion"),
    "test_trigger_drag_to_card_adds_link_note_and_undo": ("tools", "notes"),
    "test_knife_right_drag_cuts_link_into_note": ("tools", "links", "notes"),
    "test_trigger_tool_shows_sockets_and_socket_drag_changes_target": ("tools", "links"),
    "test_element_menu_via_hit_at": ("tools", "input"),
    "test_hit_at_without_palette_says_cannot_edit": ("tools",),
    "test_dblclick_title_and_desc_queue_pending_edits": ("tools", "notes"),
    "test_dblclick_screen_text_edits_with_preview": ("tools", "modal", "notes"),
    "test_element_menu_edit_text": ("tools",),
    "test_cut_hides_line_at_once_with_live_mark_and_toast_undo": ("tools", "links"),
    "test_socket_drag_draws_pending_line_at_once": ("tools", "links"),
    "test_toolbar_has_add_group": ("tools",),
    "test_layout_tool_drops_blank_card_and_undo": ("tools", "notes"),
    "test_empty_drop_makes_layout_and_links_it": ("tools", "links"),
    "test_empty_right_click_layout_here": ("tools", "input"),
    "test_memo_tool_opens_card_memo": ("tools", "notes"),
    "test_modal_pins_follow_navigated_screen": ("modal", "notes"),
    "test_element_tools_outline_hovered_element_by_kind": ("tools",),
    # test_canvas_helper.py — 7단계 로컬 도우미
    "test_helper_edit_html_ops": ("helper",),
    "test_helper_apply_backup_rebuild_and_refusals": ("helper",),
    "test_helper_server_applies_from_canvas_and_falls_back_to_copy": ("helper", "notes"),
    # test_canvas_v2.py
    "test_arrow_toggle_persists": ("flow",),
    "test_shift_click_focus": ("links",),
    "test_pick_note_pin_persists": ("notes", "modal"),
    "test_send_format": ("notes",),
    "test_clear_sent": ("notes",),
    "test_multi_select_note": ("notes", "modal"),
    "test_gym_link_colors": ("links",),
    "test_gym_zoom_floor_and_fit": ("input",),
    "test_gym_annotate_button": ("modal",),
    "test_gym_shortcut_hint": ("input",),
    "test_v2_label_positions": ("flow", "links"),
    "test_v2_focus_cycle": ("links",),
    "test_v2_hover_emphasis": ("links",),
    "test_v2_route_shapes": ("flow",),
    "test_v2_exit_focus": ("links",),
    "test_v2_expand_tall_screen": ("links",),
    "test_v2_base_curves_shot": ("flow",),
    "test_v2_no_vertical_through_cards": ("flow", "links"),
    "test_v3_back_exits_left": ("links",),
    "test_v3_tags_on_lanes": ("links",),
    "test_v3_same_target_merge": ("links",),
    "test_v3_main_flow_dashed": ("flow",),
    "test_v3_ctrl_click_camera": ("motion",),
    "test_v3_reduced_motion_jumps": ("motion",),
    "test_v3_transition_menu": ("motion",),
    "test_v3_line_style": ("links",),
}


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: 순수 함수(node) — 늘 같이 돌린다")
    for name, what in AREAS.items():
        config.addinivalue_line("markers", f"{name}: {what}")


def pytest_collection_modifyitems(config, items):
    missing = []
    for it in items:
        if it.fspath.basename == "test_canvas_modules.py":
            it.add_marker(pytest.mark.unit)
            continue
        if not it.fspath.basename.startswith("test_canvas_"):
            continue
        areas = BROWSER.get(it.originalname or it.name)
        if not areas:
            missing.append(it.nodeid)
            continue
        for a in areas:
            it.add_marker(getattr(pytest.mark, a))
    if missing:
        raise pytest.UsageError("영역 표(tests/conftest.py BROWSER)에 없는 브라우저 테스트: " + ", ".join(missing))
