#!/usr/bin/env python3
"""
Build a contact sheet of product images with the classifier's verdict under each,
so a human can check it by eye and count the mistakes.

The flat-lay percentage is the number this whole tool rests on. Nobody should put it
in front of a CEO without having looked at what produced it.

Usage:  python3 tools/labelsheet.py                    # the default mixed sample
        python3 tools/labelsheet.py ulanka.com scalpers.com
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont

from scanner import catalogue, imagery, platform
from scanner.fetch import Fetcher

# A deliberate mix: footwear and accessories skew flat-lay, apparel skews on-model.
# A sheet of only one kind cannot show a false positive.
DEFAULT = ["ulanka.com", "pompeiibrand.com", "bravafabrics.com",
           "sepiia.com", "hoffshoes.com", "laagam.com"]

PER_BRAND = 5
CELL, PAD, LABEL_H = 300, 26, 96
COLS = 6

SYS = "/System/Library/Fonts"
f_lab = ImageFont.truetype(f"{SYS}/HelveticaNeue.ttc", 21, index=1)
f_sub = ImageFont.truetype(f"{SYS}/Menlo.ttc", 15, index=0)
f_ttl = ImageFont.truetype(f"{SYS}/HelveticaNeue.ttc", 26, index=1)

BG, EDGE = (243, 242, 240), (206, 204, 200)
INK, DIM = (20, 24, 28), (110, 118, 124)
ON_MODEL, FLAT = (24, 104, 72), (168, 68, 42)


def collect(domains):
    f = Fetcher()
    cells = []
    for d in domains:
        base = f"https://{d}" if not d.startswith("http") else d
        html = f.text(base + "/")
        head = f.get(base + "/")
        if not html:
            print(f"  {d}: unreachable")
            continue
        plat, _, _ = platform.detect(html, head["headers"] if head else {})
        cat = catalogue.size(f, base, plat, sample_n=PER_BRAND)
        if not cat or not cat.samples:
            print(f"  {d}: no catalogue ({plat})")
            continue
        print(f"  {d}: {plat}, {cat.skus} SKUs")
        for s in cat.samples[:PER_BRAND]:
            if not s.get("image"):
                continue
            got = f.get(s["image"], binary=True)
            if not got or got["status"] != 200:
                continue
            v = imagery.classify(got["content"])
            cells.append({"brand": d, "bytes": got["content"], "verdict": v,
                          "title": s["title"], "image": s["image"]})
    return cells


def build(cells, out):
    rows = (len(cells) + COLS - 1) // COLS
    W = PAD + COLS * (CELL + PAD)
    H = PAD + 64 + rows * (CELL + LABEL_H + PAD)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, PAD), "CLASSIFIER CHECK — verdict under each image", font=f_ttl, fill=INK)

    for i, c in enumerate(cells):
        col, row = i % COLS, i // COLS
        x = PAD + col * (CELL + PAD)
        y = PAD + 64 + row * (CELL + LABEL_H + PAD)

        try:
            im = Image.open(__import__("io").BytesIO(c["bytes"])).convert("RGB")
        except Exception:
            continue
        im.thumbnail((CELL, CELL), Image.LANCZOS)
        canvas = Image.new("RGB", (CELL, CELL), (255, 255, 255))
        canvas.paste(im, ((CELL - im.size[0]) // 2, (CELL - im.size[1]) // 2))
        sheet.paste(canvas, (x, y))
        d.rectangle([x, y, x + CELL - 1, y + CELL - 1], outline=EDGE, width=1)

        v = c["verdict"]
        d.text((x, y + CELL + 6), f"{i:02d}  {c['brand'][:22]}", font=f_sub, fill=DIM)
        if v.error:
            d.text((x, y + CELL + 28), f"ERROR {v.error}", font=f_lab, fill=FLAT)
            continue
        lab = "ON-MODEL" if v.on_model else "FLAT-LAY"
        d.text((x, y + CELL + 28), f"{lab}  {v.confidence:.2f}", font=f_lab,
               fill=ON_MODEL if v.on_model else FLAT)
        ft = v.features
        d.text((x, y + CELL + 54),
               f"skin {ft['skin_share']:.3f} top {ft['skin_top']:.2f}",
               font=f_sub, fill=DIM)
        d.text((x, y + CELL + 72),
               f"blobs {ft['skin_blobs']}  vspan {ft['vspan']:.2f}",
               font=f_sub, fill=DIM)

    sheet.save(out)
    print(f"\n  {out}  {sheet.size[0]}x{sheet.size[1]}  ({len(cells)} images)")


if __name__ == "__main__":
    import json
    domains = sys.argv[1:] or DEFAULT
    os.makedirs("out", exist_ok=True)
    cells = collect(domains)
    build(cells, "out/classifier-check.png")
    # A manifest in sheet order, so the labels a human writes down can be matched
    # back to images without re-running anything.
    with open("out/classifier-check.json", "w") as fh:
        json.dump([{"i": i, "brand": c["brand"], "image": c["image"],
                    "title": c["title"]} for i, c in enumerate(cells)], fh, indent=1)
    print(f"  out/classifier-check.json  ({len(cells)} entries)")
