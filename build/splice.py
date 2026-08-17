# -*- coding: utf-8 -*-
"""Drop the freshly built arrays into the page.

    python3 build/splice.py

Replaces PLACES, GROUPS and EVENTS in public/index.html with the ones in
build/data.js and leaves everything else untouched. Lives in the repo rather
than a temp folder, because a build step that disappears is not a build step.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HTML = os.path.join(ROOT, "public", "index.html")
DATA = os.path.join(HERE, "data.js")


def block(src, name):
    """Span of `var NAME = [ ... ];`, found by counting brackets so a bracket
    inside a string cannot end the match early."""
    start = src.index("var " + name + " = [")
    i = src.index("[", start)
    depth, in_str, esc = 0, None, False
    for j in range(i, len(src)):
        ch = src[j]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == in_str: in_str = None
            continue
        if ch in "\"'":
            in_str = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return start, src.index(";", j) + 1
    sys.exit("unterminated array: " + name)


def main():
    html = open(HTML, encoding="utf-8").read()
    data = open(DATA, encoding="utf-8").read()
    before = len(html)

    for name in ("PLACES", "GROUPS", "EVENTS"):
        hs, he = block(html, name)
        ds, de = block(data, name)
        html = html[:hs] + data[ds:de] + html[he:]

    open(HTML, "w", encoding="utf-8").write(html)
    print("index.html %d -> %d bytes" % (before, len(html)))
    for name in ("PLACES", "GROUPS", "EVENTS"):
        s, e = block(html, name)
        print("  %-7s %d bytes" % (name, e - s))


if __name__ == "__main__":
    main()
