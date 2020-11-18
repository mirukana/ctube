import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List
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
async def results(request: Request, search_query: str):
    query   = quote_plus(search_query)
    entries = ytdl.extract_info(f"ytsearch10:{query}")["entries"]

    coros   = [video_info(entry["id"]) for entry in entries]
    details = await asyncio.gather(*coros)

    for entry, info in zip(entries, details):
        entry["small_thumbnail"] = fitting_thumbnail(info["thumbnails"], 256)
        entry["full_thumbnail"]  = largest_thumbnail(info["thumbnails"])
        entry["site_url"]        = "/watch?v=%s" % entry["id"]

    params = {"request": request, "entries": entries}
    return templates.TemplateResponse("results.html.jinja", params)


@app.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str):
    video_id = v
    info     = await video_info(video_id)
    params   = {"request": request, **info}
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


def largest_thumbnail(thumbnails: List[Dict[str, Any]]) -> str:
    if not thumbnails:
        return "static/images/no_thumbnail.png"

    return max(thumbnails, key=lambda t: t["width"])["url"]
