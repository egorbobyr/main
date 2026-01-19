import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class Comment:
    platform: str
    text: str
    author: Optional[str] = None
    created_at: Optional[str] = None
    comment_id: Optional[str] = None
    raw: Optional[dict] = None


MENTION_PATTERNS = [
    re.compile(r"\bмоно\s*-?\s*бізнес\b", re.IGNORECASE),
    re.compile(r"\bмоно\s*-?\s*бизнес\b", re.IGNORECASE),
    re.compile(r"\bмонобанк\s*-?\s*бізнес\b", re.IGNORECASE),
    re.compile(r"\bмонобанк\s*-?\s*бизнес\b", re.IGNORECASE),
    re.compile(r"\bmono\s*bank\s*-?\s*business\b", re.IGNORECASE),
    re.compile(r"\bmono\s*-?\s*business\b", re.IGNORECASE),
]

POSITIVE_WORDS = {
    "дякую",
    "супер",
    "чудово",
    "добре",
    "клас",
    "відмінно",
    "awesome",
    "great",
    "love",
    "like",
    "excellent",
    "good",
    "perfect",
    "best",
}

NEGATIVE_WORDS = {
    "жах",
    "погано",
    "жахливо",
    "проблема",
    "помилка",
    "не працює",
    "жаль",
    "hate",
    "bad",
    "terrible",
    "awful",
    "worst",
    "issue",
    "bug",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Збирає коментарі з різних платформ з локальних JSON-файлів, "
            "фільтрує згадки про моно-бізнес/моноБанк-Бізнес та будує звіт."
        )
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="PLATFORM=PATH",
        help=(
            "Джерело коментарів. Формат: platform=/шлях/до/файлу.json. "
            "Параметр можна вказати кілька разів."
        ),
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Шлях для збереження JSON-звіту (опційно).",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Шлях для збереження Markdown-звіту (опційно).",
    )
    return parser.parse_args()


def load_comments_from_json(path: Path, platform: str) -> List[Comment]:
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

    comments: List[Comment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        comment = Comment(
            platform=platform,
            text=str(item.get("text", "")),
            author=item.get("author"),
            created_at=item.get("created_at"),
            comment_id=item.get("id"),
            raw=item,
        )
        comments.append(comment)
    return comments


def has_mention(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in MENTION_PATTERNS)


def sentiment_score(text: str) -> Tuple[int, int]:
    lowered = (text or "").lower()
    positive = sum(word in lowered for word in POSITIVE_WORDS)
    negative = sum(word in lowered for word in NEGATIVE_WORDS)
    return positive, negative


def classify_sentiment(text: str) -> str:
    positive, negative = sentiment_score(text)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def filter_and_classify(comments: Iterable[Comment]) -> List[Comment]:
    return [comment for comment in comments if has_mention(comment.text)]


def build_report(comments: List[Comment]) -> dict:
    now = datetime.utcnow().isoformat()
    grouped: dict[str, dict[str, List[Comment]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for comment in comments:
        sentiment = classify_sentiment(comment.text)
        grouped[comment.platform][sentiment].append(comment)

    summary_counts = {
        platform: {
            sentiment: len(items) for sentiment, items in sentiments.items()
        }
        for platform, sentiments in grouped.items()
    }

    total_counts = Counter()
    for sentiments in summary_counts.values():
        total_counts.update(sentiments)

    serialized = {
        "generated_at": now,
        "total": dict(total_counts),
        "by_platform": summary_counts,
        "comments": {
            platform: {
                sentiment: [serialize_comment(c) for c in items]
                for sentiment, items in sentiments.items()
            }
            for platform, sentiments in grouped.items()
        },
    }
    return serialized


def serialize_comment(comment: Comment) -> dict:
    return {
        "id": comment.comment_id,
        "platform": comment.platform,
        "author": comment.author,
        "created_at": comment.created_at,
        "text": comment.text,
        "raw": comment.raw,
    }


def render_markdown(report: dict) -> str:
    lines = ["# Звіт по згадках моно-бізнес / моноБанк-Бізнес", ""]
    lines.append(f"Дата формування: {report['generated_at']}")
    lines.append("")

    lines.append("## Загальна статистика")
    totals = report.get("total", {})
    for sentiment in ("positive", "negative", "neutral"):
        lines.append(f"- {sentiment}: {totals.get(sentiment, 0)}")
    lines.append("")

    lines.append("## Розподіл за платформами")
    for platform, sentiments in report.get("by_platform", {}).items():
        lines.append(f"### {platform}")
        for sentiment in ("positive", "negative", "neutral"):
            lines.append(f"- {sentiment}: {sentiments.get(sentiment, 0)}")
        lines.append("")

    lines.append("## Коментарі")
    for platform, sentiments in report.get("comments", {}).items():
        lines.append(f"### {platform}")
        for sentiment in ("positive", "negative", "neutral"):
            items = sentiments.get(sentiment, [])
            if not items:
                continue
            lines.append(f"#### {sentiment}")
            for item in items:
                author = f" ({item.get('author')})" if item.get("author") else ""
                created = (
                    f" [{item.get('created_at')}]"
                    if item.get("created_at")
                    else ""
                )
                lines.append(f"- {item.get('text', '').strip()}{author}{created}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_sources(source_args: List[str]) -> List[Tuple[str, Path]]:
    sources: List[Tuple[str, Path]] = []
    for source in source_args:
        if "=" not in source:
            raise ValueError(
                f"Невірний формат джерела '{source}'. Очікується PLATFORM=PATH."
            )
        platform, path_str = source.split("=", 1)
        path = Path(path_str).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Файл не знайдено: {path}")
        sources.append((platform.strip(), path))
    return sources


def main() -> None:
    args = parse_args()

    sources = parse_sources(args.source)
    if not sources:
        raise SystemExit(
            "Не вказано джерел. Приклад: --source google_play=data/gp.json"
        )

    all_comments: List[Comment] = []
    for platform, path in sources:
        all_comments.extend(load_comments_from_json(path, platform))

    matched = filter_and_classify(all_comments)
    report = build_report(matched)

    json_output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(json_output, encoding="utf-8")
    else:
        print(json_output)

    if args.output_md:
        Path(args.output_md).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
