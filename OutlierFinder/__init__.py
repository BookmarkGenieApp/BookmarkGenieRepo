import logging
import azure.functions as func
import json
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
            texts = [item["text"] for item in items]

            if len(texts) < 3:
                for item in items:
                    item.update({
                        "odd_one_out": "No",
                        "outlier_score": 1.0,
                        "reason": "Not enough data to evaluate"
                    })
                    del item["text"]
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
                    "odd_one_out": "Yes" if flag else "No",
                    "outlier_score": round(float(sim_score), 3),
                    "reason": "Least similar to others" if flag else "Similar to others"
                })
                del item["text"]
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
