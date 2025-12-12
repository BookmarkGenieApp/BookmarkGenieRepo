import logging
import azure.functions as func
import json
import string
import time
from collections import defaultdict

# Synonym normalization map from categories/subcategories
SYNONYM_MAP = {
    "investment": "finance", "investments": "finance", "stocks": "finance", "stock": "finance",
    "etf": "finance", "crypto": "finance", "bitcoin": "finance", "nft": "finance",
    "budgeting": "finance", "tax": "finance", "retirement": "finance", "saving": "finance",
    "interest": "finance", "credit": "finance", "loan": "finance", "mortgage": "finance",
    "debt": "finance", "bank": "finance", "wallet": "finance", "salary": "finance",
    "freelance": "finance",

    "job": "career", "internship": "career", "resume": "career", "interview": "career",
    "linkedin": "career", "negotiation": "career", "promotion": "career",

    "baking": "food", "recipe": "food", "sourdough": "food", "bread": "food",
    "vegan": "food", "vegetarian": "food", "keto": "food", "glutenfree": "food",
    "paleo": "food", "snack": "food", "dessert": "food",

    "fitness": "health", "workout": "health", "yoga": "health", "meditation": "health",
    "wellness": "health", "diet": "health", "mental": "health", "anxiety": "health",
    "sleep": "health", "supplement": "health",

    "travel": "travel", "flight": "travel", "hotel": "travel", "visa": "travel",
    "passport": "travel", "itinerary": "travel", "roadtrip": "travel", "camping": "travel",

    "movie": "entertainment", "tv": "entertainment", "streaming": "entertainment",
    "netflix": "entertainment", "disney": "entertainment", "anime": "entertainment",
    "comic": "entertainment", "book": "entertainment",

    "decor": "home", "furniture": "home", "appliance": "home", "renovation": "home",
    "storage": "home", "kitchen": "home", "bedroom": "home", "bathroom": "home",

    "gardening": "lifestyle", "plant": "lifestyle", "outdoor": "lifestyle", "balcony": "lifestyle",
    "diy": "lifestyle", "craft": "lifestyle", "organization": "lifestyle",

    "dating": "relationships", "marriage": "relationships", "parenting": "relationships",
    "friendship": "relationships", "communication": "relationships",

    "dog": "pets", "cat": "pets", "fish": "pets", "petcare": "pets", "grooming": "pets",
    "training": "pets",

    "productivity": "selfhelp", "motivation": "selfhelp", "goal": "selfhelp",
    "habit": "selfhelp", "journaling": "selfhelp", "time": "selfhelp",

    "language": "education", "course": "education", "tutorial": "education",
    "certificate": "education", "university": "education", "degree": "education",
    "exam": "education",

    "excel": "tech", "python": "tech", "javascript": "tech", "html": "tech",
    "css": "tech", "app": "tech", "software": "tech", "coding": "tech",
    "development": "tech",

    "security": "cyber", "antivirus": "cyber", "vpn": "cyber", "phishing": "cyber",
    "password": "cyber", "firewall": "cyber",

    "cocktail": "drinks", "mocktail": "drinks", "smoothie": "drinks",
    "tea": "drinks", "coffee": "drinks", "juice": "drinks",
}

STOPWORDS = {
    "the", "and", "to", "from", "of", "in", "a", "an", "for", "with", "on", "at",
    "by", "is", "how", "what", "why", "guide", "beginner", "tips", "this", "that",
    "these", "those", "as", "are", "was", "were", "it", "its", "you", "your", "our",
    "can", "will", "be", "have", "has", "had", "but", "if", "not", "or", "about",
    "more", "some", "any",
}

MAX_PROCESSING_SECONDS = 10.0  # hard cap per request


def tokenize(text: str) -> set:
    """
    Simple normalisation:
    - lowercase
    - strip punctuation
    - remove stopwords
    - crude stemming (ing/ed/s)
    - map synonyms to canonical buckets
    """
    words = text.lower().translate(str.maketrans("", "", string.punctuation)).split()
    tokens = set()

    for word in words:
        if word in STOPWORDS:
            continue
        base = word.rstrip("ing").rstrip("ed").rstrip("s")
        tokens.add(SYNONYM_MAP.get(base, base))

    return tokens


