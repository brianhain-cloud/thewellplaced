# -*- coding: utf-8 -*-
import json, re, sys, os, unicodedata, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import clean, handle

HERE = os.path.dirname(os.path.abspath(__file__))
J    = lambda f: json.load(open(os.path.join(HERE, f), encoding="utf-8"))

core   = J("spaces_core.json")
links  = J("spaces_links.json")
prose  = J("spaces_prose.json")
groups = J("groups.json")
events = J("events.json")

photos = json.load(open("/tmp/photos.json", encoding="utf-8"))
geo    = json.load(open("/tmp/geo.json", encoding="utf-8"))
cache  = {}
if os.path.exists(os.path.join(HERE, "geocache.json")):
    cache = json.load(open(os.path.join(HERE, "geocache.json"), encoding="utf-8"))

def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())

# entries renamed in Notion whose photo and coordinates should carry over
CARRY = {
    "centnerwellnessgables":         "Centner Wellness Coral Gables",
    "flamingopark":                  "Flamingo Park Aquatic Center",
    "polestarpilatesstudiodadeland": "Polestar Pilates, Dadeland",
}
photo_idx = {norm(k): v for k, v in photos.items()}
geo_idx   = {norm(k): v for k, v in geo.items()}
for new_key, old_name in CARRY.items():
    if norm(old_name) in photo_idx: photo_idx.setdefault(new_key, photo_idx[norm(old_name)])
    if norm(old_name) in geo_idx:   geo_idx.setdefault(new_key, geo_idx[norm(old_name)])

DAYRX = {"Mon": r"\bmon(day)?s?\b", "Tue": r"\btue(s|sday)?s?\b", "Wed": r"\bwed(nesday)?s?\b",
         "Thu": r"\bthu(r|rs|rsday)?s?\b", "Fri": r"\bfri(day)?s?\b",
         "Sat": r"\bsat(urday)?s?\b", "Sun": r"\bsun(day)?s?\b"}
ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def days_of(sched):
    if not sched: return []
    if re.search(r"\bdaily\b|\bevery day\b", sched, re.I): return ORDER[:]
    return [d for d in ORDER if re.search(DAYRX[d], sched, re.I)]

def geo_variants(addr):
    """Address spellings to try, best first.

    The Census geocoder wants a plain street address. It returns nothing for a
    unit number, a trailing country, or a venue name in front of the street,
    all of which are normal in Notion. So try the address as written, then
    progressively stripped, and stop at the first hit."""
    seen, out = set(), []
    def add(a):
        a = re.sub(r"\s{2,}", " ", a).strip(" ,")
        if a and a not in seen:
            seen.add(a); out.append(a)

    add(addr)
    a = re.sub(r",?\s*(United States|USA|US)\s*$", "", addr, flags=re.I)
    add(a)
    # "Jill Mallory Studio of Dance, 13270 SW 87th Ave, ..." -> drop the venue
    a = re.sub(r"^[^,]*[A-Za-z][^,]*,\s*(?=\d)", "", a)
    add(a)
    # Drop a unit, suite or floor. "Fl" is deliberately not in this list: it is
    # also the state, and stripping it took the zip code with it.
    a = re.sub(r",?\s*(Unit|Ste\.?|Suite|Apt\.?|Floor)\s*#?\s*[\w-]+", "", a, flags=re.I)
    a = re.sub(r",?\s*#\s*[\w-]+", "", a)
    add(a)
    # and finally anything parenthesised, e.g. "(Inside Upper Buena Vista)"
    add(re.sub(r"\s*\([^)]*\)", "", a))
    return out

def census(form):
    url = ("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
           "?address=" + urllib.parse.quote(form) + "&benchmark=2020&format=json")
    with urllib.request.urlopen(url, timeout=20) as r:
        m = json.load(r)["result"]["addressMatches"]
    return [round(m[0]["coordinates"]["y"], 5), round(m[0]["coordinates"]["x"], 5)] if m else None

