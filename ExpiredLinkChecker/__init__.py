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

        urls = data.get("urls") or data.get("bookmarks") or []
        logging.info(f"Extracted URLs: {urls}")

        results = []

        for entry in urls:
            url = entry.get("url", "").strip()
            expired_flag = True  # Default to True in case of any error

            try:
                response = requests.head(url, timeout=5)
                status = response.status_code
                if status == 200:
                    expired_flag = False
                elif status in [404, 410] or 500 <= status < 600:
                    expired_flag = True
                else:
                    expired_flag = True  # Treat unknown status as expired
            except requests.exceptions.RequestException as e:
                logging.warning(f"[ExpiredLinkChecker] Request failed for {url}: {e}")
            except Exception as e:
                logging.warning(f"[ExpiredLinkChecker] Unexpected error for {url}: {e}")

            logging.info(f"[ExpiredLinkChecker] Result for {url} → expired_link = {expired_flag}")
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
