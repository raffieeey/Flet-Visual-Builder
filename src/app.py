"""Flet Visual Builder — main application."""
from __future__ import annotations

import flet as ft

from src.engine.tree_ops import (
    delete_node, find_node, find_parent, insert_child,
    reorder_sibling, wrap_node,
)
from src.models.widget_node import WidgetNode
from src.models.widget_registry import (
    WIDGET_REGISTRY, accepts_children, default_slot, defaults_for,
)
from src.state.app_state import AppState
from src.state.project_state import ProjectState
from src.ui.canvas import build_canvas
from src.ui.code_preview import build_code_preview
from src.ui.live_preview import build_live_preview
from src.ui.palette import build_palette
from src.ui.properties import build_properties
from src.ui.toolbar import build_toolbar
from src.ui.tree_view import build_tree_view
from src.utils.id_generator import new_id
from src.utils.serializer import save_project, load_project


def _initial_project() -> ProjectState:
    """Create a starter project with a sample login screen."""
    root = WidgetNode(id="root", type="Column", props={"alignment": "center", "horizontal_alignment": "center"})
    title = WidgetNode(id=new_id("text"), type="Text",
                       props={"value": "Welcome", "size": 28.0, "weight": "bold"}, slot="controls")
    username = WidgetNode(id=new_id("field"), type="TextField",
                          props={"label": "Username", "hint_text": "Enter your username"}, slot="controls")
    password = WidgetNode(id=new_id("field"), type="TextField",
                          props={"label": "Password", "password": True}, slot="controls")
    login_btn = WidgetNode(id=new_id("btn"), type="ElevatedButton",
                           props={"text": "Login", "on_click": "on_login"}, slot="controls")
    root.children = [title, username, password, login_btn]
    for i, c in enumerate(root.children):
        c.parent_id = root.id
        c.order = i
    return ProjectState(name="My App", tree=root)


