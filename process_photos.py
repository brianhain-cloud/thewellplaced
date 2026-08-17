#!/usr/bin/env python3
"""
The Well Placed — photo pipeline.

Drop raw photos into photos-raw/ (any size, any format: jpg, png, webp, heic-as-jpg).
Run this. It will:

  1. Match each file to a guide entry by filename
  2. Crop to 16:10, resize to 1600px wide
  3. Compress to roughly 200KB
  4. Write photos/<slug>.jpg
  5. Add img:"photos/<slug>.jpg" to that entry in index.html

Filenames just need to resemble the entry name. All of these match "Ahana Yoga":
  Ahana_Yoga.webp   ahana-yoga.jpg   Ahana Yoga 2.png   ahanayoga.JPG

Re-running is safe: existing img: fields are updated, not duplicated.
"""

import os, re, sys, json, unicodedata
from PIL import Image, ImageOps
try:
    import pillow_avif            # noqa: F401  registers .avif with Pillow
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "public", "photos")
HTML = os.path.join(HERE, "public", "index.html")

# Where to look for raw photos, in order. The Desktop folder is where the
# photos actually get dropped; photos-raw/ stays supported so nothing that
# already lived there stops working. A pass a directory on the command line to
# use a different one.
RAW_DIRS = [
    os.path.join(HERE, "photos-raw"),
    os.path.expanduser("~/Desktop/Well Placed Photos"),
]

TARGET_W = 1600
ASPECT = 16 / 10
MAX_KB = 220
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tif", ".tiff"}

# Filenames that do not resemble the entry name closely enough to auto-match.
ALIASES = {
    "anatomyfitness": "Anatomy Midtown",
    "tangotimesdancecompany": "Tango Times Dance Studio",
    "tangoetiempo": "Tango a Tiempo",
    "valentejiujitsu": "Valente Brothers Jiu-Jitsu",
    "thursdayeveningyogaatvizcaya": "Thursday Evening Yoga, Vizcaya Station Plaza",
    "barrysbootcamp": "Barry's Miami Midtown",
    "biscaynenationalpark": "Biscayne National Park, Dante Fascell Visitor Center",
    "biohackitwomenshealthworkshop": "Biohack-It Women's Health Workshop & Panel",
    "breathetribe": "BreathTribe Miami",
    "bunda": "BÜNDA Coral Gables",
    "carillonwellness": "Carillon Miami Wellness Resort",
    "clubpilates": "Club Pilates South Beach",
    "clubstudio": "Club Studio Miami",
    "coffeeandchillmiami": "Coffee & Chill",
    "davidkennedypark": "David T. Kennedy Park",
    "dolphinsrainbows": "Dolphins & Rainbows Swim Group",
    "eosfitness": "EoS Fitness Kendall",
    "fullmoonyogasynergy": "Full Moon Yoga & Ceremony South Pointe",
    "girlsonthewalk": "Girls On the Walk Miami",
    "hiitruntheunderline": "HIIT & RUN at The Underline",
    "jetset": "JETSET Pilates Sunset Harbour",
    "kasayoga": "Kasa Yoga Studio",
    "legacylittleriver": "LEGACY Little River",
    "lifetimegables": "Life Time Gables",
    "lincolnroadcommunityyoga": "Lincoln Road Free Community Yoga",
    "mimiyoga": "Mimi Yoga & Pilates (Wynwood)",
    "normandyislepark": "Normandy Isle Park & Pool",
    "ommovement": "Om Movement",
    "padelxmiami": "Padel X",
    "pausestudio": "Pause Studio Brickell",
    "polestarpilates": "Polestar Pilates Studio, Dadeland",
    "rawfitmiami": "Raw Fit-Miami",
    "reservepadel": "Reserve Padel, Seaplane Base",
    "reservepadeldesigndistrict": "Reserve Padel, Design District",
    "resetcryotherapy": "Reset Cryotherapy South Beach",
    "restorativesoundbathatbotanicalgarden": "Restorative Sound Bath Meditation",
    "skandayoga": "Skanda Yoga Studio",
    "studiothreemiami": "Studio Three",
    "sunsetyogasouthpointepark": "Sunset Yoga at South Pointe Park",
    "sweat440": "SWEAT440 Brickell",
    "theboardwalks": "The Board Walks, Miami",
    "thestandardmiami": "The Standard Spa",
    "theunderline": "The Underline, Brickell Backyard",
    "tremble": "TREMBLE Brickell",
    "ufcmiami": "UFC Gym Doral",
    "ultimatewellnessconference": "Ultimate Wellness Conference at Faena Forum",
    "ultrapadelaventura": "Ultra Padel Club, Aventura",
    "ultrapadelmagiccity": "Ultra Padel Club (Magic City)",
    "vizcayavillagewellnessclasses": "Vizcaya Village Sunday Wellness Classes",
    "werunthecity": "We Run The City",
    "yogaintheparkaventura": "Yoga in the Park, Aventura",
    "youfitgyms": "YouFit Gyms Coral Way",
}


def deaccent(s):
    """BÜNDA -> BUNDA, Jūce -> Juce, so accents never break a match."""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def norm(s):
    """Loose key for matching: lowercase alphanumerics, accents folded."""
    return re.sub(r"[^a-z0-9]", "", deaccent(s).lower())


def slugify(s):
    s = deaccent(s).lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def entry_names(html):
    return re.findall(r'\{"n":"((?:[^"\\]|\\.)*)"', html)


