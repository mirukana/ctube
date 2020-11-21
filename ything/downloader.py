import json
from collections import OrderedDict
from typing import Dict, NamedTuple, Optional, Union
from urllib.request import Request
from urllib.response import addinfourl

from youtube_dl import YoutubeDL


class CachedRequest(NamedTuple):
    method:       str
    url:          str
    data:         Optional[bytes]
    json_headers: str


class Downloader(YoutubeDL):
    _cache: Dict[CachedRequest, addinfourl] = OrderedDict()

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

        if cached_req in self._cache:
            response = self._cache[cached_req]
            response.seek(0)
            return response

        response = super().urlopen(req)

        if len(self._cache) >= 4096:
            oldest = list(self._cache.keys())[0]
            del self._cache[oldest]

        self._cache[cached_req] = response
        return response
