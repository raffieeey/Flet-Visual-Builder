from __future__ import annotations

import uuid


def new_id(prefix: str = "node") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
