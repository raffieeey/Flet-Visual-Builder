"""A calm, grouped account settings surface."""

from __future__ import annotations

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def settings_project() -> Project:
    s = Screen()
    t = skin("emerald")

    def setting_row(node_id: str, title: str, subtitle: str, trailing: str) -> str:
        return s.add(
            "ListTile",
            node_id,
            {},
            slots={
                "title": (s.text(f"{node_id}_title", title, 15, t.ink, "W_600"),),
                "subtitle": (s.text(f"{node_id}_subtitle", subtitle, 13, t.muted),),
                "trailing": (trailing,),
            },
        )

    header = s.box(
        "heading",
        s.centered(
            "heading_frame",
            s.column(
                "heading_content",
                s.eyebrow("eyebrow", "Workspace / Account", t.hero_muted),
                s.headline("title", "Settings", 32, t.hero_ink),
                s.text(
                    "subtitle",
                    "A little more you, a little less noise.",
                    14,
                    t.hero_ink,
                ),
                spacing=8,
            ),
            width=900,
        ),
        t.hero,
        28,
        0,
    )
    account = s.surface(
        "account_card",
        s.column(
            "account_content",
            s.text("account_title", "Account details", 19, t.ink, "W_600"),
            s.text("account_copy", "Your identity across the workspace.", 14, t.muted),
            setting_row(
                "display_name_row",
                "Display name",
                "Shown to your team",
                s.add(
                    "TextField",
                    "display_name",
                    {
                        "value": "Alex Morgan",
                        "width": 260,
                        "border": {"kind": "outline"},
                    },
                ),
            ),
            s.divider("account_divider", t.border),
            setting_row(
                "email_row",
                "Email address",
                "Used for account notifications",
                s.add(
                    "TextField",
                    "email",
                    {
                        "value": "alex@example.com",
                        "width": 260,
                        "border": {"kind": "outline"},
                    },
                ),
            ),
            spacing=4,
        ),
        color=t.surface,
        border=t.border,
        padding=18,
    )
    notifications = s.surface(
        "notifications_card",
        s.column(
            "notifications_content",
            s.text("notifications_title", "Notifications", 19, t.ink, "W_600"),
            s.text(
                "notifications_copy", "Choose what lands in your inbox.", 14, t.muted
            ),
            setting_row(
                "updates_row",
                "Email updates",
                "Important activity and mentions",
                s.add("Switch", "email_updates", {"label": "", "value": True}),
            ),
            s.divider("notifications_divider", t.border),
            setting_row(
                "digest_row",
                "Weekly digest",
                "A quiet summary every Monday",
                s.add("Switch", "weekly_digest", {"label": "", "value": False}),
            ),
            spacing=4,
        ),
        color=t.surface,
        border=t.border,
        padding=18,
    )
    actions = s.row(
        "actions",
        s.button("save", "Save changes", t.accent),
        s.add("TextButton", "cancel", {"content": "Cancel"}),
        spacing=12,
    )
    framed = s.centered(
        "body_frame",
        s.column("body_content", account, notifications, actions, spacing=10),
        width=900,
    )
    body = s.box("body", framed, t.canvas, 24, 0)
    return s.finish(
        "Settings",
        s.column("root", header, body, spacing=0),
        seed="GREEN",
        bgcolor=t.canvas,
    )
