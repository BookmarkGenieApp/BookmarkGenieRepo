import logging
import azure.functions as func
import json
import re
from datetime import datetime

def extract_years(text):
    return re.findall(r"(19|20)\\d{2}", text)

def generate_suggestion(title):
    current_year = datetime.now().year
    years = extract_years(title)
    if years:
        outdated = [y for y in years if int(y) < current_year - 2]
        if outdated:
            latest_year = max(int(y) for y in outdated)
            suggestion = title.replace(str(latest_year), str(current_year))
            return f"Try searching for '{suggestion}'", f"Title mentions outdated year ({latest_year})"
    if "python 2" in title.lower():
        return "Try searching for 'Python 3 tutorial'", "Mentions deprecated version"
    if "iphone 8" in title.lower():
        return "Try searching for 'iPhone 14 review'", "Mentions outdated device"
    return "", ""

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        results = []

        for bm in bookmarks:
            title = bm.get("title", "") or ""
            suggestion, reason = generate_suggestion(title)
            bm.update({
                "newer_source_suggestion": suggestion,
                "reason": reason if suggestion else "No outdated indicators"
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}),
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
