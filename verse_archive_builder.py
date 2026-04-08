import json
import time
from pathlib import Path
from typing import Any, Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# =========================
# 設定區
# =========================
ZEN_KEY = "281c871874404c611e2b204dbe2bcc83"

POEM_TARGET = 5000
QUOTE_TARGET = 5000

OUTPUT_DIR = Path("data")

ENGLISH_POEMS_FILE = OUTPUT_DIR / "english_poems.json"
ENGLISH_POEMS_REVIEW_FILE = OUTPUT_DIR / "english_poems_review.json"

PHILOSOPHY_QUOTES_FILE = OUTPUT_DIR / "philosophy_quotes.json"
PHILOSOPHY_REVIEW_FILE = OUTPUT_DIR / "philosophy_quotes_review.json"

POETRY_BATCH_SIZE = 20
ZEN_REQUEST_INTERVAL = 1.5
SAVE_EVERY = 50

# 日記版面友善限制
POEM_MIN_LINES = 4
POEM_MAX_LINES = 24
POEM_MIN_TEXT_LEN = 60
POEM_MAX_TEXT_LEN = 1200

QUOTE_MIN_TEXT_LEN = 35
QUOTE_MAX_TEXT_LEN = 280


# =========================
# 共用工具
# =========================
def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "verse-archive-builder/9.0"
    })
    return session


def safe_get_json(session: requests.Session, url: str, timeout: int = 30, max_retries: int = 6) -> Any:
    last_error = None

    for attempt in range(max_retries):
        try:
            resp = session.get(url, timeout=timeout)

            if resp.status_code in (429, 500, 502, 503, 504):
                wait = min(2 ** attempt, 30)
                print(f"[HTTP {resp.status_code}] 暫時失敗，{wait} 秒後重試：{url}")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            last_error = e
            wait = min(2 ** attempt, 30)
            print(f"[Request Error] {e}，{wait} 秒後重試：{url}")
            time.sleep(wait)

    raise last_error


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[讀取失敗] {path}: {e}")
        return []


def get_nested(d: Dict[str, Any], *keys: str, default: str = "") -> str:
    cur: Any = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if isinstance(cur, str) else default


def get_lines(d: Dict[str, Any]) -> List[str]:
    content = d.get("content", {})
    lines = content.get("lines", [])
    if isinstance(lines, list):
        return [str(x).strip() for x in lines if str(x).strip()]
    return []


# =========================
# 去重 key
# =========================
def poem_key(item: Dict[str, Any]) -> str:
    author_en = get_nested(item, "author", "en").strip()
    title_en = get_nested(item, "title", "en").strip()
    return f"{author_en}|||{title_en}"


def quote_key(item: Dict[str, Any]) -> str:
    author_en = get_nested(item, "author", "en").strip()
    en = get_nested(item, "content", "en").strip()
    return f"{author_en}|||{en}"


def review_key(item: Dict[str, Any]) -> str:
    author_en = get_nested(item, "author", "en").strip()
    en = get_nested(item, "content", "en").strip()
    if not en:
        en = "\n".join(get_lines(item))
    return f"{author_en}|||{en.strip()}"


# =========================
# 正式輸出格式
# =========================
def build_poem_record(title: str, author: str, lines: List[str]) -> Dict[str, Any]:
    clean_lines = [str(line).strip() for line in lines if str(line).strip()]
    en_text = "\n".join(clean_lines)

    return {
        "type": "english_poem",
        "title": {
            "en": title.strip(),
            "cn": ""
        },
        "author": {
            "en": author.strip(),
            "cn": ""
        },
        "content": {
            "lines": clean_lines,
            "en": en_text,
            "cn": ""
        }
    }


def build_quote_record(author: str, text: str) -> Dict[str, Any]:
    clean_text = text.strip()

    return {
        "type": "philosophy",
        "title": {
            "en": "",
            "cn": ""
        },
        "author": {
            "en": author.strip(),
            "cn": ""
        },
        "content": {
            "lines": [clean_text],
            "en": clean_text,
            "cn": ""
        }
    }


# =========================
# PoetryDB 審查邏輯
# =========================
def get_poem_review_reason(poem: Dict[str, Any]) -> str | None:
    lines = get_lines(poem)
    en = get_nested(poem, "content", "en").strip()

    if not lines or not en:
        return "empty"

    if len(lines) < POEM_MIN_LINES:
        return "too_short"

    if len(lines) > POEM_MAX_LINES:
        return "too_many_lines"

    avg_len = sum(len(line.strip()) for line in lines) / max(len(lines), 1)
    if avg_len < 12:
        return "lines_too_short"

    normalized_lines = [line.strip().lower() for line in lines if line.strip()]
    if normalized_lines:
        unique_ratio = len(set(normalized_lines)) / len(normalized_lines)
        if unique_ratio < 0.6:
            return "too_repetitive"

    if len(en) < POEM_MIN_TEXT_LEN:
        return "text_too_short"

    if len(en) > POEM_MAX_TEXT_LEN:
        return "text_too_long"

    return None


