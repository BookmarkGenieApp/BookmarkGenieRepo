import logging
import azure.functions as func
import json
import re

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_summary(title, description):
    if description and len(description.split()) <= 20:
        return clean_text(description), "Used description"
    elif title and description:
        title_words = title.split()
        desc_words = description.split()
        combined = title_words[:5] + desc_words[:5]
        return clean_text(" ".join(combined)), "Used title and description"
    elif title:
        return clean_text(title), "Used title"
    elif description:
        return clean_text(description), "Used description"
    else:
        return "", "No summary available"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        results = []

        for bm in bookmarks:
            title = bm.get("title", "") or ""
            description = bm.get("description", "") or ""
            summary, reason = generate_summary(title, description)
            bm.update({
                "one_line_summary": summary,
                "reason": reason
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.exception("Error in QuickSummaryGenerator")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
