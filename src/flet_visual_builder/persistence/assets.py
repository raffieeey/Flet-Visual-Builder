"""Asset bytes: hash identity, size caps, base64 encoding. No Flet imports."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping

from src.flet_visual_builder.contracts import Asset, Diagnostic, Severity
from src.flet_visual_builder.model.validation import (
    MAX_ASSET_BYTES,
    MAX_TOTAL_ASSET_BYTES,
)

__all__ = [
    "MAX_ASSET_BYTES",
    "MAX_TOTAL_ASSET_BYTES",
    "decode_data",
    "deduplicate_assets",
    "encode_data",
    "sha256_hex",
    "verify_asset",
]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_data(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_data(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.b64decode(text + pad, validate=True)


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
    )


def verify_asset(
    asset: Asset,
    *,
    path: tuple[str | int, ...] = (),
) -> tuple[Diagnostic, ...]:
    errors: list[Diagnostic] = []
    digest = sha256_hex(asset.data)
    if asset.sha256.lower() != digest:
        errors.append(
            _error(
                "asset.hash",
                f"Asset {asset.id!r} sha256 does not match data",
                path=path,
            )
        )
    size = len(asset.data)
    if size > MAX_ASSET_BYTES:
        errors.append(
            _error(
                "limit.asset_bytes",
                (
                    f"limit per-asset bytes exceeded: asset {asset.id!r} is "
                    f"{size} bytes; maximum is {MAX_ASSET_BYTES}"
                ),
                path=path,
            )
        )
    if not asset.media_type:
        errors.append(
            _error(
                "asset.media_type",
                f"Asset {asset.id!r} has an empty media_type",
                path=path,
            )
        )
    return tuple(errors)


def deduplicate_assets(assets: Mapping[str, Asset]) -> dict[str, Asset]:
    """Keep the first asset for each content hash; drop later identical bytes."""
    seen: dict[str, str] = {}
    out: dict[str, Asset] = {}
    for key, asset in assets.items():
        digest = asset.sha256.lower()
        if digest in seen:
            continue
        seen[digest] = key
        out[key] = asset
    return out
