import html
import re
from datetime import timedelta
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


def clean_up_video_tags(*tags: str) -> List[str]:
    tags = tuple(t.lower() for t in tags)

    final_tags: List[str]            = []
    words:      Dict[str, List[str]] = {}

    for tag in tags:
        for word in tag.split():
            words.setdefault(word, []).append(tag)

    for tag in tags:
        duplicate_words = False

        for word in tag.split():
            if len(words[word]) > 2:
                shortest = min(words[word], key=len)

                if shortest not in final_tags:
                    final_tags.append(shortest)

                duplicate_words = True

        if not duplicate_words and tag not in final_tags:
            final_tags.append(tag)

    return final_tags


def related_terms(
    video_info:           Dict[str, Any],
    consider_title:       bool = True,
    consider_description: bool = True,
) -> List[str]:

    terms = clean_up_video_tags(*video_info["tags"] or [])

    for word in video_info["title"].split():
        if consider_title and word not in terms:
            terms.append(word)

    for word in video_info["description"].split():
        if consider_description and word not in terms:
            terms.append(word)

    terms = re.split(r"\s+", re.sub(r"\W", " ", " ".join(terms)).strip())

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
    }

    terms = [t for t in terms if t not in useless_words]

    if len(terms) > 9:
        terms = terms[:9]

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
