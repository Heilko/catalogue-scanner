"""
Which e-commerce platform is this brand running?

Read off public markup and response headers only. Shopify is the flag that matters
most: Modelia ships a Shopify app, so a Shopify brand is a five-minute install
rather than a procurement cycle. Everything else is context.

Each detector keeps the evidence that fired, so a row in the final report can say
*why* we think so instead of asking the reader to trust it.
"""
import re

# (platform, weight, human-readable label, compiled test)
SIGNALS = [
    # ---- Shopify -----------------------------------------------------------
    ("shopify", 3, "cdn.shopify.com assets",   re.compile(r"cdn\.shopify\.com", re.I)),
    ("shopify", 3, "/cdn/shop/ asset paths",   re.compile(r"/cdn/shop/", re.I)),
    ("shopify", 3, "Shopify JS global",        re.compile(r"(window\.)?Shopify\s*[.=]", re.I)),
    ("shopify", 2, "myshopify.com reference",  re.compile(r"[\w-]+\.myshopify\.com", re.I)),
    ("shopify", 2, "shopify-features tag",     re.compile(r"shopify-features", re.I)),

    # ---- WooCommerce -------------------------------------------------------
    ("woocommerce", 3, "woocommerce plugin assets",
     re.compile(r"wp-content/plugins/woocommerce", re.I)),
    ("woocommerce", 2, "generator meta",
     re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+WooCommerce', re.I)),
    ("woocommerce", 1, "woocommerce body class",
     re.compile(r'class="[^"]*woocommerce[-\s"]', re.I)),

    # ---- PrestaShop --------------------------------------------------------
    ("prestashop", 3, "prestashop JS object", re.compile(r"var\s+prestashop\s*=", re.I)),
    ("prestashop", 3, "generator meta",
     re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+PrestaShop', re.I)),
    ("prestashop", 1, "prestashop asset path", re.compile(r"/js/jquery/ui/.*prestashop", re.I)),

    # ---- Magento / Adobe Commerce -----------------------------------------
    ("magento", 3, "Magento_ module assets", re.compile(r"/static/(version\d+/)?frontend/", re.I)),
    ("magento", 2, "Magento require config", re.compile(r"Magento_(Ui|Theme|Catalog)", re.I)),
    ("magento", 2, "mage-init directive",    re.compile(r"data-mage-init", re.I)),

    # ---- Shopware ----------------------------------------------------------
    ("shopware", 3, "storefront bundle path", re.compile(r"/bundles/storefront/", re.I)),
    ("shopware", 2, "generator meta",
     re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+Shopware', re.I)),

    # ---- Salesforce Commerce Cloud ----------------------------------------
    ("salesforce", 3, "demandware.store path", re.compile(r"/on/demandware\.store/", re.I)),
    ("salesforce", 2, "demandware static",     re.compile(r"demandware\.static", re.I)),

    # ---- VTEX --------------------------------------------------------------
    ("vtex", 3, "vtexassets.com", re.compile(r"vtexassets\.com", re.I)),
    ("vtex", 2, "vtexcommercestable", re.compile(r"vtexcommercestable", re.I)),

    # ---- others worth naming ----------------------------------------------
    ("bigcommerce", 3, "bigcommerce CDN", re.compile(r"cdn\d*\.bigcommerce\.com", re.I)),
    ("squarespace", 3, "squarespace CDN",  re.compile(r"static1\.squarespace\.com", re.I)),
    ("wix",         3, "wixstatic assets", re.compile(r"wixstatic\.com", re.I)),
    ("wordpress",   1, "wp-content assets", re.compile(r"/wp-content/", re.I)),
]

HEADER_SIGNALS = [
    ("shopify",    3, "x-shopid header",       "x-shopid"),
    ("shopify",    2, "x-shopify-stage header", "x-shopify-stage"),
    ("magento",    2, "x-magento header",      "x-magento-cache-debug"),
    ("shopware",   2, "sw-invalidation header", "sw-invalidation-states"),
]

# A generic WordPress hit should never beat the shop plugin running on top of it.
SUBSUMED = {"wordpress": {"woocommerce"}}


def detect(html, headers=None):
    """-> (platform, confidence 0-1, [evidence strings])"""
    headers = headers or {}
    scores, evidence = {}, {}

    if html:
        for name, weight, label, rx in SIGNALS:
            if rx.search(html):
                scores[name] = scores.get(name, 0) + weight
                evidence.setdefault(name, []).append(label)

    for name, weight, label, header in HEADER_SIGNALS:
        if header in headers:
            scores[name] = scores.get(name, 0) + weight
            evidence.setdefault(name, []).append(label)

    for weak, strongs in SUBSUMED.items():
        if weak in scores and any(s in scores for s in strongs):
            scores.pop(weak)

    if not scores:
        return "unknown", 0.0, []

    best = max(scores, key=scores.get)
    # 6 points is "several independent tells" — treat that as certain.
    confidence = min(scores[best] / 6.0, 1.0)
    return best, round(confidence, 2), evidence[best]
