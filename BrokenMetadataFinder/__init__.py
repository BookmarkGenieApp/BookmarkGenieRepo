import logging
import azure.functions as func
import json

GENERIC_TITLES = {"new tab", "untitled", "example page", "homepage", "home", "index", "default"}
GENERIC_DESCRIPTIONS = {"n/a", "none", "no description", ".", "lorem ipsum"}

def is_generic_text(text, generic_set):
    text = (text or "").strip().lower()
    for g in generic_set:
        g = (g or "").strip().lower()
        if not g:
            continue  # critical: ignore empty patterns
        if text == g or text.startswith(g) or (g in text):
            return True
    return False

def evaluate_metadata(bookmark):
    title = bookmark.get("title", "").strip()
    description = bookmark.get("description", "").strip()

    title_flag = is_generic_text(title, GENERIC_TITLES)
    desc_missing = (description.strip() == "")
    desc_flag = (not desc_missing) and is_generic_text(description, GENERIC_DESCRIPTIONS)
    same_flag = (title != "" and description != "" and title.lower() == description.lower())
    short_flag = len(title.split()) <= 2 and not any(w in title.lower() for w in ["blog", "news", "guide", "tips"])

    reasons = []
    if title_flag:
        reasons.append("Generic or placeholder title")
    if desc_flag:
        reasons.append("Placeholder description")
    if same_flag:
        reasons.append("Description identical to title")
    if short_flag:
        reasons.append("Title too short or vague")

    broken = "Yes" if reasons else "No"
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

