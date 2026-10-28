# Modelia catalogue scanner

Finds fashion e-commerce brands still paying a photographer for every garment, and
computes in euros what Modelia would save them. Output is a ranked page and a CSV,
for Iván Rodríguez at MBFW Madrid, 14–19 September 2026.

```bash
python3 scan.py                 # scan the seed list -> out/results.json
python3 report.py               # -> out/report.html + out/brands.csv

python3 scan.py --limit 12      # quick pass
python3 scan.py ulanka.com      # one brand, verbose, prints each classification
python3 scan.py --refresh       # ignore the cache
python3 tools/evaluate.py       # score the classifier against 69 labelled images
```

Everything is cached under `out/cache/`, so a re-run is instant and costs the brands
nothing. Requires `requests`, `numpy`, `Pillow`, `opencv-python==4.10` (5.x dropped
the Haar cascades), `lxml`.

## Why this qualifies a brand

Modelia's qualifying signal is publicly visible. A brand that photographs its
catalogue flat-lay is provably a prospect and the evidence is on every product page
it publishes. At seven people there is no GTM function, so nobody there has time to
work that list by hand. This works it.

## How a row is built

| | |
|---|---|
| `scanner/fetch.py` | polite HTTP — robots.txt, one request at a time per host, identifying UA, disk cache |
| `scanner/platform.py` | Shopify / Woo / PrestaShop / Magento / Shopware / Demandware / VTEX, from public markup and headers, keeping the evidence |
| `scanner/catalogue.py` | SKU count and images per SKU. Shopify's `/products.json` where available (exact); XML sitemaps elsewhere, deduplicated across locales |
| `scanner/imagery.py` | flat-lay vs on-model. See `VALIDATION.md` — this is the number everything multiplies |
| `scanner/economics.py` | the euro model, and where every constant came from |
| `scanner/brands.py` | the seed list, and Modelia's existing customers |

## Two things to know before quoting a number

**Modelia's pricing in the original brief was stale.** The brief said ~€1.50 per
image. Verified against modelia.ai/pricing on 2 Sep 2026: Flatlay-to-Model is
**3 credits per image**, and credits run $0.10–$0.24 depending on plan, so a
generated image is **$0.30–$0.72**. Every constant is in `economics.py` with the
plan table beside it.

**The €50 per flat-lay image is an assumption, not Modelia's published figure.** It
is not on their site today. It is one constant — `PHOTO_COST_EUR` — and the report
says so wherever a euro appears. Change it and every row recomputes.

## Rules this respects

- Public pages only. No logins, no bought contact data, no APIs needing a token.
- robots.txt obeyed; rate-limited; identifying User-Agent. `SCANNER_CONTACT` adds a
  contact string to it, deliberately empty by default so no personal mailbox is
  broadcast to every host scanned.
- **Brands the client already sells to are labelled and held out of the pitch.** They
  are scanned as a control. That list is the client's own, so `CUSTOMERS` in
  `scanner/brands.py` ships empty here and is filled in at run time.
- Never overclaim. Sampled numbers say they are sampled; estimated ones are marked.
