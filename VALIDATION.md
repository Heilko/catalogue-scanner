# Does the flat-lay classifier actually work?

The flat-lay share is the number every euro figure multiplies. It was checked rather
than asserted. This is the record of that, including the versions that were wrong.

```bash
python3 tools/evaluate.py          # score against every labelled image
python3 tools/labelsheet.py a.com  # build a contact sheet for new brands
```

69 images across 14 brands, labelled by hand off contact sheets. Labels live in
`tools/data/labels.json`, keyed by image URL, with a note on the awkward ones.

## The four rounds

Each new set of brands broke something the previous set had not. That is the useful
part of the record — a single accuracy number would hide all of it.

| Set | Brands | Result | What it exposed |
|---|---|---|---|
| **A** | Ulanka, Pompeii, Brava Fabrics, Sepiia, Hoff, Laagam | 22/29 → 29/29 | beige is skin-coloured |
| **B** | Thinking MU, Carmina, Ecoalf | 8/15 → 15/15 | dark skin; wooden shoe trees |
| **C** | Silbon, Castañer, Panama Jack | 13/15 → 14/15 | a false face on a hoodie graphic |
| **D** | TwoThirds, Dolores Promesas | **10/10** | nothing — untouched holdout |

**Overall 68/69.** Flat-lay precision 100%, recall 98%.

### Round 1 — colour alone does not work

Count skin-coloured pixels. 22/29, and every single error the same direction:
flat-lay read as on-model. Beige suede sneakers, a tan leather belt, a yellow argyle
knit. RGB(210,180,140) satisfies the published Kovac rule *and* lands inside the
YCbCr skin box — colour cannot tell camel wool from a forearm.

### Round 2 — position, and where that broke

In set A every false positive had **zero** skin in the top quarter of the frame,
while all 14 true on-model shots had some. Gating on that gave 29/29.

It did not survive set B, which fell to 53%:

- **Kovac fails on dark skin.** The rule opens with `R > 95` — a brightness floor.
  Two on-model shots of a Black model returned `skin=0.003` and `skin=0.025`: the
  detector saw no person at all. Fixed by dropping to chroma only (Cb/Cr), where
  melanin moves luma a long way and the chroma channels comparatively little.
  This one mattered beyond accuracy. A tool for a fashion company that quietly
  misreads the brands doing the most interesting casting is not shippable.
- **Carmina photograph shoes with wooden shoe trees in them.** Wood is
  skin-coloured, and the trees stand up into exactly the top strip the rule
  depended on. Four errors from one brand.

### Round 3 — find an actual face

OpenCV 5 has dropped the bundled Haar cascades; `opencv-python==4.10` still ships
them. Measured across the labelled set at that point, a detected face fired on:

- **0 of 24** packshots
- **10 of 20** on-model shots

Never wrong, but only half the time. So a face is treated as conclusive, and the
half it misses — cropped torsos, headless shots, a model facing away — falls
through to silhouette. All ten of those had `vspan ≥ 0.91` and `box_aspect ≤ 0.80`:
a subject filling the frame and clearly taller than wide, which is what a garment
does when a person is inside it.

Shape also turned out to be the cheapest reliable feature in the whole thing:
**nothing wider than it is tall is a person wearing clothes**, which is what
finally separated a model from Carmina's loafers.

### Round 4 — one more correction, then a clean holdout

Set C found Haar firing on the graphic printed across the chest of a folded hoodie,
in an image containing no skin-coloured pixel at all. A face is now required to be
corroborated by some skin anywhere in the frame.

Set D was then collected and scored once, with no further changes: **10/10**.

## The bias is in the safe direction

Across all 69 images the classifier **never once called a genuine on-model shot a
flat-lay**. Precision on flat-lay is 100%; recall is 98%.

So where it is wrong, it understates. A brand on the list is at least as good a
prospect as its row claims, which is the correct way round for a number going in
front of a CEO who can check it.

## What it still cannot do

- **Lifestyle photography on a natural background.** Espadrilles shot on sand read
  as on-model: sand is skin-coloured and there is no clean backdrop to subtract.
  This is the one remaining error in 69. A shirtless model (`skin=0.732`) and a
  sand background (`skin=0.597`) are genuinely not separable on colour features —
  that needs a real vision model.
- **One image per product.** A brand whose first image is a packshot and whose
  second is on a model counts as flat-lay. Arguably right for the pitch, but not
  what the column literally says.
- **Thirty products per brand, not a census.** This ran at six until 7 September,
  and six was not enough: Silbon read 83% flat-lay at six products and 47% at
  thirty — a EUR 222k overstatement on one row. Re-checking the top brands at
  thirty held every other one within a few points, so thirty is the floor now.
  A 9,000-SKU catalogue is still being judged on thirty of them.

## If an API key ever turns up

`scanner/imagery.py` is a pure `classify(bytes) -> Verdict`. Swapping in a vision
model means replacing `_score()` and keeping the harness — the labelled set and
`evaluate.py` would then measure the new one on exactly the same 69 images, which
is the only way to know whether it is actually better.
