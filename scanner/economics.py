"""
The euro model, and where every number in it came from.

The brief carried "~€1.50 per Modelia image" and told me to re-verify it before a
euro figure went in front of the CEO. It did not survive the check.

Verified against https://modelia.ai/pricing on 2 September 2026:

    Flatlay to Model  =  3 credits per image  (6 credits in 4K)

    plan       price          credits    $/credit   $/image (3 cr)
    Project    $12 one-time        50      0.240        0.72
    Basic      $35 / month        250      0.140        0.42
    Pro        $85 / month        750      0.1133       0.34
    Business   $300 / month      3000      0.100        0.30

So a generated image runs $0.30–$0.72 depending on plan — well under the €1.50 the
brief carried. Using the stale figure would have understated the saving, and Ivan
would have spotted it on his own pricing page inside five seconds.

What could NOT be verified: the "~€50 per flat-lay image" and "€200+ per model
shoot" comparisons. They are not on modelia.ai's homepage or pricing page as of
today. They stay in as a clearly-labelled ASSUMPTION rather than being passed off
as Modelia's published figure — see PHOTO_COST_EUR below. It is one constant, so
Ivan can substitute his own number and the whole ranking recomputes.

The measured part of every row — SKUs, images per SKU, flat-lay share — carries no
assumption at all. That is deliberate: the volume is a fact, the euros are a fact
multiplied by one number the reader is invited to argue with.
"""
import math

# ---- verified from modelia.ai/pricing, 2026-09-02 -------------------------
CREDITS_PER_IMAGE = 3
PLANS = {                       # plan: (usd_price, credits)
    "project":  (12.0,    50),
    "basic":    (35.0,   250),
    "pro":      (85.0,   750),
    "business": (300.0, 3000),
}
# A catalogue of any size lands on Business. Named explicitly so the report can
# print which plan the arithmetic assumes.
DEFAULT_PLAN = "business"

# ---- assumptions, stated ---------------------------------------------------
# Not currently published by Modelia. Carried over from the brief and labelled as
# an assumption everywhere it is used.
PHOTO_COST_EUR = 50.0
PHOTO_COST_SOURCE = "assumption — not currently published by Modelia"

# One stated rate rather than a live FX call, so a re-run gives the same answer.
EUR_PER_USD = 0.92
FX_NOTE = "EUR/USD held at 0.92; Modelia prices in USD"

# Fallback when a catalogue's images-per-SKU could not be measured. Filled in at
# runtime with the median across brands we DID measure exactly, so it is grounded
# in this sample rather than guessed.
DEFAULT_IMAGES_PER_SKU = 3.0


def modelia_cost_per_image_eur(plan=DEFAULT_PLAN):
    usd_price, credits = PLANS[plan]
    per_credit = usd_price / credits
    return per_credit * CREDITS_PER_IMAGE * EUR_PER_USD


def evaluate(skus, images_per_sku, flat_lay_share, platform, plan=DEFAULT_PLAN):
    """-> dict of the numbers a row in the report needs.

    Only the flat-lay portion of the catalogue is counted. A brand already shooting
    two thirds of its products on models is not going to re-shoot those, and
    charging Modelia's pitch for work the brand has already paid for is the kind of
    inflated number that loses the room."""
    images_total = skus * images_per_sku
    images_flat  = images_total * (flat_lay_share if flat_lay_share is not None else 0.0)

    per_image = modelia_cost_per_image_eur(plan)
    photo_cost   = images_flat * PHOTO_COST_EUR
    modelia_cost = images_flat * per_image
    saving       = photo_cost - modelia_cost

    return {
        "images_total":      round(images_total),
        "images_flat":       round(images_flat),
        "photo_cost_eur":    round(photo_cost),
        "modelia_cost_eur":  round(modelia_cost),
        "saving_eur":        round(saving),
        "per_image_eur":     round(per_image, 3),
        "plan":              plan,
    }


def score(skus, flat_lay_share, platform):
    """Rank order. Deliberately not the euro figure.

    log(SKUs) so one giant retailer does not swamp the list — the brief's point,
    and the right one: Ivan can only have so many conversations, and the best use
    of them is not all with the same size of company.

    Shopify gets a real multiplier because Modelia ships a Shopify app: that is a
    five-minute install rather than a procurement cycle, which changes the
    probability of a deal far more than a few thousand euros of catalogue does."""
    if flat_lay_share is None or skus < 1:
        return 0.0
    platform_bonus = {"shopify": 1.5}.get(platform, 1.0)
    return round(flat_lay_share * math.log10(max(skus, 10)) * platform_bonus, 4)
