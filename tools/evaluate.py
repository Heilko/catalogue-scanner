#!/usr/bin/env python3
"""
Score the classifier against the hand-labelled set. Prints a confusion matrix and
every image it got wrong, with the features that produced the mistake.

Sets are added in the order they were collected, and each one was used to fix
something, which disqualifies it as a holdout from then on. So the honest number is
always the LAST set's — printed separately, and labelled, so nobody quotes the
flattering one.

  A  six brands the thresholds were first tuned on
  B  exposed the dark-skin failure and the wooden-shoe-tree failure
  C  exposed the false face on a hoodie graphic
  D  untouched

Usage:  python3 tools/evaluate.py            # both sets
        python3 tools/evaluate.py B          # holdout only
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import imagery
from scanner.fetch import Fetcher

LABELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "labels.json")


def run(rows, fetcher):
    out = []
    for r in rows:
        got = fetcher.get(r["image"], binary=True)
        if not got or got["status"] != 200:
            continue
        v = imagery.classify(got["content"])
        if v.error:
            out.append({**r, "pred": "error", "conf": 0.0, "feat": {}, "err": v.error})
            continue
        out.append({**r, "pred": "model" if v.on_model else "flat",
                    "conf": v.confidence, "feat": v.features, "err": None})
    return out


def report(name, results):
    ok  = [r for r in results if r["pred"] == r["label"]]
    bad = [r for r in results if r["pred"] != r["label"]]
    n = len(results)
    if not n:
        print(f"\n  {name}: nothing to score")
        return 0.0

    # flat-lay is the positive class: it is what qualifies a brand as a prospect
    tp = sum(1 for r in results if r["label"] == "flat"  and r["pred"] == "flat")
    fp = sum(1 for r in results if r["label"] == "model" and r["pred"] == "flat")
    fn = sum(1 for r in results if r["label"] == "flat"  and r["pred"] != "flat")
    tn = sum(1 for r in results if r["label"] == "model" and r["pred"] == "model")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec  = tp / (tp + fn) if tp + fn else 0.0

    print(f"\n  {name}  —  {len(ok)}/{n} correct  ({len(ok)/n:.0%})")
    print("     truth\\pred    flat   model")
    print(f"     flat-lay      {tp:>4}   {fn:>5}")
    print(f"     on-model      {fp:>4}   {tn:>5}")
    print(f"     flat-lay precision {prec:.0%}   recall {rec:.0%}")
    for r in bad:
        f = r["feat"]
        detail = (f"skin {f.get('skin_share',0):.3f} top {f.get('skin_top',0):.2f} "
                  f"blobs {f.get('skin_blobs',0)} vspan {f.get('vspan',0):.2f} "
                  f"boxar {f.get('box_aspect',0):.2f} tex {f.get('skin_texture',0):.1f}"
                  if f else r.get("err", ""))
        print(f"     ✗ {r['set']}{r['i']:02d} {r['brand'][:20]:22} "
              f"said {r['pred']:5} was {r['label']:5}  {detail}")
        if r.get("note"):
            print(f"          ({r['note']})")
    return len(ok) / n


if __name__ == "__main__":
    rows = json.load(open(LABELS))
    only = sys.argv[1].upper() if len(sys.argv) > 1 else None
    f = Fetcher()
    results = run([r for r in rows if not only or r["set"] == only], f)

    sets = sorted({r["set"] for r in results})
    for i, name in enumerate(sets):
        last = (i == len(sets) - 1)
        report(f"SET {name}" + ("  (untouched — this is the real number)" if last
                                else "  (already fixed against)"),
               [r for r in results if r["set"] == name])
    if len(sets) > 1:
        report("ALL SETS", results)
