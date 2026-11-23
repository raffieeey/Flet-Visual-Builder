"""Designed, editable starter projects built only from catalogue controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from flet_visual_builder.contracts import Node, Project


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    name: str
    description: str
    category: str
    builder: Callable[[], Project]


class _Screen:
    """Collect literal nodes while retaining deterministic, unique IDs."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    def add(self, type_id: str, node_id: str, props=None, children=()) -> str:
        if node_id in self.nodes:
            raise ValueError(f"duplicate template node: {node_id}")
        slot = "content" if type_id in {"Container", "Card"} else "controls"
        slots = {slot: tuple(children)} if children else {}
        self.nodes[node_id] = Node(node_id, type_id, dict(props or {}), slots, {})
        return node_id

    def text(
        self, node_id: str, value: str, size=14, color="#172033", weight="NORMAL"
    ) -> str:
        return self.add(
            "Text",
            node_id,
            {"value": value, "size": size, "color": color, "weight": weight},
        )

    def column(self, node_id: str, *children: str, spacing=12) -> str:
        return self.add(
            "Column",
            node_id,
            {"spacing": spacing, "horizontal_alignment": "STRETCH"},
            children,
        )

    def row(self, node_id: str, *children: str, spacing=12, wrap=False) -> str:
        return self.add(
            "Row",
            node_id,
            {"spacing": spacing, "vertical_alignment": "CENTER", "wrap": wrap},
            children,
        )

    def box(self, node_id: str, child: str, color: str, padding=24, radius=10) -> str:
        return self.add(
            "Container",
            node_id,
            {"bgcolor": color, "padding": padding, "border_radius": radius},
            (child,),
        )

    def button(self, node_id: str, label: str, color="#4F46E5") -> str:
        return self.add(
            "Button",
            node_id,
            {"content": label, "bgcolor": color, "color": "#FFFFFF", "elevation": 0},
        )

    def finish(self, name: str, root: str) -> Project:
        return Project(
            name=name,
            page={
                "title": name,
                "padding": 0,
                "scroll": "AUTO",
                "theme_mode": "LIGHT",
                "theme": {"color_scheme_seed": "INDIGO"},
            },
            root_ids=(root,),
            nodes=self.nodes,
            assets={},
        )


def login_project() -> Project:
    s = _Screen()
    brand = s.column(
        "brand_content",
        s.text("brand", "NORTHSTAR / WORKSPACE", 13, "#C7D2FE", "W_600"),
        s.text("hero", "A calmer way to work.", 30, "#FFFFFF", "BOLD"),
        s.text(
            "hero_detail", "Bring your projects and people together.", 15, "#E0E7FF"
        ),
    )
    header = s.box("brand_band", brand, "#312E81", 32, 0)
    form = s.column(
        "form_content",
        s.text("welcome", "Welcome back", 24, weight="BOLD"),
        s.text("intro", "Sign in to continue to your workspace.", 14, "#64748B"),
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
        s.add("Checkbox", "remember", {"label": "Remember me", "value": True}),
        s.button("sign_in", "Sign in"),
        s.add(
            "TextButton",
            "forgot",
            {"content": "Forgot password?", "icon_color": "#4F46E5"},
        ),
    )
    body = s.box("form_card", form, "#FFFFFF", 28)
    root = s.column("root", header, s.box("body", body, "#F1F5F9", 32, 0), spacing=0)
    return s.finish("Login", root)


