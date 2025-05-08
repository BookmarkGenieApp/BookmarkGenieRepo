import logging
import azure.functions as func
import json
from datetime import datetime
import re

def keyword_score(title, description):
    text = f"{title} {description}".lower()
    score = 0
    reason_parts = []

    if any(k in text for k in ["docs", "documentation", "guide", "reference"]):
        score += 30
        reason_parts.append("Has docs/guide keywords")

    if any(k in text for k in ["joke", "meme", "funny", "entertainment"]):
        score -= 10
        reason_parts.append("Entertainment keyword")

    return score, reason_parts

def folder_score(folder):
    folder = folder.lower()
    if folder in ["work", "research"]:
        return 20, "Productivity folder"
    elif folder in ["archived", "old", "projects"]:
        return -30, "Archived folder"
    return 0, ""

def recency_score(date_str):
    try:
        added_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_old = (datetime.now() - added_date).days
        if days_old <= 365:
            return 40, "Recent"
        elif days_old > 1825:
            return -20, "Very old"
        else:
            return 0, ""
    except:
        return 0, ""

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])

        for bm in bookmarks:
            title = bm.get("title", "") or ""
            desc = bm.get("description", "") or ""
            folder = bm.get("folder_name", "") or ""
            date_added = bm.get("date_added", "") or ""

            total_score = 0
            reasons = []

            # Add scoring components
            ks, kr = keyword_score(title, desc)
            total_score += ks
            reasons.extend(kr)

            fs, fr = folder_score(folder)
            total_score += fs
            if fr: reasons.append(fr)

            rs, rr = recency_score(date_added)
            total_score += rs
            if rr: reasons.append(rr)

            # Clamp score between 0 and 100
            total_score = max(0, min(100, total_score))

            bm.update({
                "priority_score": total_score,
                "reason": "; ".join(reasons) or "No strong signals"
            })

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
