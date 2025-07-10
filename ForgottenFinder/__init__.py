import logging
import azure.functions as func
import json
from datetime import datetime

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

        for bm in bookmarks:
            date_str = bm.get("date_added") or ""
            reason = []
            score_label = "✅ Recently Added"
            days_old = "⛔ MISSING"

            if date_str:
                try:
                    added_date = datetime.strptime(date_str, "%Y-%m-%d")
                    delta = (datetime.utcnow() - added_date).days
                    days_old = delta

                    if delta > 365 * 10:
                        score_label = "🕸️ Extremely Forgotten"
                        reason.append("📅 Added over 10 years ago")
                    elif delta > 365 * 5:
                        score_label = "⏳ Likely Forgotten"
                        reason.append("📅 Added over 5 years ago")
                    elif delta > 365 * 2:
                        score_label = "🧐 Possibly Forgotten"
                        reason.append("📅 Added over 2 years ago")
                    else:
                        reason.append("📅 Added within 2 years")

                except Exception:
                    reason.append("⚠️ Invalid date format")
            else:
                reason.append("⛔ No date provided")

            if not bm.get("description"):
                reason.append("📝 No description")

            url = bm.get("url", "")
            domain = url.split("/")[2] if "//" in url else "⛔ MISSING"
            if domain in ["localhost", "example.com"]:
                reason.append("🌐 Generic domain")

            bm["forgotten_score"] = score_label
            bm["forgotten_score_reason"] = "; ".join(reason) if reason else "✅ Recent and descriptive"
            bm["days_old"] = days_old

        return func.HttpResponse(
            json.dumps({"results": bookmarks}),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in ForgottenFinder")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
