# -*- coding: utf-8 -*-
"""House style: no em or en dashes anywhere on the site."""
import re

EM = "—"; EN = "–"; NB = "‑"

# editorial notes-to-self that should never reach a reader
NOTES = [
    r"\s*Verify before publishing\.?",
    r"\s*Confirm before publishing\.?",
    r"\s*verify before attending\.?",
    r"\s*Schedule subject to change\.?",
]

def strip_notes(t):
    if not t: return t
    for p in NOTES:
        t = re.sub(p, "", t, flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip().rstrip(";").strip()

def name_dash(t):
    """Entry names: 'Reserve Padel — Design District' becomes 'Reserve Padel, Design District'."""
    if not t: return t
    return re.sub(r"\s*[" + EM + EN + r"]\s*", ", ", t).strip()

def prose_dash(t):
    """Prose: ranges become 'to', parentheticals become commas or short sentences."""
    if not t: return t
    # numeric / day / month ranges read as "to"
    t = re.sub(r"(\d(?::\d{2})?\s*(?:AM|PM|am|pm)?)\s*[" + EM + EN + r"]\s*(\d)", r"\1 to \2", t)
    t = re.sub(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)([a-z]*)\s*[" + EM + EN + r"]\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", r"\1\2 to \3", t)
    t = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)([a-z]*\.?)\s*[" + EM + EN + r"]\s*", r"\1\2 to ", t)
    t = re.sub(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|November|December|January|February|March|April|June|July|August|September|October)\s*[" + EM + EN + r"]\s*", r"\1 to ", t)
    t = re.sub(r"(\d)\s*[" + EM + EN + r"]\s*", r"\1 to ", t)
    # a dash before a lowercase word joins with a comma
    t = re.sub(r"\s*[" + EM + EN + r"]\s*([a-z])", r", \1", t)
    # a dash before a capital starts a new sentence
    t = re.sub(r"\s*[" + EM + EN + r"]\s*([A-Z0-9])", r". \1", t)
    t = t.replace(EM, ", ").replace(EN, " to ").replace(NB, "-")
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\.\s*\.", ".", t)
    t = re.sub(r",\s*,", ",", t)
    return t.strip()

URL_RX = re.compile(r"(?:https?://|www\.)\S+", re.I)
# a run of two or more slash-joined items: "hot/cold", "Mon/Wed/Fri"
RUN_RX = re.compile(r"[\w'’&$+.-]*\w(?:\s*/\s*\w[\w'’&$+.-]*)+")

# Category and neighbourhood names are written with a slash and must keep it.
# build.py fills this from the live data so the list cannot drift.
VOCAB = set()

def set_vocab(names):
    VOCAB.clear()
    VOCAB.update(n for n in names if n and "/" in n)

def slashes(t):
    """No slashes in prose. "hot/cold plunges" reads as "hot and cold plunges".

    Three things keep theirs: a URL, a name from the house vocabulary such as
    Yoga/Pilates or North Miami/NMB, and a pair of numbers so 24/7 and $28/90min
    survive. Everything else becomes a list: two items joined with "and", three
    or more with commas and a final "and"."""
    if not t or "/" not in t: return t
    holes = []
    def stash(s):
        holes.append(s)
        return "\x00%d\x00" % (len(holes) - 1)
    t = URL_RX.sub(lambda m: stash(m.group(0)), t)
    for v in sorted(VOCAB, key=len, reverse=True):
        if v in t: t = t.replace(v, stash(v))

    def swap(m):
        run = m.group(0)
        parts = [p.strip() for p in run.split("/")]
        # a number on both sides of any slash is a ratio or a date, not a list
        for a, b in zip(parts, parts[1:]):
            if a and b and a[-1].isdigit() and b[0].isdigit(): return run
        if len(parts) == 2: return parts[0] + " and " + parts[1]
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    t = RUN_RX.sub(swap, t)

    for i, h in enumerate(holes):
        t = t.replace("\x00%d\x00" % i, h)
    return t

def clean(t, is_name=False):
    if not t: return t
    t = strip_notes(t)
    t = name_dash(t) if is_name else prose_dash(t)
    if not is_name: t = slashes(t)
    t = t.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    return t.strip()

def handle(url, host):
    """instagram.com/foo/ -> foo"""
    if not url: return None
    m = re.search(host + r"/([^/?#]+)", url)
    if not m: return None
    h = m.group(1).lstrip("@")
    return h if h and h not in ("p", "explore", "groups", "people", "company", "channel", "user", "c") else None
