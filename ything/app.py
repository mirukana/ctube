from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .downloader import Downloader
from .utils import YTDL, format_duration, format_thousands, video_info

APP       = FastAPI()
CWD       = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(CWD / "templates"))

APP.mount("/static", StaticFiles(directory=str(CWD / "static")), name="static")


@APP.get("/", response_class=HTMLResponse)
async def home(request: Request):
    params = {"request": request}
    return TEMPLATES.TemplateResponse("results.html.jinja", params)


async def entries(
    request:      Request,
    page_title:   str,
    search_query: str,
    ytdl_query:   str,
    page:         int           = 1,
    exclude_id:   Optional[str] = None,
    embedded:     bool          = False,
    downloader:   Downloader    = YTDL,
):
    if not ytdl_query:
        return await home(request)

    wanted  = 10 * page
    entries = downloader.extract_info(ytdl_query)["entries"]
    entries = [e for e in entries if not exclude_id or e["id"] != exclude_id]
    entries = entries[wanted - 10:wanted]

    for entry in entries:
        entry.update({
            "preview_url":    "/preview?video_id=%s" % entry["id"],
            "watch_url":      "/watch?v=%s" % entry["id"],
            "human_duration": format_duration(entry["duration"] or 0),
            "human_views":    format_thousands(entry["view_count"] or 0),
        })

    prev_url = \
        request.url.include_query_params(page=page - 1) if page > 1 else ""

    params = {
        "request":      request,
        "page_title":   page_title,
        "search_query": search_query,
        "entries":      entries,
        "page_num":     page,
        "prev_url":     prev_url,
        "next_url":     request.url.include_query_params(page = page + 1),
        "embedded":     embedded,
    }
    return TEMPLATES.TemplateResponse("results.html.jinja", params)


@APP.get("/results", response_class=HTMLResponse)
async def results(
    request:      Request,
    search_query: str,
    page:         int           = 1,
    exclude_id:   Optional[str] = None,
    embedded:     bool          = False,
):

    wanted  = 10 * page
    total   = wanted + (1 if exclude_id else 0)

    return await entries(
        request,
        search_query,
        search_query,
        f"ytsearch{total}:{search_query}",
        page,
        exclude_id,
        embedded,
    )


@APP.get("/search", response_class=HTMLResponse)
async def search(
    request:    Request,
    q:          str,
    page:       int           = 1,
    exclude_id: Optional[str] = None,
    embedded:   bool          = False,
):
    return await results(request, q, page, exclude_id, embedded)



@APP.get("/channel/{channel_id}", response_class=HTMLResponse)
@APP.get("/channel/{channel_id}/videos", response_class=HTMLResponse)
@APP.get("/user/{channel_id}", response_class=HTMLResponse)
@APP.get("/user/{channel_id}/videos", response_class=HTMLResponse)
async def channel(
    request:    Request,
    channel_id: str,
    page:       int           = 1,
    exclude_id: Optional[str] = None,
    embedded:   bool          = False,
):
    kind       = "channel" if "/channel/" in str(request.url) else "user"
    url        = f"https://youtube.com/{kind}/{channel_id}/videos"
    downloader = Downloader(playlistend=page * 10)

    return await entries(
        request, channel_id, "", url, page, exclude_id, embedded, downloader,
    )


@APP.get("/preview", response_class=HTMLResponse)
async def preview(request: Request, video_id: str):
    info   = await video_info(video_id)
    params = {**info, "request": request}
    return TEMPLATES.TemplateResponse("preview.html.jinja", params)


@APP.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str):
    video_id = v
    info     = await video_info(video_id)
    params   = {**info, "request": request}
    return TEMPLATES.TemplateResponse("watch.html.jinja", params)
