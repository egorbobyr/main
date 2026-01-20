from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional


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


@dataclass
class AIResult:
    text: str
    author: Optional[str] = None
    created_at: Optional[str] = None


class AIClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("AI_MODEL", "gpt-4o-mini")

    def has_ai(self) -> bool:
        return bool(self.api_key)

    def has_mention(self, text: str) -> bool:
        return any(pattern.search(text or "") for pattern in MENTION_PATTERNS)

    def classify_sentiment(self, text: str) -> str:
        if not text:
            return "neutral"
        if not self.has_ai():
            return self._fallback_sentiment(text)

        prompt = (
            "Класифікуй тональність відгуку про mono-business як "
            "positive, negative або neutral. Поверни лише одне слово з цих трьох."\
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ти аналізуєш клієнтські відгуки."},
                {"role": "user", "content": f"{prompt}\n\nВідгук: {text}"},
            ],
            "temperature": 0,
        }
        response = self._call_openai(payload)
        if not response:
            return self._fallback_sentiment(text)
        return self._sanitize_sentiment(response)

    def extract_mentions(self, text: str, platform: str, source_url: str) -> list[AIResult]:
        if not text:
            return []
        if not self.has_ai():
            return self._fallback_extract(text)

        prompt = (
            "Витягни з тексту коментарі або відгуки, які згадують mono-business. "
            "Поверни JSON-масив з об'єктами: text, author (якщо відомо), "
            "created_at (якщо відомо). Якщо згадок немає, поверни порожній масив."\
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ти витягуєш структуровані згадки з веб-сторінок "
                        "для аналітики бренду."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Платформа: {platform}\nURL: {source_url}\n\n{prompt}\n\n"
                        f"Текст сторінки:\n{text}"
                    ),
                },
            ],
            "temperature": 0,
        }
        response = self._call_openai(payload)
        if not response:
            return self._fallback_extract(text)
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return self._fallback_extract(text)

        results: list[AIResult] = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                mention_text = str(item.get("text", "")).strip()
                if not mention_text:
                    continue
                if not self.has_mention(mention_text):
                    continue
                results.append(
                    AIResult(
                        text=mention_text,
                        author=item.get("author"),
                        created_at=item.get("created_at"),
                    )
                )
        return results

    def _call_openai(self, payload: dict) -> Optional[str]:
        if not self.api_key:
            return None
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except Exception:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        choices = parsed.get("choices")
        if not choices:
            return None
        message = choices[0].get("message", {})
        return message.get("content")

    def _fallback_sentiment(self, text: str) -> str:
        lowered = text.lower()
        positive = sum(word in lowered for word in POSITIVE_WORDS)
        negative = sum(word in lowered for word in NEGATIVE_WORDS)
        if positive > negative:
            return "positive"
        if negative > positive:
            return "negative"
        return "neutral"

    def _sanitize_sentiment(self, response: str) -> str:
        normalized = response.strip().lower()
        if "positive" in normalized:
            return "positive"
        if "negative" in normalized:
            return "negative"
        if "neutral" in normalized:
            return "neutral"
        return "neutral"

    def _fallback_extract(self, text: str) -> list[AIResult]:
        results: list[AIResult] = []
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            if self.has_mention(candidate):
                results.append(AIResult(text=candidate))
        return results


def extract_mentions_batch(ai_client: AIClient, texts: Iterable[str]) -> list[AIResult]:
    results: list[AIResult] = []
    for text in texts:
        results.extend(ai_client.extract_mentions(text, "", ""))
    return results
