import logging
import json
import azure.functions as func
from collections import defaultdict

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[OutlierFinder] Step 2 — Safe text field construction")

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
                # Safely construct 'text' field from components
                try:
                    title = str(item.get("title", ""))
                    description = str(item.get("description", ""))
                    content = str(item.get("url_content", ""))
                    text = f"{title} {description} {content}".strip()
                except Exception as e:
                    logging.warning(f"[OutlierFinder] Text build error for item: {e}")
                    text = ""

                results.append({
                    "url": item.get("url", ""),
                    "folder_name": folder,
                    "text": text,
                    "outlier": "Yes" if idx == 0 else "No",
                    "reason": "Constructed text, no ML yet"
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
