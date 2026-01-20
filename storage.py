from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from models import Comment


SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    text TEXT NOT NULL,
    author TEXT,
    created_at TEXT,
    comment_id TEXT,
    source_url TEXT,
    sentiment TEXT,
    collected_at TEXT
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute(SCHEMA)
    connection.commit()
    return connection


def save_comments(
    connection: sqlite3.Connection, comments: Iterable[Comment], collected_at: str
) -> None:
    rows = [
        (
            comment.platform,
            comment.text,
            comment.author,
            comment.created_at,
            comment.comment_id,
            comment.source_url,
            comment.sentiment,
            collected_at,
        )
        for comment in comments
    ]
    connection.executemany(
        """
        INSERT INTO comments (
            platform, text, author, created_at, comment_id, source_url, sentiment, collected_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