def dashboard_project() -> Project:
    s = _Screen()
    header = s.box(
        "header",
        s.row(
            "header_row",
            s.text("brand", "PULSE / OVERVIEW", 15, "#FFFFFF", "BOLD"),
            s.text("date", "Monday  ·  This week", 13, "#C7D2FE"),
        ),
        "#1E1B4B",
        24,
        0,
    )
    metrics = []
    for key, title, value, detail in (
        ("revenue", "Revenue", "$24,860", "+12% vs last week"),
        ("orders", "Orders", "328", "+8% vs last week"),
        ("customers", "Customers", "1,204", "42 new this week"),
    ):
        metrics.append(
            s.box(
                key,
                s.column(
                    key + "_content",
                    s.text(key + "_label", title, 13, "#64748B"),
                    s.text(key + "_value", value, 24, "#172033", "BOLD"),
                    s.text(key + "_detail", detail, 12, "#15803D"),
                    spacing=8,
                ),
                "#FFFFFF",
                20,
            )
        )
    activity = s.box(
        "activity",
        s.column(
            "activity_content",
            s.text("activity_title", "Recent activity", 18, weight="W_600"),
            s.add("Divider", "rule", {"thickness": 1, "color": "#E2E8F0"}),
            s.text("activity_one", "New order received  ·  10 minutes ago", 14),
            s.text(
                "activity_two", "Monthly report is ready  ·  2 hours ago", 14, "#64748B"
            ),
            s.button("view_report", "View report"),
        ),
        "#FFFFFF",
        24,
    )
    body = s.column(
        "body_content",
        s.text("title", "Good morning, Alex", 26, weight="BOLD"),
        s.text("subtitle", "Here is what is happening today.", 14, "#64748B"),
        s.row("metrics", *metrics, wrap=True),
        activity,
        spacing=16,
    )
    return s.finish(
        "Dashboard",
        s.column("root", header, s.box("body", body, "#F1F5F9", 32, 0), spacing=0),
    )


def settings_project() -> Project:
    s = _Screen()
    heading = s.box(
        "heading",
        s.column(
            "heading_content",
            s.text("eyebrow", "ACCOUNT / PREFERENCES", 12, "#A7F3D0", "W_600"),
            s.text("title", "Settings", 28, "#FFFFFF", "BOLD"),
            s.text("subtitle", "Make this workspace your own.", 14, "#D1FAE5"),
        ),
        "#064E3B",
        30,
        0,
    )
    account = s.box(
        "account_card",
        s.column(
            "account_content",
            s.text("account_title", "Account details", 18, weight="W_600"),
            s.text(
                "account_copy", "Update how you appear to your team.", 13, "#64748B"
            ),
            s.add(
                "TextField",
                "display_name",
                {
                    "label": "Display name",
                    "value": "Alex Morgan",
                    "border": {"kind": "outline"},
                },
            ),
            s.add(
                "TextField",
                "email",
                {
                    "label": "Email",
                    "value": "alex@example.com",
                    "border": {"kind": "outline"},
                },
            ),
        ),
        "#FFFFFF",
    )
    prefs = s.box(
        "preferences_card",
        s.column(
            "preferences_content",
            s.text("preferences_title", "Notifications", 18, weight="W_600"),
            s.text(
                "preferences_copy",
                "Choose the updates you want to receive.",
                13,
                "#64748B",
            ),
            s.add("Switch", "email_updates", {"label": "Email updates", "value": True}),
            s.add(
                "Switch", "weekly_digest", {"label": "Weekly digest", "value": False}
            ),
            s.button("save", "Save changes", "#047857"),
        ),
        "#FFFFFF",
    )
    return s.finish(
        "Settings",
        s.column(
            "root",
            heading,
            s.box(
                "body",
                s.column("body_content", account, prefs, spacing=16),
                "#F1F5F9",
                32,
                0,
            ),
            spacing=0,
        ),
    )


