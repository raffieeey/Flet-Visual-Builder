"""Design tokens and shared visual primitives.

Every panel in the workspace composes these tokens instead of hard-coding
colors, spacing, or typography. Keeping the vocabulary in one module is what
makes the builder look like one product rather than a pile of screens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import flet as ft


@dataclass(frozen=True)
class Tokens:
    """Light workspace palette: quiet chrome, neutral canvas, indigo accent."""

    bg: str = "#F4F5F7"
    panel: str = "#FFFFFF"
    panel_alt: str = "#FAFBFC"
    rail: str = "#FBFBFC"
    border: str = "#E3E6EA"
    border_soft: str = "#EEF0F3"
    border_strong: str = "#C9D1DA"
    text: str = "#17202A"
    text_muted: str = "#5B6B7B"
    text_faint: str = "#8A97A6"
    accent: str = "#4F46E5"
    accent_hover: str = "#4338CA"
    accent_soft: str = "#EEF0FF"
    accent_border: str = "#C7CBFA"
    canvas_bg: str = "#E9ECF1"
    selection: str = "#4F46E5"
    hover: str = "#A5B4FC"
    drop: str = "#16A34A"
    drop_soft: str = "#DCFCE7"
    success: str = "#12B76A"
    warning: str = "#F79009"
    danger: str = "#E5484D"
    danger_soft: str = "#FEECEC"
    code_bg: str = "#0F172A"
    code_text: str = "#E2E8F0"
    code_muted: str = "#94A3B8"
    shadow: str = "#12000000"


T = Tokens()

# Spacing scale (4pt grid).
XS = 4
SM = 8
MD = 12
LG = 16
XL = 24

# Radii.
R_SM = 4
R_MD = 6
R_LG = 10

# Chrome metrics.
TOOLBAR_H = 52
STATUS_H = 26
RAIL_W = 264
INSPECTOR_W = 300

# Type scale.
F_MICRO = 10
F_SMALL = 11
F_BODY = 12.5
F_LABEL = 13
F_TITLE = 15
F_HERO = 20


def page_theme() -> ft.Theme:
    """Material theme for controls that live inside the workspace."""
    return ft.Theme(
        color_scheme_seed=T.accent,
        use_material3=True,
        font_family="Roboto",
        visual_density=ft.VisualDensity.COMPACT,
    )


def text(
    value: str,
    *,
    size: float = F_LABEL,
    weight: ft.FontWeight | None = None,
    color: str | None = None,
    italic: bool = False,
    max_lines: int | None = None,
    overflow: ft.TextOverflow | None = None,
    selectable: bool = False,
    **kwargs: object,
) -> ft.Text:
    return ft.Text(
        value=value,
        size=size,
        weight=weight,
        color=color or T.text,
        italic=italic,
        max_lines=max_lines,
        overflow=overflow,
        selectable=selectable,
        **kwargs,
    )


def muted(value: str, *, size: float = F_BODY, **kwargs: object) -> ft.Text:
    return text(value, size=size, color=T.text_muted, **kwargs)


def faint(value: str, *, size: float = F_SMALL, **kwargs: object) -> ft.Text:
    return text(value, size=size, color=T.text_faint, **kwargs)


def label(value: str) -> ft.Text:
    """Small caps-ish section label used across panels."""
    return ft.Text(
        value=value.upper(),
        size=F_MICRO,
        weight=ft.FontWeight.W_600,
        color=T.text_faint,
    )


def icon_button(
    icon: str,
    tooltip: str,
    on_click: Callable[..., object] | None,
    *,
    color: str | None = None,
    disabled: bool = False,
    size: int = 18,
    selected: bool = False,
) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        icon_size=size,
        icon_color=T.accent if selected else (color or T.text_muted),
        tooltip=tooltip,
        on_click=on_click,
        disabled=disabled,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=R_MD),
            padding=ft.Padding(left=6, top=6, right=6, bottom=6),
            bgcolor={ft.ControlState.HOVERED: T.border_soft},
        ),
    )


def button(
    label_text: str,
    on_click: Callable[..., object] | None = None,
    *,
    icon: str | None = None,
    primary: bool = False,
    danger: bool = False,
    disabled: bool = False,
    compact: bool = True,
) -> ft.Control:
    """A single button vocabulary: quiet by default, filled when primary."""
    fg = T.panel if primary else (T.danger if danger else T.text)
    bg = T.accent if primary else (T.danger_soft if danger else T.panel)
    border_color = T.accent if primary else (T.danger if danger else T.border)
    control: ft.Control
    if primary or danger:
        control = ft.FilledButton(
            content=label_text,
            icon=icon,
            on_click=on_click,
            disabled=disabled,
        )
    else:
        control = ft.OutlinedButton(
            content=label_text,
            icon=icon,
            on_click=on_click,
            disabled=disabled,
        )
    control.style = ft.ButtonStyle(
        color=fg,
        bgcolor=bg,
        icon_color=fg,
        padding=ft.Padding(left=10, top=6, right=10, bottom=6),
        shape=ft.RoundedRectangleBorder(radius=R_MD),
        side=ft.BorderSide(width=1, color=border_color),
        text_style=ft.TextStyle(size=F_BODY, weight=ft.FontWeight.W_500),
    )
    if compact:
        control.height = 30
    return control


def divider(*, vertical: bool = False, color: str | None = None) -> ft.Control:
    if vertical:
        return ft.Container(width=1, bgcolor=color or T.border, height=24)
    return ft.Container(height=1, bgcolor=color or T.border_soft)


def panel(
    content: ft.Control | None = None,
    *,
    padding: int | ft.Padding = MD,
    width: int | None = None,
    height: int | None = None,
    bgcolor: str | None = None,
    border: bool = False,
    expand: bool | int | None = None,
    radius: int | None = None,
) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        width=width,
        height=height,
        bgcolor=bgcolor or T.panel,
        border=ft.Border.all(1, T.border) if border else None,
        border_radius=radius if radius is not None else R_MD,
        expand=expand,
    )


def section(
    header: str,
    content: ft.Control,
    *,
    subtitle: str | None = None,
    trailing: ft.Control | None = None,
) -> ft.Column:
    head: list[ft.Control] = [label(header)]
    if subtitle:
        head.append(faint(subtitle))
    row: list[ft.Control] = [
        ft.Column(controls=head, spacing=1, expand=True, tight=True)
    ]
    if trailing is not None:
        row.append(trailing)
    return ft.Column(
        controls=[ft.Row(controls=row, vertical_alignment=ft.CrossAxisAlignment.CENTER), content],
        spacing=SM,
        tight=True,
    )


def empty_state(icon: str, title: str, body: str) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(icon, size=26, color=T.border_strong),
                text(title, size=F_LABEL, weight=ft.FontWeight.W_600, color=T.text_muted),
                faint(body),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            tight=True,
        ),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding(left=LG, top=XL, right=LG, bottom=XL),
        expand=True,
    )


def pill(value: str, *, color: str | None = None, bgcolor: str | None = None) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            value=value,
            size=F_MICRO,
            weight=ft.FontWeight.W_600,
            color=color or T.accent,
        ),
        bgcolor=bgcolor or T.accent_soft,
        padding=ft.Padding(left=6, top=2, right=6, bottom=2),
        border_radius=R_SM,
    )


def status_dot(color: str, size: int = 6) -> ft.Container:
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size)


def separator_dot() -> ft.Container:
    return ft.Container(width=2, height=2, bgcolor=T.border_strong, border_radius=2)


def scroll(control: ft.Control, *, expand: bool | int = True, spacing: int = 0) -> ft.Column:
    """Vertical scroll host with predictable desktop behaviour."""
    return ft.Column(
        controls=[control],
        scroll=ft.ScrollMode.AUTO,
        expand=expand,
        spacing=spacing,
        tight=True,
    )
