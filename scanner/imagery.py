"""
Is this product's main image shot flat-lay, or on a model?

That single bit is what qualifies a brand. A brand photographing its catalogue flat
on a table is paying a photographer per garment and getting the conversion rate that
goes with it; a brand already shooting on models is not Modelia's problem to solve.

There is no vision model wired in here (no API key in this environment), so this is
a heuristic — and the interesting part is the failure mode it is built around.

The obvious approach, counting skin-coloured pixels, breaks immediately: a camel coat
laid on a white table passes every published skin-tone test in both RGB and YCbCr. Run
the numbers on RGB(210,180,140) and it satisfies the Kovac rule *and* lands inside the
Cb/Cr skin box. Colour alone cannot tell beige wool from a forearm.

What separates them is structure, and two facts about clothed human beings:

  * A person in a fashion photograph is mostly *clothes*. Skin runs maybe 5-35% of the
    subject. A garment that merely happens to be skin-coloured is 60-95% of it. So a
    very high skin fraction is evidence *against* a model, not for one.
  * Skin sits at the top of the frame. Head, neck and shoulders are in the top quarter
    of a standing shot; a folded garment leaves that strip empty.

So the classifier reads the skin fraction as a band rather than a threshold, and
weights where the skin sits. Every feature it used is kept on the verdict, so a row in
the report can be argued with instead of taken on faith.
"""
import io

import numpy as np
from PIL import Image

import cv2

WORK_PX      = 220     # long edge we analyse at; texture averages out, and it is fast
FACE_PX      = 460     # faces need a bigger copy — Haar wants some pixels to work with
BORDER_PX    = 3       # ring sampled to learn the background colour
BG_DIST      = 34      # colour distance from background before a pixel is "subject"
MIN_SUBJECT  = 0.012   # below this the image is effectively empty

# The band. Below LO there is no skin to speak of; above HI we are looking at a
# skin-coloured garment, because people in clothes are not 60% bare.
SKIN_LO      = 0.035
SKIN_HI      = 0.58
BOX_AR_MAX   = 1.15    # wider than this and the subject is not a standing person
TOP_MIN      = 0.10    # skin in the top quarter, below which nothing is a model
FIGURE_VSPAN = 0.90    # a worn garment crops to a subject filling the frame
FIGURE_AR    = 0.82    # ...and distinctly taller than it is wide


class Verdict:
    def __init__(self, on_model, confidence, features, error=None):
        self.on_model   = on_model
        self.confidence = confidence
        self.features   = features
        self.error      = error

    @property
    def flat_lay(self):
        return (not self.on_model) if self.error is None else None

    def __repr__(self):
        if self.error:
            return f"<Verdict error={self.error}>"
        return (f"<Verdict {'on-model' if self.on_model else 'flat-lay'} "
                f"{self.confidence:.2f} skin={self.features['skin_share']:.3f}>")


# ------------------------------------------------------------------ masks
def _skin_mask(rgb):
    """Chrominance only, deliberately.

    The published Kovac RGB rule was the obvious thing to reach for and it is wrong
    here: it opens with `R > 95`, which is a *brightness* floor, so it simply does
    not fire on dark skin. Two on-model shots of a Black model in the labelled set
    came back at skin=0.003 and skin=0.025 — the detector saw no person at all. A
    tool for a fashion company cannot fail on the brands doing the most interesting
    casting, and 'it under-counts on some catalogues' is not a bug you get to ship.

    So: work in YCbCr and use the chroma channels alone. Melanin moves luma a long
    way and Cb/Cr comparatively little, which is exactly the property wanted. What
    is left is an ordering check that holds for every tone, and a guard against
    near-black and blown-out pixels where chroma stops meaning anything.

    This is looser than Kovac and lets more beige through. That is the trade, and
    it is the right way round: beige is handled structurally in _score(), whereas
    a person the mask never saw cannot be recovered downstream."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))

    y  = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128 + (b - y) * 0.564
    cr = 128 + (r - y) * 0.713

    chroma   = (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173)
    ordering = (r > b) & (r >= g)          # skin is redder than it is blue, always
    usable   = (y > 24) & (y < 250)        # not crushed black, not blown white
    return chroma & ordering & usable


_CASCADES = None


def _cascades():
    """Haar frontal + profile face. Loaded once, lazily."""
    global _CASCADES
    if _CASCADES is None:
        import os
        d = cv2.data.haarcascades
        _CASCADES = [cv2.CascadeClassifier(os.path.join(d, f)) for f in
                     ("haarcascade_frontalface_alt2.xml", "haarcascade_profileface.xml")]
        _CASCADES = [c for c in _CASCADES if not c.empty()]
    return _CASCADES


def _count_faces(rgb):
    """A face is the only thing here that means 'person' outright.

    Run at a larger size than the rest of the analysis — Haar needs a face to be a
    few dozen pixels across, and in a 220px thumbnail a model's head is marginal."""
    if not _cascades():
        return 0
    grey = cv2.equalizeHist(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY))
    h, w = grey.shape
    min_side = max(int(min(h, w) * 0.045), 20)
    for c in _cascades():
        found = c.detectMultiScale(grey, scaleFactor=1.08, minNeighbors=6,
                                   minSize=(min_side, min_side))
        if len(found):
            return len(found)
    return 0


