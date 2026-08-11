# -*- coding: utf-8 -*-
"""Pull the three Notion databases into the build snapshots.
Run this, then build.py.

    python3 build/sync.py            # write the snapshots
    python3 build/sync.py --dry-run  # show what would change, write nothing

Reads NOTION_TOKEN from the environment or from a .env file at the repo root.
The token is never printed, never committed, and never leaves this machine.
"""
import json, os, re, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"          # data-source era; databases/:id/query is gone

SOURCES = {
    "spaces": "63797e7d-5703-43b8-bfd7-d1d911ce35c9",
    "groups": "c885593e-a539-4446-8297-5d9e3039afaf",
    "events": "8b0e81cf-4edb-42dc-8662-a33f48c3b313",
}


def token():
    t = os.environ.get("NOTION_TOKEN")
    if not t:
        env = os.path.join(ROOT, ".env")
        if os.path.exists(env):
            for line in open(env, encoding="utf-8"):
                line = line.strip()
                if line.startswith("NOTION_TOKEN"):
                    t = line.split("=", 1)[1].strip().strip("'\"")
    if not t:
        sys.exit("No NOTION_TOKEN. Put it in .env at the repo root:\n"
                 "    NOTION_TOKEN=ntn_your_token_here\n"
                 "See README, 'Rebuilding from Notion'.")
    return t


def query(ds_id, tok):
    """Every row of one data source, following pagination."""
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            "%s/data_sources/%s/query" % (API, ds_id),
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + tok,
                     "Notion-Version": VERSION,
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                page = json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code == 401:
                sys.exit("Notion rejected the token (401). Check .env.")
            if e.code == 404:
                sys.exit("Notion returned 404 for %s.\nUsually this means the "
                         "integration has not been given access to the database. "
                         "Open the database in Notion, then ... > Connections > "
                         "add your integration.\n%s" % (ds_id, detail))
            sys.exit("Notion error %s: %s" % (e.code, detail))
        rows += page["results"]
        cursor = page.get("next_cursor")
        if not page.get("has_more"):
            return rows
        time.sleep(0.34)                       # Notion allows ~3 requests/second


# ---------------------------------------------------------------- field access
def prop(row, *names):
    """A property by any of its possible names. Notion stores a curly
    apostrophe in "Who It's For" on one database and a straight one on another,
    so both spellings have to be accepted."""
    props = row["properties"]
    for n in names:
        for variant in (n, n.replace("'", "’"), n.replace("’", "'")):
            if variant in props:
                return props[variant]
    return None


def rich(p):
    if not p:
        return None
    t = p["type"]
    if t in ("rich_text", "title"):
        s = "".join(x["plain_text"] for x in p[t]).strip()
        return s or None
    if t in ("url", "phone_number", "email"):
        return p[t] or None
    if t == "select":
        return p[t]["name"] if p[t] else None
    if t == "status":
        return p[t]["name"] if p[t] else None
    if t == "checkbox":
        return p[t]
    if t == "date":
        return (p[t] or {}).get("start")
    if t == "number":
        return p[t]
    return None


def multi(p):
    if not p or p["type"] != "multi_select":
        return []
    return [o["name"] for o in p["multi_select"]]


def date_part(v):
    return v[:10] if isinstance(v, str) and len(v) >= 10 else None


# ---------------------------------------------------------------- shapes
def build_spaces(rows):
    core, links, prose = [], {}, {}
    for r in rows:
        n = rich(prop(r, "Name"))
        if not n:
            continue
        core.append({
            "n": n,
            "br": rich(prop(r, "Brand")),
            "h": rich(prop(r, "Neighborhood")),
            "st": rich(prop(r, "Status")),
            "c": multi(prop(r, "Category")),
            "gf": multi(prop(r, "Good For")),
            "v": multi(prop(r, "The Vibe")),
            "ac": multi(prop(r, "Access")),
            "pf": multi(prop(r, "Platforms")) or None,
            "hrs": rich(prop(r, "Hours")),
            "tel": rich(prop(r, "Phone Number")),
            "addr": rich(prop(r, "Address")),
        })
        # order matters: build.py unpacks these positionally
        prose[n] = [rich(prop(r, "Curator Note")), rich(prop(r, "The Space")),
                    rich(prop(r, "Getting In")), rich(prop(r, "Good To Know")),
                    rich(prop(r, "Hot Tip")), rich(prop(r, "Getting There")),
                    rich(prop(r, "What to Bring")), rich(prop(r, "Best Time"))]
        links[n] = [rich(prop(r, "Website")), rich(prop(r, "Booking Link")),
                    rich(prop(r, "Instagram")), rich(prop(r, "Facebook")),
                    rich(prop(r, "TikTok")), rich(prop(r, "YouTube")),
                    rich(prop(r, "LinkedIn")), rich(prop(r, "Google Maps"))]
    core.sort(key=lambda x: x["n"].lower())
    return core, links, prose


