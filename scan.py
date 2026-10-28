#!/usr/bin/env python3
"""
Scan the seed list and rank it.

    python3 scan.py                    # everything in scanner/brands.py
    python3 scan.py --limit 12         # first 12, for a quick pass
    python3 scan.py ulanka.com         # one brand, verbose
    python3 scan.py --refresh          # ignore the cache

Writes out/results.json, then report.py turns that into the page and the CSV.
Everything is cached, so a second run costs the brands nothing and is instant.
"""
import argparse
import json
import os
import statistics
import time

from scanner import brands, catalogue, economics, imagery, platform
from scanner.fetch import Fetcher

# The brief said ~5. Six turned out to be indefensible: at 6 products Silbon read
# 83% flat-lay, at 30 it reads 47% — a EUR 222k overstatement on a single row. The
# cost of being wrong in front of the CEO is far higher than 20 minutes of scanning.
SAMPLE_N = 30          # products classified per brand


def resolve(fetcher, domain):
    """Find the URL that actually serves the shop. Some redirect www -> apex,
    some the other way, and a few only answer on one of them."""
    for candidate in (f"https://{domain}", f"https://www.{domain}"):
        got = fetcher.get(candidate + "/")
        if got and got["status"] == 200 and len(got["content"]) > 2000:
            base = got["url"].rstrip("/")
            # keep only scheme://host
            parts = base.split("/")
            return "/".join(parts[:3]), got
    return None, None


def scan_one(fetcher, domain, name, bucket, verbose=False):
    row = {"domain": domain, "name": name, "bucket": bucket,
           "customer": brands.is_customer(domain), "status": "ok"}

    base, got = resolve(fetcher, domain)
    if not base:
        row["status"] = "unreachable"
        return row
    row["url"] = base

    html = got["content"].decode("utf-8", errors="replace")
    plat, conf, evidence = platform.detect(html, got["headers"])
    row.update(platform=plat, platform_confidence=conf, platform_evidence=evidence)

    cat = catalogue.size(fetcher, base, plat, sample_n=SAMPLE_N)
    if not cat or cat.skus < 5:
        row["status"] = "catalogue not sized"
        return row

    row.update(skus=cat.skus, images_per_sku=round(cat.images_per_sku, 2),
               catalogue_method=cat.method, catalogue_exact=cat.exact,
               catalogue_notes=cat.notes)

    share, n, details = imagery.brand_flat_lay_share(fetcher, cat.samples, verbose)
    if share is None:
        row["status"] = "no images classified"
        return row

    row.update(flat_lay_share=round(share, 3), sampled=n,
               samples=[{k: d.get(k) for k in ("title", "url", "image", "verdict",
                                               "confidence")} for d in details])
    return row


def finish(rows):
    """Fill in the images-per-SKU we could not measure, then price and rank.

    The fallback is the median of the brands we DID measure exactly, so it is
    grounded in this sample rather than invented. Rows that use it are flagged."""
    # A sitemap's <image:image> usually lists only the primary shot, so it reports
    # 1.0 for brands whose product pages carry a dozen. Checked by hand against a
    # Bimba y Lola product page: 1 in the sitemap, dozens on the page. No fashion
    # product has one image, so treat 1.0 as "not measured" rather than believe it.
    ONE_IMAGE_IS_NOT_A_MEASUREMENT = 1.05
    for r in rows:
        if (r.get("images_per_sku") or 0) <= ONE_IMAGE_IS_NOT_A_MEASUREMENT:
            r["images_per_sku"] = 0

    measured = [r["images_per_sku"] for r in rows
                if r.get("images_per_sku") and r["images_per_sku"] > 0]
    fallback = round(statistics.median(measured), 2) if measured else \
        economics.DEFAULT_IMAGES_PER_SKU

    for r in rows:
        if r.get("status") != "ok":
            continue
        if not r.get("images_per_sku"):
            r["images_per_sku"] = fallback
            r["images_assumed"] = True
        else:
            r["images_assumed"] = False

        r.update(economics.evaluate(r["skus"], r["images_per_sku"],
                                    r["flat_lay_share"], r["platform"]))
        r["score"] = economics.score(r["skus"], r["flat_lay_share"], r["platform"])

    rows.sort(key=lambda r: (r.get("score") or 0), reverse=True)
    return rows, fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domains", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    if args.domains:
        targets = [(d, d, "adhoc") for d in args.domains]
    else:
        targets = brands.seed()
        if args.limit:
            targets = targets[:args.limit]

    fetcher = Fetcher(delay=args.delay, refresh=args.refresh,
                      verbose=bool(args.domains))
    os.makedirs("out", exist_ok=True)

    rows, t0 = [], time.time()
    for i, (domain, name, bucket) in enumerate(targets, 1):
        print(f"  [{i:>2}/{len(targets)}] {name[:26]:28}", end="", flush=True)
        try:
            row = scan_one(fetcher, domain, name, bucket, verbose=bool(args.domains))
        except Exception as e:                      # one bad site must not stop the run
            row = {"domain": domain, "name": name, "bucket": bucket,
                   "customer": brands.is_customer(domain),
                   "status": f"error: {type(e).__name__}: {e}"}
        rows.append(row)

        if row["status"] == "ok":
            print(f"{row['platform']:<12} {row['skus']:>6} SKUs  "
                  f"{row['images_per_sku']:>4.1f} img  "
                  f"{row['flat_lay_share']:>5.0%} flat-lay"
                  + ("   [customer]" if row["customer"] else ""))
        else:
            print(f"— {row['status']}")

    rows, fallback = finish(rows)
    meta = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "scanned": len(rows),
        "sized": sum(1 for r in rows if r["status"] == "ok"),
        "sample_per_brand": SAMPLE_N,
        "images_per_sku_fallback": fallback,
        "economics": {
            "photo_cost_eur": economics.PHOTO_COST_EUR,
            "photo_cost_source": economics.PHOTO_COST_SOURCE,
            "credits_per_image": economics.CREDITS_PER_IMAGE,
            "plan": economics.DEFAULT_PLAN,
            "modelia_per_image_eur": round(economics.modelia_cost_per_image_eur(), 3),
            "fx": economics.FX_NOTE,
        },
        "elapsed_s": round(time.time() - t0),
    }
    with open("out/results.json", "w") as fh:
        json.dump({"meta": meta, "rows": rows}, fh, indent=1, ensure_ascii=False)

    ok = meta["sized"]
    print(f"\n  {ok}/{len(rows)} brands sized in {meta['elapsed_s']}s "
          f"-> out/results.json")
    if ok:
        top = [r for r in rows if r["status"] == "ok" and not r["customer"]][:3]
        print("  top of the list:")
        for r in top:
            print(f"    {r['name'][:24]:26} {r['flat_lay_share']:>4.0%} flat-lay  "
                  f"{r['skus']:>5} SKUs   saving €{r['saving_eur']:,}")


if __name__ == "__main__":
    main()
