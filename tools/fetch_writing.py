#!/usr/bin/env python3
"""Pull the latest Substack posts into writing.json for the Latest Writing strip."""
import json, re, html, urllib.request, urllib.parse, sys

FEED = "https://elidavis4.substack.com/feed"
OUT = "writing.json"
N = 4

BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER,
        "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

try:
    xml = get(FEED)
except Exception as e:
    print(f"direct fetch failed ({e}); trying rss2json fallback", file=sys.stderr)
    data = json.loads(get("https://api.rss2json.com/v1/api.json?rss_url=" +
                          urllib.parse.quote(FEED, safe="")))
    posts = [{"title": i["title"], "link": i["link"],
              "date": i.get("pubDate", "")[:16],
              "snippet": re.sub(r"<[^>]+>", "", i.get("description", ""))[:180].strip()}
             for i in data.get("items", [])[:N]]
    if not posts:
        sys.exit("fallback also returned no posts")
    json.dump({"source": "elidavis4.substack.com", "posts": posts},
              open(OUT, "w"), indent=2, ensure_ascii=False)
    print(f"wrote {OUT} with {len(posts)} posts (fallback)")
    sys.exit(0)

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