def build_token_frequencies(tokenized_lists):
    freq_map = defaultdict(int)
    for token_set in tokenized_lists:
        for token in token_set:
            freq_map[token] += 1
    return freq_map


def compute_rarity_scores(tokenized_lists, freq_map):
    """
    Outlier heuristic:
    - For each item, sum 1/freq for each token it contains.
    - Items with *higher* sums contain rarer tokens overall → more "outlier-ish".
    """
    scores = []
    for tokens in tokenized_lists:
        score = 0.0
        for t in tokens:
            f = freq_map.get(t, 0)
            if f > 0:
                score += 1.0 / float(f)
        scores.append(score)
    return scores


def find_outlier_quick(items):
    """
    Lightweight outlier detector: no pairwise O(n^2) loop, just global rarity.
    Returns: (index_of_outlier, scores_list)
    """
    tokenized = [tokenize(item.get("text", "")) for item in items]
    freq_map = build_token_frequencies(tokenized)

    rarity_scores = compute_rarity_scores(tokenized, freq_map)

    if not rarity_scores:
        return None, []

    # Outlier = item with the highest rarity score
    outlier_index = max(range(len(rarity_scores)), key=lambda i: rarity_scores[i])
    return outlier_index, rarity_scores


def main(req: func.HttpRequest) -> func.HttpResponse:
    start_time = time.monotonic()
    try:
        req_body = req.get_json()
    except ValueError:
        logging.exception("OutlierFinder: invalid JSON payload")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON payload"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        bookmarks = req_body.get("bookmarks") or req_body.get("urls") or []
        if not isinstance(bookmarks, list):
            bookmarks = []

        logging.info("OutlierFinder: received %d bookmarks", len(bookmarks))

        folder_groups = defaultdict(list)
        for item in bookmarks:
            folder = item.get("folder_name", "Unknown")
            title = item.get("title", "") or ""
            description = item.get("description", "") or ""
            combined = f"{title} {description}".strip()
            item = dict(item)  # avoid mutating caller's dict in place
            item["text"] = combined
            folder_groups[folder].append(item)

        results = []

        for folder, items in folder_groups.items():
            # Time safety: if we've already spent too long, just mark remaining as normal
            if time.monotonic() - start_time > MAX_PROCESSING_SECONDS:
                logging.warning(
                    "OutlierFinder: time limit reached, marking remaining folder '%s' items as normal",
                    folder,
                )
                for item in items:
                    item.pop("text", None)
                    item.update(
                        {
                            "outlier_score": "✅ Normal",
                            "outlier_score_reason": "Time limit reached; treated as normal",
                        }
                    )
                    results.append(item)
                continue

            n_items = len(items)
            logging.info("OutlierFinder: processing folder '%s' with %d items", folder, n_items)

            if n_items < 3:
                # Not enough data to make a judgement
                for item in items:
                    item.pop("text", None)
                    item.update(
                        {
                            "outlier_score": "✅ Normal",
                            "outlier_score_reason": "Not enough data to evaluate",
                        }
                    )
                    results.append(item)
                continue

            outlier_index, scores = find_outlier_quick(items)

            if outlier_index is None:
                # Fallback: treat everything as normal
                logging.warning(
                    "OutlierFinder: could not compute outlier for folder '%s'", folder
                )
                for item in items:
                    item.pop("text", None)
                    item.update(
                        {
                            "outlier_score": "✅ Normal",
                            "outlier_score_reason": "Could not compute outlier",
                        }
                    )
                    results.append(item)
                continue

            for idx, item in enumerate(items):
                is_outlier = idx == outlier_index
                score_label = "🌠 Outlier" if is_outlier else "✅ Normal"
                reason_label = (
                    "Least similar to others (heuristic)"
                    if is_outlier
                    else "Similar to others (heuristic)"
                )

                item.pop("text", None)
                item.update(
                    {
                        "outlier_score": score_label,
                        "outlier_score_reason": reason_label,
                    }
                )
                results.append(item)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.exception("OutlierFinder: unexpected error")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
