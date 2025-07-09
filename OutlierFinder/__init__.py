import logging
import azure.functions as func
import json
from collections import defaultdict
import string

# Synonym normalization map from categories/subcategories
SYNONYM_MAP = {
    "investment": "finance", "investments": "finance", "stocks": "finance", "stock": "finance", "etf": "finance", "crypto": "finance", "bitcoin": "finance", "nft": "finance", "budgeting": "finance", "tax": "finance", "retirement": "finance", "saving": "finance", "interest": "finance", "credit": "finance", "loan": "finance", "mortgage": "finance", "debt": "finance", "bank": "finance", "wallet": "finance", "salary": "finance", "freelance": "finance",
    "job": "career", "internship": "career", "resume": "career", "interview": "career", "linkedin": "career", "negotiation": "career", "promotion": "career", "salary": "career",
    "baking": "food", "recipe": "food", "sourdough": "food", "bread": "food", "vegan": "food", "vegetarian": "food", "keto": "food", "glutenfree": "food", "paleo": "food", "snack": "food", "dessert": "food",
    "fitness": "health", "workout": "health", "yoga": "health", "meditation": "health", "wellness": "health", "diet": "health", "mental": "health", "anxiety": "health", "sleep": "health", "supplement": "health",
    "travel": "travel", "flight": "travel", "hotel": "travel", "visa": "travel", "passport": "travel", "itinerary": "travel", "roadtrip": "travel", "camping": "travel",
    "movie": "entertainment", "tv": "entertainment", "streaming": "entertainment", "netflix": "entertainment", "disney": "entertainment", "anime": "entertainment", "comic": "entertainment", "book": "entertainment",
    "decor": "home", "furniture": "home", "appliance": "home", "renovation": "home", "storage": "home", "kitchen": "home", "bedroom": "home", "bathroom": "home",
    "gardening": "lifestyle", "plant": "lifestyle", "outdoor": "lifestyle", "balcony": "lifestyle", "diy": "lifestyle", "craft": "lifestyle", "organization": "lifestyle",
    "dating": "relationships", "marriage": "relationships", "parenting": "relationships", "friendship": "relationships", "communication": "relationships",
    "dog": "pets", "cat": "pets", "fish": "pets", "petcare": "pets", "grooming": "pets", "training": "pets",
    "productivity": "selfhelp", "motivation": "selfhelp", "goal": "selfhelp", "habit": "selfhelp", "journaling": "selfhelp", "time": "selfhelp",
    "language": "education", "course": "education", "tutorial": "education", "certificate": "education", "university": "education", "degree": "education", "exam": "education",
    "excel": "tech", "python": "tech", "javascript": "tech", "html": "tech", "css": "tech", "app": "tech", "software": "tech", "coding": "tech", "development": "tech",
    "security": "cyber", "antivirus": "cyber", "vpn": "cyber", "phishing": "cyber", "password": "cyber", "firewall": "cyber",
    "cocktail": "drinks", "mocktail": "drinks", "smoothie": "drinks", "tea": "drinks", "coffee": "drinks", "juice": "drinks"
}

def tokenize(text):
    stopwords = {
        "the", "and", "to", "from", "of", "in", "a", "an", "for", "with", "on", "at", "by", "is", "how", "what", "why",
        "guide", "beginner", "tips", "this", "that", "these", "those", "as", "are", "was", "were", "it", "its", "you",
        "your", "our", "can", "will", "be", "have", "has", "had", "but", "if", "not", "or", "about", "more", "some", "any"
    }
    words = text.lower().translate(str.maketrans('', '', string.punctuation)).split()
    normalized = set()
    for word in words:
        if word in stopwords:
            continue
        base = word.rstrip('ing').rstrip('ed').rstrip('s')
        normalized.add(SYNONYM_MAP.get(base, base))
    return normalized


def build_token_frequencies(tokenized_lists):
    freq_map = defaultdict(int)
    for token_set in tokenized_lists:
        for token in token_set:
            freq_map[token] += 1
    return freq_map


def weighted_overlap(set1, set2, freq_map):
    return sum(1 / freq_map[token] for token in (set1 & set2) if freq_map[token] > 0)


def hybrid_score(set1, set2, freq_map):
    raw_overlap = len(set1 & set2)
    weighted = weighted_overlap(set1, set2, freq_map)
    return (raw_overlap * 1.5) + weighted


def find_outlier(items):
    tokenized = [tokenize(item["text"]) for item in items]
    logging.info(f"Tokenized sets: {tokenized}")
    freq_map = build_token_frequencies(tokenized)
    logging.info(f"Frequency map: {dict(freq_map)}")
    avg_scores = []

    for i, tokens_i in enumerate(tokenized):
        total_score = 0.0
        for j, tokens_j in enumerate(tokenized):
            if i != j:
                score = hybrid_score(tokens_i, tokens_j, freq_map)
                logging.info(f"Score between item {i} and {j}: {score}")
                total_score += score
        avg_score = total_score / (len(items) - 1)
        avg_scores.append(avg_score)
        logging.info(f"Average score for item {i}: {avg_score}")

    min_index = avg_scores.index(min(avg_scores))
    logging.info(f"Minimum score index: {min_index}")
    return min_index, avg_scores


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        bookmarks = req_body.get("bookmarks", [])

        folder_groups = defaultdict(list)
        for item in bookmarks:
            folder = item.get("folder_name", "Unknown")
            title = item.get("title", "")
            description = item.get("description", "")
            combined = f"{title} {description}".lower()
            item["text"] = combined
            folder_groups[folder].append(item)

        results = []
        for folder, items in folder_groups.items():
            if len(items) < 3:
                for item in items:
                    item.update({
                        "odd_one_out": "No",
                        "outlier_score": 1.0,
                        "reason": "Not enough data to evaluate"
                    })
                    del item["text"]
                    results.append(item)
                continue

            min_index, scores = find_outlier(items)

            for idx, item in enumerate(items):
                item.update({
                    "odd_one_out": "Yes" if idx == min_index else "No",
                    "outlier_score": round(scores[idx], 3),
                    "reason": "Least similar to others" if idx == min_index else "Similar to others"
                })
                del item["text"]
                results.append(item)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in OutlierFinder pure Python version")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
