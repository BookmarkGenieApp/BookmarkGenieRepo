import logging
import azure.functions as func
import json
import http.client
import urllib.parse


def normalize_url(url):
    if url and not url.startswith("http"):
        return "https://" + url
    return url


def check_url_status(url):
    url = normalize_url(url)
    try:
        parsed_url = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=5)
        path = parsed_url.path or "/"
        if parsed_url.query:
            path += "?" + parsed_url.query

        conn.request("HEAD", path)
        response = conn.getresponse()
        status = response.status
        is_expired = status in {404, 410} or 500 <= status < 600
        return is_expired, status
    except Exception:
        return True, None


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        input_items = data.get("bookmarks") or data.get("urls") or []

        results = []
        for item in input_items:
            url = item.get("url") if isinstance(item, dict) else item
            if not url:
                continue

            expired, status = check_url_status(url)
            result = {
                "url": url,
                "expired_link": expired,
                "status_code": status
            }

            if isinstance(item, dict):
                result.update({
                    "title": item.get("title", ""),
                    "folder_name": item.get("folder_name", "")
                })

            results.append(result)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in ExpiredLinkChecker")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
