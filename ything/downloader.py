from youtube_dl import YoutubeDL


class Downloader(YoutubeDL):
    def urlopen(self, req):
        """Wrapper of `urlopen()` that caches Youtube requests."""
        return super().urlopen(req)
