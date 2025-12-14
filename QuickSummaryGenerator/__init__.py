import logging
import azure.functions as func
import json
import re

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def generate_summary(title: str, description: str):
    title = clean_text(title)
    description = clean_text(description)

    if description and len(description.split()) <= 20:
        return description, "📝 Used description"
    elif title and description:
        title_words = title.split()
        desc_words = description.split()
        combined = title_words[:5] + desc_words[:5]
        return clean_text(" ".join(combined)), "🧠 Used title and description"
    elif title:
        return title, "🔤 Used title"
    elif description:
        return description, "📝 Used description"
    else:
        return "N/A", "⚠️ No title or description available"

def _derive_title_desc(bm: dict):
    title = clean_text(bm.get("title"))
    desc  = clean_text(bm.get("description"))

    # Your real pipeline uses url_content like: "Title - Description"
    if not (title or desc):
        uc = clean_text(bm.get("url_content"))
        if uc:
            if " - " in uc:
                t, d = uc.split(" - ", 1)
                title = title or clean_text(t)
                desc  = desc  or clean_text(d)
            else:
                title = title or uc

    return title, desc

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks") or data.get("urls") or []

        if not bookmarks:
            return func.HttpResponse(
                json.dumps({"error": "No bookmarks or URLs provided."}),
                mimetype="application/json",
                status_code=400
            )

        out = []
        for bm in bookmarks:
            # tolerate strings
            if isinstance(bm, str):
                bm = {"url": bm}
            if not isinstance(bm, dict):
                continue

            title, description = _derive_title_desc(bm)
            summary, reason = generate_summary(title, description)

            # Canonical fields expected by Vue/Flask merge
            bm["one_line_summary"] = summary
            bm["one_line_summary_reason"] = reason

            # Back-compat aliases (your Flask also maps quick_summary -> one_line_summary)
            bm["quick_summary"] = summary
            bm["quick_summary_reason"] = reason

            out.append(bm)

        return func.HttpResponse(
            json.dumps({"results": out}, ensure_ascii=False),
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