def photo_index(filename):
    """Trailing number picks the order: 'Venetian Pool 2.jpg' is the second photo."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    m = re.search(r"[\s_-]+(\d+)$", stem)
    return int(m.group(1)) if m else 1


def match_entry(filename, names):
    """Best entry match for a filename, or None."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    # Drop a trailing photo number: "Venetian Pool 2", "Pause Studio_01". The
    # separator is required. Without it "F45" lost its digits, became "F", and
    # a one letter key then matched by containment against almost every entry,
    # landing the F45 photo on Biscayne National Park.
    stem = re.sub(r"[\s_-]+\d+$", "", stem)
    key = norm(stem)
    if not key:
        return None
    if key in ALIASES and ALIASES[key] in names:
        return ALIASES[key]
    exact = [n for n in names if norm(n) == key]
    if exact:
        return exact[0]
    # containment either direction, longest wins
    cands = [n for n in names if norm(n) and (norm(n) in key or key in norm(n))]
    # A short key carries little signal, so it has to start the entry name
    # rather than merely appear inside it. "f45" still finds F45 Training;
    # a stray "f" no longer finds Biscayne National Park.
    if len(key) < 5:
        cands = [n for n in cands if norm(n).startswith(key)]
    if cands:
        return max(cands, key=lambda n: len(norm(n)))
    return None


def process_image(src, dst):
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)                  # honour phone rotation
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    elif im.mode == "L":
        im = im.convert("RGB")

    # centre-crop to 16:10
    w, h = im.size
    if w / h > ASPECT:
        new_w = int(h * ASPECT)
        im = im.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:
        new_h = int(w / ASPECT)
        im = im.crop((0, (h - new_h) // 2, w, (h - new_h) // 2 + new_h))

    if im.width > TARGET_W:
        im = im.resize((TARGET_W, int(TARGET_W / ASPECT)), Image.LANCZOS)

    for q in (82, 76, 70, 64, 58, 52):
        im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(dst) <= MAX_KB * 1024:
            return q, os.path.getsize(dst)
    return q, os.path.getsize(dst)


def set_imgs(html, name, paths):
    """Write img: (the lead photo) and imgs: (the full carousel) for one entry."""
    esc = re.escape(name)
    field = '"img":"%s",' % paths[0]
    if len(paths) > 1:
        field += '"imgs":[%s],' % ",".join('"%s"' % p for p in paths)
    html = re.sub(r'(\{"n":"' + esc + r'",)"img":"[^"]*",("imgs":\[[^\]]*\],)?',
                  lambda m: m.group(1), html, count=1)
    pat = re.compile(r'(\{"n":"' + esc + r'",)')
    if not pat.search(html):
        return html, "entry-not-found"
    return pat.sub(lambda m: m.group(1) + field, html, count=1), (
        "%d photos" % len(paths) if len(paths) > 1 else "1 photo")


def main():
    dirs = [os.path.expanduser(a) for a in sys.argv[1:]] or RAW_DIRS
    dirs = [d for d in dirs if os.path.isdir(d)]
    if not dirs:
        sys.exit("No photo folder found. Looked in:\n  " + "\n  ".join(RAW_DIRS))

    os.makedirs(OUT, exist_ok=True)
    html = open(HTML, encoding="utf-8").read()
    names = entry_names(html)

    # full paths, first directory wins when a filename appears in both
    files, seen = [], set()
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if f.startswith(".") or os.path.splitext(f)[1].lower() not in EXTS:
                continue
            if f.lower() in seen:
                continue
            seen.add(f.lower())
            files.append(os.path.join(d, f))
    print("Reading from:")
    for d in dirs:
        print("  %s" % d)
    print("%d image file(s) found.\n" % len(files))
    if not files:
        sys.exit("No images in those folders.")

    # group every raw file by the entry it belongs to, ordered by any trailing number
    groups, skipped = {}, []
    for f in files:
        name = match_entry(f, names)
        if not name:
            skipped.append((os.path.basename(f), "no matching entry"))
            continue
        groups.setdefault(name, []).append(f)

    done = []
    for name, fl in sorted(groups.items()):
        fl.sort(key=lambda x: (photo_index(x), x))
        slug = slugify(name)
        paths = []
        for i, f in enumerate(fl):
            suffix = "" if i == 0 else "-%d" % (i + 1)
            dst = os.path.join(OUT, slug + suffix + ".jpg")
            try:
                q, size = process_image(f, dst)
            except Exception as e:
                skipped.append((os.path.basename(f), "could not read: %s" % e))
                continue
            paths.append("photos/%s%s.jpg" % (slug, suffix))
            done.append((os.path.basename(f), name, slug + suffix, q, size // 1024, ""))
        if not paths:
            continue
        html, status = set_imgs(html, name, paths)
        done[-1] = done[-1][:5] + (status,)

    open(HTML, "w", encoding="utf-8").write(html)

    print("Processed %d photo(s):\n" % len(done))
    for f, name, slug, q, kb, status in done:
        print("  %-28s -> %-32s %4dKB  q%d  (%s)" % (f[:28], slug + ".jpg", kb, q, status))
    if skipped:
        print("\nSkipped %d:" % len(skipped))
        for f, why in skipped:
            print("  %-28s %s" % (f[:28], why))
        print("\n  Rename these to match an entry name and re-run.")
    total = sum(kb for *_, kb, _ in done)
    print("\nTotal added: %d KB across %d files." % (total, len(done)))


if __name__ == "__main__":
    main()
