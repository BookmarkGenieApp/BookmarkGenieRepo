import logging
import azure.functions as func
import json

CATEGORY_KEYWORDS = {
    "Finance": ["investment", "investments", "stocks", "stock", "etf", "crypto", "bitcoin", "nft", "budgeting", "tax", "retirement", "saving", "interest", "credit", "loan", "mortgage", "debt", "bank", "wallet", "salary", "freelance"],
    "Career": ["job", "internship", "resume", "interview", "linkedin", "negotiation", "promotion"],
    "Food": ["baking", "recipe", "sourdough", "bread", "vegan", "vegetarian", "keto", "glutenfree", "paleo", "snack", "dessert"],
    "Health": ["fitness", "workout", "yoga", "meditation", "wellness", "diet", "mental", "anxiety", "sleep", "supplement"],
    "Travel": ["travel", "flight", "hotel", "visa", "passport", "itinerary", "roadtrip", "camping"],
    "Entertainment": ["movie", "tv", "streaming", "netflix", "disney", "anime", "comic", "book"],
    "Home": ["decor", "furniture", "appliance", "renovation", "storage", "kitchen", "bedroom", "bathroom"],
    "Lifestyle": ["gardening", "plant", "outdoor", "balcony", "diy", "craft", "organization"],
    "Relationships": ["dating", "marriage", "parenting", "friendship", "communication"],
    "Pets": ["dog", "cat", "fish", "petcare", "grooming", "training"],
    "SelfHelp": ["productivity", "motivation", "goal", "habit", "journaling", "time"],
    "Education": ["language", "course", "tutorial", "certificate", "university", "degree", "exam"],
    "Tech": ["excel", "python", "javascript", "html", "css", "app", "software", "coding", "development"],
    "Cyber": ["security", "antivirus", "vpn", "phishing", "password", "firewall"],
    "Drinks": ["cocktail", "mocktail", "smoothie", "tea", "coffee", "juice"]
}

# Normalize keyword map (case-insensitive)
CATEGORY_KEYWORDS = {
    cat: [kw.lower() for kw in kws] for cat, kws in CATEGORY_KEYWORDS.items()
}
CATEGORY_KEYWORDS = {
    cat: [kw.lower() for kw in kws] for cat, kws in CATEGORY_KEYWORDS.items()
}


def suggest_category(title, description):
    text = f"{title} {description}".lower()
    match_counts = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            match_counts[category] = count

    if not match_counts:
        return "Uncategorized", "No keyword match"

    best_match = max(match_counts, key=match_counts.get)
    reason = ", ".join([kw for kw in CATEGORY_KEYWORDS[best_match] if kw in text])
    return best_match, reason


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])

        results = []
        for bm in bookmarks:
            title = bm.get("title", "")
            description = bm.get("description", "")

            suggestion, reason = suggest_category(title, description)
            bm.update({
                "ai_folder_suggestion": suggestion,
                "reason": reason
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in FolderCategorySuggester")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
