import logging
import azure.functions as func
import json
from datetime import datetime
import re

# Optional: Priority keyword weights
KEYWORD_WEIGHTS = {
    "docs": 30,
    "documentation": 30,
    "guide": 30,
    "reference": 25,
    "urgent": 40,
    "important": 30,
    "deadline": 25,
    "joke": -10,
    "meme": -10,
    "funny": -10,
    "entertainment": -10,
    "inspiration": -5,
    "quote": -5
}

PRIORITY_FOLDERS = ["work", "research", "projects", "admin"]
ARCHIVE_FOLDERS = ["archived", "old", "misc"]

PRIORITY_LABELS = [
    (50, "🔥 High"),
    (10, "⚠️ Medium"),
    (0,  "❄️ Low")
]

def keyword_score(title, description):
    text = f"{title} {description}".lower()
    score = 0
    reasons = []
    for keyword, weight in KEYWORD_WEIGHTS.items():
        # Word-boundary match to avoid substring hits (e.g., "docs" in "products")
        pattern = rf"\b{re.escape(keyword)}\b"
        matches = re.findall(pattern, text)
        count = len(matches)
        if count:
            # Cap influence at 3 occurrences to avoid runaway scores
            score += weight * min(count, 3)
            reasons.append(f"{count}× '{keyword}' ({weight:+} each)")
    return score, reasons

def folder_score(folder):
    folder = (folder or "").lower()
    if folder in PRIORITY_FOLDERS:
        return 12, f"Productivity folder: '{folder}'"
    elif folder in ARCHIVE_FOLDERS:
        return -30, f"Archived folder: '{folder}'"
    return 0, ""

def recency_score(date_str):
    try:
        added_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_old = (datetime.now() - added_date).days
        if days_old <= 365:
            return 28, "Recent (< 1 year)"
        elif days_old > 1825:
            return -15, "Very old (> 5 years)"
        else:
            return 0, "Moderately old"
    except:
        return 0, None  # Suppress irrelevant reason

def label_priority(score):
    for threshold, label in PRIORITY_LABELS:
        if score >= threshold:
            return label
    return "🧊 Low"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])

        for bm in bookmarks:
            title = bm.get("title", "")
            desc = bm.get("description", "")
            folder = bm.get("folder_name", "")
            date_added = bm.get("date_added", "")

            total_score = 0
            reasons = []

            ks, kr = keyword_score(title, desc)
            total_score += ks
            reasons.extend(kr)

            fs, fr = folder_score(folder)
            total_score += fs
            if fr:
                reasons.append(fr)

            rs, rr = recency_score(date_added)
            total_score += rs
            if rr:
                reasons.append(rr)

            total_score = max(-20, min(100, total_score))

            bm["priority_score"] = label_priority(total_score)
            bm["priority_score_reason"] = "; ".join(reasons) or "No strong signals"

        return func.HttpResponse(
            json.dumps({"results": bookmarks}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.exception("Error in SmartPriorityScorer")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )



