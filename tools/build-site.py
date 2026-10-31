#!/usr/bin/env python3
"""Assemble the documentation site and build it with MkDocs.

The Markdown of this repository lives next to the code it describes (docs/, boards/*/README.md,
boards/*/docs/), which is what you want on GitHub but not what MkDocs wants (one docs_dir). This
script copies everything into build/site-src/, rewrites every relative link so it still works there
(links to files that are not part of the site become links to the file on GitHub), generates the
navigation, and runs MkDocs.

    python3 tools/build-site.py              build into build/site-out/
    python3 tools/build-site.py --strict     fail on any warning (what CI runs)
    python3 tools/build-site.py --serve      live preview at http://127.0.0.1:8000
    python3 tools/build-site.py --no-build   only assemble build/site-src/ and build/mkdocs.yml

Needs: pip install -r requirements-docs.txt
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(ROOT, "build")
SRC = os.path.join(BUILD, "site-src")
REPO_URL = "https://github.com/N3b3x/embedded-linux-primer"
BRANCH = "main"

# Tab names for the boards; a board that is not listed gets its directory name.
BOARD_TITLES = {
    "imx8mp-variscite": "i.MX 8M Plus",
    "stm32mp1-dk2": "STM32MP1",
    "stm32mp2-dk": "STM32MP2",
    "zynq7000-eclypse-z7": "Zynq-7000",
    "jetson-orin-nano": "Jetson Orin Nano",
}
SKIP_DIRS = {"_src", "__pycache__", "icons", "build", ".git"}
COPY_EXT = {".md", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".json"}

LINK = re.compile(r"""(\]\(|(?<![\w-])(?:src|href)=")([^)"\s]+)""")
FENCE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN = re.compile(r"(`[^`]*`)")


def rel(path):
    return os.path.relpath(path, ROOT)


def collect():
    """Return {absolute source path: destination path relative to site-src}."""
    m = {}

    def add(src, dest):
        m[src] = dest.replace(os.sep, "/")

    add(os.path.join(ROOT, "site", "index.md"), "index.md")
    for sub in ("stylesheets", "assets", "javascripts"):
        base = os.path.join(ROOT, "site", sub)
        for dp, dn, fn in os.walk(base):
            for f in fn:
                src = os.path.join(dp, f)
                add(src, os.path.join(sub, os.path.relpath(src, base)))

    def walk_docs(base, dest_base):
        for dp, dn, fn in os.walk(base):
            dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
            for f in sorted(fn):
                if os.path.splitext(f)[1].lower() not in COPY_EXT:
                    continue
                src = os.path.join(dp, f)
                r = os.path.relpath(src, base)
                if r == "README.md":
                    r = "index.md"
                add(src, os.path.join(dest_base, r))

    walk_docs(os.path.join(ROOT, "docs"), "docs")
    boards = os.path.join(ROOT, "boards")
    for b in sorted(os.listdir(boards)):
        bdir = os.path.join(boards, b)
        if not os.path.isdir(bdir):
            continue
        readme = os.path.join(bdir, "README.md")
        if os.path.exists(readme):
            add(readme, "boards/%s/index.md" % b)
        walk_docs(os.path.join(bdir, "docs"), "boards/%s/docs" % b)
    for name, dest in (("CONTRIBUTING.md", "contributing.md"), ("THIRD_PARTY_NOTICES.md", "third-party.md")):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            add(p, dest)
    # the repository README is the front page on GitHub, the site has its own landing page
    add(os.path.join(ROOT, "README.md"), "index.md")
    return m


def github_url(abs_path):
    r = rel(abs_path).replace(os.sep, "/")
    kind = "tree" if os.path.isdir(abs_path) else "blob"
    return "%s/%s/%s/%s" % (REPO_URL, kind, BRANCH, r)


def rewrite(text, src, mapping, warnings):
    dest = mapping[src]
    dest_dir = os.path.dirname(dest)
    out = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        def fix(m):
            prefix, target = m.group(1), m.group(2)
            if re.match(r"^(https?:|mailto:|#|data:|/)", target):
                return m.group(0)
            path, _, anchor = target.partition("#")
            if not path:
                return m.group(0)
            abs_t = os.path.normpath(os.path.join(os.path.dirname(src), path))
            if os.path.isdir(abs_t) and os.path.join(abs_t, "README.md") in mapping:
                abs_t = os.path.join(abs_t, "README.md")
            if abs_t in mapping:
                new = os.path.relpath(mapping[abs_t], dest_dir or ".").replace(os.sep, "/")
            elif os.path.exists(abs_t):
                new = github_url(abs_t)
            else:
                warnings.append("%s:%d: link target does not exist: %s" % (rel(src), lineno, target))
                return m.group(0)
            return prefix + new + ("#" + anchor if anchor else "")

        parts = CODE_SPAN.split(line)
        for i in range(0, len(parts), 2):  # even parts are outside inline code
            parts[i] = LINK.sub(fix, parts[i])
        out.append("".join(parts))
    return "\n".join(out)


def title_of(path):
    with open(path, encoding="utf-8") as fh:
        in_fence = False
        for line in fh:
            if FENCE.match(line):
                in_fence = not in_fence
            if not in_fence and line.startswith("# "):
                t = re.sub(r"<[^>]+>", "", line[2:]).strip()
                return re.sub(r"[`*]", "", t)
    return os.path.splitext(os.path.basename(path))[0]


def nav_for_dir(base_dest, skip=()):
    """Nav entries (title, path) for the numbered chapters of a docs directory in site-src."""
    d = os.path.join(SRC, base_dest)
    entries = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md") or f in skip:
            continue
        entries.append({title_of(os.path.join(d, f)): "%s/%s" % (base_dest, f)})
    return entries



TAG_RULES = [
    ("boot", ("boot", "uboot", "chain", "login", "bootcmd")),
    ("security", ("trustzone", "smc", "secure", "el-", "exception", "scmi", "optee")),
    ("storage", ("storage", "layout", "partition", "memory", "sd-", "fip", "anatomy")),
    ("build", ("build", "pipeline", "flash", "image")),
    ("device tree", ("dt-", "dt_", "device-tree", "dts")),
    ("source", ("source",)),
    ("hardware", ("soc-", "board")),
    ("concepts", ("stack", "ladder", "models", "customiz", "env", "linux-fs")),
]


def tags_for(stem):
    out = []
    for tag, keys in TAG_RULES:
        if any(k in stem for k in keys) and tag not in out:
            out.append(tag)
    return out[:3] or ["overview"]


def svg_meta(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    head = text[:6000]
    label = re.search(r'aria-label="([^"]*)"', head)
    m = re.search(r'viewBox="[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
    t = re.search(r"<text[^>]*>([^<]+)</text>", text)
    return {
        "title": html.unescape(t.group(1)).strip() if t else None,
        "description": html.unescape(label.group(1)).strip() if label else "",
        "w": float(m.group(1)) if m else 1400.0,
        "h": float(m.group(2)) if m else 800.0,
    }


def reading_rank():
    """Order diagrams by where they first appear in the text, README first, chapters in order."""
    order = {}
    files = []
    for dp, dn, fn in os.walk(SRC):
        dn.sort()
        for f in sorted(fn):
            if f.endswith(".md"):
                files.append(os.path.join(dp, f))

    def key(p):
        r = os.path.relpath(p, SRC).replace(os.sep, "/")
        board = r.startswith("boards/")
        return (board, r.split("/")[1] if board else "", 0 if r.endswith("index.md") else 1, r)

    for md in sorted(files, key=key):
        base = os.path.dirname(md)
        with open(md, encoding="utf-8") as fh:
            for ref in re.findall(r"\(([^)\s]+\.svg)\)", fh.read()):
                full = os.path.normpath(os.path.join(base, ref))
                order.setdefault(full, len(order))
    return order


def build_manifest():
    rank = reading_rank()
    entries = []
    for dp, dn, fn in os.walk(SRC):
        for f in fn:
            if not f.endswith(".svg"):
                continue
            full = os.path.join(dp, f)
            r = os.path.relpath(full, SRC).replace(os.sep, "/")
            m = re.match(r"^(docs|boards/([^/]+)/docs)/images/([^/]+)\.svg$", r)
            if not m:
                continue
            board = m.group(2)
            stem = m.group(3)
            meta = svg_meta(full)
            steps = r[:-4] + ".steps.json"
            entries.append({
                "id": "%s/%s" % (board or "concepts", stem),
                "src": r,
                "title": meta["title"] or stem.replace("-", " ").replace("_", " ").capitalize(),
                "description": meta["description"],
                "group": BOARD_TITLES.get(board, board) if board else "Concepts",
                "board": board or "",
                "tags": tags_for(stem),
                "steps": steps if os.path.exists(os.path.join(SRC, steps)) else None,
                "w": meta["w"], "h": meta["h"],
                "_rank": rank.get(full, 10 ** 6),
            })
    order_group = {"Concepts": 0}
    entries.sort(key=lambda e: (order_group.get(e["group"], 1), e["group"], e["_rank"], e["id"]))
    for e in entries:
        e.pop("_rank")
    return entries


GALLERY_MD = """---
hide:
  - toc
