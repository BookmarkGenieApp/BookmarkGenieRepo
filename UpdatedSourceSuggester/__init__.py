import logging
import json
import re
from datetime import datetime

import azure.functions as func

# Fast regexes (compiled once)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
URL_YEAR_RE = re.compile(r"(?:/|=)(19\d{2}|20\d{2})(?:/|&|$)")

# A few high-signal, low-maintenance “outdated tech” hints (optional but useful)
EOL_HINTS = [
    ("python 2",  "Try searching for 'Python 3 tutorial'", "🐍 Mentions deprecated version"),
    ("windows 7", "Try searching for 'Windows 11' (or latest support info)", "🪟 Mentions end-of-life OS"),
    ("internet explorer", "Try searching for 'Microsoft Edge' equivalent", "🌐 Mentions retired browser"),
]

def _pick_url(bm: dict) -> str:
    # tolerate common key variants
    return (
        (bm.get("url") or bm.get("Website Address") or bm.get("href") or bm.get("link") or "")
        .strip()
    )

def _pick_title(bm: dict) -> str:
    return (bm.get("title") or bm.get("Website Description") or bm.get("name") or "").strip()

def _suggest_from_year(text: str, current_year: int):
    years = [int(y) for y in YEAR_RE.findall(text or "")]
    if not years:
        return None
    # treat "outdated" as older than current_year - 2
    outdated = [y for y in years if y < current_year - 2]
    if not outdated:
        return None
    y = max(outdated)
    # Don't try to rewrite the whole title; just suggest a search query
    clean = YEAR_RE.sub("", text).strip()
    clean = " ".join(clean.split())
    if clean:
        return (f"Try searching for '{clean} {current_year}'",
                f"📅 Mentions outdated year ({y})")
    return (f"Try searching with year {current_year}",
            f"📅 Mentions outdated year ({y})")

def generate_suggestion(title: str, url: str):
    current_year = datetime.now().year
    title_l = (title or "").lower()
    url_s = (url or "").strip()

    # 1) URL scheme hint (cheap + often valid)
    if url_s.lower().startswith("http://"):
        return (f"Try {re.sub(r'^http://', 'https://', url_s, flags=re.I)}",
                "🔒 Uses http (https is usually preferred)")

    # 2) Year heuristics (title first, then URL)
    yr = _suggest_from_year(title or "", current_year)
    if yr:
        return yr

    uyears = [int(y) for y in URL_YEAR_RE.findall(url_s)]
    if uyears:
        outdated = [y for y in uyears if y < current_year - 2]
        if outdated:
            y = max(outdated)
            return (f"Try searching for a newer version ({current_year}) of this source",
                    f"📅 URL contains outdated year ({y})")

    # 3) Small set of deprecated-tech hints
    for needle, suggestion, reason in EOL_HINTS:
        if needle in title_l:
            return suggestion, reason

    # 4) No signal → return dash (keeps column useful)
    return "-", ""

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()

        # ✅ Accept both keys (your global standard)
        bookmarks = data.get("bookmarks") or data.get("urls") or []
        if not isinstance(bookmarks, list):
            bookmarks = []

        results = []
        for item in bookmarks:
            # Allow either dict rows or raw URL strings
            if isinstance(item, str):
                bm = {"url": item, "title": ""}
            elif isinstance(item, dict):
                bm = item
            else:
                continue

            url = _pick_url(bm)
            title = _pick_title(bm)

            suggestion, reason = generate_suggestion(title, url)

            # ✅ Return minimal payload (faster + smaller)
            results.append({
                "url": url,
                "updated_source_suggestion": suggestion,
                "updated_source_reason": reason
            })

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in UpdatedSourceSuggester")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