def profile_project() -> Project:
    s = _Screen()
    avatar = s.box(
        "avatar", s.text("initials", "AM", 24, "#4338CA", "BOLD"), "#E0E7FF", 20, 40
    )
    identity = s.column(
        "identity",
        s.text("name", "Alex Morgan", 28, "#FFFFFF", "BOLD"),
        s.text("role", "Product designer  ·  Kuala Lumpur", 14, "#CBD5E1"),
        s.text("status", "Available for collaboration", 13, "#A7F3D0"),
        spacing=8,
    )
    banner = s.box(
        "banner",
        s.row("identity_row", avatar, identity, spacing=20, wrap=True),
        "#1E293B",
        32,
        0,
    )
    about = s.box(
        "about",
        s.column(
            "about_content",
            s.text("about_title", "About", 18, weight="W_600"),
            s.text(
                "bio",
                "I design thoughtful tools that make everyday work feel simpler.",
                14,
                "#475569",
            ),
            s.text("location", "Based in Kuala Lumpur  ·  Joined 2022", 13, "#64748B"),
        ),
        "#FFFFFF",
    )
    work = s.box(
        "work",
        s.column(
            "work_content",
            s.text("work_title", "Selected work", 18, weight="W_600"),
            s.add("Divider", "rule", {"thickness": 1, "color": "#E2E8F0"}),
            s.text("project_one", "Atlas  /  Design systems", 14, weight="W_600"),
            s.text("project_two", "Fieldnotes  /  Research tools", 14, "#475569"),
            s.button("contact", "Get in touch"),
        ),
        "#FFFFFF",
    )
    return s.finish(
        "Profile",
        s.column(
            "root",
            banner,
            s.box(
                "body",
                s.column("body_content", about, work, spacing=16),
                "#F1F5F9",
                32,
                0,
            ),
            spacing=0,
        ),
    )


def onboarding_project() -> Project:
    s = _Screen()
    header = s.box(
        "header",
        s.column(
            "header_content",
            s.text("brand", "NORTHSTAR", 13, "#C7D2FE", "BOLD"),
            s.text("title", "Let's set up your space", 28, "#FFFFFF", "BOLD"),
            s.text("subtitle", "A few small steps to get you started.", 14, "#E0E7FF"),
        ),
        "#3730A3",
        32,
        0,
    )
    progress = s.box(
        "progress",
        s.column(
            "progress_content",
            s.text("step", "STEP 2 OF 3", 12, "#4F46E5", "W_600"),
            s.add(
                "ProgressBar",
                "bar",
                {"value": 0.66, "color": "#4F46E5", "bgcolor": "#E0E7FF"},
            ),
            s.text("progress_note", "Your workspace is almost ready", 13, "#64748B"),
        ),
        "#FFFFFF",
    )
    details = s.box(
        "details",
        s.column(
            "details_content",
            s.text("details_title", "Tell us about your team", 20, weight="W_600"),
            s.text(
                "details_copy", "You can change these details later.", 13, "#64748B"
            ),
            s.add(
                "TextField",
                "workspace_name",
                {
                    "label": "Workspace name",
                    "hint_text": "Acme Studio",
                    "border": {"kind": "outline"},
                },
            ),
            s.add(
                "TextField",
                "team_name",
                {
                    "label": "Team name",
                    "hint_text": "Design team",
                    "border": {"kind": "outline"},
                },
            ),
            s.add("Checkbox", "tips", {"label": "Send me setup tips", "value": True}),
            s.row(
                "actions",
                s.button("continue_button", "Continue"),
                s.add(
                    "TextButton", "back", {"content": "Back", "icon_color": "#4F46E5"}
                ),
            ),
        ),
        "#FFFFFF",
    )
    return s.finish(
        "Onboarding",
        s.column(
            "root",
            header,
            s.box(
                "body",
                s.column("body_content", progress, details, spacing=16),
                "#F1F5F9",
                32,
                0,
            ),
            spacing=0,
        ),
    )


TEMPLATES: tuple[Template, ...] = (
    Template(
        "login",
        "Login",
        "A welcoming sign-in form for a team workspace.",
        "Authentication",
        login_project,
    ),
    Template(
        "dashboard",
        "Dashboard",
        "Metrics and recent activity at a glance.",
        "Analytics",
        dashboard_project,
    ),
    Template(
        "settings",
        "Settings",
        "Account details and notification preferences.",
        "Account",
        settings_project,
    ),
    Template(
        "profile",
        "Profile",
        "A personal introduction and selected work.",
        "Account",
        profile_project,
    ),
    Template(
        "onboarding",
        "Onboarding",
        "A guided workspace setup with progress.",
        "Getting started",
        onboarding_project,
    ),
)
