import logging
import azure.functions as func
import json
import re

# Full category map (preserved from original Flask source)
CATEGORIES = {
    "Travel": {
        "Destinations": ["destination", "travel guide", "city", "country", "places", "sights"],
        "Flights": ["flight", "airline", "tickets", "aviation"],
        "Hotels": ["hotel", "accommodation", "resort", "stay"],
        "Travel Tips": ["travel tips", "packing", "itinerary"],
        "Cruises": ["cruise", "ship", "ocean travel"]
    },
    "Food & Drink": {
        "Recipes": ["recipe", "cooking", "baking", "how to bake"],
        "Restaurants": ["restaurant", "dining", "eat out", "cuisine"],
        "Nutrition": ["nutrition", "diet", "healthy eating"],
        "Drinks": ["beverages", "cocktails", "smoothies"],
        "Meal Planning": ["meal plan", "weekly menu", "cooking schedule"]
    },
    "Technology": {
        "Gadgets": ["tech", "gadget", "device", "smartphone"],
        "Programming": ["programming", "coding", "developer", "python", "javascript"],
        "AI": ["AI", "artificial intelligence", "machine learning"],
        "Cybersecurity": ["cybersecurity", "hacking", "network security"]
    },
    "Education": {
        "Online Courses": ["online course", "e-learning", "study material"],
        "Tutorials": ["tutorial", "how to", "guide"],
        "Research": ["research", "papers", "studies"],
        "Schools": ["school", "college", "university", "campus"],
        "Certifications": ["certification", "exam", "qualification"]
    },
    "Entertainment": {
        "Movies": ["movie", "film", "cinema"],
        "TV Shows": ["tv show", "series", "streaming"],
        "Music": ["music", "songs", "album", "band"],
        "Gaming": ["gaming", "video game", "console", "esports"],
        "Live Events": ["live event", "concert", "festival"]
    },
    "Health": {
        "Fitness": ["fitness", "exercise", "workout", "gym"],
        "Medicine": ["medicine", "treatment", "doctor", "pharmacy"],
        "Mental Health": ["mental health", "stress", "therapy"],
        "Alternative Therapies": ["alternative medicine", "natural remedies", "yoga"],
        "Diet Plans": ["diet", "meal plan", "nutrition"]
    },
    "Business": {
        "Marketing": ["marketing", "advertising", "SEO"],
        "Entrepreneurship": ["entrepreneurship", "startup", "business plan"],
        "HR": ["HR", "human resources", "recruitment"],
        "Industry Trends": ["industry trends", "business insights"],
        "Startups": ["startup", "funding", "business"]
    },
    "Lifestyle": {
        "Fashion": ["fashion", "style", "clothing", "trend"],
        "Home Decor": ["home decor", "interior design", "furniture"],
        "Parenting": ["parenting", "childcare", "kids"],
        "Relationships": ["relationships", "dating", "marriage"],
        "Minimalism": ["minimalism", "simple living", "declutter"]
    },
    "Sports": {
        "Football": ["football", "soccer", "goal"],
        "Tennis": ["tennis", "grand slam", "racquet"],
        "Running": ["running", "marathon", "track"],
        "Gym": ["gym", "workout", "weightlifting"],
        "Extreme Sports": ["extreme sports", "adventure", "bungee jumping"]
    },
    "Shopping": {
        "Online Stores": ["online shopping", "ecommerce", "store"],
        "Product Reviews": ["product review", "ratings", "comparison"],
        "Coupons": ["coupon", "discount", "promo code"],
        "Deals": ["deal", "bargain", "sale"],
        "Luxury Goods": ["luxury", "premium", "designer"]
    },
    "Automotive": {
        "Car Reviews": ["car", "cars", "review", "test", "drive", "road"],
        "Buying & Selling": ["buy", "sell", "used", "dealership", "trade-in", "value"],
        "Electric Vehicles": ["electric", "EV", "tesla", "hybrid", "battery", "charging"],
        "Motorsports": ["racing", "formula", "nascar", "le mans", "indycar", "track"],
        "Car Maintenance": ["repair", "oil", "brake", "service", "tuning", "detailing"],
        "Car Accessories": ["gadgets", "dashcam", "stereo", "covers", "tires", "rims", "spoiler"]
    },
    "News & Politics": {
        "Breaking News": ["breaking news", "headline", "current events"],
        "Opinion Pieces": ["opinion", "editorial", "column"],
        "Global Events": ["global event", "world news"],
        "Political Discussions": ["politics", "election", "government"]
    },
    "Environment": {
        "Climate Change": ["climate change", "global warming"],
        "Conservation": ["conservation", "wildlife", "ecology"],
        "Renewable Energy": ["renewable energy", "solar", "wind power"],
        "Wildlife": ["wildlife", "animals", "biodiversity"]
    },
    "Science": {
        "Discoveries": ["scientific discovery", "breakthrough"],
        "Space": ["space", "nasa", "rocket", "astronomy"],
        "Biology": ["biology", "genetics", "nature"],
        "Physics": ["physics", "quantum", "particles"],
        "Research Studies": ["research study", "scientific paper"]
    },
    "Arts & Culture": {
        "Literature": ["literature", "books", "novel"],
        "Visual Arts": ["painting", "art gallery", "sculpture"],
        "History": ["history", "historical", "past"],
        "Museums": ["museum", "exhibit", "artifacts"],
        "Film Festivals": ["film festival", "cinema event"]
    }
}

