import html
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlencode


def fitting_thumbnail(thumbnails: List[Dict[str, Any]], for_width: int) -> str:
    if not thumbnails:
        return "/static/images/no_thumbnail.png"

    ascending_width = sorted(thumbnails, key=lambda t: t["width"])

    for thumb in ascending_width:
        if thumb["width"] >= for_width:
            return thumb["url"]

    return thumbnails[-1]["url"]


def deduplicate_video_terms(*terms: str) -> List[str]:
    terms = tuple(t.lower() for t in terms)

    final_terms: List[str]            = []
    words:       Dict[str, List[str]] = {}

    for term in terms:
        for word in term.split():
            words.setdefault(word, []).append(term)

    for term in terms:
        duplicate_words = False

        for word in term.split():
            if len(words[word]) > 2:
                shortest = min(words[word], key=len)

                if shortest not in final_terms:
                    final_terms.append(shortest)

                duplicate_words = True

        if not duplicate_words and term not in final_terms:
            final_terms.append(term)

    return final_terms


def related_terms(video_info: Dict[str, Any], max_terms: int = 9) -> List[str]:
    useless_words = {
        "ourselves", "hers", "between", "yourself", "but", "again", "there",
        "about", "once", "during", "out", "very", "having", "with", "they",
        "own", "an", "be", "some", "for", "do", "its", "yours", "such",
        "into", "of", "most", "itself", "other", "off", "is", "s", "am", "or",
        "who", "as", "from", "him", "each", "the", "themselves", "until",
        "below", "are", "we", "these", "your", "his", "through", "don", "nor",
        "me", "were", "her", "more", "himself", "this", "down", "should",
        "our", "their", "while", "above", "both", "up", "to", "ours", "had",
        "she", "all", "no", "when", "at", "any", "before", "them", "same",
        "and", "been", "have", "in", "will", "on", "does", "yourselves",
        "then", "that", "because", "what", "over", "why", "so", "can", "did",
        "not", "now", "under", "he", "you", "herself", "has", "just", "where",
        "too", "only", "myself", "which", "those", "i", "after", "few", "whom",
        "t", "being", "if", "theirs", "my", "against", "a", "by", "doing",
        "it", "how", "further", "was", "here", "than",
    }  # taken from NLTK

    def cleanup(term: str) -> List[str]:
        # Blank out special characters like punctuation and remove casing
        word = re.sub(r"\W", " ", term).lower()

        # Normalize whitespace
        word = re.sub(r"\s+", " ", word).strip()

        # Split CJK "words" that are combined with latin without whitespace
        parts = [t for t in re.split(r"([\u4e00-\u9fff]+)", word) if t.strip()]

        # Try to exclude words that aren't topics/subjects/nouns
        return [p for p in parts if p not in useless_words]

    terms = []

    for tag in (video_info["tags"] or []):
        for term in cleanup(tag):
            terms.append(term)

    for word in video_info["title"].split():
        for term in cleanup(word):
            if term not in terms:
                terms.append(term)

    terms = deduplicate_video_terms(*terms)

    if len(terms) > max_terms:
        terms = terms[:max_terms]

    return terms


def related_videos_url(video_info: Dict[str, Any]) -> str:
    return "/results?%s" % urlencode({
        "search_query": " ".join(related_terms(video_info)),
        "exclude_id":   video_info["id"],
        "embedded":     True,
    })


def format_duration(seconds: float) -> str:
    return re.sub(r"^0:", "", str(timedelta(seconds=seconds)))


def format_date(ytdl_date: str) -> str:  # ytdl format example: 20200102
    return re.sub(r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", ytdl_date)


def format_thousand(num: float) -> str:
    num       = float("{: .3g}".format(num))
    magnitude = 0

    while abs(num) >= 1000:
        magnitude += 1
        num       /= 1000.0

    return "{}{}".format(
        "{:f}".format(int(num)).rstrip("0").rstrip("."),
        ["", "K", "M", "B", "T"][magnitude],
    )


def plain2html(text: str) -> str:
    return html.escape(text).replace("\n", "<br>").replace("\t", "&nbsp;" * 4)


def json_dumps(data: Any) -> str:
    def defaults(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()

        raise TypeError(f"Cannot dump {value}")

    return json.dumps(data, ensure_ascii=False, default=defaults)
