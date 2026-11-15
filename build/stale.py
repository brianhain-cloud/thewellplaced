"""List entries whose dates have gone stale, so they get fixed in Notion
before a deploy rather than noticed by a visitor.

    python3 build/stale.py           # report, exit 0
    python3 build/stale.py --strict  # exit 1 if anything is stale

Two kinds of staleness:

  1. A dated event or group whose end date has passed while its Notion Status
     is still Active. The page hides these on its own, but Notion should be
     moved to Past (Archive) or given the next date.
  2. Prose that names a specific date that has passed: "through Aug 12, 2026",
     "next verified session: Aug 16, 2026", "2026 dates are Sept 24-26".
     Only dates with a year are checked; "Sundays, 9 AM" is never flagged.

Reads the snapshots that sync.py writes, so run it after a sync.
"""
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# "Aug 31, 2026", "Sept. 21, 2026", "Sep 24–26, 2026", "Thu, Aug 27, 2026"
DATED = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?,?\s+(20\d\d)\b", re.I)
# "through the end of September 2026", "July 1–August 31 ... 2026" handled above;
# a bare month and year means the whole month.
MONTH_YEAR = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(20\d\d)\b", re.I)
ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


def last_date_in(text):
    """The latest explicit date mentioned in a piece of text, or None."""
    found = []
    for m in DATED.finditer(text):
        mon = MONTHS[m.group(1).lower()[:3]]
        day = int(m.group(3) or m.group(2))
        try:
            found.append(dt.date(int(m.group(4)), mon, day))
        except ValueError:
            pass
    for m in MONTH_YEAR.finditer(text):
        mon, yr = MONTHS[m.group(1).lower()[:3]], int(m.group(2))
        nxt = dt.date(yr + (mon == 12), mon % 12 + 1, 1)
        found.append(nxt - dt.timedelta(days=1))
    for m in ISO.finditer(text):
        try:
            found.append(dt.date(*map(int, m.groups())))
        except ValueError:
            pass
    return max(found) if found else None


def scan_text(kind, name, fields, out):
    for label, text in fields:
        if not isinstance(text, str):
            continue
        d = last_date_in(text)
        if d and d < TODAY:
            out.append((kind, name, "%s mentions %s" % (label, d.isoformat()), text))


def main():
    out = []

    for r in load("events.json"):
        if r.get("st") == "Past (Archive)":
            continue
        last = r.get("dend") or r.get("dstart")
        if last and last < TODAY.isoformat():
            out.append(("event", r["n"], "date ended %s" % last, "Status is still %s" % r.get("st")))
        scan_text("event", r["n"], [("schedule", r.get("sched")), ("note", r.get("note")),
                                    ("good to know", r.get("know"))], out)

    for r in load("groups.json"):
        if r.get("st") == "Past (Archive)":
            continue
        scan_text("group", r["n"], [("schedule", r.get("sched")), ("note", r.get("note")),
                                    ("good to know", r.get("know"))], out)

    prose = load("spaces_prose.json")
    for r in load("spaces_core.json"):
        if r.get("st") == "Past (Archive)":
            continue
        p = prose.get(r["n"], [None] * 8)
        scan_text("space", r["n"], [("hours", r.get("hrs")), ("good to know", p[3]),
                                    ("hot tip", p[4])], out)

    if not out:
        print("No stale dates. Checked against %s." % TODAY.isoformat())
        return 0
    print("%d stale item(s) as of %s. Fix these in Notion, then sync:\n"
          % (len(out), TODAY.isoformat()))
    for kind, name, why, text in out:
        print("  %-5s  %s\n         %s\n         %s\n" % (kind, name, why, text[:150]))
    return 1 if "--strict" in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())
