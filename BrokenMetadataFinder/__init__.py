import logging
import azure.functions as func
import json

# Define generic or placeholder indicators
GENERIC_TITLES = {"new tab", "untitled", "example page", "homepage", "home", "index", "default"}
GENERIC_DESCRIPTIONS = {"n/a", "none", "no description", "", "...", "lorem ipsum"}


def is_generic_text(text, generic_set):
    text = text.strip().lower()
    return any(
        text == g or text.startswith(g) or g in text
        for g in generic_set
    )


def evaluate_metadata(bookmark):
    title = bookmark.get("title", "").strip()
    description = bookmark.get("description", "").strip()

    title_flag = is_generic_text(title, GENERIC_TITLES)
    desc_flag = is_generic_text(description, GENERIC_DESCRIPTIONS)
    same_flag = title.lower() == description.lower() and title != ""
    short_flag = len(title.split()) <= 2 and not any(w in title.lower() for w in ["blog", "news", "guide", "tips"])

    reasons = []
    if title_flag:
        reasons.append("Generic or placeholder title")
    if desc_flag:
        reasons.append("Generic or missing description")
    if same_flag:
        reasons.append("Description identical to title")
    if short_flag:
        reasons.append("Title too short or vague")

    broken = "Yes" if reasons else "No"
    return broken, "; ".join(reasons) if reasons else "Looks OK"


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])

        results = []
        for bm in bookmarks:
            broken, reason = evaluate_metadata(bm)
            bm.update({
                "broken_metadata": broken,
                "reason": reason
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in BrokenMetadataFinder")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
