"""An emerald profile and selected-work showcase."""

from __future__ import annotations

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def profile_project() -> Project:
    s = Screen()
    t = skin("emerald")
    status = s.box(
        "status_badge",
        s.text("status", "AVAILABLE FOR COLLABORATION", 12, t.accent, "W_600"),
        t.accent_soft,
        7,
        16,
    )
    identity = s.column(
        "identity",
        s.eyebrow("profile_eyebrow", "People / Profile", t.hero_muted),
        s.headline("name", "Alex Morgan", 32, t.hero_ink),
        s.text("role", "Product designer  ·  Kuala Lumpur", 15, t.hero_ink),
        s.row("status_row", status),
        spacing=6,
    )
    banner = s.box(
        "banner",
        s.centered(
            "banner_frame",
            s.row(
                "identity_row",
                s.avatar(
                    "avatar", "AM", size=80, bgcolor=t.accent_soft, color=t.accent
                ),
                identity,
                spacing=24,
                wrap=True,
            ),
            width=940,
        ),
        t.hero,
        20,
        0,
    )
    about = s.surface(
        "about",
        s.column(
            "about_content",
            s.eyebrow("about_eyebrow", "A little introduction", t.accent),
            s.text("about_title", "Thoughtful by design.", 22, t.ink, "W_600"),
            s.text(
                "bio",
                "I design thoughtful tools that make everyday work feel simpler.",
                15,
                t.ink,
            ),
            s.text("location", "Based in Kuala Lumpur  ·  Joined 2022", 14, t.muted),
            spacing=5,
        ),
        color=t.surface,
        border=t.border,
        padding=16,
    )

    def work_tile(
        node_id: str, title: str, subtitle: str, initials: str, tag: str
    ) -> str:
        return s.add(
            "ListTile",
            node_id,
            {},
            slots={
                "leading": (
                    s.avatar(
                        f"{node_id}_icon",
                        initials,
                        size=44,
                        bgcolor=t.accent_soft,
                        color=t.accent,
                    ),
                ),
                "title": (s.text(f"{node_id}_title", title, 15, t.ink, "W_600"),),
                "subtitle": (s.text(f"{node_id}_subtitle", subtitle, 13, t.muted),),
                "trailing": (s.text(f"{node_id}_tag", tag, 12, t.accent, "W_600"),),
            },
        )

    work = s.surface(
        "work",
        s.column(
            "work_content",
            s.eyebrow("work_eyebrow", "A few favourites", t.accent),
            s.text("work_title", "Selected work", 22, t.ink, "W_600"),
            work_tile(
                "atlas",
                "Atlas",
                "A design system built for teams",
                "A",
                "DESIGN SYSTEM",
            ),
            s.divider("work_divider", t.border),
            work_tile(
                "fieldnotes",
                "Fieldnotes",
                "Research tools for curious minds",
                "F",
                "RESEARCH",
            ),
            spacing=4,
        ),
        color=t.surface,
        border=t.border,
        padding=16,
    )
    actions = s.row(
        "actions",
        s.button("contact", "Get in touch", t.accent),
        s.text("contact_note", "Open to thoughtful collaborations", 13, t.muted),
        spacing=16,
    )
    framed = s.centered(
        "body_frame",
        s.column("body_content", about, work, actions, spacing=12),
        width=940,
    )
    body = s.box("body", framed, t.canvas, 20, 0)
    return s.finish(
        "Profile",
        s.column("root", banner, body, spacing=0),
        seed="GREEN",
        bgcolor=t.canvas,
    )