---

# Diagrams

Every diagram in this primer, in one place. **Click a card** to open it in the viewer; diagrams
marked **▶ walkthrough** can also be stepped through one part at a time. Tick the check mark on
two cards to compare them side by side.

<div id="dv-gallery"></div>

## Using the viewer

| Do this | To |
| --- | --- |
| Scroll, pinch, or press `+` `-` | zoom toward the pointer |
| Drag, or arrow keys | move around a zoomed diagram |
| Double-click, or press `f` | zoom in on a spot, or fit the whole diagram back in the window |
| Press `w` | start the walkthrough: the viewer dims everything except the part being explained and zooms to it |
| Press `s` | show two diagrams side by side (for example the SMC flow next to how TrustZone is enforced); `l` links their zoom |
| Press `g` | open the strip of all diagrams to switch quickly |
| Press `[` and `]` | previous and next diagram |
| Press `?` | the full list of shortcuts |

The address bar follows what you are looking at (`#dv=…&step=3`), so you can paste a link to an exact
step of a walkthrough.
"""


def write_manifest_and_gallery():
    entries = build_manifest()
    path = os.path.join(SRC, "assets", "diagrams.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"diagrams": entries}, fh, indent=1, ensure_ascii=False)
    gdir = os.path.join(SRC, "diagrams")
    os.makedirs(gdir, exist_ok=True)
    with open(os.path.join(gdir, "index.md"), "w", encoding="utf-8") as fh:
        fh.write(GALLERY_MD)
    return entries


def build_nav():
    nav = [{"Home": "index.md"}]
    concepts = [{"Reading order": "docs/index.md"}]
    concepts += nav_for_dir("docs", skip=("index.md", "board-contract.md", "authoring-diagrams.md"))
    nav.append({"Concepts": concepts})
    nav.append({"Diagrams": "diagrams/index.md"})
    boards = os.path.join(SRC, "boards")
    for b in sorted(os.listdir(boards)):
        bdir = os.path.join(boards, b)
        if not os.path.isdir(bdir):
            continue
        items = [{"Overview": "boards/%s/index.md" % b}]
        ddir = os.path.join(bdir, "docs")
        if os.path.isdir(ddir):
            if os.path.exists(os.path.join(ddir, "index.md")):
                items.append({"Reading order": "boards/%s/docs/index.md" % b})
            items += nav_for_dir("boards/%s/docs" % b, skip=("index.md",))
        nav.append({BOARD_TITLES.get(b, b): items})
    contribute = [{"The board contract": "docs/board-contract.md"}, {"Authoring diagrams": "docs/authoring-diagrams.md"}]
    for dest, label in (("contributing.md", None), ("third-party.md", None)):
        if os.path.exists(os.path.join(SRC, dest)):
            contribute.append({title_of(os.path.join(SRC, dest)): dest})
    nav.append({"Contribute": contribute})
    return nav


def assemble():
    if os.path.isdir(SRC):
        shutil.rmtree(SRC)
    mapping = collect()
    warnings = []
    # README.md -> index.md is ambiguous for the root: the landing page wins
    mapping[os.path.join(ROOT, "README.md")] = "index.md"
    for src, dest in sorted(mapping.items()):
        if src == os.path.join(ROOT, "README.md"):
            continue
        target = os.path.join(SRC, dest)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if src.endswith(".md"):
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
            # site/ holds pages written for the site itself: their links are already site-relative
            if not src.startswith(os.path.join(ROOT, "site") + os.sep):
                text = rewrite(text, src, mapping, warnings)
                # GitHub renders Markdown inside a centred <div>; MkDocs needs to be told to
                text = text.replace('<div align="center">', '<div align="center" markdown="1">')
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text)
        else:
            shutil.copy2(src, target)
    entries = write_manifest_and_gallery()
    print("%d diagrams, %d with walkthroughs" % (len(entries), sum(1 for e in entries if e["steps"])))
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    return warnings


def write_config():
    cfg = {
        "INHERIT": "../mkdocs.yml",
        "docs_dir": "site-src",
        "site_dir": "site-out",
        "nav": build_nav(),
    }
    # the workflow passes the address GitHub actually serves the site from: a private repository gets a
    # generated one, not <org>.github.io/<repo>
    if os.environ.get("SITE_URL"):
        cfg["site_url"] = os.environ["SITE_URL"].rstrip("/") + "/"
    path = os.path.join(BUILD, "mkdocs.yml")
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="fail on any warning")
    ap.add_argument("--serve", action="store_true", help="serve with live reload")
    ap.add_argument("--no-build", action="store_true", help="only assemble")
    args = ap.parse_args()

    os.makedirs(BUILD, exist_ok=True)
    warnings = assemble()
    cfg = write_config()
    if args.strict and warnings:
        print("%d link warning(s) while assembling" % len(warnings), file=sys.stderr)
        return 1
    if args.no_build:
        print("assembled %s" % rel(SRC))
        return 0
    cmd = [sys.executable, "-m", "mkdocs", "serve" if args.serve else "build", "-f", cfg]
    if args.strict:
        cmd.append("--strict")
    if not args.serve:
        cmd += ["--quiet"] if not args.strict else []
    print("+", " ".join(cmd))
    env = dict(os.environ, NO_MKDOCS_2_WARNING="1")
    rc = subprocess.call(cmd, cwd=BUILD, env=env)
    if rc == 0 and not args.serve:
        print("site built in %s" % rel(os.path.join(BUILD, "site-out")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
