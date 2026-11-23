"""Shared visual language for the template documents.

Templates are the product's shop window: they decide whether the exported apps
look designed. They share one neutral base (ink, canvas, surface, border, muted)
and differ only in their accent skin, so the set reads as one family.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skin:
    accent: str
    accent_soft: str
    hero: str
    hero_ink: str
    hero_muted: str
    canvas: str
    surface: str
    ink: str
    muted: str
    border: str
    positive: str
    positive_soft: str


_SKINS: dict[str, Skin] = {
    "indigo": Skin(
        accent="#4F46E5",
        accent_soft="#EEF2FF",
        hero="#0B1220",
        hero_ink="#FFFFFF",
        hero_muted="#A5B4FC",
        canvas="#F6F7F9",
        surface="#FFFFFF",
        ink="#0B1220",
        muted="#64748B",
        border="#E2E8F0",
        positive="#15803D",
        positive_soft="#DCFCE7",
    ),
    "emerald": Skin(
        accent="#047857",
        accent_soft="#ECFDF5",
        hero="#052E26",
        hero_ink="#FFFFFF",
        hero_muted="#6EE7B7",
        canvas="#F5F8F6",
        surface="#FFFFFF",
        ink="#0B1220",
        muted="#5B6B63",
        border="#E1EAE5",
        positive="#15803D",
        positive_soft="#DCFCE7",
    ),
    "amber": Skin(
        accent="#B45309",
        accent_soft="#FFFBEB",
        hero="#1C1917",
        hero_ink="#FFFFFF",
        hero_muted="#FCD34D",
        canvas="#F8F6F2",
        surface="#FFFFFF",
        ink="#1C1917",
        muted="#6B6259",
        border="#EDE7DC",
        positive="#15803D",
        positive_soft="#DCFCE7",
    ),
    "slate": Skin(
        accent="#0F172A",
        accent_soft="#F1F5F9",
        hero="#0F172A",
        hero_ink="#FFFFFF",
        hero_muted="#94A3B8",
        canvas="#F4F5F7",
        surface="#FFFFFF",
        ink="#0B1220",
        muted="#64748B",
        border="#E2E8F0",
        positive="#15803D",
        positive_soft="#DCFCE7",
    ),
}


def skin(name: str = "indigo") -> Skin:
    return _SKINS.get(name, _SKINS["indigo"])


SKINS = tuple(_SKINS)
