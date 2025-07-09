import logging
import azure.functions as func
import json
from datetime import datetime
import re

# Expanded priority keyword weights
KEYWORD_WEIGHTS = {
    # 🚀 High-priority (Productivity/Reference)
    "docs": 30,
    "documentation": 30,
    "guide": 30,
    "reference": 25,
    "urgent": 40,
    "important": 30,
    "deadline": 25,
    "how to": 20,
    "manual": 20,
    "setup": 20,
    "installation": 20,
    "step-by-step": 20,

    # 💼 Work/Admin-related
    "invoice": 20,
    "form": 15,
    "policy": 15,
    "contract": 25,
    "procedure": 20,
    "compliance": 20,
    "submission": 20,
    "meeting": 15,
    "minutes": 10,
    "report": 20,
    "task": 15,
    "project": 25,
    "review": 20,
    "update": 15,
    "presentation": 20,
    "brief": 15,
    "roadmap": 20,

    # 🧑‍🎓 Academic/Knowledge Assets
    "syllabus": 15,
    "lecture": 15,
    "thesis": 30,
    "dissertation": 30,
    "exam": 20,
    "curriculum": 15,
    "learning module": 20,

    # 🧪 Tech & Dev Resources
    "changelog": 25,
    "release notes": 20,
    "debug": 15,
    "issue tracker": 15,
    "patch": 15,
    "deprecated": -15,
    "legacy": -15,

    # 🧘 Lifestyle / Soft Topics
    "mindset": -10,
    "gratitude": -5,
    "self-care": -5,
    "wellness": -5,
    "habit": -5,

    # 📺 Media / Pop Culture
    "trailer": -10,
    "celebrity": -10,
    "gossip": -15,
    "streaming": -5,
    "episode": -5,
    "reaction": -10,

    # 🚫 Deprioritize
    "joke": -10,
    "meme": -10,
    "funny": -10,
    "entertainment": -10,
    "quote": -5,
    "inspiration": -5,
    "blog": -5,
    "news": -5,
    "opinion": -10,
    "promo": -15,
    "advertisement": -20,
    "clickbait": -25
}

PRIORITY_FOLDERS = ["work", "research", "projects", "admin"]
ARCHIVE_FOLDERS = ["archived", "old", "misc"]

def keyword_score(title, description):
    text = f"{title} {description}".lower()
    score = 0
    reasons = []
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in text:
            score += weight
            reasons.append(f"Keyword '{keyword}' ({weight:+})")
    return score, reasons

def folder_score(folder):
    folder = folder.lower()
    if folder in PRIORITY_FOLDERS:
        return 20, f"Productivity folder: '{folder}'"
    elif folder in ARCHIVE_FOLDERS:
        return -30, f"Archived folder: '{folder}'"
    return 0, ""

def recency_score(date_str):
    try:
        added_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_old = (datetime.now() - added_date).days
        if days_old <= 365:
            return 40, "Recent (< 1 year)"
        elif days_old > 1825:
            return -20, "Very old (> 5 years)"
        else:
            return 0, "Moderately old"
    except:
        return 0, "Invalid or missing date"

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

            total_score = max(0, min(100, total_score))

            bm["priority_score"] = total_score
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
