import logging
import azure.functions as func
import json
from urllib.parse import urlparse

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("OutlierFinder function processed a request.")

    try:
        payload = req.get_json()
        urls = payload.get("urls", [])

        results = []
        for item in urls:
            raw_url = item.get("url") if isinstance(item, dict) else item
            parsed = urlparse(raw_url)

            # Dummy logic for demo: flag as "outlier" if domain ends with ".xyz" or path is very long
            outlier_reason = None
            if parsed.netloc.endswith(".xyz"):
                outlier_reason = "Unusual TLD"
            elif len(parsed.path) > 30:
                outlier_reason = "Suspiciously long URL path"

            results.append({
                "url": raw_url,
                "outlier": outlier_reason
            })

        return func.HttpResponse(
            json.dumps(results),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Exception in OutlierFinder: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
