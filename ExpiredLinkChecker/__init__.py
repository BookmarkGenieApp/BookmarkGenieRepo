import logging
import requests
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        urls = req.get_json()
        results = []

        for url in urls:
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    status = "Active"
                elif response.status_code in [404, 410] or 500 <= response.status_code < 600:
                    status = "Expired"
                else:
                    status = "Unknown"
            except Exception:
                status = "Unreachable"

            results.append({
                "url": url,
                "status": status
            })

        return func.HttpResponse(
            json.dumps(results),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in ExpiredLinkChecker: {str(e)}")
        return func.HttpResponse(
            "Internal Server Error",
            status_code=500
        )
