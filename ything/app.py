from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .utils import (
    YTDL, fitting_thumbnail, format_duration, related_url, video_info,
)

APP       = FastAPI()
CWD       = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(CWD / "templates"))

APP.mount("/static", StaticFiles(directory=str(CWD / "static")), name="static")


@APP.get("/", response_class=HTMLResponse)
async def home(request: Request):
    params = {"request": request}
    return TEMPLATES.TemplateResponse("results.html.jinja", params)


@APP.get("/results", response_class=HTMLResponse)
async def results(
    request:      Request,
    search_query: str,
    page:         int           = 1,
    exclude_id:   Optional[str] = None,
    embedded:     bool          = False,
):

    if not search_query:
        return await home(request)

    wanted  = 10 * page
    total   = wanted + (1 if exclude_id else 0)
    entries = YTDL.extract_info(f"ytsearch{total}:{search_query}")["entries"]
    entries = [e for e in entries if not exclude_id or e["id"] != exclude_id]
    entries = entries[wanted - 10:wanted]

    for entry in entries:
        entry["preview_url"] = "/preview?video_id=%s" % entry["id"]
        entry["watch_url"]   = "/watch?v=%s" % entry["id"]

    previous = \
        request.url.include_query_params(page=page - 1) if page > 1 else ""

    params = {
        "request":      request,
        "search_query": search_query,
        "entries":      entries,
        "page_num":     page,
        "previous_url": previous,
        "next_url":     request.url.include_query_params(page = page + 1),
        "embedded":     embedded,
    }
    return TEMPLATES.TemplateResponse("results.html.jinja", params)


@APP.get("/search", response_class=HTMLResponse)
async def search(
    request:    Request,
    q:          str,
    page:       int           = 1,
    exclude_id: Optional[str] = None,
    embedded:   bool          = False,
):
    return await results(request, q, page, exclude_id, embedded)


@APP.get("/preview", response_class=HTMLResponse)
async def preview(request: Request, video_id: str):
    info   = await video_info(video_id)
    params = {
        **info,
        "request":         request,
        "small_thumbnail": fitting_thumbnail(info["thumbnails"], 256),
        "watch_url":       "/watch?v=%s" % info["id"],
        "human_duration":  format_duration(info["duration"]),
    }
    return TEMPLATES.TemplateResponse("preview.html.jinja", params)


@APP.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str):
    video_id = v
    info     = await video_info(video_id)
    params   = {
        **info,
        "request":     request,
        "related_url": related_url(info),
    }
    return TEMPLATES.TemplateResponse("watch.html.jinja", params)