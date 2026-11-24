"""A three-screen flow: home, review queue and settings, wired with navigation."""

from __future__ import annotations

from flet_visual_builder.contracts import Project

from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def _hero(
    s: Screen,
    node_id: str,
    *,
    eyebrow: str,
    title: str,
    subtitle: str,
    color: str,
    muted: str,
    ink: str,
) -> str:
    return s.box(
        node_id,
        s.centered(
            f"{node_id}_frame",
            s.column(
                f"{node_id}_content",
                s.eyebrow(f"{node_id}_eyebrow", eyebrow, muted),
                s.headline(f"{node_id}_title", title, 30, ink),
                s.text(f"{node_id}_subtitle", subtitle, 14, muted),
                spacing=8,
            ),
            width=920,
        ),
        color,
        28,
        0,
    )


def _action_row(
    s: Screen,
    node_id: str,
    *,
    title: str,
    subtitle: str,
    badge: str,
    route: str,
    accent: str,
    muted: str,
    surface: str,
    border: str,
) -> str:
    tile = s.list_tile(node_id, title, subtitle)
    return s.add(
        "Container",
        f"{node_id}_box",
        {
            "bgcolor": surface,
            "padding": 6,
            "border_radius": 14,
            "border": {
                "top": {"width": 1, "color": border},
                "right": {"width": 1, "color": border},
                "bottom": {"width": 1, "color": border},
                "left": {"width": 1, "color": border},
            },
        },
        (
            s.row(
                f"{node_id}_row",
                s.add(
                    "Container",
                    f"{node_id}_badge",
                    {
                        "width": 34,
                        "height": 34,
                        "bgcolor": accent,
                        "border_radius": 17,
                        "alignment": "CENTER",
                    },
                    (s.text(f"{node_id}_badge_text", badge, 13, "#FFFFFF", "W_600"),),
                ),
                tile,
                s.text(f"{node_id}_chevron", "›", 20, muted, "W_600"),
                spacing=12,
            ),
        ),
    )


