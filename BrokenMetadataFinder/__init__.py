import logging
import azure.functions as func
import json

GENERIC_TITLES = {"untitled", "new tab", "n/a", "example", "test", ""}
GENERIC_DESCRIPTIONS = {"", "n/a", "no description", "lorem ipsum", "...", "none"}

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        results = []

        for bm in bookmarks:
            reasons = []
            title = (bm.get("title") or "").strip().lower()
            description = (bm.get("description") or "").strip().lower()

            if title in GENERIC_TITLES:
                reasons.append("Generic or missing title")
            if description in GENERIC_DESCRIPTIONS:
                reasons.append("Empty or placeholder description")

            bm.update({
                "broken_metadata": "Yes" if reasons else "No",
                "reason": "; ".join(reasons) if reasons else "Title and description are valid"
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}),
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
