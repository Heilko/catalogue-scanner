"""
The seed list.

Ordering follows the brief: Madrid Fashion Week exhibitors first, because the client
was an official partner of the show and those are the conversations that can happen
in the same week; then Spanish DTC brands running their own e-commerce; then footwear
and accessories, which skew heavily flat-lay; then European brands one step out.

Nothing here came from behind a login or off a bought list. Brand names and their
own public domains, which is all this needs.

CUSTOMERS holds the domains the client already works with, so the report can label
them and hold them out of the pitch — handing a founder his own client list back is
the fastest possible way to look careless. That list was the client's own and is not
published here; it is empty in this repository and filled in at run time.
"""

# Domains the client already sells to. Scanned as a control, labelled, never pitched.
# Deliberately empty here: the real list belongs to the client, not to this repository.
CUSTOMERS = set()

# (domain, display name, bucket)
SEED = [
    # ---- MBFW Madrid, Sept 14-19. The client is an official partner. --------
    ("palomospain.com",         "Palomo Spain",           "mbfw"),
    ("duyos.com",               "Juan Duyos",             "mbfw"),
    ("angelschlesser.com",      "Ángel Schlesser",        "mbfw"),
    ("custo.com",               "Custo Barcelona",        "mbfw"),
    ("robertoverino.com",       "Roberto Verino",         "mbfw"),
    ("devotaylomba.com",        "Devota & Lomba",         "mbfw"),
    ("hanniballaguna.com",      "Hannibal Laguna",        "mbfw"),
    ("ulisesmerida.com",        "Ulises Mérida",          "mbfw"),
    ("pedrodelhierro.com",      "Pedro del Hierro",       "mbfw"),
    ("isabelsanchis.com",       "Isabel Sanchís",         "mbfw"),
    ("teresahelbig.com",        "Teresa Helbig",          "mbfw"),
    ("dominnico.com",           "Dominnico",              "mbfw"),
    ("the2ndskinco.com",        "The 2nd Skin Co",        "mbfw"),
    ("marcosluengo.com",        "Marcos Luengo",          "mbfw"),
    ("malne.es",                "Malne",                  "mbfw"),

    # ---- Spanish DTC apparel ------------------------------------------------
    ("scalperscompany.com",     "Scalpers",               "es-dtc"),
    ("silbonshop.com",          "Silbon",                 "es-dtc"),
    ("elganso.com",             "El Ganso",               "es-dtc"),
    ("sepiia.com",              "Sepiia",                 "es-dtc"),
    ("bravafabrics.com",        "Brava Fabrics",          "es-dtc"),
    ("thinkingmu.com",          "Thinking MU",            "es-dtc"),
    ("pompeiibrand.com",        "Pompeii",                "es-dtc"),
    ("laagam.com",              "Laagam",                 "es-dtc"),
    ("ecoalf.com",              "Ecoalf",                 "es-dtc"),
    ("bimbaylola.com",          "Bimba y Lola",           "es-dtc"),
    ("adolfodominguez.com",     "Adolfo Domínguez",       "es-dtc"),
    ("dolorespromesas.com",     "Dolores Promesas",       "es-dtc"),
    ("lolacasademunt.com",      "Lola Casademunt",        "es-dtc"),
    ("theextremecollection.com","The Extreme Collection", "es-dtc"),
    ("skfk.com",                "Skunkfunk",              "es-dtc"),
    ("twothirds.com",           "TwoThirds",              "es-dtc"),
    ("brownieshop.com",         "Brownie",                "es-dtc"),
    ("hossintropia.com",        "Hoss Intropia",          "es-dtc"),
    ("nicoli.es",               "Nícoli",                 "es-dtc"),
    ("slowlove.es",             "Slowlove",               "es-dtc"),
    ("poete.com",               "Poète",                  "es-dtc"),
    ("sixvalves.com",           "Six Valves",             "es-dtc"),
    ("nudeproject.com",         "Nude Project",           "es-dtc"),

    # ---- footwear and accessories: the flat-lay heartland -------------------
    ("castaner.com",            "Castañer",               "es-shoes"),
    ("pikolinos.com",           "Pikolinos",              "es-shoes"),
    ("mustang.es",              "Mustang",                "es-shoes"),
    ("gioseppo.com",            "Gioseppo",               "es-shoes"),
    ("hispanitas.com",          "Hispanitas",             "es-shoes"),
    ("wonders.com",             "Wonders",                "es-shoes"),
    ("unisa-europa.com",        "Unisa",                  "es-shoes"),
    ("carminashoemaker.com",    "Carmina Shoemaker",      "es-shoes"),
    ("meermin.es",              "Meermin",                "es-shoes"),
    ("magnanni.com",            "Magnanni",               "es-shoes"),
    ("lottusse.com",            "Lottusse",               "es-shoes"),
    ("panamajack.es",           "Panama Jack",            "es-shoes"),
    ("chiemihara.com",          "Chie Mihara",            "es-shoes"),
    ("prettyballerinas.com",    "Pretty Ballerinas",      "es-shoes"),
    ("muroexe.com",             "Muroexe",                "es-shoes"),
    ("hoffshoes.com",           "Hoff",                   "es-shoes"),
    ("bibilou.com",             "Bibi Lou",               "es-shoes"),

    # ---- Europe, one step out ----------------------------------------------
    ("sezane.com",              "Sézane",                 "eu"),
    ("rouje.com",               "Rouje",                  "eu"),
    ("ba-sh.com",               "ba&sh",                  "eu"),
    ("nanushka.com",            "Nanushka",               "eu"),
    ("ganni.com",               "Ganni",                  "eu"),
    ("samsoe.com",              "Samsøe Samsøe",          "eu"),
    ("lesdeux.com",               "Les Deux",             "eu"),
    ("nakd.com",                "NA-KD",                  "eu"),
    ("stinegoya.com",           "Stine Goya",             "eu"),
    ("filippa-k.com",           "Filippa K",              "eu"),
    ("holzweiler.com",          "Holzweiler",             "eu"),
    ("rotatebirgerchristensen.com", "ROTATE",             "eu"),

]

BUCKET_LABEL = {
    "mbfw":     "MBFW Madrid exhibitor",
    "es-dtc":   "Spanish DTC apparel",
    "es-shoes": "Spanish footwear / accessories",
    "eu":       "European",
    "customer": "already a customer",
}


def is_customer(domain):
    d = domain.lower().removeprefix("www.")
    return d in CUSTOMERS


def seed():
    return list(SEED)
