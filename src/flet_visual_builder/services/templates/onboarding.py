"""A focused, three-step workspace setup template."""

from __future__ import annotations

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import skin


def onboarding_project() -> Project:
    s = Screen()
    t = skin("indigo")

    header_content = s.column(
        "header_content",
        s.eyebrow("brand", "NORTHSTAR  /  WORKSPACE SETUP", t.hero_muted),
        s.headline("title", "Make space for your best work.", 30, t.hero_ink),
        s.text(
            "subtitle",
            "A few thoughtful details, and you're ready to go.",
            14,
            t.hero_muted,
        ),
        spacing=8,
    )
    header = s.box("header", header_content, t.hero, padding=32, radius=0)

    progress_heading = s.add(
        "Row",
        "progress_heading",
        {"alignment": "SPACE_BETWEEN", "vertical_alignment": "CENTER"},
        (
            s.eyebrow("step", "STEP 2 OF 3  /  YOUR TEAM", t.accent),
            s.text("progress_fraction", "02 / 03", 13, t.muted, "W_600"),
        ),
    )
    progress = s.surface(
        "progress",
        s.column(
            "progress_content",
            progress_heading,
            s.progress("bar", 2 / 3, color=t.accent, bgcolor=t.accent_soft),
            s.text("progress_note", "Next up: invite your teammates.", 14, "#475569"),
            spacing=12,
        ),
        color=t.surface,
        padding=22,
        border=t.border,
    )
    workspace = s.column(
        "workspace_group",
        s.text("workspace_label", "Workspace name", 13, t.ink, "W_600"),
        s.add(
            "TextField",
            "workspace_name",
            {"hint_text": "e.g. Acme Studio", "border": {"kind": "outline"}},
        ),
        spacing=6,
    )
    team = s.column(
        "team_group",
        s.text("team_label", "Team name", 13, t.ink, "W_600"),
        s.add(
            "TextField",
            "team_name",
            {"hint_text": "e.g. Design team", "border": {"kind": "outline"}},
        ),
        spacing=6,
    )
    tips = s.row(
        "tips_row",
        s.add("Checkbox", "tips", {"value": False}),
        s.text("tips_label", "Send me helpful setup tips", 13, t.ink),
        spacing=2,
    )
    actions = s.add(
        "Row",
        "actions",
        {"alignment": "SPACE_BETWEEN", "vertical_alignment": "CENTER"},
        (
            s.add("OutlinedButton", "back", {"content": "Back"}),
            s.button("continue_button", "Continue  →", t.accent),
        ),
    )
    details = s.surface(
        "details",
        s.column(
            "details_content",
            s.headline("details_title", "Tell us about your team", 21, t.ink),
            s.text(
                "details_copy",
                "Give your workspace a name. You can change it later.",
                14,
                "#475569",
            ),
            s.box("form_gap", None, t.surface, padding=2),
            workspace,
            team,
            tips,
            s.divider("rule", t.border),
            actions,
            spacing=12,
        ),
        color=t.surface,
        padding=24,
        border=t.border,
    )
    content = s.add(
        "Container",
        "content_width",
        {"width": 760},
        (s.column("body_content", progress, details, spacing=14),),
    )
    body = s.box(
        "body",
        s.add("Row", "body_center", {"alignment": "CENTER"}, (content,)),
        t.canvas,
        padding=24,
        radius=0,
    )
    return s.finish(
        "Onboarding",
        s.column("root", header, body, spacing=0),
        bgcolor=t.canvas,
    )
