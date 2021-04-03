# heretube

## Installation

1. Install these packages on your system: `python3-pip entr sassc`
2. Install the python requirements: `pip3 install --user -Ur requirements.txt`
3. `./run.sh`
4. Visit some youtube-like URLs, e.g. <http://localhost:8000/results?search_query=example+search>

When things start to break, an update to youtube-dl and 
youtube-comment-downloader will usually fix it, update the requirements 
using the second command.


## Blocking ads

If your browser doesn't support uBlock or similar but can run GreaseMonkey 
scripts (e.g. qutebrowser), you can use something like this:


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