# =========================
# ZenQuotes 過濾雞湯
# =========================
SOUP_PHRASES = [
    "believe in yourself",
    "never give up",
    "follow your heart",
    "dream big",
    "live your best life",
    "best version of yourself",
    "happiness is a choice",
    "you can do anything",
    "stay positive",
    "good vibes",
    "shine your light",
    "reach for the stars",
    "manifest your dreams",
    "trust the process",
]

SOUP_WORDS = {
    "success",
    "motivation",
    "motivational",
    "inspiration",
    "inspirational",
    "positive",
    "positivity",
    "mindset",
    "grind",
    "hustle",
    "winner",
    "winners",
    "winning",
    "achieve",
    "achievement",
    "greatness",
    "destiny",
    "abundance",
    "manifest",
    "dream",
    "dreams",
}

PHILOSOPHY_HINTS = {
    "death",
    "time",
    "truth",
    "soul",
    "self",
    "silence",
    "lonely",
    "loneliness",
    "suffering",
    "existence",
    "freedom",
    "meaning",
    "void",
    "memory",
    "beauty",
    "love",
    "fear",
    "god",
    "human",
    "life",
    "world",
    "mind",
    "being",
    "nothingness",
    "desire",
    "wisdom",
    "fate",
    "consciousness",
}


def get_low_quality_reason(text: str) -> str | None:
    t = text.strip().lower()

    if not t:
        return "empty"

    if len(t) < QUOTE_MIN_TEXT_LEN:
        return "too_short"

    if len(t) > QUOTE_MAX_TEXT_LEN:
        return "too_long"

    for phrase in SOUP_PHRASES:
        if phrase in t:
            return f"matched_phrase:{phrase}"

    soup_hits = sum(1 for w in SOUP_WORDS if w in t)
    philosophy_hits = sum(1 for w in PHILOSOPHY_HINTS if w in t)

    if soup_hits >= 2 and philosophy_hits == 0:
        return f"soup_words:{soup_hits}"

    if t.count("!") >= 2:
        return "too_many_exclamations"

    return None


# =========================
# PoetryDB：抓英文詩
# =========================
def fetch_poetrydb_poems(target_count: int = 5000, batch_size: int = 20) -> List[Dict[str, Any]]:
    poems = load_json_list(ENGLISH_POEMS_FILE)
    review_items = load_json_list(ENGLISH_POEMS_REVIEW_FILE)

    seen: Set[str] = {poem_key(x) for x in poems if poem_key(x) != "|||"}
    review_seen: Set[str] = {poem_key(x) for x in review_items if poem_key(x) != "|||"}
    all_seen: Set[str] = seen | review_seen

    print(f"[PoetryDB] 已有通過 {len(poems)} 筆，待審 {len(review_items)} 筆，目標 {target_count}")

    if len(poems) >= target_count:
        print(f"[PoetryDB] 已達目標 {target_count} 筆，跳過抓取")
        return poems

    session = make_session()
    added_since_save = 0

    while len(poems) < target_count:
        take = min(batch_size, target_count - len(poems))
        url = f"https://poetrydb.org/random/{take}/author,title,lines,linecount"
        data = safe_get_json(session, url)

        if not isinstance(data, list):
            print(f"[PoetryDB] 非預期回應，略過：{data}")
            time.sleep(1)
            continue

        for item in data:
            author = str(item.get("author", "")).strip()
            title = str(item.get("title", "")).strip()
            lines = item.get("lines", []) or []

            if not author or not title or not isinstance(lines, list):
                continue

            poem = build_poem_record(title, author, lines)
            key = poem_key(poem)

            if key in all_seen:
                continue

            reason = get_poem_review_reason(poem)
            if reason is not None:
                review_item = {
                    "type": poem["type"],
                    "title": poem["title"],
                    "author": poem["author"],
                    "content": poem["content"],
                    "reason": reason
                }
                review_items.append(review_item)
                review_seen.add(key)
                all_seen.add(key)
                added_since_save += 1
            else:
                poems.append(poem)
                seen.add(key)
                all_seen.add(key)
                added_since_save += 1

            if len(poems) >= target_count:
                break

            if added_since_save >= SAVE_EVERY:
                write_json(ENGLISH_POEMS_FILE, poems)
                write_json(ENGLISH_POEMS_REVIEW_FILE, review_items)
                print(f"[PoetryDB] 自動保存 通過 {len(poems)} 筆，待審 {len(review_items)} 筆")
                added_since_save = 0

        print(f"[PoetryDB] 已收集 通過 {len(poems)}/{target_count}，待審 {len(review_items)} 筆")
        time.sleep(0.5)

    write_json(ENGLISH_POEMS_FILE, poems)
    write_json(ENGLISH_POEMS_REVIEW_FILE, review_items)
    print(f"[PoetryDB] 最終保存 通過 {len(poems)} 筆，待審 {len(review_items)} 筆")
    return poems


