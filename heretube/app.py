from pathlib import Path
from typing import Collection, Optional

from autolink import linkify
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .downloader import Downloader
from .store import Store
from .utils import format_duration, format_thousand, plain2html

APP       = FastAPI()
CWD       = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(CWD / "templates"))

STORE      = Store()
DOWNLOADER = Downloader()

APP.mount("/static", StaticFiles(directory=str(CWD / "static")), name="static")


async def entries(
    request:      Request,
    page_title:   str,
    field_query:  str,
    ytdl_query:   str,
    page:         int             = 1,
    result_count: int             = 10,
    exclude_ids:  Collection[str] = (),
    embedded:     bool            = False,
    downloader:   Downloader      = DOWNLOADER,
):
    wanted  = result_count * page
    entries = downloader.extract_info(ytdl_query)["entries"]
    entries = [e for e in entries if e["id"] not in exclude_ids]
    entries = entries[wanted - result_count:wanted]

    for entry in entries:
        entry.update({
            "preview_url":    "/preview?video_id=%s" % entry["id"],
            "watch_url":      "/watch?v=%s" % entry["id"],
            "human_duration": format_duration(entry["duration"] or 0),
            "human_views":    format_thousand(entry["view_count"] or 0),
            "seen_class":     "seen" if entry["id"] in STORE.watched else "",
        })

    prev_url = \
        request.url.include_query_params(page=page - 1) if page > 1 else ""

    params = {
        "request":     request,
        "page_title":  page_title,
        "field_query": field_query,
        "entries":     entries,
        "page_num":    page,
        "prev_url":    prev_url,
        "next_url":    request.url.include_query_params(page = page + 1),
        "embedded":    embedded,
    }
    return TEMPLATES.TemplateResponse("results.html.jinja", params)


@APP.get("/", response_class=HTMLResponse)
async def home(request: Request, page: int  = 1, embedded: bool = False):
    search  = STORE.recommendations_query()

    if not search.strip():
        params = {"request": request}
        return TEMPLATES.TemplateResponse("results.html.jinja", params)

    return await entries(
        request     = request,
        page_title  = "HereTube",
        field_query = "",
        ytdl_query  = f"ytsearch{10 * page}:{search}",
        page        = page,
        embedded    = embedded,
    )


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

    return await entries(
        request     = request,
        page_title  = search_query,
        field_query = search_query,
        ytdl_query  = f"ytsearch{total}:{search_query}",
        page        = page,
        exclude_ids = [exclude_id] if exclude_id else [],
        embedded    = embedded,
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
    kind = "channel" if "/channel/" in str(request.url) else "user"

    return await entries(
        request     = request,
        page_title  = channel_id,
        field_query = "",
        ytdl_query  = f"https://youtube.com/{kind}/{channel_id}/videos",
        page        = page,
        exclude_ids = [exclude_id] if exclude_id else [],
        embedded    = embedded,
        downloader  = Downloader(playlistend=page * 10),
    )


@APP.get("/preview", response_class=HTMLResponse)
async def preview(request: Request, video_id: str):
    info   = await DOWNLOADER.video_info(video_id)
    params = {
        **info,
        "request":    request,
        "seen_class": "seen" if info["id"] in STORE.watched else "",
    }
    return TEMPLATES.TemplateResponse("preview.html.jinja", params)


@APP.get("/watch", response_class=HTMLResponse)
async def watch(request: Request, v: str):
    video_id = v
    info     = await DOWNLOADER.video_info(video_id)
    await STORE.record_watch(video_id, info["tags"])

    params = {**info, "request": request}
    return TEMPLATES.TemplateResponse("watch.html.jinja", params)


@APP.get("/comments", response_class=HTMLResponse)
async def comments(request: Request, video_id: str, page: int = 1):
    comments, reached_end = await DOWNLOADER.comments(video_id, page)

    for i, comment in enumerate(comments):
        comments[i].update({
            "is_reply":    "." in comment["cid"],
            "html_text":   linkify(plain2html(comment["text"])),
            "channel_url": "/channel/%s" % comment["channel"],
        })

    prev_url = \
        request.url.include_query_params(page=page - 1) if page > 1 else ""

    next_url = \
        "" if reached_end else request.url.include_query_params(page=page + 1)

    params = {
        "request":  request,
        "comments": comments,
        "page_num": page,
        "prev_url": prev_url,
        "next_url": next_url,
    }

    return TEMPLATES.TemplateResponse("comments.html.jinja", params)
