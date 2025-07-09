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

def clean_text(text):
    return re.findall(r"\b[a-z]{3,}\b", text.lower())

def match_folder_category(text):
    for category, subcats in CATEGORIES.items():
        for subcat, keywords in subcats.items():
            for keyword in keywords:
                if keyword in text:
                    return subcat, f"Matched keyword '{keyword}' in {subcat} → {category}"
    return None, "No strong match"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks") or data.get("urls") or []

        for bm in bookmarks:
            title = bm.get("title", "")
            description = bm.get("description", "")
            combined_text = " ".join(clean_text(f"{title} {description}"))
            subcat, reason = match_folder_category(combined_text)
            bm["smarter_folder"] = subcat if subcat else ""
            bm["smarter_folder_reason"] = reason

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
