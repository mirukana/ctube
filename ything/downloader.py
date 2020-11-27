import asyncio
import json
from collections import OrderedDict
from typing import (
    Any, DefaultDict, Dict, Generator, List, NamedTuple, Optional, Tuple,
    Union,
)
from urllib.request import Request
from urllib.response import addinfourl

from youtube_dl import YoutubeDL

from .youtube_comment_downloader.downloader import download_comments

Comment        = Dict[str, Any]
CommentsResult = Tuple[List[Comment], bool]  # bool = reached last comment
CommentGen     = Generator[Comment, None, None]

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

        if len(self._request_cache) >= 4096:
            oldest = list(self._request_cache.keys())[0]
            del self._request_cache[oldest]

        self._request_cache[cached_req] = response
        return response


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
