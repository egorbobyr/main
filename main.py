import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_client import AIClient
from collectors import load_comments_from_json, load_comments_from_url
from models import Comment
from report import build_report, render_html
from storage import init_db, save_comments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Сканує інтернет-джерела та локальні файли, "
            "витягує згадки про моно-бізнес за допомогою AI "
            "та формує HTML-звіт."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Шлях до JSON-конфігу з джерелами та шляхами виходу.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Шлях для збереження JSON-звіту (опційно, перекриває конфіг).",
    )
    parser.add_argument(
        "--output-html",
        default=None,
        help="Шлях для збереження HTML-звіту (опційно, перекриває конфіг).",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Шлях до SQLite-бази (опційно, перекриває конфіг).",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некоректний JSON у файлі {path}: {exc}") from exc
    return payload


def collect_sources(config: dict[str, Any], ai_client: AIClient) -> list[Comment]:
    sources = config.get("sources", [])
    if not sources:
        raise ValueError("Конфіг має містити список sources")

    comments: list[Comment] = []
    for source in sources:
        source_type = source.get("type")
        platform = source.get("platform")
        if not source_type or not platform:
            raise ValueError("Кожне джерело має містити type та platform")
        if source_type == "json":
            path = Path(source["path"]).expanduser()
            comments.extend(load_comments_from_json(path, platform))
        elif source_type == "url":
            url = source["url"]
            comments.extend(load_comments_from_url(url, platform, ai_client))
        else:
            raise ValueError(f"Невідомий тип джерела: {source_type}")
    return comments


def apply_sentiment(comments: list[Comment], ai_client: AIClient) -> list[Comment]:
    for comment in comments:
        comment.sentiment = ai_client.classify_sentiment(comment.text)
    return comments


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)

    ai_client = AIClient(
        api_key=config.get("openai_api_key"),
        model=config.get("openai_model"),
    )

    comments = collect_sources(config, ai_client)
    mentions = [c for c in comments if ai_client.has_mention(c.text)]
    analyzed = apply_sentiment(mentions, ai_client)

    report = build_report(analyzed)
    report_json = json.dumps(report, ensure_ascii=False, indent=2)

    output = config.get("output", {})
    output_json = args.output_json or output.get("json_report")
    output_html = args.output_html or output.get("html_report")
    db_path = args.db_path or output.get("db_path")

    if output_json:
        Path(output_json).write_text(report_json, encoding="utf-8")
    else:
        print(report_json)

    if output_html:
        Path(output_html).write_text(render_html(report), encoding="utf-8")

    if db_path:
        db = init_db(Path(db_path))
        collected_at = datetime.utcnow().isoformat()
        save_comments(db, analyzed, collected_at)
        db.close()


if __name__ == "__main__":
    main()
