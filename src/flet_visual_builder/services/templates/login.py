"""A focused sign-in screen for the Northstar workspace."""

from __future__ import annotations

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def login_project() -> Project:
    s = Screen()
    c = skin("indigo")

    brand = s.column(
        "brand_content",
        s.eyebrow("brand", "NORTHSTAR / WORKSPACE", c.hero_muted),
        s.headline("hero", "Make room for\nyour best work.", 32, c.hero_ink),
        s.text(
            "hero_detail",
            "A quieter place for your projects,\nyour people, and the work that matters.",
            15,
            "#E0E7FF",
        ),
        s.surface(
            "brand_note",
            s.row(
                "brand_note_row",
                s.avatar(
                    "brand_avatar", "N", size=48, bgcolor=c.accent_soft, color=c.accent
                ),
                s.column(
                    "brand_note_content",
                    s.eyebrow(
                        "brand_note_label", "YOUR WORKSPACE, IN FOCUS", c.hero_muted
                    ),
                    s.text(
                        "brand_note_text",
                        "Everything moving forward, together.",
                        15,
                        c.hero_ink,
                        "W_600",
                    ),
                    spacing=8,
                ),
                spacing=16,
            ),
            color="#1E293B",
            padding=24,
            radius=16,
        ),
        spacing=24,
    )
    header = s.add(
        "Container",
        "brand_band",
        {"bgcolor": c.hero, "padding": 32, "border_radius": 20, "width": 500},
        (brand,),
    )
    form = s.column(
        "form_content",
        s.eyebrow("form_label", "WELCOME TO NORTHSTAR", c.accent),
        s.headline("welcome", "Welcome back", 32, c.ink),
        s.body("intro", "Sign in to continue to your workspace.", "#475569"),
        s.add(
            "TextField",
            "email",
            {
                "label": "Email address",
                "hint_text": "you@example.com",
                "border": {"kind": "outline"},
            },
        ),
        s.add(
            "TextField",
            "password",
            {"label": "Password", "password": True, "border": {"kind": "outline"}},
        ),
        s.row(
            "form_options",
            s.add("Checkbox", "remember", {"label": "Remember me", "value": True}),
            s.text_button("forgot", "Forgot password?", c.accent),
            spacing=16,
        ),
        s.button("sign_in", "Sign in", c.accent),
        s.text("form_footer", "Your workspace is ready when you are.", 13, c.muted),
        spacing=16,
    )
    body = s.add(
        "Container",
        "form_card",
        {"bgcolor": c.surface, "padding": 32, "border_radius": 20, "width": 480},
        (form,),
    )
    layout = s.add(
        "Row",
        "body",
        {
            "alignment": "CENTER",
            "vertical_alignment": "CENTER",
            "spacing": 32,
            "wrap": True,
        },
        (header, body),
    )
    canvas = s.add(
        "Container",
        "canvas",
        {
            "bgcolor": c.canvas,
            "padding": {"left": 32, "top": 48, "right": 32, "bottom": 48},
        },
        (layout,),
    )
    root = s.add(
        "Column",
        "root",
        {
            "spacing": 0,
            "expand": True,
            "alignment": "CENTER",
            "horizontal_alignment": "STRETCH",
        },
        (canvas,),
    )
    return s.finish("Login", root, seed="INDIGO", bgcolor=c.canvas, scroll="none")