def main(page: ft.Page) -> None:
    page.title = "Flet Visual Builder"
    page.bgcolor = "#f0f0f0"
    page.window.width = 1280
    page.window.height = 800
    page.padding = 0
    page.spacing = 0

    state = AppState(project=_initial_project())
    current_tab = 0  # 0=Design, 1=Preview, 2=Code

    # ─── State helpers ─────────────────────────────────────────

    def get_selected_node() -> WidgetNode | None:
        sid = state.project.selected_node_id
        if sid:
            return find_node(state.project.tree, sid)
        return None

    # ─── UI Rebuild ────────────────────────────────────────────

    def rebuild_ui():
        nonlocal current_tab
        proj = state.project
        root = proj.tree
        selected = get_selected_node()

        # Toolbar
        toolbar = build_toolbar(
            project_name=proj.name,
            on_undo=handle_undo,
            on_redo=handle_redo,
            on_save=handle_save,
            on_load=handle_load,
            on_tab_change=handle_tab_change,
            current_tab=current_tab,
            can_undo=bool(state._undo_stack),
            can_redo=bool(state._redo_stack),
        )

        if current_tab == 0:
            # Design view: palette + canvas + tree + properties
            palette = build_palette(on_add_widget=handle_add_widget)
            canvas = build_canvas(
                root=root,
                selected_id=proj.selected_node_id,
                on_select=handle_select,
                on_delete=handle_delete,
                on_move_up=handle_move_up,
                on_move_down=handle_move_down,
                on_wrap=handle_wrap,
            )
            tree_view = build_tree_view(
                root=root,
                selected_id=proj.selected_node_id,
                on_select=handle_select,
            )
            props_panel = build_properties(
                node=selected,
                on_prop_change=handle_prop_change,
            )

            left_col = ft.Column(
                controls=[
                    ft.Container(content=palette, expand=3),
                    ft.Container(content=tree_view, expand=2),
                ],
                expand=True,
                spacing=0,
            )

            body = ft.Row(
                controls=[
                    ft.Container(content=left_col, width=200),
                    ft.Container(content=canvas, expand=True),
                    ft.Container(content=props_panel, width=260),
                ],
                expand=True,
                spacing=0,
            )

        elif current_tab == 1:
            # Preview view
            body = build_live_preview(root=root, theme=proj.theme)

        else:
            # Code view
            body = build_code_preview(
                root=root,
                on_copy=handle_copy_code,
                on_export=handle_export_code,
            )

        page.controls.clear()
        page.add(
            ft.Column(
                controls=[toolbar, body],
                expand=True,
                spacing=0,
            )
        )
        page.update()

    # ─── Handlers ──────────────────────────────────────────────

    def handle_tab_change(index: int):
        nonlocal current_tab
        current_tab = index
        rebuild_ui()

    def handle_select(node_id: str):
        state.project.selected_node_id = node_id
        rebuild_ui()

    def handle_add_widget(widget_type: str):
        """Add a new widget. If a layout node is selected, add as child.
        Otherwise add as sibling after the selected node."""
        def _add(proj: ProjectState):
            new_node = WidgetNode(
                id=new_id(widget_type.lower()),
                type=widget_type,
                props=dict(defaults_for(widget_type)),
            )
            target_id = proj.selected_node_id or proj.tree.id
            target = find_node(proj.tree, target_id)
            if not target:
                target = proj.tree

            if accepts_children(target.type):
                # Add as child of the selected layout node
                slot = default_slot(target.type)
                insert_child(target, new_node, slot=slot)
            else:
                # Add as sibling after the selected node
                parent = find_parent(proj.tree, target.id)
                if parent:
                    idx = next(
                        (i for i, c in enumerate(parent.children) if c.id == target.id),
                        len(parent.children) - 1,
                    )
                    slot = target.slot
                    insert_child(parent, new_node, index=idx + 1, slot=slot)
                else:
                    # Target is root, add as child
                    slot = default_slot(proj.tree.type)
                    insert_child(proj.tree, new_node, slot=slot)

            proj.selected_node_id = new_node.id

        state.transact(_add)
        rebuild_ui()

    def handle_delete():
        sid = state.project.selected_node_id
        if not sid or sid == state.project.tree.id:
            return

        def _del(proj: ProjectState):
            parent = find_parent(proj.tree, sid)
            delete_node(proj.tree, sid)
            proj.selected_node_id = parent.id if parent else proj.tree.id

        state.transact(_del)
        rebuild_ui()

    def handle_move_up():
        sid = state.project.selected_node_id
        if not sid:
            return

        def _up(proj: ProjectState):
            reorder_sibling(proj.tree, sid, -1)

        state.transact(_up)
        rebuild_ui()

    def handle_move_down():
        sid = state.project.selected_node_id
        if not sid:
            return

        def _down(proj: ProjectState):
            reorder_sibling(proj.tree, sid, 1)

        state.transact(_down)
        rebuild_ui()

    def handle_wrap(wrapper_type: str):
        sid = state.project.selected_node_id
        if not sid or sid == state.project.tree.id:
            return

        def _wrap(proj: ProjectState):
            wrapper = WidgetNode(
                id=new_id(wrapper_type.lower()),
                type=wrapper_type,
                props=dict(defaults_for(wrapper_type)),
            )
            ws = default_slot(wrapper_type) or "content"
            wrap_node(proj.tree, sid, wrapper, wrapper_slot=ws)
            proj.selected_node_id = wrapper.id

        state.transact(_wrap)
        rebuild_ui()

    def handle_prop_change(prop_name: str, value):
        sid = state.project.selected_node_id
        if not sid:
            return

        def _change(proj: ProjectState):
            node = find_node(proj.tree, sid)
            if node:
                node.props[prop_name] = value

        state.transact(_change)
        rebuild_ui()

    def handle_undo():
        state.undo()
        rebuild_ui()

    def handle_redo():
        state.redo()
        rebuild_ui()

    def handle_save():
        def _on_result(e: ft.FilePickerResultEvent):
            if e.path:
                path = e.path
                if not path.endswith(".fvb.json"):
                    path += ".fvb.json"
                save_project(state.project, path)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Saved to {path}"),
                    bgcolor="#4caf50",
                )
                page.snack_bar.open = True
                page.update()

        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.save_file(
            dialog_title="Save FVB Project",
            file_name=f"{state.project.name}.fvb.json",
            allowed_extensions=["json"],
        )

    def handle_load():
        def _on_result(e: ft.FilePickerResultEvent):
            if e.files and e.files[0].path:
                try:
                    loaded = load_project(e.files[0].path)
                    state.project = loaded
                    state._undo_stack.clear()
                    state._redo_stack.clear()
                    rebuild_ui()
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Loaded: {loaded.name}"),
                        bgcolor="#4caf50",
                    )
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Load error: {ex}"),
                        bgcolor="#d32f2f",
                    )
                    page.snack_bar.open = True
                    page.update()

        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.pick_files(
            dialog_title="Open FVB Project",
            allowed_extensions=["json"],
        )

    def handle_copy_code(code: str):
        page.set_clipboard(code)
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Code copied to clipboard!"),
            bgcolor="#4caf50",
        )
        page.snack_bar.open = True
        page.update()

    def handle_export_code(code: str):
        def _on_result(e: ft.FilePickerResultEvent):
            if e.path:
                path = e.path
                if not path.endswith(".py"):
                    path += ".py"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Exported to {path}"),
                    bgcolor="#4caf50",
                )
                page.snack_bar.open = True
                page.update()

        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.save_file(
            dialog_title="Export Python Code",
            file_name="app.py",
            allowed_extensions=["py"],
        )

    # ─── Keyboard shortcuts ────────────────────────────────────

    def on_keyboard(e: ft.KeyboardEvent):
        if e.ctrl:
            if e.key == "Z":
                if e.shift:
                    handle_redo()
                else:
                    handle_undo()
            elif e.key == "Y":
                handle_redo()
            elif e.key == "S":
                handle_save()
        elif e.key == "Delete" or e.key == "Backspace":
            handle_delete()

    page.on_keyboard_event = on_keyboard

    # ─── Initial render ────────────────────────────────────────
    rebuild_ui()


def run() -> None:
    ft.app(target=main)