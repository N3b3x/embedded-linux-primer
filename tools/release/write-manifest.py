#!/usr/bin/env python3
"""Write manifest.json for one built image. Called by make-assets.sh; not meant to be run by hand.

Inputs are plain files so the shell script stays in charge of the filesystem:
  --entry     JSON from  matrix.py --entry BOARD VARIANT
  --files     TSV, one line per asset:  name role size sha256 raw_name raw_size raw_sha256 compression
  --info      text of  ./build.sh info  (the pinned source revisions)
  --tools     TSV  tool<TAB>version line
Standard library only.
"""
import argparse
import datetime
import json
import os
import re
import sys

SCHEMA = 1
URL = re.compile(r"https?://[^\s,;]+")
REV = re.compile(r"\brev\s+([0-9a-f]{40})\b")
SHA = re.compile(r"\bsha256\s+([0-9a-f]{64})\b")
REF = re.compile(r"\b(?:branch|ref)\s+(\S+)")


def parse_sources(text):
    """Group the lines of `build.sh info` by component and pull out URL, ref, commit and sha256."""
    comps, cur = [], None
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            parts = re.split(r"\s{2,}|\s(?=https?://)", line.rstrip(), maxsplit=1)
            cur = {"component": parts[0].strip(), "_text": parts[1] if len(parts) > 1 else ""}
            comps.append(cur)
        elif cur is not None:
            cur["_text"] += "\n" + line.strip()
    out = []
    for c in comps:
        t = c.pop("_text")
        d = {"component": c["component"]}
        for key, rx in (("url", URL), ("rev", REV), ("sha256", SHA), ("ref", REF)):
            m = rx.search(t)
            if m:
                d[key] = m.group(1) if key != "url" else m.group(0)
        if len(d) > 1:
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True)
    ap.add_argument("--files", required=True)
    ap.add_argument("--info", required=True)
    ap.add_argument("--tools", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--epoch", required=True, type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.entry, encoding="utf-8") as fh:
        e = json.load(fh)
    with open(a.info, encoding="utf-8") as fh:
        info = fh.read()
    tools = {}
    with open(a.tools, encoding="utf-8") as fh:
        for line in fh:
            if "\t" in line:
                k, v = line.rstrip("\n").split("\t", 1)
                tools[k] = v
    files = []
    with open(a.files, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            n, role, size, sha, rn, rsize, rsha, comp = line.rstrip("\n").split("\t")
            files.append({"name": n, "role": role, "size": int(size), "sha256": sha, "compression": comp,
                          "raw_name": rn, "raw_size": int(rsize), "raw_sha256": rsha})

    ver = a.tag[1:] if re.match(r"^v\d", a.tag) else a.tag
    when = datetime.datetime.fromtimestamp(a.epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = {
        "schema": SCHEMA,
        "kind": "image",
        "board": e["board"],
        "variant": e["variant"],
        "name": e["name"],
        "title": e["title"],
        "board_title": e.get("short", e["board"]),
        "image_kind": e["kind"],
        "flashing_model": e.get("flashing_model", ""),
        "tag": a.tag,
        "version": ver,
        "git_commit": a.commit,
        "source_date_epoch": a.epoch,
        "build_date": when,
        "build_command": e["build"],
        "sources": parse_sources(info),
        "build_info": [l.rstrip() for l in info.splitlines() if l.strip()],
        "tools": tools,
        "verified_on_hardware": {"verified": bool(e["verified_on_hardware"].get("verified")),
                                 "text": e["verified_on_hardware"].get("text", "")},
        "redistribution": e.get("redistribution", ""),
        "licence_ids": e.get("licence_ids", []),
        "docs": e.get("docs", ""),
        "files": files,
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=False)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
