import logging
import azure.functions as func
import json
from collections import defaultdict, Counter
import re

def clean_text(text):
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return words

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        bookmarks = data.get("bookmarks", [])
        folder_keywords = defaultdict(list)

        for bm in bookmarks:
            folder = bm.get("folder_name", "Unknown")
            title = bm.get("title", "") or ""
            desc = bm.get("description", "") or ""
            text = f"{title} {desc}"
            folder_keywords[folder].extend(clean_text(text))

        suggestions = {}
        for folder, words in folder_keywords.items():
            if not words:
                continue
            top_words = [word for word, _ in Counter(words).most_common(2)]
            if top_words:
                suggestion = " ".join(word.capitalize() for word in top_words)
                if suggestion.lower() not in ["default", "misc", "folder1", "unsorted", "bookmarks"]:
                    suggestions[folder] = suggestion

        for bm in bookmarks:
            folder = bm.get("folder_name", "Unknown")
            smarter_name = suggestions.get(folder)
            bm.update({
                "smarter_folder_name": smarter_name or "",
                "reason": "Based on bookmark content" if smarter_name else "No suggestion"
            })

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
