import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python_packages"))

import logging
import azure.functions as func
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import numpy as np

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])

        titles = [bm.get("title", "") for bm in bookmarks]
        if not titles or len(titles) < 2:
            for bm in bookmarks:
                bm["cluster_group"] = "None"
            return func.HttpResponse(json.dumps({"results": bookmarks}), mimetype="application/json")

        vectorizer = TfidfVectorizer(stop_words='english')
        X = vectorizer.fit_transform(titles)
        similarity_matrix = cosine_similarity(X)

        clustering = DBSCAN(eps=0.3, min_samples=2, metric='precomputed')
        distance_matrix = 1 - similarity_matrix
        labels = clustering.fit_predict(distance_matrix)

        for bm, label in zip(bookmarks, labels):
            bm["cluster_group"] = f"Group {label}" if label != -1 else "None"

        return func.HttpResponse(
            json.dumps({"results": bookmarks}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.exception("Error in ClusterSimilarBookmarks")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