def osm(form):
    """OpenStreetMap fallback. The Census file has real gaps, mostly newer
    streets and highway addresses, and it simply returns nothing for them."""
    url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=us&q="
           + urllib.parse.quote(form))
    req = urllib.request.Request(url, headers={
        "User-Agent": "thewellplaced.com build script (brianhain@gmail.com)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        m = json.load(r)
    return [round(float(m[0]["lat"]), 5), round(float(m[0]["lon"]), 5)] if m else None

def geocode(addr):
    if not addr: return None, False
    if addr in cache: return cache[addr], False
    ll = None
    for lookup, pause in ((census, 0.4), (osm, 1.1)):   # OSM asks for 1 req/sec
        for form in geo_variants(addr):
            try:
                ll = lookup(form)
            except Exception:
                ll = None
            time.sleep(pause)
            if ll: break
        if ll: break
    cache[addr] = ll
    return ll, True

def trim(o):
    return {k: v for k, v in o.items() if v not in (None, "", [], False)}

# ---------- Spaces ----------
active = [r for r in core if r["st"] != "Past (Archive)"]

# A Brand only collapses into one card when it is a real consumer brand, meaning
# every entry name starts with it. "City of Miami Parks" owns two different
# parks; those are not two locations of one business.
members = {}
for r in active:
    if r["br"]: members.setdefault(r["br"], []).append(r["n"])
brand_count = {b: len(ns) for b, ns in members.items()
               if len(ns) > 1 and all(n.startswith(b) for n in ns)}

places, geocoded = [], 0
for r in active:
    nm  = clean(r["n"], is_name=True)
    key = norm(r["n"])
    lk  = links.get(r["n"], [None] * 8)
    pr  = prose.get(r["n"], [None] * 8)
    note, space, getin, know, tip, park, bring, best = [clean(x) for x in pr]

    ll = geo_idx.get(key)
    if not ll and r.get("addr"):
        ll, hit = geocode(r["addr"])
        geocoded += 1 if hit else 0

    o = {"n": nm}
    br = r["br"] if r["br"] and brand_count.get(r["br"], 0) > 1 else None
    if br:
        bn = clean(br, is_name=True)
        o["br"]  = bn
        lab = nm[len(bn):].strip(" ,()") if nm.startswith(bn) else ""
        o["loc"] = lab or r["h"]
    o.update({
        "h": r["h"], "c": r["c"], "gf": r["gf"] or [], "v": r["v"] or [],
        "ac": r["ac"] or [], "plat": r["pf"] or [],
        "note": note, "space": space, "getin": getin, "know": know, "move": tip,
        "park": park, "bring": bring, "best": best,
        "hrs": clean(r.get("hrs")),
        # Addresses go through clean() too. A Notion address can carry an en dash
        # in a block range ("11th–15th St") and the no-dash rule covers the whole
        # site, not just the prose.
        "tel": r.get("tel"), "addr": clean(r.get("addr")),
        "w": lk[0], "book": lk[1],
        "ig": handle(lk[2], "instagram.com"), "fb": lk[3], "tt": handle(lk[4], "tiktok.com"),
        "yt": lk[5], "li": lk[6], "gmu": lk[7],
        "ll": ll, "soon": r["st"] == "Upcoming (Draft)",
        "add": "2026-08-10",
    })
    ph = photo_idx.get(key)
    if ph:
        o["img"] = ph[0]
        if len(ph) > 1: o["imgs"] = ph
    places.append(trim(o))

# ---------- Groups ----------
gs = []
for r in groups:
    o = {"n": clean(r["n"], is_name=True), "h": r["h"], "c": r["c"], "v": r["v"] or [],
         "gf": r["gf"] or [], "ac": r["ac"] or [],
         "fmt": r["fmt"], "who": r["who"] or [], "freq": r["freq"],
         "sched": clean(r["sched"]), "meet": clean(r["meet"]),
         "note": clean(r["note"]), "know": clean(r["know"]), "move": clean(r["tip"]),
         "bring": clean(r["bring"]),
         "w": r["w"], "book": r["book"], "ig": handle(r["ig"], "instagram.com"),
         "d": days_of(r["sched"]), "add": "2026-08-10"}
    ph = photo_idx.get(norm(r["n"]))
    if ph:
        o["img"] = ph[0]
        if len(ph) > 1: o["imgs"] = ph
    gs.append(trim(o))

# ---------- Events ----------
es = []
for r in events:
    o = {"n": clean(r["n"], is_name=True), "h": r["h"], "c": r["c"], "v": r["v"] or [],
         "who": r["who"] or [], "etype": r["etype"], "feat": r.get("feat", False),
         "draft": r.get("draft", False),
         "sched": clean(r["sched"]), "meet": clean(r["meet"]),
         "note": clean(r["note"]), "know": clean(r["know"]), "bring": clean(r["bring"]),
         "book": r["book"], "ig": handle(r["ig"], "instagram.com"),
         "ds": r["dstart"], "de": r["dend"],
         "d": days_of(r["sched"]), "add": "2026-08-10"}
    ph = photo_idx.get(norm(r["n"]))
    if ph:
        o["img"] = ph[0]
        if len(ph) > 1: o["imgs"] = ph
    es.append(trim(o))

json.dump(cache, open(os.path.join(HERE, "geocache.json"), "w"), indent=0)

def dump(name, arr):
    body = ",\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in arr)
    return "var %s = [\n%s\n];\n" % (name, body)

out = dump("PLACES", places) + dump("GROUPS", gs) + dump("EVENTS", es)
open(os.path.join(HERE, "data.js"), "w", encoding="utf-8").write(out)

print("spaces %d (multi-location brands: %d)  groups %d  events %d"
      % (len(places), sum(1 for b, c in brand_count.items() if c > 1), len(gs), len(es)))
print("geocoded fresh: %d | with coords: %d | without: %s"
      % (geocoded, sum(1 for p in places if p.get("ll")),
         ", ".join(p["n"] for p in places if not p.get("ll")) or "none"))
print("photos carried: %d spaces, %d groups, %d events"
      % (sum(1 for p in places if p.get("img")),
         sum(1 for g in gs if g.get("img")), sum(1 for e in es if e.get("img"))))
print("hours: %d | google maps links: %d | phone: %d"
      % (sum(1 for p in places if p.get("hrs")), sum(1 for p in places if p.get("gmu")),
         sum(1 for p in places if p.get("tel"))))
dashes = sum(out.count(c) for c in "—–")
print("dashes in data:", dashes)
if dashes:
    for line in out.split("\n"):
        if "—" in line or "–" in line:
            print("   !", line[:240])
