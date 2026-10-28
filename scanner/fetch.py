"""
Polite HTTP for reading other people's public pages.

Everything this tool learns comes from pages a brand publishes to anyone with a
browser. No logins, no APIs that need a token, no bought data. The rules here are
the ones that keep it that way, and keep us off anybody's blocklist:

  * robots.txt is fetched once per host and obeyed
  * one request at a time per host, with a delay between them
  * a User-Agent that says what this is, so an admin who looks can tell
  * everything is cached to disk, so a re-run costs the brand nothing
"""
import hashlib
import json
import os
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

CACHE_DIR = os.environ.get("SCANNER_CACHE", "out/cache")
TIMEOUT   = 15
DELAY     = 1.5          # seconds between requests to the same host
MAX_BYTES = 8 * 1024 * 1024

# No contact address here on purpose: this string is sent to every host we touch,
# and a personal mailbox in a header is a mailbox that gets scraped. Set
# SCANNER_CONTACT if you want one advertised.
CONTACT = os.environ.get("SCANNER_CONTACT", "")
UA = ("ModeliaCatalogueScanner/1.0 (+market research; reads public product pages only"
      + (f"; {CONTACT}" if CONTACT else "") + ")")


class Fetcher:
    def __init__(self, delay=DELAY, cache_dir=CACHE_DIR, refresh=False, verbose=False):
        self.delay     = delay
        self.cache_dir = cache_dir
        self.refresh   = refresh
        self.verbose   = verbose
        self.session   = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        self._last_hit = {}      # host -> monotonic time of last request
        self._robots   = {}      # host -> RobotFileParser or None
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------ cache
    def _paths(self, url):
        h = hashlib.sha256(url.encode()).hexdigest()[:20]
        return (os.path.join(self.cache_dir, f"{h}.meta.json"),
                os.path.join(self.cache_dir, f"{h}.body"))

    def _cached(self, url):
        meta_p, body_p = self._paths(url)
        if self.refresh or not (os.path.exists(meta_p) and os.path.exists(body_p)):
            return None
        with open(meta_p) as fh:
            meta = json.load(fh)
        with open(body_p, "rb") as fh:
            meta["content"] = fh.read()
        return meta

    def _store(self, url, status, headers, content):
        meta_p, body_p = self._paths(url)
        with open(meta_p, "w") as fh:
            json.dump({"url": url, "status": status,
                       "headers": {k.lower(): v for k, v in headers.items()}}, fh)
        with open(body_p, "wb") as fh:
            fh.write(content)

    # ------------------------------------------------------------ manners
    def _wait(self, host):
        last = self._last_hit.get(host)
        if last is not None:
            gap = self.delay - (time.monotonic() - last)
            if gap > 0:
                time.sleep(gap)
        self._last_hit[host] = time.monotonic()

    def allowed(self, url):
        """robots.txt, fetched once per host. A host we cannot ask, we assume yes —
        that is what a browser does, and we are reading pages meant to be read."""
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
            try:
                self._wait(host)
                r = self.session.get(robots_url, timeout=TIMEOUT)
                if r.status_code == 200 and len(r.content) < 512_000:
                    rp.parse(r.text.splitlines())
                else:
                    rp = None
            except requests.RequestException:
                rp = None
            self._robots[host] = rp
            if rp is not None:
                cd = rp.crawl_delay(UA)
                if cd:
                    self.delay = max(self.delay, float(cd))
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(UA, url)

    # ------------------------------------------------------------ get
    def get(self, url, binary=False):
        """Returns dict(status, headers, content, url, from_cache) or None."""
        hit = self._cached(url)
        if hit is not None:
            hit["from_cache"] = True
            return hit

        if not self.allowed(url):
            if self.verbose:
                print(f"      robots.txt says no: {url}")
            return None

        host = urlparse(url).netloc
        for attempt in (1, 2):
            try:
                self._wait(host)
                r = self.session.get(url, timeout=TIMEOUT, stream=True,
                                     allow_redirects=True)
                content = b""
                for chunk in r.iter_content(65536):
                    content += chunk
                    if len(content) > MAX_BYTES:
                        break
                r.close()
                self._store(url, r.status_code, dict(r.headers), content)
                return {"url": r.url, "status": r.status_code, "content": content,
                        "headers": {k.lower(): v for k, v in r.headers.items()},
                        "from_cache": False}
            except requests.RequestException as e:
                if attempt == 2:
                    if self.verbose:
                        print(f"      {type(e).__name__}: {url}")
                    return None
                time.sleep(1.5)

    def text(self, url):
        r = self.get(url)
        if not r or r["status"] != 200:
            return None
        enc = "utf-8"
        ctype = r["headers"].get("content-type", "")
        if "charset=" in ctype:
            enc = ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
        try:
            return r["content"].decode(enc, errors="replace")
        except LookupError:
            return r["content"].decode("utf-8", errors="replace")

    def json(self, url):
        r = self.get(url)
        if not r or r["status"] != 200:
            return None
        ctype = r["headers"].get("content-type", "")
        if "json" not in ctype:
            return None
        try:
            return json.loads(r["content"])
        except (ValueError, UnicodeDecodeError):
            return None
