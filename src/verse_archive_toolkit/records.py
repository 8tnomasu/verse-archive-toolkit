from __future__ import annotations

from typing import Any


def get_nested(mapping: dict[str, Any], *keys: str, default: str = "") -> str:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if isinstance(current, str) else default


def get_lines(item: dict[str, Any]) -> list[str]:
    content = item.get("content", {})
    lines = content.get("lines", [])
    if isinstance(lines, list):
        return [str(line).strip() for line in lines if str(line).strip()]
    return []


def poem_key(item: dict[str, Any]) -> str:
    author = get_nested(item, "author", "en").strip()
    title = get_nested(item, "title", "en").strip()
    return f"{author}|||{title}"


def quote_key(item: dict[str, Any]) -> str:
    author = get_nested(item, "author", "en").strip()
    content = get_nested(item, "content", "en").strip()
    return f"{author}|||{content}"


def review_key(item: dict[str, Any]) -> str:
    author = get_nested(item, "author", "en").strip()
    content = get_nested(item, "content", "en").strip()
    if not content:
        content = "\n".join(get_lines(item))
    return f"{author}|||{content.strip()}"


def build_poem_record(title: str, author: str, lines: list[str]) -> dict[str, Any]:
    clean_lines = [str(line).strip() for line in lines if str(line).strip()]
    english_text = "\n".join(clean_lines)

    return {
        "type": "english_poem",
        "title": {"en": title.strip(), "cn": ""},
        "author": {"en": author.strip(), "cn": ""},
        "content": {"lines": clean_lines, "en": english_text, "cn": ""},
    }


def build_quote_record(author: str, text: str) -> dict[str, Any]:
    clean_text = text.strip()

    return {
        "type": "philosophy",
        "title": {"en": "", "cn": ""},
        "author": {"en": author.strip(), "cn": ""},
        "content": {"lines": [clean_text], "en": clean_text, "cn": ""},
    }
