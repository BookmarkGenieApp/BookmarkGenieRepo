import logging
import requests
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
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

        results = []

        for entry in urls:
            url = entry.get("url")
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    expired_flag = False
                elif response.status_code in [404, 410] or 500 <= response.status_code < 600:
                    expired_flag = True
                else:
                    expired_flag = True  # treat unknown status as expired
            except Exception as e:
                logging.warning(f"Error checking URL {url}: {str(e)}")
                expired_flag = True  # assume expired if HEAD fails
                
            logging.info(f"Azure returning for {url}: expired_link = {expired_flag}")

            results.append({
                "url": url,
                "expired_link": expired_flag
            })

        return func.HttpResponse(
            json.dumps({
                "results": results,
                "success": True
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Top-level error: {str(e)}")
        return func.HttpResponse(
            "Internal Server Error",
            status_code=500
        )
