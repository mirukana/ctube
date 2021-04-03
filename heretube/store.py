import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Collection, DefaultDict, Dict, List, Optional, Set

import aiofiles
from appdirs import user_data_dir

from .utils import clean_up_video_tags

ZERO_DATE = datetime.fromtimestamp(0)


@dataclass
class Store:
    _watched: Optional[Set[str]] = field(init=False, default=None)

    _tags: Optional[Dict[str, List[float]]] = field(init=False, default=None)

    _updated_tags: Dict[str, datetime] = field(  # {video_id: at}
        init=False, default_factory=lambda: DefaultDict(lambda: ZERO_DATE),
    )


    def __post_init__(self) -> None:
        self.watched_file.parent.mkdir(parents=True, exist_ok=True)
        self.tags_file.parent.mkdir(parents=True, exist_ok=True)


    @property
    def folder(self) -> Path:
        return Path(user_data_dir("heretube", roaming=True))


    @property
    def watched_file(self) -> Path:
        return self.folder / "watched.csv"


    @property
    def tags_file(self) -> Path:
        return self.folder / "tags.json"


    @property
    def watched(self) -> Set[str]:
        if self._watched is None:
            if self.watched_file.exists():
                self._watched = set(self.watched_file.read_text().splitlines())
            else:
                self._watched = set()

        return self._watched


    @property
    def tags(self) -> Dict[str, List[float]]:
        if self._tags is None:
            if self.tags_file.exists():
                self._tags = json.loads(self.tags_file.read_text())
            else:
                self._tags = {}

        return self._tags


    async def record_watch(
        self, video_id: str, tags: Collection[str] = (),
    ) -> None:

        tags = clean_up_video_tags(*tags)

        if video_id not in self.watched:
            self.watched.add(video_id)

            async with aiofiles.open(self.watched_file, "w") as file:
                await file.write("\n".join(self.watched))


        now = datetime.now()

        if (now - self._updated_tags[video_id]).total_seconds() < 60 * 60:
            print(f"Already updated tags in the past hour for {video_id}")
            return

        print(f"Updating tags: {video_id}, {tags}")
        self._updated_tags[video_id] = now

        for tag in tags:
            self.tags.setdefault(tag, []).append(now.timestamp())

        dumped_tags = json.dumps(
            self.tags, ensure_ascii=False, indent=4, sort_keys=True,
        )

        async with aiofiles.open(self.tags_file, "w") as file:
            await file.write(dumped_tags)


    def recommendations_query(self) -> str:
        limit = datetime.now() - timedelta(days=30)

        def sort_key(tag: str) -> float:
            watches = [datetime.fromtimestamp(t) for t in self.tags[tag]]
            return sum((w - limit).total_seconds() / 1000 for w in watches)

        tags = sorted(self.tags, key=sort_key, reverse=True)
        return " ".join(tags[:6])
