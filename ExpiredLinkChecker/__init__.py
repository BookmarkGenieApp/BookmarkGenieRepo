import logging
import json
import http.client
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Dict, List, Optional

import azure.functions as func

# --- Config -------------------------------------------------------------------

# Max time we allow for a single HTTP HEAD call
PER_URL_TIMEOUT = 3.0  # seconds

# Max redirects to follow per URL
MAX_REDIRECTS = 3

# Degree of parallelism when checking URLs
MAX_WORKERS = 20

# Schemes we don't even try to check (non-web / hopeless)
SKIP_SCHEMES = {
    "chrome",
    "edge",
    "about",
    "file",
    "javascript",
    "mailto",
    "data",
}

logger = logging.getLogger(__name__)


# --- Helpers ------------------------------------------------------------------


def normalize_url(raw: str) -> str:
    """
    Normalise input URL:

    - Trim whitespace
    - Leave non-web schemes unchanged (we'll skip them later)
    - If no scheme, assume https://
    """
    if not raw:
        return ""

    url = raw.strip()
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in SKIP_SCHEMES:
        # Non-web scheme; caller will treat as not checkable.
        return url

    if not scheme:
        # No scheme at all -> assume https
        return "https://" + url

    return url


def head_status_with_redirects(url: str,
                               timeout: float,
                               max_redirects: int) -> Optional[int]:
    """
    Perform a cheap HEAD request with a small number of redirects.
    Returns the final HTTP status code, or None on error.
    """
    current = url
    last_status: Optional[int] = None

    for _ in range(max_redirects + 1):
        parsed = urllib.parse.urlparse(current)
        scheme = (parsed.scheme or "https").lower()
        if scheme not in ("http", "https"):
            return None

        host = parsed.netloc
        if not host:
            return None

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(host, timeout=timeout)
        try:
            conn.request("HEAD", path)
            resp = conn.getresponse()
            status = resp.status
            last_status = status

            # Follow a few redirects, then stop
            if status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                if not location:
                    return status
                current = urllib.parse.urljoin(current, location)
                continue

            return status
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return last_status


def build_result(original_item: Any,
                 url: str,
                 status: Optional[int],
                 expired: bool) -> Dict[str, Any]:
    """
    Build a result row with the expected schema.
    """
    result: Dict[str, Any] = {
        "url": url,
        # Only mark True when we are clearly sure (e.g. 404/410).
        "expired_link": bool(expired),
        "status_code": status,
    }

    if isinstance(original_item, dict):
        result["title"] = original_item.get("title", "") or ""
        result["folder_name"] = original_item.get("folder_name", "") or ""

    return result


# --- Azure entrypoint --------------------------------------------------------


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            mimetype="application/json",
            status_code=400,
        )

    input_items: List[Any] = data.get("bookmarks") or data.get("urls") or []
    if not isinstance(input_items, list):
        input_items = [input_items]

    # Per-invocation cache of clearly unreachable domains
    domain_failures: Dict[str, bool] = {}
    lock = Lock()

    def process_one(item: Any) -> Optional[Dict[str, Any]]:
        url = item.get("url") if isinstance(item, dict) else item
        if not url:
            return None

        normalized = normalize_url(str(url))
        if not normalized:
            return None

        parsed = urllib.parse.urlparse(normalized)
        scheme = (parsed.scheme or "").lower()
        host = parsed.netloc

        # Skip non-web / malformed URLs early
        if scheme in SKIP_SCHEMES or not host:
            return build_result(item, str(url), None, False)

        domain = host.lower()

        # If we already know this domain is unreachable, skip the network call
        with lock:
            if domain_failures.get(domain):
                return build_result(item, str(url), None, False)

        status: Optional[int] = None
        expired = False

        try:
            status = head_status_with_redirects(
                normalized,
                timeout=PER_URL_TIMEOUT,
                max_redirects=MAX_REDIRECTS,
            )
            # "Ultra-lean" rule: only flag as expired on clear 404/410.
            expired = bool(status in (404, 410))
        except Exception:
            # Mark domain as unreachable for the rest of this invocation
            with lock:
                domain_failures[domain] = True

        return build_result(item, str(url), status, expired)

    results: List[Dict[str, Any]] = []

    try:
        # Concurrency with predictable order (we consume futures in submit order)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_one, item) for item in input_items]
            for fut in futures:
                try:
                    res = fut.result()
                except Exception:
                    logger.exception("Error processing URL in ExpiredLinkChecker")
                    res = None
                if res is not None:
                    results.append(res)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error in ExpiredLinkChecker")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
