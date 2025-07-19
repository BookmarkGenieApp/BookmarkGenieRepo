import logging
import azure.functions as func
from typing import List, Dict
import json
import re

def tokenize(text: str) -> set:
    return set(re.findall(r"\b\w{3,}\b", text.lower()))

def jaccard_similarity(set1: set, set2: set) -> float:
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0

def cluster_bookmarks(bookmarks: List[Dict], threshold: float = 0.5) -> List[List[Dict]]:
    clusters = []
    for bookmark in bookmarks:
        content = bookmark.get("url_content", "")
        token_set = tokenize(content)
        placed = False

        for cluster in clusters:
            rep = cluster[0]  # Use the first bookmark in the cluster as representative
            rep_tokens = tokenize(rep.get("url_content", ""))
            similarity = jaccard_similarity(token_set, rep_tokens)

            if similarity >= threshold:
                cluster.append(bookmark)
                placed = True
                break

        if not placed:
            clusters.append([bookmark])

    return clusters

def format_response(clusters: List[List[Dict]]) -> List[Dict]:
    response = []
    for idx, cluster in enumerate(clusters):
        for bm in cluster:
            bm_copy = bm.copy()
            bm_copy["cluster_group"] = f"Group {idx + 1}"
            response.append(bm_copy)
    return response

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for ClusterSimilarBookmarks.")

    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks") or data.get("urls") or []

        if not bookmarks or not isinstance(bookmarks, list):
            return func.HttpResponse(
                json.dumps({"error": "No valid bookmark list provided."}),
                status_code=400,
                mimetype="application/json"
            )

        clusters = cluster_bookmarks(bookmarks, threshold=0.15)
        result = format_response(clusters)

        return func.HttpResponse(
            json.dumps({"success": True, "results": result}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in ClusterSimilarBookmarks: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e), "success": False}),
            status_code=500,
            mimetype="application/json"
        )
