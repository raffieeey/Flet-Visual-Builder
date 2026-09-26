"""Flet Visual Builder reference export. Target: Flet 1.0.1."""

from collections.abc import Callable

import flet as ft


def build_ui(
    handle_reset_click: Callable[[ft.Event[ft.TextButton]], None],
    handle_save_click: Callable[[ft.Event[ft.Button]], None],
) -> ft.Control:
    return ft.Container(
        alignment=ft.Alignment.TOP_LEFT,
        border=ft.Border.all(width=1, color=ft.Colors.BLACK_12),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(color=ft.Colors.INDIGO, icon=ft.Icons.PERSON),
                        ft.Text(
                            size=24,
                            value="Profile settings",
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.TextField(
                                    border=ft.OutlineInputBorder(),
                                    label="Display name",
                                    value="",
                                ),
                                ft.Checkbox(
                                    label="Receive notifications",
                                    value=True,
                                ),
                                ft.Switch(label="Profile enabled", value=True),
                            ],
                            spacing=12,
                        ),
                        padding=16,
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.TextButton(
                            content="Reset",
                            on_click=handle_reset_click,
                        ),
                        ft.Button(
                            content="Save",
                            icon=ft.Icons.SAVE,
                            on_click=handle_save_click,
                        ),
                    ],
                ),
                ft.Divider(),
                ft.Text(color=ft.Colors.INDIGO, value="Ready"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=16,
        ),
        padding=ft.Padding.all(20),
        width=640,
    )


def main(page: ft.Page) -> None:
    page.appbar = ft.AppBar(title=ft.Text("Generated Flet application"))
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.title = "Profile settings"

    def handle_reset_click(e: ft.Event[ft.TextButton]) -> None:
        # Add application behavior in the exported application.
        pass

    def handle_save_click(e: ft.Event[ft.Button]) -> None:
        # Add application behavior in the exported application.
        pass

    page.add(build_ui(handle_reset_click, handle_save_click))


if __name__ == "__main__":
    ft.run(main)
