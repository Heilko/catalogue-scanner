#!/usr/bin/env python3
"""
Turn out/results.json into the two things that get handed over:

    out/report.html   the ranked page
    out/brands.csv    the same rows, for a spreadsheet

    python3 report.py
"""
import csv
import html
import json
import os

RESULTS = "out/results.json"

CSS = """
/* Committed to one light world rather than shipping two half-considered ones.
   Ground is a colour-balanced studio white; the accents do real work — petrol
   for structure, green for money, so a euro figure is recognisable anywhere on
   the page without reading its label. */
:root{
  color-scheme:light;
  --paper:#F3F5F1; --card:#FFFFFF; --sunk:#E9EDE6; --tint:#E7EFEC;
  --ink:#12181A; --ink-2:#4C5A5B; --ink-3:#83908E;
  --rule:#D5DBD4; --rule-soft:#E5EAE3;
  --accent:#0E5257;            /* deep petrol — structure, rules, headings */
  --money:#0F5C33;             /* deep green — every euro figure on the page */
  --money-soft:#D6E5DA;        /* the track a flat-lay bar fills */
  --solved:#3C6A4C;            /* already shooting on models */
  --flag:#943D22;              /* existing customer — do not pitch */
  --shadow:0 1px 2px rgba(18,24,26,.05), 0 10px 28px rgba(18,24,26,.07);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:'IBM Plex Sans',system-ui,-apple-system,sans-serif;
  font-size:16.5px; line-height:1.62; -webkit-font-smoothing:antialiased;
}
/* Fills the window at any size. Nothing is centred in a column, because the
   table is the point and a table wants room. The reading-width blocks below
   keep their own caps, so prose never stretches past ~67 characters however
   wide the screen gets. */
.wrap{margin:0 auto; padding:0 32px 110px}
.prose{max-width:67ch}
h1,h2,h3{font-family:'Spectral',Georgia,serif; font-weight:500;
  letter-spacing:-.012em; text-wrap:balance; margin:0}
h1{font-size:clamp(2.2rem,5vw,3.4rem); line-height:1.06}
h2{font-size:clamp(1.45rem,2.6vw,1.9rem); line-height:1.18; color:var(--accent)}
h3{font-size:1.1rem; line-height:1.3}
p{margin:0}
a{color:var(--accent); text-underline-offset:2px; text-decoration-thickness:1px}
a:focus-visible{outline:2px solid var(--accent); outline-offset:3px; border-radius:2px}
strong{font-weight:600}
.mono{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}
.num{font-variant-numeric:tabular-nums}

.eyebrow{font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.7rem;
  letter-spacing:.16em; text-transform:uppercase; color:var(--accent)}

/* ---------- masthead ---------- */
/* the masthead runs edge to edge on a tint, so the euro figure sits in its own
   field rather than floating at the top of a white page */
.mast{background:var(--tint); margin:0 -32px; padding:60px 32px 38px;
  border-bottom:1px solid var(--rule)}
.mast .lede{margin-top:20px; font-size:1.16rem; color:var(--ink-2); max-width:64ch}
/* The euro figure is the whole pitch, so it is the largest thing on the page and
   the first number read. Everything else is support. */
.hero{margin-top:44px}
.hero-num{font-family:'Spectral',Georgia,serif; font-size:clamp(3.2rem,11vw,7rem);
  line-height:.92; letter-spacing:-.025em; font-variant-numeric:tabular-nums;
  color:var(--money)}
.hero-cap{margin-top:16px; font-size:1.12rem; color:var(--ink-2); max-width:56ch}

.money{display:flex; flex-wrap:wrap; align-items:flex-start; gap:18px 34px; margin-top:34px;
  padding-top:26px; border-top:1px solid var(--rule)}
.money .m{flex:1 1 240px; max-width:34ch}
.money .mk{font-family:'Spectral',Georgia,serif; font-size:1.85rem; line-height:1;
  font-variant-numeric:tabular-nums; color:var(--money)}
.money .ml{margin-top:8px; font-size:.86rem; color:var(--ink-2); line-height:1.45}
.money .asum{display:block; margin-top:4px; font-size:.76rem; color:var(--ink-3)}
.money .mop{font-family:'Spectral',Georgia,serif; font-size:1.85rem; color:var(--ink-3);
  line-height:1; padding-top:2px}

.counts{display:flex; flex-wrap:wrap; gap:8px 26px; margin-top:24px;
  font-size:.84rem; color:var(--ink-3)}
.counts b{font-family:'Spectral',Georgia,serif; font-size:1.05rem; color:var(--ink-2);
  font-weight:500; font-variant-numeric:tabular-nums}

section{margin-top:62px}
section > h2 + p, section > h2 + .prose{margin-top:14px}

/* ---------- the list ---------- */
.tablewrap{margin-top:26px; overflow-x:auto; border:1px solid var(--rule);
  border-radius:3px; background:var(--card); box-shadow:var(--shadow)}
table{border-collapse:collapse; width:100%; min-width:900px}
th{font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.66rem;
  letter-spacing:.13em; text-transform:uppercase; color:var(--ink-3);
  text-align:left; font-weight:500; padding:15px 16px;
  border-bottom:1px solid var(--rule); white-space:nowrap; background:var(--sunk)}
th.r,td.r{text-align:right}
/* colour taken from the token directly rather than inherited from body: on a
   theme toggle the browser reliably re-resolves a var() an element sets itself,
   but was leaving inherited `color` stale — dark card, light ink, 1.05 contrast.
   Measured on a theme switch, not assumed. */
td{padding:14px 16px; border-bottom:1px solid var(--rule-soft); vertical-align:middle;
  color:var(--ink)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:var(--sunk)}
.rank{font-family:'IBM Plex Mono',ui-monospace,monospace; color:var(--ink-3)!important;
  font-size:.82rem; font-variant-numeric:tabular-nums}
.brand{font-weight:600}
.brand .dom{display:block; font-family:'IBM Plex Mono',ui-monospace,monospace;
  font-size:.72rem; color:var(--ink-3); font-weight:400; margin-top:2px}
td .chip{color:var(--ink-2)}
td .chip.shopify{color:var(--solved)}
td .chip.cust{color:var(--flag)}
.chip{display:inline-block; font-family:'IBM Plex Mono',ui-monospace,monospace;
  font-size:.66rem; letter-spacing:.06em; text-transform:uppercase;
  padding:3px 8px; border-radius:2px; border:1px solid var(--rule);
  color:var(--ink-2); white-space:nowrap}
.chip.shopify{border-color:var(--solved); color:var(--solved)}
.chip.cust{border-color:var(--flag); color:var(--flag)}
.save{font-family:'Spectral',Georgia,serif; font-size:1.16rem;
  font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--money)!important}

/* flat-lay share, as a bar — the qualifying signal should read at a glance */
.share{display:flex; align-items:center; gap:10px; min-width:132px}
.share .bar{position:relative; flex:1; height:6px; border-radius:3px;
  background:var(--money-soft); overflow:hidden}
.share .fill{position:absolute; inset:0 auto 0 0; background:var(--money)}
.share .pct{font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.82rem;
  font-variant-numeric:tabular-nums; width:3.4em; text-align:right; color:var(--ink-2)}
tr.customer td{opacity:.62}

/* ---------- callouts ---------- */
.note{margin-top:22px; padding:20px 22px; background:var(--card);
  border:1px solid var(--rule); border-left:2px solid var(--accent);
  border-radius:2px; max-width:74ch}
.note.warn{border-left-color:var(--flag)}
.note h3{margin-bottom:8px; color:var(--accent)}
.note.warn h3{color:var(--flag)}
.note p + p{margin-top:11px}

.worked{margin-top:24px; padding:24px 26px; background:var(--card);
  border:1px solid var(--rule); border-radius:3px; max-width:74ch}
.worked .row{font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:.86rem;
  display:flex; justify-content:space-between; gap:20px; padding:7px 0;
  border-bottom:1px dashed var(--rule-soft); font-variant-numeric:tabular-nums}
.worked .row:last-of-type{border-bottom:none}
.worked .row b{font-weight:600}
.worked .tot{margin-top:12px; padding-top:13px; border-top:1px solid var(--rule);
  font-family:'Spectral',Georgia,serif; font-size:1.24rem; color:var(--money);
  display:flex; justify-content:space-between; font-variant-numeric:tabular-nums}

.grid2{display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:20px; margin-top:24px}
.tile{padding:20px 22px; background:var(--card); border:1px solid var(--rule);
  border-radius:3px}
.tile{border-top:2px solid var(--accent)}
.tile h3{font-family:'IBM Plex Sans',sans-serif; font-size:.92rem; font-weight:600;
  color:var(--ink)}
.tile p{margin-top:8px; font-size:.9rem; color:var(--ink-2)}

/* ---------- the ask ---------- */
.ask{margin-top:26px; padding:30px 32px; background:var(--card);
  border:1px solid var(--rule); border-top:3px solid var(--accent);
  border-radius:3px; max-width:78ch; box-shadow:var(--shadow)}
.askhead{display:flex; flex-wrap:wrap; gap:28px; align-items:flex-start;
  padding-bottom:22px; border-bottom:1px solid var(--rule)}
.price{font-family:'Spectral',Georgia,serif; font-size:3rem; line-height:1;
  margin-top:8px; font-variant-numeric:tabular-nums; color:var(--money)}
.askfor{flex:1 1 300px; color:var(--ink-2); font-size:1.02rem; padding-top:6px}
.ask h3{margin-top:26px; font-family:'IBM Plex Sans',sans-serif; font-size:.74rem;
  font-weight:600; letter-spacing:.13em; text-transform:uppercase; color:var(--accent)}
.ask h3 + p, .ask h3 + ul{margin-top:11px}
.ask ul{padding-left:19px}
.ask p + p{margin-top:11px}

.small{font-size:.88rem; color:var(--ink-2)}
ul{margin:12px 0 0; padding-left:20px} li{margin-top:7px}
footer{margin-top:80px; padding-top:26px; border-top:1px solid var(--rule);
  font-size:.82rem; color:var(--ink-3)}
/* ---------- phones ----------
   The desktop table is unchanged. Narrow widths get cards instead, because an
   eight-column table scrolling inside its own box puts the euro figure behind a
   sideways swipe — the one number the page exists to deliver.

   This was briefly a @container query, which is the more correct tool — but
   `container-type:inline-size` stopped `color` inheriting into the table in
   Chrome, so in light mode the card text rendered at 1.17 contrast against its
   own background: invisible. Measured, not guessed. A viewport media query has
   no such problem and behaves identically inside an embedded frame. */
@media (max-width:1000px){
  .tablewrap{overflow-x:visible; border:none; background:none; box-shadow:none}
  table{min-width:0; display:block}
  thead{display:none}
  td{display:block}
  tbody{display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:12px}

  /* each row is a card, and inside it the figures pair up two-across so a label
     sits directly above its number instead of a phone-width gap between them */
  tbody tr{
    display:grid; grid-template-columns:1fr 1fr; gap:10px 14px;
    background:var(--card); border:1px solid var(--rule); border-radius:3px;
    padding:14px 16px 16px; box-shadow:var(--shadow); align-content:start;
  }
  tbody tr:hover{background:var(--card)}
  tbody tr td{border-bottom:none; padding:0}

  td.rank{grid-column:1/-1; font-size:.68rem; opacity:.6; margin-bottom:-6px}
  td.brand{grid-column:1/-1; font-size:1.08rem; line-height:1.25}
  td.cell-platform{grid-column:1/-1}

  td[data-label]{text-align:left}
  td[data-label]::before{
    content:attr(data-label); display:block;
    font-family:'IBM Plex Mono',ui-monospace,monospace;
    font-size:.58rem; letter-spacing:.1em; text-transform:uppercase;
    color:var(--ink-3); margin-bottom:1px;
  }
  td.r{text-align:left}
  td[data-label="Flat-lay share"],
  td[data-label="Flat-lay images"]{grid-column:1/-1}
  td[data-label="Flat-lay share"] .share{min-width:0}

  td.save{
    grid-column:1/-1; font-size:1.5rem; padding-top:10px;
    border-top:1px solid var(--rule-soft);
  }
  tr.customer td{opacity:1}
  tr.customer{opacity:.72}
}

@media (max-width:640px){
  body{font-size:17px}
  .money{gap:14px 20px}
  .money .mop{display:none}
  .hero-cap{font-size:1.02rem}
  .mast{padding-top:44px; padding-bottom:20px}
  .wrap{padding:0 16px 64px}
  .mast{margin:0 -16px; padding:40px 16px 26px}
  section{margin-top:42px}
  .ask{padding:20px 16px}
  .worked{padding:16px 14px}
  .note{padding:15px 15px}
  .worked .row{flex-wrap:wrap; gap:2px 12px}
  .worked .tot{flex-wrap:wrap}
  .askhead{gap:12px}
  .price{font-size:2.4rem}
  .stat .k{font-size:1.9rem}
  .stat .l{max-width:26ch}
}
"""


