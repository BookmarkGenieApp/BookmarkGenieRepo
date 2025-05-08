import logging
import azure.functions as func
import json
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        results = []

        for bm in bookmarks:
            date_str = bm.get("date_added", "")
            reason = []
            days_old = None
            forgotten = False

            if date_str:
                try:
                    added_date = datetime.strptime(date_str, "%Y-%m-%d")
                    delta = (datetime.utcnow() - added_date).days
                    days_old = delta
                    if delta > 365:
                        forgotten = True
                        reason.append("Added over 1 year ago")
                except Exception:
                    reason.append("Invalid date format")

            if not bm.get("description"):
                forgotten = True
                reason.append("No description")

            domain = bm.get("url", "").split("/")[2] if "url" in bm and "//" in bm.get("url", "") else ""
            if domain in ["localhost", "example.com"]:
                forgotten = True
                reason.append("Generic domain")

            bm.update({
                "forgotten_flag": "Yes" if forgotten else "No",
                "reason": "; ".join(reason) if reason else "Recent and descriptive",
                "days_old": days_old
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}),
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
