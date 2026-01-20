from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path
from typing import Iterable

from ai_client import AIClient, AIResult
from models import Comment


TAG_RE = re.compile(r"<[^>]+>")


def load_comments_from_json(path: Path, platform: str) -> list[Comment]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некоректний JSON у файлі {path}: {exc}") from exc

    if isinstance(payload, dict):
        items = payload.get("comments", [])
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError(
            f"Невідомий формат JSON у файлі {path}: очікувався список або словник"
        )

    comments: list[Comment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        comments.append(
            Comment(
                platform=platform,
                text=str(item.get("text", "")),
                author=item.get("author"),
                created_at=item.get("created_at"),
                comment_id=item.get("id"),
                source_url=item.get("source_url"),
                raw=item,
            )
        )
    return comments


def _strip_html(html_text: str) -> str:
    clean = TAG_RE.sub(" ", html_text)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MonoBusinessBot/1.0)",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def load_comments_from_url(url: str, platform: str, ai_client: AIClient) -> list[Comment]:
    html_text = _fetch_url(url)
    text = _strip_html(html_text)
    extracted = ai_client.extract_mentions(text, platform, url)
    return _results_to_comments(extracted, platform, url)


def _results_to_comments(
    results: Iterable[AIResult], platform: str, source_url: str
) -> list[Comment]:
    comments: list[Comment] = []
    for result in results:
        comments.append(
            Comment(
                platform=platform,
                text=result.text,
                author=result.author,
                created_at=result.created_at,
                source_url=source_url,
            )
        )
    return comments
