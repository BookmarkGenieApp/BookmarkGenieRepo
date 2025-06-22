import logging
import azure.functions as func
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])

        folder_groups = defaultdict(list)
        for item in bookmarks:
            folder = item.get("folder_name", "Unknown")
            title = item.get("title", "") or ""
            description = item.get("description", "") or ""
            combined = f"{title} {description}".lower()
            item["text"] = combined
            folder_groups[folder].append(item)

        results = []
        for folder, items in folder_groups.items():
            try:
                ...
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

            vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(texts).toarray()
            pairwise_sim = cosine_similarity(tfidf_matrix)
            avg_similarities = pairwise_sim.mean(axis=1)

            # Find the index of the lowest average similarity
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

                # ✅ Insert logging here
                logging.info(
                    f"[OutlierFinder] Bookmark='{item.get('title', 'Untitled')}', "
                    f"Outlier={item['outlier']}, Score={item['outlier_score']}, Folder='{folder}'"
                )
                
                results.append(item)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in OutlierFinder (lowest-index version)")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
