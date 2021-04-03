# HereTube

A simple self-hosted front-end for YouTube, powered by Youtube-DL.


## Features

- Searches
- Channel video lists
- Likes, dislikes, view count, uploader, upload date, description and tags
- Comments sorted by date
- Related entries for video being watched, based on video tags and title
- Global "recommendations" on homepage, based on commonly watched tags frecency
- Dims thumbnails for already watched videos
- Reactive layout taking maximum advantage of any window size
- Doesn't have a light theme
- *Currently* uses YouTube's embedded player
- Uses a stupid amount of iframes to minimize javascript usage and speed up 
  page rendering while Youtube-DL responses are loading


## Installation

1. Clone the repository: `git clone https://github.com/mirukana/heretube`
2. Enter the cloned repository: `cd heretube`
2. Install `python3-pip` and `sassc` from your distro's package manager
3. Install the python requirements: `pip3 install --user -Ur requirements.txt`
4. Launch the server: `./run.sh`
5. Visit some youtube-like URLs, e.g. <http://localhost:8000/results?search_query=example+search>

The server binds to localhost on port 8000 by default, see `./run.sh --help`
for options.


## Updating

1. Go to the cloned repository and update the source code: `git pull` 
2. Update the python requirements: `pip3 install --user -Ur requirements.txt`

Youtube-DL and youtube-comment-downloader, part of the python requirements,
need to be frequently kept up-to-date to fix new issues with YouTube.


## Stored data

Recommendation system data such as last watched video dates, tag frequencies 
and such are stored in `~/.local/share/heretube`. 

If you make your server accessible outside of your local machine 
(e.g. with `./run.sh --host 0.0.0.0`), be aware that any connecting client
will share the same set of data.


## Embedded player ads

If your browser doesn't support uBlock or similar but can run GreaseMonkey 
scripts (e.g. pre-2.0 qutebrowser), you can use a script like below to
clean up what remains on the embedded YouTube player:

```javascript
// ==UserScript==
// @name         Youtube Cleaner
// @namespace    youtube_cleaner
// @version      0.1
// @match        *://www.youtube-nocookie.com/*
// @run-at       document-end
// ==/UserScript==

var style         = document.createElement("style");
style.type        = "text/css"
style.id          = "youtube-cleaner"
style.textContent = `
.video-ads, .ytp-pause-overlay {
    display: none !important;
}
`

document.getElementsByTagName("head")[0].appendChild(style)
```
