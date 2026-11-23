"""A concise overview for the Northstar workspace."""

from __future__ import annotations

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def dashboard_project() -> Project:
    s = Screen()
    c = skin("indigo")
    hero = s.column(
        "header_row",
        s.eyebrow("brand", "NORTHSTAR / OVERVIEW", c.hero_muted),
        s.headline("title", "Good morning, Alex", 30, c.hero_ink),
        s.text(
            "subtitle", "Here's how your workspace is moving this week.", 15, "#E0E7FF"
        ),
        s.surface(
            "hero_insight",
            s.row(
                "hero_insight_row",
                s.text(
                    "hero_insight_label", "WEEKLY SNAPSHOT", 11, c.hero_muted, "W_600"
                ),
                s.text(
                    "hero_insight_value",
                    "Your business is growing  ·  Revenue up 12%",
                    14,
                    c.hero_ink,
                    "W_600",
                ),
                spacing=24,
                wrap=True,
            ),
            color="#1E293B",
            padding=16,
            radius=12,
        ),
        spacing=12,
    )
    header = s.box(
        "header", s.centered("header_frame", hero, width=1040), c.hero, 24, 18
    )
    metrics = []
    for key, title, value, detail in (
        ("revenue", "Revenue", "$24,860", "+12% vs last week"),
        ("orders", "Orders", "328", "+8% vs last week"),
        ("customers", "Customers", "1,204", "42 new this week"),
    ):
        contents = s.column(
            key + "_content",
            s.text(key + "_label", title.upper(), 12, c.muted, "W_600"),
            s.text(key + "_value", value, 28, c.ink, "BOLD"),
            s.text(key + "_detail", detail, 13, c.positive, "W_500"),
            spacing=8,
        )
        metrics.append(
            s.add(
                "Container",
                key,
                {
                    "bgcolor": c.surface,
                    "padding": 24,
                    "border_radius": 16,
                    "expand": 1,
                },
                (contents,),
            )
        )
    activity_content = s.column(
        "activity_content",
        s.eyebrow("activity_eyebrow", "LATEST UPDATES", c.accent),
        s.text("activity_title", "Recent activity", 20, c.ink, "BOLD"),
        s.divider("rule", c.border),
        s.list_tile("activity_one", "New order received", "10 minutes ago"),
        s.list_tile("activity_two", "Monthly report is ready", "2 hours ago"),
        s.row(
            "activity_action",
            s.button("view_report", "View report", c.accent),
            spacing=24,
        ),
        spacing=8,
    )
    activity = s.add(
        "Container",
        "activity",
        {
            "bgcolor": c.surface,
            "padding": 24,
            "border_radius": 16,
            "expand": 2,
            "height": 312,
        },
        (activity_content,),
    )
    goal = s.add(
        "Container",
        "weekly_goal",
        {
            "bgcolor": c.accent_soft,
            "padding": 24,
            "border_radius": 16,
            "expand": 1,
            "height": 312,
        },
        (
            s.column(
                "goal_content",
                s.eyebrow("goal_label", "ON YOUR RADAR", c.accent),
                s.text("goal_title", "Weekly revenue goal", 20, c.ink, "BOLD"),
                s.text("goal_value", "$24,860 / $30,000", 18, c.ink, "W_600"),
                s.progress("goal_progress", 0.83, color=c.accent, bgcolor=c.border),
                s.text("goal_detail", "83% of your weekly target reached", 13, c.muted),
                s.text("date", "THIS WEEK  ·  OVERVIEW", 12, c.accent, "W_600"),
                spacing=16,
            ),
        ),
    )
    body = s.column(
        "body_content",
        s.row(
            "metrics_heading",
            s.text("metrics_title", "Your numbers", 20, c.ink, "BOLD"),
            s.chip("metrics_period", "This week", selected=True),
            spacing=16,
        ),
        s.row("metrics", *metrics, spacing=16),
        s.row("activity_section", activity, goal, spacing=16, align="START"),
        spacing=16,
    )
    framed = s.centered("body_frame", body, width=1040)
    return s.finish(
        "Dashboard",
        s.column(
            "root",
            s.centered("header_wrap", header, width=1040),
            s.box("body", framed, c.canvas, 32, 0),
            spacing=0,
        ),
        seed="INDIGO",
        bgcolor=c.canvas,
    )