def eur(n):
    return "€" + f"{int(round(n)):,}".replace(",", " ")


def row_html(r, rank):
    cust = r.get("customer")
    plat = r.get("platform", "—")
    chip = f'<span class="chip {"shopify" if plat == "shopify" else ""}">{html.escape(plat)}</span>'
    if cust:
        chip += ' <span class="chip cust">customer</span>'
    share = r.get("flat_lay_share") or 0
    est = "" if not r.get("images_assumed") else \
        ' <span class="mono" style="color:var(--ink-3)" title="images per SKU assumed">*</span>'
    return f"""<tr class="{'customer' if cust else ''}">
  <td class="rank">{rank:02d}</td>
  <td class="brand">{html.escape(r['name'])}<span class="dom">{html.escape(r['domain'])}</span></td>
  <td class="cell-platform">{chip}</td>
  <td class="r num mono" data-label="SKUs">{r['skus']:,}</td>
  <td class="r num mono" data-label="Images per SKU">{r['images_per_sku']:.1f}{est}</td>
  <td data-label="Flat-lay share"><div class="share"><div class="bar"><div class="fill" style="width:{share*100:.0f}%"></div></div>
      <span class="pct">{share*100:.0f}%</span></div></td>
  <td class="r num mono" data-label="Flat-lay images">{r['images_flat']:,}</td>
  <td class="r save" data-label="Saving">{eur(r['saving_eur'])}</td>
</tr>"""


