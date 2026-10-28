"""
Which site-search engine does each storefront run?

The qualifying signal for a search company, and the same shape as the other two:
a store cannot hide its search vendor, because the engine has to ship its
JavaScript to every visitor's browser. The vendor's name is in the page source.

Three places are read, and the order matters:

    homepage        where most engines load
    search page     some stores only load the engine where it is used — reading
                    the homepage alone missed one store on the first pass
    GTM container   an engine injected through Google Tag Manager never appears
                    in the page HTML at all

The third one is there because of which way the error runs. Every engine this
misses turns into a store reported as having NO engine — and "N stores have no
search engine" is exactly the number a search company would be pitched on.
Missing engines overstates the opportunity. So everything below leans the other
way: anything that might be a search engine counts as one, and a store whose
pages did not load is reported as unread, never as "none".
"""
import re

ENGINES = {
    "Kimera":       r"kimeratechnologies|KIMERA_HOOK|km-load\.min",
    # a live loader or config call — not the word. Castañer carries empty
    # <!--DOOFINDER-SHOPIFY--> comments and loads nothing (checked in a browser).
    "Doofinder":    r"cdn\.doofinder\.com/(?:livelayer|media/js)|eu\d?-config\.doofinder\.com|eu\d-search\.doofinder\.com",
    "Algolia":      r"algolianet|algoliasearch|algolia\.net|algolia\.io",
    "Klevu":        r"klevu",
    "Searchanise":  r"searchanise",
    "Boost":        r"boostcommerce|boost-pfs|boost-sd|bc-sf-filter",
    "Searchspring": r"searchspring",
    "Empathy":      r"empathy\.co|empathybroker",
    "Constructor":  r"cnstrc|constructor\.io",
    "Bloomreach":   r"dxpapi\.com|brsearch|bloomreach",
    "Coveo":        r"coveo",
    "Findify":      r"findify",
    "Nosto Search": r"search\.nosto\.com|nosto-?search",
    "Clerk":        r"clerk\.io",
    "Luigi's Box":  r"luigisbox",
    "Fast Simon":   r"fastsimon|instantsearchplus",
    "Lupa":         r"lupasearch",
    "Sooqr":        r"sooqr",
    "Attraqt":      r"attraqt|fredhopper",
    "Hawksearch":   r"hawksearch",
    "Nextopia":     r"nextopia",
    "Prefixbox":    r"prefixbox",
    "Motive":       r"assets\.motive\.co",             # Spanish; found on Wonders
    "Apptus":       r"apptus|elevate\.voyado",  # Voyado Elevate; Samsøe, browser only
}

# Signs of an engine that is not demonstrably running. Neither "has one" nor "has
# none" — reported separately so they inflate neither count.
TRACES = {
    "Doofinder app installed, no search layer": r"doofinder-installed\.js",
    "Doofinder leftover markup":                r"<!--\s*DOOFINDER",
}

# The platform's own search, not a third-party engine: Salesforce Commerce Cloud
# stores load Einstein from cquotient.com.
PLATFORM = {"Salesforce Einstein": r"cquotient\.com"}

NOT_A_STORE = re.compile(r"coming soon|launching soon|en mantenimiento|maintenance", re.I)
STORE_WORDS = re.compile(r"cart|carrito|cesta|basket|bolsa|checkout", re.I)

SEARCH_PATHS = ("/search?q=vestido", "/?s=vestido", "/catalogsearch/result/?q=vestido")
GTM_ID       = re.compile(r"GTM-[A-Z0-9]{4,10}")
MIN_PAGE     = 5000          # below this the page did not really load

# Engines are matched on the page with its HTML comments removed. Sepiia has the
# whole Kimera loader wrapped in <!-- --> — switched off, nothing loads (checked in
# a browser) — and the first version of this file counted it as a live install.
COMMENT      = re.compile(r"<!--.*?-->", re.S)


def _engines_in(text):
    """-> {engine: evidence snippet}"""
    out = {}
    for name, sig in ENGINES.items():
        m = re.search(sig, text, re.I)
        if m:
            a, b = max(0, m.start() - 50), m.end() + 50
            out[name] = re.sub(r"\s+", " ", text[a:b])
    return out


def detect(fetcher, base):
    """-> dict(status, engines, found_on, evidence, gtm_ids)

    status is one of: engine, trace, platform, none, unread."""
    home_raw = fetcher.text(base + "/") or ""
    if len(home_raw) < MIN_PAGE or (len(home_raw) < 20000 and
            (NOT_A_STORE.search(home_raw) or not STORE_WORDS.search(home_raw))):
        return {"status": "unread", "engines": [], "found_on": "", "evidence": "", "gtm_ids": []}

    search_raw = ""
    for p in SEARCH_PATHS:
        t = fetcher.text(base + p) or ""
        if len(t) >= MIN_PAGE:
            search_raw = t
            break
    home, search = COMMENT.sub(" ", home_raw), COMMENT.sub(" ", search_raw)

    found = {k: ("homepage", v) for k, v in _engines_in(home).items()}
    for k, v in _engines_in(search).items():
        found.setdefault(k, ("search page", v))

    gtm_ids = sorted(set(GTM_ID.findall(home + search)))
    if not found:
        for gid in gtm_ids:
            js = fetcher.text(f"https://www.googletagmanager.com/gtm.js?id={gid}") or ""
            for k, v in _engines_in(js).items():
                found.setdefault(k, (f"GTM {gid}", v))

    if found:
        names = sorted(found)
        return {"status": "engine", "engines": names,
                "found_on": "; ".join(f"{n}: {found[n][0]}" for n in names),
                "evidence": found[names[0]][1], "gtm_ids": gtm_ids}

    raw = home_raw + search_raw
    dead = sorted(_engines_in(" ".join(COMMENT.findall(raw))))
    if dead:
        return {"status": "trace", "engines": [f"{d} commented out" for d in dead],
                "found_on": "", "evidence": "", "gtm_ids": gtm_ids}
    for label, table in (("trace", TRACES), ("platform", PLATFORM)):
        hit = [k for k, v in table.items() if re.search(v, raw, re.I)]
        if hit:
            return {"status": label, "engines": hit, "found_on": "", "evidence": "", "gtm_ids": gtm_ids}
    return {"status": "none", "engines": [], "found_on": "", "evidence": "", "gtm_ids": gtm_ids}
