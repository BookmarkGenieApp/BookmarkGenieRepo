import logging
import azure.functions as func
import json
import re

GENERIC_TITLES = {
    "new tab", "untitled", "example page", "homepage", "home", "index", "default"
}

# NOTE: removed "." because it matches almost any real description if substring checks exist
GENERIC_DESCRIPTIONS = {
    "n/a", "na", "none", "no description", "lorem ipsum"
}

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def is_generic_text(text, generic_set):
    """
    Safer generic matcher:
    - For very short patterns (<=2 chars), only exact match.
    - For others: exact match OR whole-word match OR startswith (for 'homepage', etc).
    Avoids 'g in text' which makes '.' or 'home' overly trigger-happy.
    """
    t = _norm(text)
    if not t:
        return False

    padded = f" {t} "
    for g in generic_set:
        g = _norm(g)
        if not g:
            continue

        if len(g) <= 2:
            if t == g:
                return True
            continue

        if t == g:
            return True

        # whole-word match (prevents "home" matching "home depot" unless exact word)
        if f" {g} " in padded:
            return True

        # allow startswith for some placeholders like "homepage ..." etc
        if t.startswith(g + " "):
            return True

    return False

def extract_title_desc(bookmark):
    """
    Accept a variety of payload shapes:
    - title/description
    - website_title/website_description
    - url_content formatted like 'Title - Desc'
    """
    title = (bookmark.get("title") or bookmark.get("website_title") or "").strip()
    description = (bookmark.get("description") or bookmark.get("website_description") or "").strip()

    if (not title and not description):
        uc = (bookmark.get("url_content") or "").strip()
        # Many of your rows use url_content; try to split "Title - Desc"
        if uc and uc.lower() not in {"no title available", "error"}:
            parts = [p.strip() for p in uc.split(" - ", 1)]
            if parts:
                title = title or parts[0]
            if len(parts) == 2:
                description = description or parts[1]

    return title, description

def evaluate_metadata(bookmark):
    title, description = extract_title_desc(bookmark)

    title_n = _norm(title)
    desc_n  = _norm(description)

    title_flag = is_generic_text(title, GENERIC_TITLES)
    desc_missing = (desc_n == "")
    desc_flag = (not desc_missing) and is_generic_text(description, GENERIC_DESCRIPTIONS)
    same_flag = (title_n and desc_n and title_n == desc_n)

    # Much softer "short title" heuristic:
    # - single-word titles are COMMON and often fine (Safari exports especially)
    # - only treat as a weak signal if it's extremely short (<=2 chars) or purely non-alpha
    title_words = title.split()
    has_alpha = any(c.isalpha() for c in title)
    short_flag = False
    if title_n:
        if (len(title_words) == 1 and (len(title_n) <= 2 or not has_alpha)):
            short_flag = True
        elif (len(title_words) == 2 and len(title_n) <= 5):
            short_flag = True

    reasons = []
    score = 0

    # Strong signals
    if (not title_n) and (not desc_n):
        reasons.append("No title or description")
        score += 2

    if title_flag:
        reasons.append("Generic or placeholder title")
        score += 2

    if same_flag:
        reasons.append("Description identical to title")
        score += 1

    if desc_flag:
        reasons.append("Placeholder description")
        score += 1

    # Weak signal (don’t auto-fail on this alone)
    if short_flag:
        reasons.append("Title extremely short")
        score += 1

    # Decide: require at least 2 points to mark "Yes"
    broken = "Yes" if score >= 2 else "-"
    return broken, "; ".join(reasons) if reasons else "Looks OK"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        try:
            req_body = req.get_json()
        except Exception as e:
            logging.error(f"Failed to parse JSON: {str(e)}")
            req_body = {}

        if not isinstance(req_body, dict):
            logging.error("Parsed JSON is not a dictionary.")
            req_body = {}

        bookmarks = req_body.get("bookmarks") or req_body.get("urls") or []
        logging.info(f"✅ Received {len(bookmarks)} bookmarks")

        results = []
        for bm in bookmarks:
            broken, reason = evaluate_metadata(bm)
            bm.update({
                "broken_metadata": broken,
                "broken_metadata_reason": reason
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("💥 Error in BrokenMetadataFinder")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

