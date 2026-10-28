"""
Read a brand's own returns policy and pull out what it commits to.

The qualifying signal for a returns company is the same shape as the flat-lay one
was for an imagery company: the brand publishes it themselves, on purpose, because
EU consumer law requires it. Shopify exposes /policies/refund-policy as a standard
path — the returns equivalent of /products.json.

Four things come off the page:

    refund_days     how long until the customer's money comes back
    free_returns    the brand says returns cost the customer nothing
    priced_returns  there is a price, or a per-country table
    exchanges       exchanges are offered

Every extractor here is anchored to a RETURN word. That is not fussiness — the
naive version read "envío gratuito a partir de 59,95 €" as free returns, and
Panama Jack's "acceso libre y gratuito" (free website access) too. A number or a
"gratis" only counts if it is sitting next to language about returning something.
"""
import html as H
import re

# Shopify's standard path first, then the paths Spanish stores actually use.
POLICY_PATHS = (
    "/policies/refund-policy",
    "/pages/devoluciones",
    "/policies/return-policy",
    "/pages/returns",
    "/pages/envios-y-devoluciones",
    "/pages/politica-de-devoluciones",
    "/pages/return-policy",
)

# Danish cost us Stine Goya on the first pass — she states "INDENFOR 10
# ARBEJDSDAGE" and the regex only spoke Spanish, English and French.
_DAYS   = (r'(\d{1,3})\s*(?:d[ií]as?\s*(?:h[áa]biles|laborables)?|days|business days|'
           r'working days|arbejdsdage|hverdage|jours(?:\s+ouvr[ée]s)?|giorni|Tage)')
_REFUND = r'(?:reembolso|reintegro|devoluci[oó]n del importe|refund|refunder|refunding|abono|remboursement|rimborso)'
_RETURN = r'(?:devoluci[oó]n\w*|devolver|return\w*|retour\w*|reso|resi)'
_FREE   = r'(?:gratis|gratuit\w*|sin coste|sin cargo|sin gastos|free|no cost|kostenlos)'

MAX_PLAUSIBLE_DAYS = 90

# "gratis" only counts beside a RETURN word. The naive version read Gioseppo's
# "envío gratuito a partir de 59,95 €" and Panama Jack's "acceso libre y gratuito"
# (free website access) as free returns.
FREE_NEAR   = re.compile(rf'{_RETURN}[^.]{{0,45}}?{_FREE}|{_FREE}[^.]{{0,45}}?{_RETURN}', re.I)
PRICED_NEAR = re.compile(rf'{_RETURN}[^.]{{0,60}}?\d+[,.]?\d*\s*€|coste de devoluci[oó]n|'
                         rf'gastos de devoluci[oó]n', re.I)
EXCH_NEAR   = re.compile(rf'(?:cambio\w*|exchange\w*)[^.]{{0,60}}?(?:{_FREE})|'
                         rf'(?:ofrecemos|puedes|you can|we offer)[^.]{{0,40}}?(?:cambio|exchange)', re.I)

# A refund word near a number is NOT enough. Policies discuss two different
# periods in the same breath: the window the customer has to SEND IT BACK, and the
# time the brand takes to GIVE THE MONEY BACK. Only the second is the pain a
# returns company sells against. Panama Jack says "plazo máximo de 14 días desde
# que lo hayamos recibido" (latency, 14) in a policy that also says 30 days to
# return — and the naive version reported 30. So the number must sit in a clause
# about the money moving, and the clause must not be about requesting.
_LATENCY = (r'(?:tardar\w*|plazo m[áa]ximo|en un plazo de|plazo de \d|proceder\w+ a su reembolso|se procesar[áa]\w*|procesaremos|verse reflejad\w+|'
            r'recibir[áa]s|ser[áa] abonad\w+|abonaremos|reintegrar\w*|'
            r'will be (?:processed|issued|refunded|credited)|we will (?:refund|process)|'
            r'once we (?:have )?receive\w*|after (?:we|receiving)|within|inden ?for|modtage en refundering|innerhalb|entro|dans un d[ée]lai)')
_REQUESTY = re.compile(r'(?:solicit\w+|per[íi]odo de solicitud|initiat\w+|request\w*|'
                       r'para devolver|to return|dispones de|tienes)', re.I)

SENTENCE = re.compile(r'[^.!?]{15,400}[.!?]')


def _latency_days(txt):
    """Days found only in sentences that talk about the refund actually arriving."""
    out = []
    for m in SENTENCE.finditer(txt):
        s = m.group(0)
        if not re.search(_REFUND, s, re.I):
            continue
        if not re.search(_LATENCY, s, re.I):
            continue
        # a sentence about initiating a return is the other period; skip it
        if _REQUESTY.search(s) and not re.search(r'(?:tardar|plazo m[áa]ximo|verse reflejad)', s, re.I):
            continue
        for d in re.finditer(_DAYS, s, re.I):
            v = int(d.group(1))
            if 1 <= v <= MAX_PLAUSIBLE_DAYS:
                out.append((v, s.strip()))
    return out


def _plain(html_text):
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html_text, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', t)))


def fetch_policy(fetcher, base):
    """-> (plain text, path used) or (None, None)."""
    for path in POLICY_PATHS:
        raw = fetcher.text(base + path)
        if raw and len(raw) > 1200:
            return _plain(raw), path
    return None, None


def read(fetcher, base):
    """-> dict describing what this brand commits to, or None if no policy found."""
    txt, path = fetch_policy(fetcher, base)
    if not txt:
        return None

    hits = _latency_days(txt)
    days = [d for d, _ in hits]

    return {
        "policy_path":    path,
        "policy_chars":   len(txt),
        # The MOST FAVOURABLE reading, not the worst. Where a policy states two
        # periods, quoting the longer one at a brand invites a correction and
        # loses the room; quoting the shorter one is unarguable. Understating is
        # the safe direction, exactly as with the imagery classifier.
        "refund_days":    min(days) if days else None,
        "refund_days_all": sorted(set(days)),
        "free_returns":   bool(FREE_NEAR.search(txt)),
        # both free and priced is not a contradiction — it is the per-country
        # pattern: free at home, charged abroad. That is the cross-border signal.
        "priced_returns": bool(PRICED_NEAR.search(txt)),
        "exchanges":      bool(EXCH_NEAR.search(txt)),
        "quote":          (min(hits, key=lambda h: h[0])[1] if hits
                           else _quote(txt, days)),
    }


def _quote(txt, days):
    """The sentence the finding rests on, so a row can be checked in one click.

    A claim about someone's published policy should travel with the sentence that
    supports it — the same reason the imagery report shipped every sampled image."""
    target = re.compile(rf'[^.]*{_REFUND}[^.]*\.', re.I)
    best = None
    for m in target.finditer(txt):
        s = m.group(0).strip()
        if len(s) < 25 or len(s) > 300:
            continue
        # prefer a sentence carrying one of the numbers we extracted
        if days and any(str(d) in s for d in days):
            return s
        best = best or s
    return best