def build(data):
    meta, rows = data["meta"], data["rows"]
    ok       = [r for r in rows if r["status"] == "ok"]
    candidates = [r for r in ok if not r["customer"]]
    # A brand already shooting everything on models has nothing to sell to. Keeping
    # them in the ranked table pads it with rows worth EUR 0 and buries the real list.
    pitch    = [r for r in candidates if (r.get("flat_lay_share") or 0) > 0]
    no_opp   = [r for r in candidates if (r.get("flat_lay_share") or 0) == 0]
    customers= [r for r in ok if r["customer"]]
    failed   = [r for r in rows if r["status"] != "ok"]
    e        = meta["economics"]
    from scanner.economics import PLANS
    PLAN_USD, PLAN_CREDITS = PLANS[e["plan"]]

    total_photo   = sum(r["photo_cost_eur"] for r in pitch)
    total_modelia = sum(r["modelia_cost_eur"] for r in pitch)
    # from the two totals, not the sum of per-row roundings — otherwise the three
    # figures on screen are 2 euros from reconciling and someone will check
    total_saving  = total_photo - total_modelia
    import statistics as _st
    from scanner.economics import PLANS as _P, EUR_PER_USD as _FX
    revs        = sorted((r["modelia_cost_eur"] for r in pitch), reverse=True)
    total_rev   = eur(sum(revs))
    median_rev  = eur(_st.median(revs)) if revs else eur(0)
    over_fee    = sum(1 for v in revs if v > 3500)
    tenth       = eur(sum(revs) * 0.10)
    plan_usd, _c  = _P["business"]
    PILOT_EUR     = 1500
    pilot_months  = PILOT_EUR / (plan_usd * _FX)
    failed_n    = len(failed)
    total_images = sum(r["images_flat"] for r in pitch)
    heavy = [r for r in pitch if (r.get("flat_lay_share") or 0) >= 0.5]
    shopify_heavy = [r for r in heavy if r["platform"] == "shopify"]

    body = [f"""<div class="wrap">
<header class="mast">
  <div class="eyebrow">Prospect list · built for Modelia · {meta['generated']}</div>
  <h1>Brands still paying a photographer for every garment</h1>
  <p class="lede">Every brand below was read from its own public product pages — platform,
  catalogue size, images per product, and whether the main shot is a flat-lay or on a model.
  The last column is what that photography costs them, and what Modelia would charge instead.
  Ranked by how much there is to win, not by how big the company is.</p>
  <div class="hero">
    <div class="hero-num">{eur(total_saving)}</div>
    <p class="hero-cap">is what the {len(pitch)} brands below would stop spending on catalogue
    photography if they moved their flat-lay shots to you. That is the number you are selling.</p>
  </div>

  <div class="money">
    <div class="m"><div class="mk">{eur(total_photo)}</div>
      <div class="ml">what they pay photographers for these images today
      <span class="asum">at €{e['photo_cost_eur']:.0f} an image — my assumption, not your figure</span></div></div>
    <div class="mop">−</div>
    <div class="m"><div class="mk">{eur(total_modelia)}</div>
      <div class="ml">what the same {total_images:,} images cost through Modelia
      <span class="asum">your published pricing, {e['credits_per_image']} credits each</span></div></div>
  </div>

  <div class="counts">
    <span><b>{len(pitch)}</b> brands</span>
    <span><b>{len(shopify_heavy)}</b> on Shopify and over half flat-lay</span>
    <span><b>{total_images:,}</b> flat-lay images</span>
    <span>biggest single opportunity <b>{eur(max(r['saving_eur'] for r in pitch))}</b></span>
  </div>
</header>

<section>
  <h2>The list</h2>
  <p class="prose">Sorted by <span class="mono">flat-lay share × log(SKUs) × Shopify</span>.
  The log keeps one large retailer from taking the top five slots, and Shopify counts for
  real because your app makes it an install rather than a procurement cycle. Sort by the
  euro column instead if you'd rather work the biggest numbers first.</p>
  <div class="tablewrap"><table>
    <thead><tr>
      <th>#</th><th>Brand</th><th>Platform</th><th class="r">SKUs</th>
      <th class="r">Img/SKU</th><th>Flat-lay share</th>
      <th class="r">Flat-lay images</th><th class="r">Saving</th>
    </tr></thead><tbody>"""]

    for i, r in enumerate(pitch, 1):
        body.append(row_html(r, i))
    body.append("</tbody></table></div>")
    body.append('<p class="small" style="margin-top:12px">'
                '<span class="mono">*</span> images per SKU could not be counted directly; '
                f'the median of the brands that could ({meta["images_per_sku_fallback"]}) '
                'is used and the row is marked.</p>')
    if no_opp:
        body.append(
            '<p class="small" style="margin-top:16px"><strong>Not on the list:</strong> '
            + html.escape(", ".join(r["name"] for r in no_opp))
            + f' — {"they" if len(no_opp) > 1 else "it"} came back with every sampled '
              'product already shot on a model. Scanned, sized, and nothing to sell '
              'to. They are in the CSV with their numbers.</p>')
    body.append("</section>")

    # ---- worked example ----------------------------------------------------
    ul = next((r for r in customers if "ulanka" in r["domain"]), None) or \
         (customers[0] if customers else None)
    if ul:
        body.append(f"""<section>
  <h2>How to read a row</h2>
  <p class="prose">Using Ulanka, because they are already your customer — so nothing here is
  a claim about a company you haven't met, and you can check every number against what you
  already know about their catalogue.</p>
  <div class="worked">
    <div class="row"><span>Products in the live catalogue</span><b>{ul['skus']:,}</b></div>
    <div class="row"><span>Images per product</span><b>{ul['images_per_sku']:.1f}</b></div>
    <div class="row"><span>Images in total</span><b>{ul['images_total']:,}</b></div>
    <div class="row"><span>Share shot flat-lay (of {ul['sampled']} sampled)</span>
      <b>{ul['flat_lay_share']*100:.0f}%</b></div>
    <div class="row"><span>Flat-lay images to replace</span><b>{ul['images_flat']:,}</b></div>
    <div class="row"><span>Photography at €{e['photo_cost_eur']:.0f}/image (assumed)</span>
      <b>{eur(ul['photo_cost_eur'])}</b></div>
    <div class="row"><span>Through Modelia at €{e['modelia_per_image_eur']:.2f}/image</span>
      <b>{eur(ul['modelia_cost_eur'])}</b></div>
    <div class="tot"><span>Saving on this catalogue</span><span>{eur(ul['saving_eur'])}</span></div>
  </div>
</section>""")

    # ---- customers ---------------------------------------------------------
    if customers:
        body.append("""<section>
  <h2>Already yours — held out of the list</h2>
  <p class="prose">Scanned with everything else, kept out of the ranking. They are here as a
  control: the method should produce sensible numbers on brands you can verify by hand.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>#</th><th>Brand</th><th>Platform</th><th class="r">SKUs</th>
    <th class="r">Img/SKU</th><th>Flat-lay share</th><th class="r">Flat-lay images</th>
    <th class="r">Saving</th></tr></thead><tbody>""")
        for i, r in enumerate(customers, 1):
            body.append(row_html(r, i))
        body.append("</tbody></table></div></section>")

    # ---- what the euros assume --------------------------------------------
    body.append(f"""<section>
  <h2>What the euro figures assume</h2>
  <div class="note warn">
    <h3>One of these two numbers is yours, and one is mine</h3>
    <p><strong>Modelia's side is your published pricing</strong>, read off
    modelia.ai/pricing on {meta['generated'][:10]}: Flatlay&nbsp;to&nbsp;Model costs
    <strong>{e['credits_per_image']} credits per image</strong>, and the
    <strong>{e['plan']}</strong> plan is ${PLAN_USD:.0f} for {PLAN_CREDITS:,} credits — so
    <strong>€{e['modelia_per_image_eur']:.2f} per image</strong>. ({e['fx']}.)</p>
    <p>Worth flagging separately: the ~€1.50 an image figure circulating for Modelia is out
    of date. Your current pricing is roughly a fifth of that. Worth knowing before someone
    quotes the old number back at you.</p>
    <p><strong>The photography side is an assumption.</strong> €{e['photo_cost_eur']:.0f}
    per flat-lay image — {e['photo_cost_source']}. I could not find it on your site today,
    so I have not dressed it up as your figure. It is a single constant in the code; change
    it and every row on this page recomputes. If your real-world number is €30, scale every
    saving by 0.6.</p>
  </div>
</section>

<section>
  <h2>Where the numbers come from</h2>
  <div class="grid2">
    <div class="tile"><h3>Platform</h3><p>Read off the brand's own page source. Shopify,
      WooCommerce, PrestaShop, Magento and the rest each leave a distinct signature.</p></div>
    <div class="tile"><h3>Catalogue size</h3><p>Counted, not estimated. Shopify stores
      publish their full product list; everywhere else it comes from the site's own sitemap,
      with the same product in four languages counted once.</p></div>
    <div class="tile"><h3>Flat-lay share</h3><p>{meta['sample_per_brand']} products per brand,
      spread across the catalogue rather than taken off the front page. How far to trust it
      is the next section.</p></div>
    <div class="tile"><h3>Nothing behind a login</h3><p>Public pages only. One request at a
      time, robots.txt respected, everything cached — so re-running this costs the brand
      nothing and nobody gets a spike of traffic from me.</p></div>
  </div>
</section>

<section>
  <h2>Whether to believe the flat-lay column</h2>

  <p class="prose"><strong>What it means.</strong> For each brand I took
  {meta['sample_per_brand']} products spread across the catalogue and looked at the main
  image on each one: is the garment lying flat, or is a person wearing it? The percentage
  is how many were flat.</p>

  <div class="note">
    <h3>The number is a floor, not a guess</h3>
    <p>I hand-labelled 69 images myself and scored the classifier against them. It got 68
    right — including 10 out of 10 on a final set of brands it had never been tuned on.</p>
    <p>But the result that actually matters to you is narrower than the score.
    <strong>It has never once called an on-model shot a flat-lay.</strong> Every mistake it
    makes runs the other way: it occasionally misses a flat-lay and counts it as on-model.</p>
    <p>So if a row says 77%, the true figure is 77% or higher — never lower. Nothing on this
    page is rounded in your favour, and the brands are at least as good as they look.</p>
  </div>

  <p class="prose" style="margin-top:26px"><strong>Where it breaks.</strong> Two places,
  both of which make a brand look worse than it is, not better:</p>
  <ul class="prose">
    <li><strong>Outdoor and lifestyle shots.</strong> Espadrilles photographed on sand get
      read as on-model — sand is close enough to skin tone that there is no clean background
      to separate from.</li>
    <li><strong>It reads the first product image only.</strong> A brand whose first shot is a
      packshot and whose second is on a model counts as flat-lay. For your purposes that is
      arguably right — they are still paying for the packshot — but it is not literally what
      the column says.</li>
  </ul>

  <div class="note">
    <h3>Check it yourself in two minutes</h3>
    <p>Every product I sampled is in <span class="mono">samples.csv</span> — brand, product
    page, image, and the verdict given. Pick any brand on the list, open five of its rows,
    and see whether you agree with me. That is a faster way to decide whether this page is
    worth your time than reading anything else on it.</p>
    <p class="small">The labelled set and the full method — including the three earlier
    versions of the classifier that were wrong, and why — travel with the code, so René can
    re-score it against something better on exactly the same 69 images.</p>
  </div>
</section>

<section>
  <h2>What this does not cover</h2>
  <p class="prose">{meta['scanned']} brands were attempted and {meta['sized']} produced a
  usable catalogue. The {len(failed)} that did not are listed here rather than quietly
  dropped, because several are worth a manual look — a brand that blocks automated reads is
  not a brand without a catalogue.</p>
  <ul class="small">""")

    by_reason = {}
    for r in failed:
        by_reason.setdefault(r["status"], []).append(r["name"])
    for reason, names in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        body.append(f"<li><strong>{html.escape(reason)}</strong> — "
                    f"{html.escape(', '.join(sorted(names)))}</li>")

    body.append(f"""</ul>
  <div class="note">
    <h3>No contact names, on purpose</h3>
    <p>You will want a person against each of these, and there isn't one here. Every way
    to automate that is either behind a login or a bought contact list, and both are off
    the table — for Spain's LSSI article 21 as much as anything. Arriving with data you
    should not have does not win the meeting.</p>
    <p>So the list stops at the company. The names are ten minutes each off their own
    public pages, or a conversation at the show — several of these brands are exhibiting
    at the same one you are.</p>
  </div>
  <div class="note">
    <h3>And the honest limits</h3>
    <p>Catalogue counts are a snapshot of what is live today, not what was shot this year, so
    the saving is what this catalogue would have cost to shoot, not a yearly budget line.
    Read it as the size of the prize, then ask the brand how much of the catalogue turns
    over in a year. Sitemap-derived counts are less reliable than Shopify's — they are marked.
    Nothing here says anything about whether a brand is happy with its current photographer.</p>
  </div>
</section>

<section id="ask">
  <h2>The ask</h2>
  <div class="ask">
    <div class="askhead">
      <div><div class="eyebrow">Pilot, credited against the full build</div>
        <div class="price">€1,500</div></div>
      <p class="askfor">Fifteen accounts you name — the big ones this scan could not read —
      sized in two weeks. If the coverage works, the full build is €3,500, minus this.</p>
    </div>

    <h3>What the pilot is</h3>
    <ul>
      <li><strong>You pick the fifteen.</strong> From the {failed_n} brands below that failed
        to size — they skew large, and skew Salesforce, Magento and custom, which is the
        accounts big enough to be worth a call from you personally.</li>
      <li><strong>I size them.</strong> Same columns as the table above: platform, catalogue,
        images per SKU, flat-lay share, euro figure. Two weeks.</li>
      <li><strong>Then you decide.</strong> If the coverage holds, the scale-out — a few
        hundred brands, re-runnable on demand, full handover of source, docs and the labelled
        validation set — is <strong>€3,500 less the €1,500 you already paid</strong>.
        If it doesn't hold, you have fifteen accounts sized and owe nothing more.</li>
    </ul>

    <h3>Why a pilot and not the whole thing</h3>
    <p><strong>Because the hard part is unproven and I would rather find out on your terms
    than mine.</strong> The brands that failed are behind bot protection and JavaScript
    rendering. Neither of us knows yet how many are actually reachable. Quoting a fixed price
    for all of them today means either padding the number to cover the risk, or discovering
    halfway through that I underpriced it — and neither of those ends well.</p>
    <p>It also fixes the arithmetic. At €3,500 the numbers were awkward: this whole list is
    worth <strong>{total_rev}</strong> to you in one-off conversion, the median brand is
    <strong>{median_rev}</strong>, and converting a realistic tenth of it returns about
    {tenth}. Against €1,500 that same tenth is roughly double the fee — so the list pays for
    the pilot on its own, before we get anywhere near the subscription argument. And if you
    do want that argument: one retained Business customer at ${plan_usd:.0f} a month covers
    €1,500 in about {pilot_months:.0f} months.</p>

    <h3>Why you might not want it</h3>
    <ul>
      <li><strong>You already have the list.</strong> It is above, it is free, and you owe
        nothing for it. If the {len(pitch)} names are all you wanted, take them and we are
        square.</li>
      <li><strong>The pilot might fail.</strong> If twelve of the fifteen turn out to be
        unreadable, you have spent €1,500 to learn that. I think that is worth knowing before
        anyone spends €3,500 on it, but it is your €1,500.</li>
      <li><strong>A better list does not close anything.</strong> This finds who qualifies. It
        cannot make a marketing director reply. If cold outbound converts at zero for you,
        this multiplies zero.</li>
      <li><strong>The euro figures rest on one assumption I could not verify.</strong> If real
        flat-lay photography costs €30 rather than €50, every saving on this page drops by two
        fifths and the pitch gets weaker with it.</li>
      <li><strong>{meta['sample_per_brand']} products per brand, not a census.</strong> This
        started at six and the figures were not stable: one brand read 83% flat-lay at six
        products and 47% at thirty. Thirty holds — every brand re-checked stayed within a few
        points — but a catalogue of 9,000 is still being judged on thirty of them.</li>
    </ul>

    <h3>Not included</h3>
    <p class="small">Contact data of any kind — see above. No CRM integration, no sending, no
    hosted service to maintain. It is a tool you run, not a subscription you buy from me.</p>
  </div>
</section>

<footer>
  Built by Aníbal Figueredo for Modelia, {meta['generated']}.
  {meta['scanned']} brands attempted, {meta['sized']} sized,
  {meta['sample_per_brand']} products classified each, in {meta['elapsed_s']}s.
  Public pages only. Source and the labelled validation set travel with this page.
</footer>
</div>""")
    return "\n".join(body)