def build_groups(rows):
    out = []
    for r in rows:
        n = rich(prop(r, "Name"))
        if not n:
            continue
        out.append({
            "n": n,
            "h": rich(prop(r, "Neighborhood")),
            "c": multi(prop(r, "Category")),
            "v": multi(prop(r, "The Vibe")),
            "gf": multi(prop(r, "Good For")),
            "ac": multi(prop(r, "Access")),
            "fmt": rich(prop(r, "Community Format")),
            "who": multi(prop(r, "Who It's For")),
            "freq": rich(prop(r, "Frequency Confidence")),
            "sched": rich(prop(r, "Recurring Schedule")),
            "meet": rich(prop(r, "Meeting Point")),
            "note": rich(prop(r, "Curator Note")),
            "know": rich(prop(r, "Good To Know")),
            "tip": rich(prop(r, "Hot Tip")),
            "bring": rich(prop(r, "What to Bring")),
            "w": rich(prop(r, "Website")),
            "book": rich(prop(r, "Link / RSVP")),
            "ig": rich(prop(r, "Instagram")),
        })
    return out


def build_events(rows):
    out = []
    for r in rows:
        n = rich(prop(r, "Name"))
        if not n:
            continue
        d = prop(r, "Date & Time")
        dv = (d or {}).get("date") or {}
        out.append({
            "n": n,
            "h": rich(prop(r, "Neighborhood")),
            "c": multi(prop(r, "Category")),
            "v": multi(prop(r, "The Vibe")),
            "who": multi(prop(r, "Who It's For")),
            "etype": rich(prop(r, "Event Type")),
            "feat": bool(rich(prop(r, "Featured"))),
            "sched": rich(prop(r, "Recurring Schedule")),
            "dstart": date_part(dv.get("start")),
            "dend": date_part(dv.get("end")),
            "meet": rich(prop(r, "Meeting Point")),
            "note": rich(prop(r, "Curator Note")),
            "know": rich(prop(r, "Good To Know")),
            "bring": rich(prop(r, "What to Bring")),
            "book": rich(prop(r, "Link / RSVP")),
            "ig": rich(prop(r, "Instagram")),
        })
    return out


# ---------------------------------------------------------------- write
def write(name, obj, dry):
    path = os.path.join(HERE, name)
    new = json.dumps(obj, ensure_ascii=False, indent=1) + "\n"
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if old == new:
        print("  %-22s unchanged" % name)
        return 0
    if not dry:
        open(path, "w", encoding="utf-8").write(new)
    print("  %-22s %s (%d -> %d bytes)" % (name, "WOULD CHANGE" if dry else "written",
                                           len(old), len(new)))
    return 1


def main():
    dry = "--dry-run" in sys.argv
    tok = token()
    print("Notion sync%s" % (" (dry run)" if dry else ""))

    raw = {}
    for key, ds in SOURCES.items():
        raw[key] = query(ds, tok)
        print("  %-22s %d rows" % (key, len(raw[key])))

    core, links, prose = build_spaces(raw["spaces"])
    groups = build_groups(raw["groups"])
    events = build_events(raw["events"])

    # A property rename in Notion would silently empty a column here, so shout
    # rather than quietly writing a snapshot with the guts missing.
    checks = [
        ("spaces category", sum(1 for r in core if r["c"])),
        ("spaces address", sum(1 for r in core if r["addr"])),
        ("spaces curator note", sum(1 for v in prose.values() if v[0])),
        ("groups schedule", sum(1 for r in groups if r["sched"])),
        ("events schedule or date", sum(1 for r in events if r["sched"] or r["dstart"])),
    ]
    print()
    bad = False
    for label, n in checks:
        print("  %-24s %d" % (label, n))
        if n == 0:
            bad = True
    if bad:
        sys.exit("\nA whole column came back empty. A property was probably renamed "
                 "in Notion; fix the name in sync.py before writing.")

    print()
    changed = 0
    changed += write("spaces_core.json", core, dry)
    changed += write("spaces_links.json", links, dry)
    changed += write("spaces_prose.json", prose, dry)
    changed += write("groups.json", groups, dry)
    changed += write("events.json", events, dry)

    print()
    if dry:
        print("Dry run, nothing written. %d file(s) would change." % changed)
    elif changed:
        print("%d file(s) changed. Next: python3 build/build.py" % changed)
    else:
        print("Already in sync.")


if __name__ == "__main__":
    main()
