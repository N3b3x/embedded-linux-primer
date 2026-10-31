#!/usr/bin/env python3
"""Check that every relative link and image in the Markdown files points at a file that exists.

Usage: tools/check-links.py            (run from anywhere; checks the whole repository)

External links (http, https, mailto) and pure #anchors are not checked: CI must not depend on
the network. Anchors on relative links (file.md#section) are checked for the file only.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP_DIRS = {".git", "build", "node_modules", "__pycache__"}
# [text](target) and <img src="target">; the target ends at whitespace or ')'
LINK = re.compile(r"""(?:\]\(|(?<![\w-])src=")([^)"\s]+)""")
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        # site/ holds pages written for the site itself, with site-relative links
        if os.path.abspath(dirpath) == ROOT and "site" in dirnames:
            dirnames.remove("site")
        for f in filenames:
            if f.endswith(".md"):
                yield os.path.join(dirpath, f)


def main():
    bad = 0
    checked = 0
    for md in sorted(markdown_files()):
        in_fence = False
        with open(md, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if FENCE.match(line):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                # inline code can show example links; drop it before matching
                line = re.sub(r"`[^`]*`", "", line)
                for target in LINK.findall(line):
                    if re.match(r"^(https?:|mailto:|#)", target):
                        continue
                    path = target.split("#", 1)[0]
                    if not path:
                        continue
                    checked += 1
                    full = os.path.normpath(os.path.join(os.path.dirname(md), path))
                    if not os.path.exists(full):
                        bad += 1
                        print("%s:%d: broken link -> %s" % (os.path.relpath(md, ROOT), lineno, target))
    print("checked %d relative links, %d broken" % (checked, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
