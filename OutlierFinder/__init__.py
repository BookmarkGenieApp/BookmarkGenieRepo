import logging
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("⚙️ OutlierFinder called")

        bookmarks = req.get_json().get("bookmarks", [])

        results = []
        for i, b in enumerate(bookmarks):
            result = {
                "title": b.get("title", ""),
                "outlier": "Yes" if i == 0 else "No",
                "reason": "Placeholder test logic"
            }
            results.append(result)

        return func.HttpResponse(
            body=json.dumps({"results": results}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"❌ Error in OutlierFinder: {e}")
        return func.HttpResponse("Internal Server Error", status_code=500)
