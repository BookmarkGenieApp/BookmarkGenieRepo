import logging
import requests
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Add debugging wrapper to surface input
        try:
            data = req.get_json()
            logging.info(f"Received payload: {data}")
        except Exception as parse_err:
            logging.error(f"JSON parse error: {str(parse_err)}")
            return func.HttpResponse(
                f"Bad Request: {str(parse_err)}",
                status_code=400
            )

        urls = data.get("urls", [])
        logging.info(f"Extracted URLs: {urls}")

        for url in urls:
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    status = "Active"
                elif response.status_code in [404, 410] or 500 <= response.status_code < 600:
                    status = "Expired"
                else:
                    status = "Unknown"
            except Exception as e:
                logging.warning(f"Error checking URL {url}: {str(e)}")
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
        logging.error(f"Top-level error: {str(e)}")
        return func.HttpResponse(
            "Internal Server Error",
            status_code=500
        )