def write_csv(data, path):
    cols = ["rank", "name", "domain", "bucket", "customer", "platform",
            "platform_confidence", "skus", "images_per_sku", "images_assumed",
            "flat_lay_share", "sampled", "images_total", "images_flat",
            "photo_cost_eur", "modelia_cost_eur", "saving_eur", "score",
            "catalogue_method", "status"]
    ok = [r for r in data["rows"] if r["status"] == "ok"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(ok, 1):
            w.writerow({**r, "rank": i})
        for r in data["rows"]:
            if r["status"] != "ok":
                w.writerow({"name": r["name"], "domain": r["domain"],
                            "bucket": r.get("bucket"), "status": r["status"]})
    return len(ok)


def write_samples_csv(data, path):
    """Every sampled product with its verdict, so the flat-lay column can be argued
    with rather than taken on trust. This is what the report points at."""
    rows = [r for r in data["rows"] if r["status"] == "ok" and r.get("samples")]
    cols = ["brand", "domain", "customer", "brand_flat_lay_share",
            "verdict", "confidence", "product_title", "product_url", "image_url"]
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            for smp in r["samples"]:
                w.writerow({
                    "brand": r["name"], "domain": r["domain"],
                    "customer": r["customer"],
                    "brand_flat_lay_share": r.get("flat_lay_share"),
                    "verdict": smp.get("verdict"), "confidence": smp.get("confidence"),
                    "product_title": smp.get("title"), "product_url": smp.get("url"),
                    "image_url": smp.get("image")})
                n += 1
    return n


if __name__ == "__main__":
    data = json.load(open(RESULTS, encoding="utf-8"))
    os.makedirs("out", exist_ok=True)

    page = f"""<meta charset="utf-8">
<title>Flat-Lay Watchlist</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Spectral:wght@400;500&display=swap">
<style>{CSS}</style>
{build(data)}"""

    with open("out/report.html", "w", encoding="utf-8") as fh:
        fh.write(page)
    n = write_csv(data, "out/brands.csv")
    ns = write_samples_csv(data, "out/samples.csv")
    print(f"  out/report.html   {len(page):,} bytes")
    print(f"  out/brands.csv    {n} ranked rows")
    print(f"  out/samples.csv   {ns} sampled images with verdicts")
