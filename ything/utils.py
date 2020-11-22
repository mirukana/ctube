import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from functools import partial
from typing import Any, Dict, List
from urllib.parse import quote_plus, urlencode

from .downloader import Downloader

POOL = ThreadPoolExecutor(max_workers=16)
YTDL = Downloader({"extract_flat": "in_playlist"})

pool_run = partial(asyncio.get_event_loop().run_in_executor, POOL)


async def video_info(video_id: str) -> Dict[str, Any]:
    get_info = partial(YTDL.extract_info, download=False)
    return await pool_run(get_info, video_id)  # type: ignore


def fitting_thumbnail(thumbnails: List[Dict[str, Any]], for_width: int) -> str:
    if not thumbnails:
        return "static/images/no_thumbnail.png"

    ascending_width = sorted(thumbnails, key=lambda t: t["width"])

    for thumb in ascending_width:
        if thumb["width"] >= for_width:
            return thumb["url"]

    return thumbnails[-1]["url"]


def related_url(video_info: Dict[str, Any]) -> str:
    terms = (video_info["tags"] or []).copy()

    terms += video_info["title"].split()
    terms += list(set(video_info["description"].split()))

    terms = [t.lower() for t in terms]
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

    params = urlencode({
        "search_query": quote_plus(" ".join(terms)),
        "exclude_id":   video_info["id"],
        "embedded":     True,
    })

    return f"/results?{params}"


def format_duration(seconds: float) -> str:
    return re.sub(r"^0:", "", str(timedelta(seconds=seconds)))


def format_date(date: str) -> str:
    return re.sub(r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", date)
