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

def clean(t, is_name=False):
    if not t: return t
    t = strip_notes(t)
    t = name_dash(t) if is_name else prose_dash(t)
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
