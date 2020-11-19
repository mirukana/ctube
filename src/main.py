import asyncio
import random
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from async_lru import alru_cache
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from youtube_dl import YoutubeDL

pool     = ThreadPoolExecutor(max_workers=16)
pool_run = partial(asyncio.get_event_loop().run_in_executor, pool)
ytdl     = YoutubeDL({"extract_flat": "in_playlist"})

app       = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home():
    return "hi"


@app.get("/results", response_class=HTMLResponse)
async def results(
    request: Request, search_query: str, exclude_id: Optional[str] = None,
):
    entries = ytdl.extract_info(f"ytsearch10:{search_query}")["entries"]

    for entry in entries:
        entry["preview_url"] = "/preview?video_id=%s" % entry["id"]

    entries = [e for e in entries if not exclude_id or e["id"] != exclude_id]

    params = {"request": request, "query": search_query, "entries": entries}
    return templates.TemplateResponse("results.html.jinja", params)


@app.get("/preview", response_class=HTMLResponse)
async def preview(request: Request, video_id: str):
    info   = await video_info(video_id)
    params = {
        **info,
        "request":         request,
        "small_thumbnail": fitting_thumbnail(info["thumbnails"], 256),
        "watch_url":       "/watch?v=%s" % info["id"],
    }
    return templates.TemplateResponse("preview.html.jinja", params)


@app.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str):
    video_id = v
    info     = await video_info(video_id)
    params   = {
        **info,
        "request":     request,
        "related_url": related_url(info),
    }
    return templates.TemplateResponse("watch.html.jinja", params)


@alru_cache(maxsize=4096)
async def video_info(video_id: str) -> Dict[str, Any]:
    get_info = partial(ytdl.extract_info, download=False)
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
    random.shuffle(terms)

    terms += video_info["title"].split()
    terms += set(video_info["description"].split())

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

    query = quote_plus(" ".join(terms))
    return f"/results?search_query={query}&exclude_id={video_info['id']}"