def flow_project() -> Project:
    s = Screen()
    t = skin("indigo")

    # ── screen 1: home ────────────────────────────────────────────────
    actions = s.column(
        "home_actions",
        _action_row(
            s,
            "action_reviews",
            title="Review queue",
            subtitle="3 items waiting for a decision",
            badge="3",
            route="/reviews",
            accent=t.accent,
            muted=t.muted,
            surface=t.surface,
            border=t.border,
        ),
        _action_row(
            s,
            "action_settings",
            title="Workspace settings",
            subtitle="Members, notifications and billing",
            badge="S",
            route="/settings",
            accent=t.hero,
            muted=t.muted,
            surface=t.surface,
            border=t.border,
        ),
        spacing=10,
    )
    s.navigate("action_reviews_box", "on_click", "/reviews")
    s.navigate("action_settings_box", "on_click", "/settings")

    home_hero = _hero(
        s,
        "home_hero",
        eyebrow="Fieldnotes / Home",
        title="Good morning, Alex.",
        subtitle="Three reviews are waiting. Two shipped yesterday.",
        color=t.hero,
        muted=t.hero_muted,
        ink=t.hero_ink,
    )
    home_body = s.box(
        "home_body",
        s.centered(
            "home_body_frame",
            s.column(
                "home_body_content",
                s.row(
                    "home_section",
                    s.text("home_section_title", "What's next", 20, t.ink, "BOLD"),
                    spacing=8,
                ),
                actions,
                s.button("home_open_queue", "Open the review queue", t.accent),
                s.text(
                    "home_note",
                    "Navigation is wired: these controls jump between screens in the exported app.",
                    13,
                    t.muted,
                ),
                spacing=18,
            ),
            width=920,
        ),
        t.canvas,
        28,
        0,
    )
    s.navigate("home_open_queue", "on_click", "/reviews")
    home = s.column("home", home_hero, home_body, spacing=0)

    # ── screen 2: review queue ────────────────────────────────────────
    reviews = []
    for index, (name, detail) in enumerate(
        (
            ("Atlas · design system audit", "Requested by Maya · due today"),
            ("Fieldnotes · research brief", "Requested by Sam · due tomorrow"),
            ("Northstar · pricing page", "Requested by Jo · no due date"),
        ),
        start=1,
    ):
        reviews.append(
            s.box(
                f"review_{index}",
                s.column(
                    f"review_{index}_content",
                    s.text(f"review_{index}_title", name, 15, t.ink, "W_600"),
                    s.text(f"review_{index}_detail", detail, 13, t.muted),
                    spacing=4,
                ),
                t.surface,
                18,
                14,
            )
        )

    reviews_hero = s.box(
        "reviews_hero",
        s.centered(
            "reviews_frame",
            s.column(
                "reviews_content",
                s.eyebrow("reviews_eyebrow", "Reviews / Queue", t.hero_muted),
                s.headline("reviews_title", "Review queue", 28, t.hero_ink),
                s.text(
                    "reviews_subtitle",
                    "Three items need a decision before Friday.",
                    14,
                    t.hero_muted,
                ),
                spacing=8,
            ),
            width=920,
        ),
        t.hero,
        24,
        0,
    )
    reviews_body = s.box(
        "reviews_body",
        s.centered(
            "reviews_body_frame",
            s.column(
                "reviews_body_content",
                *reviews,
                s.row(
                    "reviews_actions",
                    s.button("reviews_back", "Back home", t.accent),
                    spacing=12,
                ),
                spacing=12,
            ),
            width=920,
        ),
        t.canvas,
        28,
        0,
    )
    s.navigate("reviews_back", "on_click", "/")
    reviews_screen = s.column("reviews", reviews_hero, reviews_body, spacing=0)

    # ── screen 3: settings ────────────────────────────────────────────
    settings_hero = s.box(
        "settings_hero",
        s.centered(
            "settings_frame",
            s.column(
                "settings_content",
                s.eyebrow("settings_eyebrow", "Workspace / Settings", t.hero_muted),
                s.headline("settings_title", "Settings", 28, t.hero_ink),
                s.text(
                    "settings_subtitle",
                    "Account details and what lands in your inbox.",
                    14,
                    t.hero_muted,
                ),
                spacing=8,
            ),
            width=920,
        ),
        t.hero,
        24,
        0,
    )
    toggles = s.column(
        "settings_toggles",
        s.row(
            "row_email_updates",
            s.column(
                "row_email_updates_text",
                s.text("email_updates", "Email updates", 14, t.ink, "W_500"),
                s.text(
                    "email_updates_hint", "Important activity and mentions", 12, t.muted
                ),
                spacing=2,
            ),
            s.add("Switch", "switch_email_updates", {"value": True}),
            spacing=16,
        ),
        s.divider("settings_rule", t.border),
        s.row(
            "row_weekly_digest",
            s.column(
                "row_weekly_digest_text",
                s.text("weekly_digest", "Weekly digest", 14, t.ink, "W_500"),
                s.text(
                    "weekly_digest_hint", "A quiet summary every Monday", 12, t.muted
                ),
                spacing=2,
            ),
            s.add("Switch", "switch_weekly_digest", {"value": False}),
            spacing=16,
        ),
        spacing=12,
    )
    settings_body = s.box(
        "settings_body",
        s.centered(
            "settings_body_frame",
            s.column(
                "settings_body_content",
                s.surface(
                    "settings_card",
                    toggles,
                    color=t.surface,
                    border=t.border,
                    padding=20,
                ),
                s.row(
                    "settings_actions",
                    s.button("settings_save", "Save changes", t.accent),
                    s.text_button("settings_back", "Back home", t.accent),
                    spacing=12,
                ),
                spacing=16,
            ),
            width=920,
        ),
        t.canvas,
        28,
        0,
    )
    s.navigate("settings_back", "on_click", "/")
    settings_screen = s.column("settings", settings_hero, settings_body, spacing=0)

    return s.finish_flow(
        "Fieldnotes",
        [
            ("home", "Home", "/"),
            ("reviews", "Review queue", "/reviews"),
            ("settings", "Settings", "/settings"),
        ],
        seed="INDIGO",
        bgcolor=t.canvas,
    )
