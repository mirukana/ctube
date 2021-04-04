from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Collection, Dict, List, Optional

import aiofiles
import orjson
from appdirs import user_data_dir
from dateutil.parser import parse as parse_date

from .utils import clean_up_video_tags

ZERO_DATE = datetime.fromtimestamp(0)


@dataclass
class Store:
    _seen: Optional[Dict[str, datetime]] = field(init=False, default=None)

    _tags: Optional[Dict[str, List[datetime]]] = field(
        init=False, default=None,
    )


    def __post_init__(self) -> None:
        self.seen_file.parent.mkdir(parents=True, exist_ok=True)
        self.tags_file.parent.mkdir(parents=True, exist_ok=True)


    @property
    def folder(self) -> Path:
        return Path(user_data_dir("ctube", roaming=True))


    @property
    def seen_file(self) -> Path:
        return self.folder / "seen.json"


    @property
    def tags_file(self) -> Path:
        return self.folder / "tags.json"


    @property
    def seen(self) -> Dict[str, datetime]:
        if self._seen is None:
            if self.seen_file.exists():
                self._seen = {
                    video_id: parse_date(last_seen)
                    for video_id, last_seen in
                    orjson.loads(self.seen_file.read_text()).items()
                }
            else:
                self._seen = {}

        return self._seen


    @property
    def tags(self) -> Dict[str, List[datetime]]:
        if self._tags is None:
            if self.tags_file.exists():
                self._tags = {
                    tag: [parse_date(d) for d in dates]
                    for tag, dates in
                    orjson.loads(self.tags_file.read_text()).items()
                }
            else:
                self._tags = {}

        return self._tags


    async def record_seen(
        self, video_id: str, tags: Collection[str] = (),
    ) -> None:

        last_update         = self.seen.get(video_id, ZERO_DATE)
        self.seen[video_id] = datetime.now()
        dumped_seen         = orjson.dumps(self.seen)

        async with aiofiles.open(self.seen_file, "wb") as file:
            await file.write(dumped_seen)

        tags = clean_up_video_tags(*tags)
        now  = datetime.now()

        if (now - last_update).total_seconds() < 60 * 60:
            print(f"Already updated tags in the past hour for {video_id}")
            return

        print(f"Updating tags: {video_id}, {tags}")

        for tag in tags:
            self.tags.setdefault(tag, []).append(now)

        dumped_tags = orjson.dumps(self.tags)

        async with aiofiles.open(self.tags_file, "wb") as file:
            await file.write(dumped_tags)


    def recommendations_query(self) -> str:
        limit = datetime.now() - timedelta(days=30)

        def sort_key(tag: str) -> float:
            recent_watches = sorted(self.tags[tag], reverse=True)
            return sum(
                (time - limit).total_seconds() / 1000 / nth ** 5
                for nth, time in enumerate(recent_watches, 1)
            )

        tags = sorted(self.tags, key=sort_key, reverse=True)
        # for t in reversed(tags): print(t,sort_key(t), self.tags[t], sep="\t")
        return " ".join(tags[:9])