# allow 2+ chars so "ai", "ev" etc survive
_TOKEN_RE = re.compile(r"[a-z0-9]{2,}", re.I)

def normalize_text(*parts: str) -> str:
    raw = " ".join([p for p in parts if p])
    raw = raw.lower()
    # keep it simple: punctuation -> spaces
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return " ".join(raw.split())

def score_match(text_norm: str, tokens: set[str], keywords: list[str]) -> tuple[int, list[str]]:
    """
    Score:
      +2 for phrase match ("wind power")
      +1 for token match ("flight")
    Return (score, matched_keywords)
    """
    score = 0
    hits = []
    for kw in keywords:
        kw = kw.lower().strip()
        if not kw:
            continue
        if " " in kw:
            if kw in text_norm:
                score += 2
                hits.append(kw)
        else:
            if kw in tokens:
                score += 1
                hits.append(kw)
    return score, hits

def match_folder_category_scored(text_norm: str, hint_category: str | None = None):
    tokens = set(_TOKEN_RE.findall(text_norm))

    best = (None, None, 0, [])   # (parent, subcat, score, hits)
    second_score = 0

    cats = CATEGORIES.items()
    if hint_category and hint_category in CATEGORIES:
        cats = [(hint_category, CATEGORIES[hint_category])]

    for parent, subcats in cats:
        for subcat, keywords in subcats.items():
            score, hits = score_match(text_norm, tokens, keywords)
            if score > best[2]:
                second_score = best[2]
                best = (parent, subcat, score, hits)
            elif score > second_score:
                second_score = score

    parent, subcat, score, hits = best
    if score <= 0:
        return None, "", 0.0, "No strong match"

    # confidence similar to your Flask fast classifier style
    margin = score - second_score
    conf = 0.55 + 0.10 * score + 0.08 * max(0, margin)
    conf = max(0.0, min(0.95, conf))

    reason = f"score={score} conf={conf:.2f} hits={hits[:3]} parent={parent}"
    return parent, subcat, conf, reason


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks") or data.get("urls") or []

        # --- Safety net: validate input early (avoid 500s) ---
        if not isinstance(data, dict):
            logging.error("Bad payload: req.get_json() did not return a dict")
            return func.HttpResponse(
                json.dumps({"error": "JSON body must be an object"}),
                mimetype="application/json",
                status_code=400
            )

        if not isinstance(bookmarks, list):
            logging.error(f"Bad payload: urls/bookmarks is {type(bookmarks).__name__}, value={str(bookmarks)[:200]}")
            return func.HttpResponse(
                json.dumps({
                    "error": "urls/bookmarks must be a list",
                    "got_type": type(bookmarks).__name__
                }),
                mimetype="application/json",
                status_code=400
            )

        # validate list items
        bad = next((i for i, x in enumerate(bookmarks) if not isinstance(x, dict)), None)
        if bad is not None:
            logging.error(f"Bad payload: urls/bookmarks[{bad}] is {type(bookmarks[bad]).__name__}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Each item in urls/bookmarks must be an object",
                    "bad_index": bad,
                    "got_type": type(bookmarks[bad]).__name__
                }),
                mimetype="application/json",
                status_code=400
            )

        # --- parse flags and params ---
        only_outliers_raw = data.get("only_outliers", True)
        if isinstance(only_outliers_raw, bool):
            only_outliers = only_outliers_raw
        else:
            only_outliers = str(only_outliers_raw).strip().lower() in ("1", "true", "yes", "y")

        try:
            min_conf = float(data.get("min_conf", 0.70))
        except Exception:
            min_conf = 0.70

        # --- main loop ---
        for bm in bookmarks:
            # ✅ schema-flexible (works with your Flask rows too)
            url = bm.get("url", "")
            title = bm.get("title") or bm.get("url_content") or ""
            desc = bm.get("description", "")
            hint_cat = (bm.get("suggested_category") or "").strip()

            if only_outliers and not hint_cat:
                bm["smarter_folder"] = ""
                bm["smarter_folder_reason"] = "Skipped (not an outlier)"
                bm["smarter_folder_conf"] = 0.0
                continue

            text_norm = normalize_text(title, desc, url)
            parent, subcat, conf, reason = match_folder_category_scored(
                text_norm, hint_category=hint_cat or None
            )

            if conf >= min_conf and subcat:
                # ✅ keep existing field for merging
                bm["smarter_folder"] = f"{parent} > {subcat}" if parent else subcat
                bm["smarter_folder_reason"] = reason
                bm["smarter_folder_conf"] = conf
            else:
                bm["smarter_folder"] = ""
                bm["smarter_folder_reason"] = f"Below min_conf ({conf:.2f} < {min_conf:.2f})"
                bm["smarter_folder_conf"] = conf

        return func.HttpResponse(
            json.dumps({"results": bookmarks}),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in SmarterFolderSuggester")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )



