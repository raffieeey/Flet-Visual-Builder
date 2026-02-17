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
    root = WidgetNode(id="root", type="Column",
                      props={"alignment": "center", "horizontal_alignment": "center"})
    children = [
        WidgetNode(id=new_id("text"), type="Text",
                   props={"value": "Welcome", "size": 28.0, "weight": "bold"}, slot="controls"),
        WidgetNode(id=new_id("field"), type="TextField",
                   props={"label": "Username", "hint_text": "Enter your username"}, slot="controls"),
        WidgetNode(id=new_id("field"), type="TextField",
                   props={"label": "Password", "password": True}, slot="controls"),
        WidgetNode(id=new_id("btn"), type="ElevatedButton",
                   props={"text": "Login", "on_click": "on_login"}, slot="controls"),
    ]
    root.children = children
    for i, c in enumerate(children):
        c.parent_id = root.id
        c.order = i
    return ProjectState(name="My App", tree=root)


def _show_snack(page: ft.Page, message: str, color: str = "#4caf50"):
    """Show a snackbar message."""
    sb = ft.SnackBar(content=ft.Text(message, color="white"), bgcolor=color)
    page.overlay.append(sb)
    sb.open = True
    page.update()


def main(page: ft.Page) -> None:
    page.title = "Flet Visual Builder"
    page.bgcolor = "#f0f0f0"
    page.padding = 0
    page.spacing = 0

    state = AppState(project=_initial_project())
    current_tab = [0]  # mutable container: 0=Design, 1=Preview, 2=Code

    # ─── Helpers ───────────────────────────────────────────────

    def get_selected() -> WidgetNode | None:
        sid = state.project.selected_node_id
        return find_node(state.project.tree, sid) if sid else None

    # ─── Rebuild ───────────────────────────────────────────────

    def rebuild():
        proj = state.project
        root = proj.tree
        selected = get_selected()

        toolbar = build_toolbar(
            project_name=proj.name,
            on_undo=do_undo, on_redo=do_redo,
            on_save=do_save, on_load=do_load,
            on_tab_change=do_tab_change,
            current_tab=current_tab[0],
            can_undo=bool(state._undo_stack),
            can_redo=bool(state._redo_stack),
        )

        tab = current_tab[0]
        if tab == 0:
            palette = build_palette(on_add_widget=do_add_widget)
            canvas = build_canvas(
                root=root, selected_id=proj.selected_node_id,
                on_select=do_select, on_delete=do_delete,
                on_move_up=do_move_up, on_move_down=do_move_down,
                on_wrap=do_wrap,
            )
            tree_view = build_tree_view(
                root=root, selected_id=proj.selected_node_id,
                on_select=do_select,
            )
            props_panel = build_properties(node=selected, on_prop_change=do_prop_change)

            left_col = ft.Column(controls=[
                ft.Container(content=palette, expand=3),
                ft.Container(content=tree_view, expand=2),
            ], expand=True, spacing=0)

            body = ft.Row(controls=[
                ft.Container(content=left_col, width=200),
                ft.Container(content=canvas, expand=True),
                ft.Container(content=props_panel, width=260),
            ], expand=True, spacing=0)

        elif tab == 1:
            body = build_live_preview(root=root, theme=proj.theme)
        else:
            body = build_code_preview(root=root, on_copy=do_copy_code, on_export=do_export_code)

        page.controls.clear()
        page.add(ft.Column(controls=[toolbar, body], expand=True, spacing=0))
        page.update()

    # ─── Handlers ──────────────────────────────────────────────

    def do_tab_change(index: int):
        current_tab[0] = index
        rebuild()

    def do_select(node_id: str):
        state.project.selected_node_id = node_id
        rebuild()

    def do_add_widget(widget_type: str):
        def _add(proj: ProjectState):
            new_node = WidgetNode(
                id=new_id(widget_type.lower()), type=widget_type,
                props=dict(defaults_for(widget_type)),
            )
            target_id = proj.selected_node_id or proj.tree.id
            target = find_node(proj.tree, target_id) or proj.tree

            if accepts_children(target.type):
                insert_child(target, new_node, slot=default_slot(target.type))
            else:
                parent = find_parent(proj.tree, target.id)
                if parent:
                    idx = next((i for i, c in enumerate(parent.children)
                                if c.id == target.id), len(parent.children) - 1)
                    insert_child(parent, new_node, index=idx + 1, slot=target.slot)
                else:
                    insert_child(proj.tree, new_node, slot=default_slot(proj.tree.type))
            proj.selected_node_id = new_node.id

        state.transact(_add)
        rebuild()

    def do_delete():
        sid = state.project.selected_node_id
        if not sid or sid == state.project.tree.id:
            return
        def _del(proj: ProjectState):
            parent = find_parent(proj.tree, sid)
            delete_node(proj.tree, sid)
            proj.selected_node_id = parent.id if parent else proj.tree.id
        state.transact(_del)
        rebuild()

    def do_move_up():
        sid = state.project.selected_node_id
        if sid:
            state.transact(lambda proj: reorder_sibling(proj.tree, sid, -1))
            rebuild()

    def do_move_down():
        sid = state.project.selected_node_id
        if sid:
            state.transact(lambda proj: reorder_sibling(proj.tree, sid, 1))
            rebuild()

    def do_wrap(wrapper_type: str):
        sid = state.project.selected_node_id
        if not sid or sid == state.project.tree.id:
            return
        def _wrap(proj: ProjectState):
            wrapper = WidgetNode(
                id=new_id(wrapper_type.lower()), type=wrapper_type,
                props=dict(defaults_for(wrapper_type)),
            )
            ws = default_slot(wrapper_type) or "content"
            wrap_node(proj.tree, sid, wrapper, wrapper_slot=ws)
            proj.selected_node_id = wrapper.id
        state.transact(_wrap)
        rebuild()

    def do_prop_change(prop_name: str, value):
        sid = state.project.selected_node_id
        if not sid:
            return
        def _change(proj: ProjectState):
            node = find_node(proj.tree, sid)
            if node:
                node.props[prop_name] = value
        state.transact(_change)
        rebuild()

    def do_undo():
        state.undo()
        rebuild()

    def do_redo():
        state.redo()
        rebuild()

    def do_save():
        def _on_result(e: ft.FilePickerResultEvent):
            if e.path:
                path = e.path if e.path.endswith(".fvb.json") else e.path + ".fvb.json"
                save_project(state.project, path)
                _show_snack(page, f"Saved to {path}")
        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.save_file(dialog_title="Save FVB Project",
                         file_name=f"{state.project.name}.fvb.json",
                         allowed_extensions=["json"])

    def do_load():
        def _on_result(e: ft.FilePickerResultEvent):
            if e.files and e.files[0].path:
                try:
                    loaded = load_project(e.files[0].path)
                    state.project = loaded
                    state._undo_stack.clear()
                    state._redo_stack.clear()
                    rebuild()
                    _show_snack(page, f"Loaded: {loaded.name}")
                except Exception as ex:
                    _show_snack(page, f"Load error: {ex}", "#d32f2f")
        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.pick_files(dialog_title="Open FVB Project",
                          allowed_extensions=["json"])

    def do_copy_code(code: str):
        page.clipboard = code
        page.update()
        _show_snack(page, "Code copied to clipboard!")

    def do_export_code(code: str):
        def _on_result(e: ft.FilePickerResultEvent):
            if e.path:
                path = e.path if e.path.endswith(".py") else e.path + ".py"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
                _show_snack(page, f"Exported to {path}")
        picker = ft.FilePicker(on_result=_on_result)
        page.overlay.append(picker)
        page.update()
        picker.save_file(dialog_title="Export Python Code",
                         file_name="app.py", allowed_extensions=["py"])

    # ─── Keyboard shortcuts ────────────────────────────────────

    def on_keyboard(e: ft.KeyboardEvent):
        if e.ctrl:
            if e.key == "Z":
                do_redo() if e.shift else do_undo()
            elif e.key == "Y":
                do_redo()
            elif e.key == "S":
                do_save()
        elif e.key == "Delete":
            do_delete()

    page.on_keyboard_event = on_keyboard

    # ─── Go ────────────────────────────────────────────────────
    rebuild()


def run() -> None:
    ft.app(target=main)