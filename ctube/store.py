import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from appdirs import user_data_dir
from dateutil.parser import parse as parse_date

from .utils import json_dumps, related_terms

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
                    json.loads(self.seen_file.read_text()).items()
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
                    json.loads(self.tags_file.read_text()).items()
                }
            else:
                self._tags = {}

        return self._tags


    async def record_seen(self, video_info: Dict[str, Any]) -> None:
        video_id            = video_info["id"]
        last_update         = self.seen.get(video_id, ZERO_DATE)
        self.seen[video_id] = datetime.now()
        dumped_seen         = json_dumps(self.seen)

        async with aiofiles.open(self.seen_file, "w") as file:
            await file.write(dumped_seen)

        tags = related_terms(video_info)
        now  = datetime.now()

        if (now - last_update).total_seconds() < 60 * 60 * 12:
            print(f"Already updated tags in the past 12 hours for {video_id}")
            return

        print(f"Updating tags: {video_id}, {tags}")

        for tag in tags:
            self.tags.setdefault(tag, []).append(now)

        dumped_tags = json_dumps(self.tags)

        async with aiofiles.open(self.tags_file, "w") as file:
            await file.write(dumped_tags)


    def recommendations_query(self, term_count: int) -> List[str]:
        limit = datetime.now() - timedelta(days=30)

        def score(tag: str, recent_watches: List[datetime]) -> float:
            recent_watches.sort(reverse=True)
            return sum(
                (time - limit).total_seconds() / 1000 / nth ** 2
                for nth, time in enumerate(recent_watches, 1)
            )

        tags   = self.tags
        scores = [score(t, rc) for t, rc in tags.items()]
        return random.choices(list(tags), scores, k=min(len(tags), term_count))
