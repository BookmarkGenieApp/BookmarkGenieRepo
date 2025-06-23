import logging
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("📡 Minimal OutlierFinder function triggered.")

    try:
        req_body = req.get_body()
        data = json.loads(req_body.decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Expected a list of items")

        results = []
        for idx, item in enumerate(data):
            url = item.get("url", "")
            if not url:
                logging.warning(f"Skipping item with missing URL: {item}")
                continue
            results.append({
                "url": url,
                "outlier": "Yes" if idx == 0 else "No"
            })

        return func.HttpResponse(
            json.dumps(results),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"💥 Exception in OutlierFinder: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
