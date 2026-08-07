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

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "photos-raw")
OUT = os.path.join(HERE, "photos")
HTML = os.path.join(HERE, "index.html")

TARGET_W = 1600
ASPECT = 16 / 10
MAX_KB = 220
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tif", ".tiff"}

# Filenames that do not resemble the entry name closely enough to auto-match.
ALIASES = {
    "anatomyfitness": "Anatomy Midtown",
    "barrysbootcamp": "Barry's Miami Midtown",
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
    return re.findall(r'\{n:"((?:[^"\\]|\\.)*)"', html)


def match_entry(filename, names):
    """Best entry match for a filename, or None."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"[\s_-]*\d+$", "", stem)          # drop trailing " 2", "_01"
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


def set_img(html, name, path):
    esc = re.escape(name)
    # already has img: -> replace it
    pat_existing = re.compile(r'(\{n:"' + esc + r'",)img:"[^"]*",')
    if pat_existing.search(html):
        return pat_existing.sub(lambda m: m.group(1) + 'img:"%s",' % path, html, count=1), "updated"
    pat = re.compile(r'(\{n:"' + esc + r'",)')
    if not pat.search(html):
        return html, "entry-not-found"
    return pat.sub(lambda m: m.group(1) + 'img:"%s",' % path, html, count=1), "added"


def main():
    if not os.path.isdir(RAW):
        sys.exit("No photos-raw/ folder. Create it and drop photos in.")
    os.makedirs(OUT, exist_ok=True)
    html = open(HTML, encoding="utf-8").read()
    names = entry_names(html)

    files = sorted(f for f in os.listdir(RAW)
                   if os.path.splitext(f)[1].lower() in EXTS and not f.startswith("."))
    if not files:
        sys.exit("photos-raw/ is empty — drop some photos in first.")

    done, skipped = [], []
    for f in files:
        name = match_entry(f, names)
        if not name:
            skipped.append((f, "no matching entry"))
            continue
        slug = slugify(name)
        dst = os.path.join(OUT, slug + ".jpg")
        q, size = process_image(os.path.join(RAW, f), dst)
        html, status = set_img(html, name, "photos/%s.jpg" % slug)
        done.append((f, name, slug, q, size // 1024, status))

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
