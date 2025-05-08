import logging
import azure.functions as func
import json

CATEGORY_KEYWORDS = {
    "Travel - Destinations": ["destination", "travel guide", "city", "country", "places", "sights"],
    "Travel - Flights": ["flight", "airline", "tickets", "aviation"],
    "Travel - Hotels": ["hotel", "accommodation", "resort", "stay"],
    "Travel - Travel Tips": ["travel tips", "packing", "itinerary"],
    "Travel - Cruises": ["cruise", "ship", "ocean travel"],

    "Food & Drink - Recipes": ["recipe", "cooking", "baking", "how to bake"],
    "Food & Drink - Restaurants": ["restaurant", "dining", "eat out", "cuisine"],
    "Food & Drink - Nutrition": ["nutrition", "diet", "healthy eating"],
    "Food & Drink - Drinks": ["beverages", "cocktails", "smoothies"],
    "Food & Drink - Meal Planning": ["meal plan", "weekly menu", "cooking schedule"],

    "Technology - Gadgets": ["tech", "gadget", "device", "smartphone"],
    "Technology - Programming": ["programming", "coding", "developer", "python", "javascript"],
    "Technology - AI": ["AI", "artificial intelligence", "machine learning"],
    "Technology - Cybersecurity": ["cybersecurity", "hacking", "network security"],

    "Education - Online Courses": ["online course", "e-learning", "study material"],
    "Education - Tutorials": ["tutorial", "how to", "guide"],
    "Education - Research": ["research", "papers", "studies"],
    "Education - Schools": ["school", "college", "university", "campus"],
    "Education - Certifications": ["certification", "exam", "qualification"],

    "Entertainment - Movies": ["movie", "film", "cinema"],
    "Entertainment - TV Shows": ["tv show", "series", "streaming"],
    "Entertainment - Music": ["music", "songs", "album", "band"],
    "Entertainment - Gaming": ["gaming", "video game", "console", "esports"],
    "Entertainment - Live Events": ["live event", "concert", "festival"],

    "Health - Fitness": ["fitness", "exercise", "workout", "gym"],
    "Health - Medicine": ["medicine", "treatment", "doctor", "pharmacy"],
    "Health - Mental Health": ["mental health", "stress", "therapy"],
    "Health - Alternative Therapies": ["alternative medicine", "natural remedies", "yoga"],
    "Health - Diet Plans": ["diet", "meal plan", "nutrition"],

    "Business - Marketing": ["marketing", "advertising", "SEO"],
    "Business - Entrepreneurship": ["entrepreneurship", "startup", "business plan"],
    "Business - HR": ["HR", "human resources", "recruitment"],
    "Business - Industry Trends": ["industry trends", "business insights"],
    "Business - Startups": ["startup", "funding", "business"],

    "Lifestyle - Fashion": ["fashion", "style", "clothing", "trend"],
    "Lifestyle - Home Decor": ["home decor", "interior design", "furniture"],
    "Lifestyle - Parenting": ["parenting", "childcare", "kids"],
    "Lifestyle - Relationships": ["relationships", "dating", "marriage"],
    "Lifestyle - Minimalism": ["minimalism", "simple living", "declutter"],

    "Sports - Football": ["football", "soccer", "goal"],
    "Sports - Tennis": ["tennis", "grand slam", "racquet"],
    "Sports - Running": ["running", "marathon", "track"],
    "Sports - Gym": ["gym", "workout", "weightlifting"],
    "Sports - Extreme Sports": ["extreme sports", "adventure", "bungee jumping"],

    "Shopping - Online Stores": ["online shopping", "ecommerce", "store"],
    "Shopping - Product Reviews": ["product review", "ratings", "comparison"],
    "Shopping - Coupons": ["coupon", "discount", "promo code"],
    "Shopping - Deals": ["deal", "bargain", "sale"],
    "Shopping - Luxury Goods": ["luxury", "premium", "designer"],

    "Automotive - Car Reviews": ["car", "cars", "review", "test", "drive", "road"],
    "Automotive - Buying & Selling": ["buy", "sell", "used", "dealership", "trade-in", "value"],
    "Automotive - Electric Vehicles": ["electric", "EV", "tesla", "hybrid", "battery", "charging"],
    "Automotive - Motorsports": ["racing", "formula", "nascar", "le mans", "indycar", "track"],
    "Automotive - Car Maintenance": ["repair", "oil", "brake", "service", "tuning", "detailing"],
    "Automotive - Car Accessories": ["gadgets", "dashcam", "stereo", "covers", "tires", "rims", "spoiler"],

    "News & Politics - Breaking News": ["breaking news", "headline", "current events"],
    "News & Politics - Opinion Pieces": ["opinion", "editorial", "column"],
    "News & Politics - Global Events": ["global event", "world news"],
    "News & Politics - Political Discussions": ["politics", "election", "government"],

    "Environment - Climate Change": ["climate change", "global warming"],
    "Environment - Conservation": ["conservation", "wildlife", "ecology"],
    "Environment - Renewable Energy": ["renewable energy", "solar", "wind power"],
    "Environment - Wildlife": ["wildlife", "animals", "biodiversity"],

    "Science - Discoveries": ["scientific discovery", "breakthrough"],
    "Science - Space": ["space", "nasa", "rocket", "astronomy"],
    "Science - Biology": ["biology", "genetics", "nature"],
    "Science - Physics": ["physics", "quantum", "particles"],
    "Science - Research Studies": ["research study", "scientific paper"],

    "Arts & Culture - Literature": ["literature", "books", "novel"],
    "Arts & Culture - Visual Arts": ["painting", "art gallery", "sculpture"],
    "Arts & Culture - History": ["history", "historical", "past"],
    "Arts & Culture - Museums": ["museum", "exhibit", "artifacts"],
    "Arts & Culture - Film Festivals": ["film festival", "cinema event"]
}

def match_category(text):
    text = text.lower()
    score = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        match_count = sum(1 for word in keywords if word in text)
        if match_count > 0:
            score[category] = match_count
    if score:
        best_match = max(score, key=score.get)
        matched_words = [kw for kw in CATEGORY_KEYWORDS[best_match] if kw in text]
        return best_match, matched_words
    return "", []

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        results = []

        for bm in bookmarks:
            title = bm.get("title", "") or ""
            description = bm.get("description", "") or ""
            combined_text = f"{title} {description}"
            suggestion, words = match_category(combined_text)

            bm.update({
                "ai_folder_suggestion": suggestion,
                "reason": f"Matched keywords: {', '.join(words)}" if words else "No strong match"
            })
            results.append(bm)

        return func.HttpResponse(
            json.dumps({"results": results}),
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
