import logging
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import azure.functions as func
from collections import defaultdict

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("[OutlierFinder] Step 3 — TF-IDF outlier logic enabled")

    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])
        folder_groups = defaultdict(list)

        for item in bookmarks:
            folder_name = item.get("folder_name", "Unknown")
            folder_groups[folder_name].append(item)

        results = []
        for folder, items in folder_groups.items():
            texts = []
            for item in items:
                try:
                    title = str(item.get("title", ""))
                    description = str(item.get("description", ""))
                    content = str(item.get("url_content", ""))
                    item["text"] = f"{title} {description} {content}".strip()
                except Exception as e:
                    logging.warning(f"[OutlierFinder] Text build error: {e}")
                    item["text"] = ""

            texts = [item["text"] for item in items if item.get("text") and "error" not in item["text"].lower()]

            if len(texts) < 3:
                logging.warning(f"[OutlierFinder] Folder '{folder}' has insufficient valid texts.")
                for item in items:
                    item.update({
                        "outlier": "",
                        "outlier_score": 0.0,
                        "reason": "Not enough valid content to compute similarity"
                    })
                    results.append(item)
                continue

            try:
                vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform(texts).toarray()
                pairwise_sim = cosine_similarity(tfidf_matrix)
                avg_similarities = pairwise_sim.mean(axis=1)
                min_index = int(np.argmin(avg_similarities))

                for idx, item in enumerate(items):
                    sim_score = avg_similarities[idx] if idx < len(avg_similarities) else 0.0
                    flag = (idx == min_index)
                    item.update({
                        "outlier": "Yes" if flag else "No",
                        "outlier_score": round(float(sim_score), 3),
                        "reason": "Least similar to others" if flag else "Similar to others"
                    })
                    item.pop("text", None)
                    results.append(item)

            except Exception as e:
                logging.warning(f"[OutlierFinder] TF-IDF failed for folder '{folder}': {e}")
                for item in items:
                    item.update({
                        "outlier": "No",
                        "outlier_score": 0.0,
                        "reason": f"TF-IDF error: {str(e)}"
                    })
                    results.append(item)

        return func.HttpResponse(
            json.dumps({"results": results}),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"💥 OutlierFinder Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
