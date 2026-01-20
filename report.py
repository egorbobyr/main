from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable

from models import Comment


def build_report(comments: Iterable[Comment]) -> dict:
    now = datetime.utcnow().isoformat()
    grouped: dict[str, dict[str, list[Comment]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for comment in comments:
        sentiment = comment.sentiment or "neutral"
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

    totals = dict(total_counts)
    total_mentions = sum(totals.values()) or 1

    platform_stats = {}
    for platform, sentiments in summary_counts.items():
        platform_total = sum(sentiments.values()) or 1
        platform_stats[platform] = {
            "counts": sentiments,
            "percent": {
                sentiment: round(count / platform_total * 100, 2)
                for sentiment, count in sentiments.items()
            },
        }

    report = {
        "generated_at": now,
        "total": totals,
        "total_percent": {
            sentiment: round(count / total_mentions * 100, 2)
            for sentiment, count in totals.items()
        },
        "by_platform": platform_stats,
        "comments": {
            platform: {
                sentiment: [serialize_comment(c) for c in items]
                for sentiment, items in sentiments.items()
            }
            for platform, sentiments in grouped.items()
        },
    }
    return report


def serialize_comment(comment: Comment) -> dict:
    return {
        "id": comment.comment_id,
        "platform": comment.platform,
        "author": comment.author,
        "created_at": comment.created_at,
        "text": comment.text,
        "sentiment": comment.sentiment,
        "source_url": comment.source_url,
        "raw": comment.raw,
    }


def render_html(report: dict) -> str:
    total = report.get("total", {})
    total_percent = report.get("total_percent", {})
    lines = [
        "<!doctype html>",
        "<html lang=\"uk\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <title>Звіт по згадках mono-business</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 24px; }",
        "    table { border-collapse: collapse; width: 100%; margin-bottom: 24px; }",
        "    th, td { border: 1px solid #ddd; padding: 8px; }",
        "    th { background: #f4f4f4; }",
        "    .muted { color: #666; font-size: 0.9em; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Звіт по згадках моно-бізнес / mono-business</h1>",
        f"  <p class=\"muted\">Дата формування: {report.get('generated_at')}</p>",
        "  <h2>Загальна статистика</h2>",
        "  <table>",
        "    <tr><th>Тональність</th><th>Кількість</th><th>Відсоток</th></tr>",
    ]
    for sentiment in ("positive", "negative", "neutral"):
        lines.append(
            "    <tr>"
            f"<td>{sentiment}</td>"
            f"<td>{total.get(sentiment, 0)}</td>"
            f"<td>{total_percent.get(sentiment, 0)}%</td>"
            "</tr>"
        )
    lines.extend(["  </table>", "  <h2>Розподіл за платформами</h2>"])

    for platform, stats in report.get("by_platform", {}).items():
        lines.append(f"  <h3>{platform}</h3>")
        lines.append("  <table>")
        lines.append("    <tr><th>Тональність</th><th>Кількість</th><th>Відсоток</th></tr>")
        counts = stats.get("counts", {})
        percents = stats.get("percent", {})
        for sentiment in ("positive", "negative", "neutral"):
            lines.append(
                "    <tr>"
                f"<td>{sentiment}</td>"
                f"<td>{counts.get(sentiment, 0)}</td>"
                f"<td>{percents.get(sentiment, 0)}%</td>"
                "</tr>"
            )
        lines.append("  </table>")

    lines.append("  <h2>Коментарі</h2>")
    for platform, sentiments in report.get("comments", {}).items():
        lines.append(f"  <h3>{platform}</h3>")
        for sentiment in ("positive", "negative", "neutral"):
            items = sentiments.get(sentiment, [])
            if not items:
                continue
            lines.append(f"  <h4>{sentiment}</h4>")
            lines.append("  <ul>")
            for item in items:
                author = f" ({item.get('author')})" if item.get("author") else ""
                created = (
                    f" [{item.get('created_at')}]"
                    if item.get("created_at")
                    else ""
                )
                source = (
                    f" <span class=\"muted\">{item.get('source_url')}</span>"
                    if item.get("source_url")
                    else ""
                )
                lines.append(
                    "    <li>"
                    f"{item.get('text', '').strip()}{author}{created}{source}"
                    "</li>"
                )
            lines.append("  </ul>")

    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines) + "\n"
