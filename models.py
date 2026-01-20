from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Comment:
    platform: str
    text: str
    author: Optional[str] = None
    created_at: Optional[str] = None
    comment_id: Optional[str] = None
    source_url: Optional[str] = None
    sentiment: Optional[str] = None
    raw: Optional[dict] = None