# =========================
# ZenQuotes：抓哲學句
# =========================
def fetch_zenquotes_authors(session: requests.Session, api_key: str) -> List[Dict[str, Any]]:
    url = f"https://zenquotes.io/api/authors/{api_key}"
    data = safe_get_json(session, url)
    return data if isinstance(data, list) else []


def fetch_zenquotes_by_author(session: requests.Session, author_tag: str, api_key: str) -> List[Dict[str, Any]]:
    url = f"https://zenquotes.io/api/quotes/author/{author_tag}/{api_key}"
    data = safe_get_json(session, url)
    return data if isinstance(data, list) else []


def fetch_zenquotes_quotes(target_count: int = 5000, api_key: str = "") -> List[Dict[str, Any]]:
    if not api_key or api_key == "YOUR_ZENQUOTES_KEY":
        raise ValueError("請先填入有效的 ZEN_KEY")

    quotes = load_json_list(PHILOSOPHY_QUOTES_FILE)
    review_items = load_json_list(PHILOSOPHY_REVIEW_FILE)

    seen: Set[str] = {quote_key(x) for x in quotes if quote_key(x) != "|||"}
    review_seen: Set[str] = {review_key(x) for x in review_items if review_key(x) != "|||"}
    all_seen: Set[str] = seen | review_seen

    print(f"[ZenQuotes] 已有通過 {len(quotes)} 筆，待審 {len(review_items)} 筆，目標 {target_count}")

    if len(quotes) >= target_count:
        print(f"[ZenQuotes] 已達目標 {target_count} 筆，跳過抓取")
        return quotes

    session = make_session()
    authors = fetch_zenquotes_authors(session, api_key)
    print(f"[ZenQuotes] 作者數量：{len(authors)}")

    added_since_save = 0

    for idx, author in enumerate(authors, start=1):
        if len(quotes) >= target_count:
            break

        tag = str(author.get("t", "")).strip()
        display_name = str(author.get("a", "")).strip()

        if not tag:
            continue

        try:
            batch = fetch_zenquotes_by_author(session, tag, api_key)
        except Exception as e:
            print(f"[ZenQuotes] 抓取作者失敗 {display_name or tag}: {e}")
            time.sleep(ZEN_REQUEST_INTERVAL)
            continue

        for item in batch:
            text = str(item.get("q", "")).strip()
            quote_author = str(item.get("a", display_name)).strip()

            if not text or not quote_author:
                continue

            quote = build_quote_record(quote_author, text)
            unique = quote_key(quote)

            if unique in all_seen:
                continue

            reason = get_low_quality_reason(text)

            if reason is not None:
                review_item = {
                    "type": quote["type"],
                    "title": quote["title"],
                    "author": quote["author"],
                    "content": quote["content"],
                    "reason": reason,
                    "source_tag": tag
                }
                review_items.append(review_item)
                review_seen.add(unique)
                all_seen.add(unique)
                added_since_save += 1
            else:
                quotes.append(quote)
                seen.add(unique)
                all_seen.add(unique)
                added_since_save += 1

            if len(quotes) >= target_count:
                break

            if added_since_save >= SAVE_EVERY:
                write_json(PHILOSOPHY_QUOTES_FILE, quotes)
                write_json(PHILOSOPHY_REVIEW_FILE, review_items)
                print(f"[ZenQuotes] 自動保存 通過 {len(quotes)} 筆，待審 {len(review_items)} 筆")
                added_since_save = 0

        print(f"[ZenQuotes] {idx}/{len(authors)} 位作者，通過 {len(quotes)}/{target_count}，待審 {len(review_items)} 筆")
        time.sleep(ZEN_REQUEST_INTERVAL)

    write_json(PHILOSOPHY_QUOTES_FILE, quotes)
    write_json(PHILOSOPHY_REVIEW_FILE, review_items)
    print(f"[ZenQuotes] 最終保存 通過 {len(quotes)} 筆，待審 {len(review_items)} 筆")
    return quotes


# =========================
# 任務包裝
# =========================
def build_poems_file() -> int:
    print("開始處理英文詩（PoetryDB）...")
    poems = fetch_poetrydb_poems(target_count=POEM_TARGET, batch_size=POETRY_BATCH_SIZE)
    return len(poems)


def build_quotes_file() -> int:
    print("開始處理哲學句（ZenQuotes）...")
    quotes = fetch_zenquotes_quotes(target_count=QUOTE_TARGET, api_key=ZEN_KEY)
    return len(quotes)


# =========================
# 主流程：並行
# =========================
def main() -> None:
    tasks = {
        "poems": build_poems_file,
        "quotes": build_quotes_file,
    }

    results = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {executor.submit(func): name for name, func in tasks.items()}

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                count = future.result()
                results[name] = count
                print(f"[完成] {name}: {count} 筆")
            except Exception as e:
                print(f"[失敗] {name}: {e}")
                results[name] = None

    print("全部流程結束。")
    print(results)


if __name__ == "__main__":
    main()