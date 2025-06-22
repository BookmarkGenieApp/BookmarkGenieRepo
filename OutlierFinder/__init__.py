import logging
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import azure.functions as func
from collections import defaultdict

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        urls = req_body.get("bookmarks", [])
        folder_groups = defaultdict(list)
        for item in urls:
            folder_groups[item.get("folder_name", "Unknown")].append(item)

        results = []
        for folder, items in folder_groups.items():
            try:
                for item in items:
                    item["text"] = (
                        item.get("title", "") + " " +
                        item.get("description", "") + " " +
                        item.get("url_content", "")
                    ).strip()

                texts = [item["text"] for item in items if item.get("text") and "error" not in item["text"].lower()]
                if len(texts) < 3:
                    logging.warning(f"[OutlierFinder] Not enough valid texts in folder '{folder}' to perform analysis.")
                    for item in items:
                        item.update({
                            "outlier": "",
                            "outlier_score": 0.0,
                            "reason": "Not enough valid content to compute similarity"
                        })
                        results.append(item)
                    continue

                vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform(texts).toarray()
                pairwise_sim = cosine_similarity(tfidf_matrix)
                avg_similarities = pairwise_sim.mean(axis=1)
                min_index = int(np.argmin(avg_similarities))

                for idx, item in enumerate(items):
                    sim_score = avg_similarities[idx]
                    flag = (idx == min_index)
                    item.update({
                        "outlier": "Yes" if flag else "No",
                        "outlier_score": round(float(sim_score), 3),
                        "reason": "Least similar to others" if flag else "Similar to others"
                    })
                    del item["text"]
                    logging.info(
                        f"[OutlierFinder] Bookmark='{item.get('title', 'Untitled')}', "
                        f"Outlier={item['outlier']}, Score={item['outlier_score']}, Folder='{folder}'"
                    )
                    results.append(item)

            except Exception as e:
                logging.warning(f"[OutlierFinder] Folder '{folder}' processing failed: {str(e)}")
                for item in items:
                    item.update({
                        "outlier": "No",
                        "outlier_score": 0.0,
                        "reason": f"Folder error: {str(e)}"
                    })
                    results.append(item)
                continue

        return func.HttpResponse(json.dumps({"results": results}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"[OutlierFinder] Unhandled error: {str(e)}")
        return func.HttpResponse("Internal Server Error", status_code=500)