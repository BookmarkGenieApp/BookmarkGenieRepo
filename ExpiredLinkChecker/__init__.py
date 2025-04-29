import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        urls = req.get_json()
        results = []

        for url in urls:
            # Fake response (for now)
            if "google" in url:
                status = "Active"
            else:
                status = "Expired"

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
        return func.HttpResponse(
            f"Internal Server Error: {str(e)}",
            status_code=500
        )
