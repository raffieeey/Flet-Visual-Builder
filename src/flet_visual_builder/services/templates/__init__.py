"""Designed starter documents, built only from catalogue controls.

Each template lives in its own module so a screen can be redesigned without
touching the others. This module owns the registry the product exposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from flet_visual_builder.contracts import Project

from flet_visual_builder.services.templates.dashboard import dashboard_project
from flet_visual_builder.services.templates.flow import flow_project
from flet_visual_builder.services.templates.login import login_project
from flet_visual_builder.services.templates.onboarding import onboarding_project
from flet_visual_builder.services.templates.profile import profile_project
from flet_visual_builder.services.templates.screen import Screen
from flet_visual_builder.services.templates.style import Skin, skin
from flet_visual_builder.services.templates.settings import settings_project


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    name: str
    description: str
    category: str
    builder: Callable[[], Project]


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
        "flow",
        "Flow",
        "A three-screen app: home, review queue and settings, wired with navigation.",
        "Application",
        flow_project,
    ),
    Template(
        "onboarding",
        "Onboarding",
        "A guided workspace setup with progress.",
        "Getting started",
        onboarding_project,
    ),
)

__all__ = [
    "Screen",
    "Skin",
    "TEMPLATES",
    "Template",
    "dashboard_project",
    "flow_project",
    "login_project",
    "onboarding_project",
    "profile_project",
    "settings_project",
    "skin",
]
