import logging
import json
import azure.functions as func
from collections import defaultdict

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])
        folder_groups = defaultdict(list)

        for item in bookmarks:
            folder_name = item.get("folder_name", "Unknown")
            folder_groups[folder_name].append(item)

        results = []
        for folder, items in folder_groups.items():
            for idx, item in enumerate(items):
                results.append({
                    "url": item.get("url", ""),
                    "folder_name": folder,
                    "outlier": "Yes" if idx == 0 else "No",
                    "reason": "Hardcoded result for test"
                })

        return func.HttpResponse(
            json.dumps({"results": results}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"💥 OutlierFinder Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
