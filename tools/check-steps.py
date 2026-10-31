#!/usr/bin/env python3
"""Check the walkthrough files (*.steps.json) against the SVG each one belongs to.

For every <diagram>.steps.json next to <diagram>.svg:
  - the file is valid JSON of the documented shape (see docs/interactive-diagrams.md);
  - every text anchor matches at least one <text> element of the SVG (an exact match is
    preferred at run time, a substring match is the fallback), and `nth` exists;
  - every `id:` anchor names an id that exists in the SVG.
This is a text-level check: it cannot tell how big the highlighted box will be. The browser check
(tools/check-steps.sh) resolves the anchors against the real layout.

Usage: tools/check-steps.py [files...]       (default: every *.steps.json in the repository)
"""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP = {"build", ".git", "node_modules"}


def norm(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def svg_texts(path):
    with open(path, encoding="utf-8") as fh:
        data = fh.read()
    texts = [norm(m) for m in re.findall(r"<text[^>]*>(.*?)</text>", data, flags=re.S)]
    ids = set(re.findall(r'\bid="([^"]+)"', data))
    return texts, ids


def find_all():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP]
        out += [os.path.join(dp, f) for f in fn if f.endswith(".steps.json")]
    return sorted(out)


def check(path):
    problems = []
    svg = path[: -len(".steps.json")] + ".svg"
    if not os.path.exists(svg):
        return ["no matching SVG: " + os.path.relpath(svg, ROOT)]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as e:
        return ["invalid JSON: %s" % e]
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["'steps' must be a non-empty list"]
    texts, ids = svg_texts(svg)
    for i, s in enumerate(steps, 1):
        where = "step %d" % i
        if not s.get("title"):
            problems.append(where + ": missing title")
        if not s.get("body"):
            problems.append(where + ": missing body")
        for k in s:
            if k not in {"anchor", "title", "body", "nth", "up", "pad", "exact"}:
                problems.append("%s: unknown key '%s'" % (where, k))
        a = s.get("anchor")
        for item in ([] if a is None else a if isinstance(a, list) else [a]):
            if not isinstance(item, str):
                problems.append(where + ": anchors must be strings")
                continue
            if item.startswith("rect:"):
                if not re.match(r"^rect:\s*[-\d.]+[,\s]+[-\d.]+[,\s]+[-\d.]+[,\s]+[-\d.]+\s*$", item):
                    problems.append("%s: bad rect anchor %r" % (where, item))
            elif item.startswith("id:"):
                if item[3:] not in ids:
                    problems.append("%s: id not in the SVG: %s" % (where, item[3:]))
            else:
                want = norm(item)
                exact = [t for t in texts if t == want]
                hits = exact or [t for t in texts if want in t]
                if not hits:
                    problems.append("%s: no <text> matches %r" % (where, item))
                elif s.get("nth", 0) >= len(hits):
                    problems.append("%s: nth=%d but only %d match(es) for %r" % (where, s["nth"], len(hits), item))
    return problems


def main():
    files = sys.argv[1:] or find_all()
    bad = 0
    for f in files:
        probs = check(f)
        for p in probs:
            print("%s: %s" % (os.path.relpath(f, ROOT), p))
        bad += len(probs)
    print("checked %d walkthrough file(s), %d problem(s)" % (len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
