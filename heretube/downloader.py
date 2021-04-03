import asyncio
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import (
    Any, DefaultDict, Dict, Generator, List, NamedTuple, Optional, Tuple,
    Union,
)
from urllib.parse import urlparse
from urllib.request import Request
from urllib.response import addinfourl

from autolink import linkify
from youtube_comment_downloader.downloader import download_comments
from youtube_dl import YoutubeDL

from .utils import (
    fitting_thumbnail, format_date, format_duration, format_thousand,
    plain2html, related_url,
)

Comment        = Dict[str, Any]
CommentsResult = Tuple[List[Comment], bool]  # bool = reached last comment
CommentGen     = Generator[Comment, None, None]

POOL     = ThreadPoolExecutor(max_workers=16)
pool_run = partial(asyncio.get_event_loop().run_in_executor, POOL)


class CachedRequest(NamedTuple):
    method:       str
    url:          str
    data:         Optional[bytes]
    json_headers: str


class Downloader(YoutubeDL):
    _request_cache: Dict[CachedRequest, addinfourl]       = OrderedDict()
    _comment_pages: Dict[Tuple[str, int], CommentsResult] = {}
    _comment_gens:  Dict[str, Tuple[CommentGen, int]]     = {}
    _comment_locks: Dict[Tuple[str, int], asyncio.Lock]   = \
        DefaultDict(asyncio.Lock)


    def __init__(self, **params) -> None:
        ytdl_params = {"extract_flat": "in_playlist"}
        ytdl_params.update(params)
        super().__init__(ytdl_params)


    def urlopen(self, req: Union[Request, str]) -> addinfourl:
        """Wrapper of `urlopen()` that caches Youtube requests."""

        if isinstance(req, str):
            cached_req = CachedRequest("GET", req, None, "{}")
        else:
            cached_req = CachedRequest(
                req.get_method(),
                req.full_url,
                req.data,
                json.dumps(req.headers),
            )

        if cached_req in self._request_cache:
            response = self._request_cache[cached_req]
            response.seek(0)
            return response

        response = super().urlopen(req)

        if len(self._request_cache) >= 1024:
            oldest = list(self._request_cache.keys())[0]
            del self._request_cache[oldest]

        self._request_cache[cached_req] = response
        return response


    async def video_info(self, video_id: str) -> Dict[str, Any]:
        get_info   = partial(self.extract_info, download=False)
        info: dict = await pool_run(get_info, video_id)  # type: ignore

        info.update({
            "small_thumbnail": fitting_thumbnail(info["thumbnails"], 256),
            "watch_url":       "/watch?v=%s" % info["id"],
            "related_url":     related_url(info),
            "comments_url":    "/comments?video_id=%s" % info["id"],
            "channel_url":     urlparse(info["channel_url"]).path,
            "human_duration":  format_duration(info["duration"] or 0),
            "human_views":     format_thousand(info["view_count"] or 0),
            "human_date":      format_date(info["upload_date"] or "?"),
            "likes":           format_thousand(info.get("like_count") or 0),
            "dislikes":        format_thousand(info.get("dislike_count") or 0),

            "html_description": linkify(plain2html(info["description"] or "")),
            "ratio":
                ((info["width"] or 0) / (info["height"] or 1)) or 16 / 9,
        })

        return info


    async def comments(self, video_id: str, page: int = 1) -> CommentsResult:
        if (video_id, page) in self._comment_pages:
            return self._comment_pages[video_id, page]

        async with self._comment_locks[video_id, page]:
            default          = (download_comments(video_id, sleep=0), 0)
            gen, yield_pages = self._comment_gens.setdefault(video_id, default)

            if yield_pages >= page:
                gen, yield_pages = default

            comments    = []
            reached_end = False

            for _ in range(20):
                try:
                    comments.append(next(gen))
                except StopIteration:
                    reached_end = True
                    break

            self._comment_gens[video_id] = (gen, yield_pages + 1)

            if len(self._comment_pages) >= 256:
                oldest = list(self._comment_pages.keys())[0]
                del self._comment_pages[oldest]

            self._comment_pages[video_id, page] = (comments, reached_end)

            return (comments, reached_end)