def _subject_mask(rgb):
    """Everything that is not the backdrop, learned from the border ring."""
    h, w = rgb.shape[:2]
    ring = np.concatenate([
        rgb[:BORDER_PX].reshape(-1, 3), rgb[-BORDER_PX:].reshape(-1, 3),
        rgb[:, :BORDER_PX].reshape(-1, 3), rgb[:, -BORDER_PX:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    bg_spread = float(np.mean(np.std(ring.astype(np.float32), axis=0)))
    dist = np.linalg.norm(rgb.astype(np.float32) - bg, axis=2)
    return dist > BG_DIST, bg, bg_spread


# ------------------------------------------------------------------ classify
def classify(image_bytes):
    try:
        im = Image.open(io.BytesIO(image_bytes))
        im = im.convert("RGB")
    except Exception as e:                      # truncated download, webp, svg, ...
        return Verdict(False, 0.0, {}, error=f"decode: {type(e).__name__}")

    big = im.copy()
    big.thumbnail((FACE_PX, FACE_PX), Image.LANCZOS)
    n_faces = _count_faces(np.asarray(big))

    im.thumbnail((WORK_PX, WORK_PX), Image.LANCZOS)
    rgb = np.asarray(im)
    if rgb.ndim != 3 or min(rgb.shape[:2]) < 40:
        return Verdict(False, 0.0, {}, error="too small")

    h, w = rgb.shape[:2]
    subject, bg, bg_spread = _subject_mask(rgb)
    subject_frac = float(subject.mean())
    if subject_frac < MIN_SUBJECT:
        return Verdict(False, 0.0, {"subject_frac": subject_frac}, error="blank image")

    skin = _skin_mask(rgb) & subject
    skin_share = float(skin.sum()) / max(int(subject.sum()), 1)

    # Where does the skin sit? Head and shoulders live in the top quarter.
    top = slice(0, max(h // 4, 1))
    top_subject = int(subject[top].sum())
    skin_top = float(skin[top].sum()) / top_subject if top_subject > 30 else 0.0

    # How much of the frame's height does the subject occupy? A standing model runs
    # nearly the full frame; a folded garment sits in a band in the middle.
    rows = np.where(subject.any(axis=1))[0]
    cols = np.where(subject.any(axis=0))[0]
    vspan = float((rows[-1] - rows[0] + 1) / h) if rows.size else 0.0

    # Shape of the subject's bounding box. This is the cheap, robust one: a person
    # photographed for e-commerce is always taller than wide, and a pair of shoes
    # sitting side by side is always wider than tall. It is what separates a model
    # from Carmina's loafers-with-wooden-shoe-trees, where the wood is genuinely
    # skin-coloured and genuinely at the top of the frame.
    box_aspect = (float((cols[-1] - cols[0] + 1) / (rows[-1] - rows[0] + 1))
                  if rows.size and cols.size else 1.0)

    # Skin is smooth. Wood grain, suede and knit are not.
    skin_texture = 0.0
    if skin.sum() > 40:
        grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        lap  = cv2.Laplacian(grey, cv2.CV_32F, ksize=3)
        skin_texture = float(np.sqrt(np.mean(lap[skin] ** 2)))

    # Distinct skin regions — a face plus two forearms is three, a camel coat is one.
    n_blobs = 0
    if skin.any():
        n, labels = cv2.connectedComponents(skin.astype(np.uint8), connectivity=8)
        if n > 1:
            sizes = np.bincount(labels.ravel())[1:]
            n_blobs = int((sizes >= max(int(0.004 * h * w), 12)).sum())

    feats = {
        "skin_share":   round(skin_share, 4),
        "skin_top":     round(skin_top, 4),
        "subject_frac": round(subject_frac, 4),
        "vspan":        round(vspan, 3),
        "box_aspect":   round(box_aspect, 3),
        "skin_texture": round(skin_texture, 2),
        "skin_blobs":   n_blobs,
        "faces":        n_faces,
        "bg_lum":       round(float(np.mean(bg)), 1),
        "bg_spread":    round(bg_spread, 1),
        "aspect":       round(w / h, 3),
    }

    score = _score(feats)
    return Verdict(score >= 0.5, round(abs(score - 0.5) * 2, 2), feats)


def _score(f):
    """0 = certainly flat-lay, 1 = certainly on-model.

    Three passes over 44 hand-labelled images got this to its current shape, and the
    route matters more than the thresholds:

    1. Count skin-coloured pixels. Useless on its own — beige suede, tan leather and
       a yellow argyle knit all read as forearm.
    2. Require the skin to sit at the top of the frame. Better, until Carmina, who
       photograph shoes with wooden shoe trees standing up out of them. Wood is
       skin-coloured and lands exactly where a head would.
    3. Find an actual face. Across the labelled set this fired on 0 of 24 packshots
       and 10 of 20 model shots — never wrong, but only half the time.

    So a face is taken as conclusive, and the half it misses (cropped torsos,
    headless shots, a model facing away) fall to silhouette: every one of those ten
    filled the frame vertically and was clearly taller than wide, which is what a
    garment does when a person is inside it and does not do otherwise."""
    # Near-conclusive — but corroborated. Haar fired once on the graphic printed
    # across the chest of a folded hoodie, in an image that contained not one
    # skin-coloured pixel. A face with no skin anywhere is not a face.
    if f["faces"] >= 1 and f["skin_share"] >= SKIN_LO:
        return 0.97

    # Nothing wider than it is tall is a person wearing clothes.
    if f["box_aspect"] > BOX_AR_MAX:
        return 0.08

    # Not a warm-toned pixel in it. A packshot.
    if f["skin_share"] < SKIN_LO:
        return 0.05

    # No face, so silhouette has to carry it: a tall figure filling the frame.
    if f["vspan"] >= FIGURE_VSPAN and f["box_aspect"] <= FIGURE_AR:
        s = 0.62
        s += 0.18 * min(f["skin_top"] / 0.40, 1.0)      # skin up where a head goes
        s += 0.10 if f["skin_blobs"] >= 2 else 0.0      # face + hands, not one mass
        return min(s, 0.95)

    return 0.12


# ------------------------------------------------------------------ per brand
def brand_flat_lay_share(fetcher, samples, verbose=False):
    """Classify a brand's sampled products. -> (share, n_classified, [details])"""
    details, on_model, flat = [], 0, 0
    for s in samples:
        if not s.get("image"):
            continue
        got = fetcher.get(s["image"], binary=True)
        if not got or got["status"] != 200:
            details.append({**s, "verdict": "fetch failed"})
            continue
        v = classify(got["content"])
        if v.error:
            details.append({**s, "verdict": f"error: {v.error}"})
            continue
        if v.on_model:
            on_model += 1
        else:
            flat += 1
        details.append({**s, "verdict": "on-model" if v.on_model else "flat-lay",
                        "confidence": v.confidence, "features": v.features})
        if verbose:
            print(f"      {'on-model' if v.on_model else 'flat-lay '} "
                  f"{v.confidence:.2f}  skin={v.features['skin_share']:.3f} "
                  f"top={v.features['skin_top']:.3f} blobs={v.features['skin_blobs']} "
                  f"{s['title'][:40]}")

    n = on_model + flat
    return (flat / n if n else None), n, details
