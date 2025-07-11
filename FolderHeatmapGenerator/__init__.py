import logging
import azure.functions as func
import json
from collections import Counter

def assign_heat(count):
    if count <= 4:
        return "Low", "🟢"
    elif count <= 15:
        return "Medium", "🟡"
    elif count <= 30:
        return "High", "🟠"
    else:
        return "Very High", "🔴"

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

        folder_counts = Counter(bm.get("folder_name", "⛔ MISSING") for bm in bookmarks)

        for bm in bookmarks:
            folder = bm.get("folder_name") or "⛔ MISSING"
            count = folder_counts[folder]
            heat_level, icon = assign_heat(count)
            bm["folder_load_score"] = heat_level
            bm["folder_load_score_reason"] = f"{icon} Folder '{folder}' has {count} bookmark(s)"

        return func.HttpResponse(
            json.dumps({"results": bookmarks}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.exception("Error in FolderHeatmapGenerator")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
