#!/usr/bin/env python3
"""Pull the latest Substack posts into writing.json for the Latest Writing strip."""
import json, re, html, urllib.request, sys

FEED = "https://elidavis4.substack.com/feed"
OUT = "writing.json"
N = 4

req = urllib.request.Request(FEED, headers={"User-Agent": "elimdavis.com site bot"})
xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

items = re.findall(r"<item>(.*?)</item>", xml, re.S)[:N]
posts = []
for it in items:
    def grab(tag):
        m = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", it, re.S)
        return html.unescape(m.group(1).strip()) if m else ""
    title = grab("title")
    link = grab("link")
    date = grab("pubDate")[:16]  # e.g. "Mon, 02 Jun 2026"
    desc = re.sub(r"<[^>]+>", "", grab("description"))[:180].strip()
    if title and link:
        posts.append({"title": title, "link": link, "date": date, "snippet": desc})

if not posts:
    sys.exit("no posts parsed — refusing to overwrite writing.json")

json.dump({"source": "elidavis4.substack.com", "posts": posts},
          open(OUT, "w"), indent=2, ensure_ascii=False)
print(f"wrote {OUT} with {len(posts)} posts")
