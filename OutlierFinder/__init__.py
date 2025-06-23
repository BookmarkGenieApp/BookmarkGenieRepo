import logging
import json
import azure.functions as func
from collections import defaultdict


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[OutlierFinder-DebugStub] Starting simplified debug version")

    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])
        folder_groups = defaultdict(list)

        for item in bookmarks:
            folder_name = item.get("folder_name", "Unknown")
            folder_groups[folder_name].append(item)

        results = []
        for folder, items in folder_groups.items():
            logging.info(f"[OutlierFinder-DebugStub] Folder: {folder} with {len(items)} items")
            for idx, item in enumerate(items):
                item.update({
                    "outlier": "Yes" if idx == 0 else "No",
                    "outlier_score": 0.0,
                    "reason": "Hardcoded result for test stub"
                })
                results.append(item)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"[OutlierFinder-DebugStub] 💥 Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
