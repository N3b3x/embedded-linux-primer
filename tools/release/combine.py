#!/usr/bin/env python3
"""Merge per-image manifests into one release: flat asset directory, SHA256SUMS, manifest.json, release notes.

    combine.py INDIR OUTDIR --tag TAG [--pages-url URL] [--repo OWNER/NAME]

INDIR is the directory the CI artifacts were downloaded into (one sub-directory per image, each with a
manifest.json from make-assets.sh). OUTDIR receives:
    every asset file (flat)        SHA256SUMS       manifest.json (kind "release")       RELEASE_NOTES.md
Two releases come out, in OUTDIR/stable (tag: only images verified on hardware, a normal release) and OUTDIR/preview
(tag + "-preview": everything else, a pre-release; only created when something unverified was built). Each directory
has its own assets, SHA256SUMS, manifest.json and RELEASE_NOTES.md. Standard library only.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import matrix  # noqa: E402  (shares the images.json loader)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1000 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.0f %s" % (n, unit) if n >= 100 else "%.1f %s" % (n, unit))
        n /= 1000.0


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def find_manifests(indir):
    out = []
    for dp, dn, fn in os.walk(indir):
        if dp[len(indir):].count(os.sep) > 3:
            dn[:] = []
        if "manifest.json" in fn:
            out.append(os.path.join(dp, "manifest.json"))
    return sorted(out)


ROLE_TEXT = {
    "image": "SD-card image (xz-compressed). Write it with tools/flash-sd.sh, Raspberry Pi Imager or balenaEtcher",
    "bmap": "block map: lets bmaptool write only the used blocks (optional)",
    "bundle": "bundle (see the archive's README.txt)",
}


def split_streams(images):
    """Split image manifests into (verified, unverified) by their verified_on_hardware flag.
    Verified images go to the normal release <tag>, the others to the pre-release <tag>-preview."""
    ok = [im for im in images if im["verified_on_hardware"]["verified"]]
    preview = [im for im in images if not im["verified_on_hardware"]["verified"]]
    return ok, preview


def notes(rel, pages, repo, cfg):
    tag = rel["tag"]
    lines = []
    w = lines.append
    w("# Boot images %s%s" % (tag, " (preview, not verified on hardware)" if rel["prerelease"] else ""))
    w("")
    w("Built from commit `%s` on %s by `.github/workflows/images.yml`." % (rel["git_commit"][:12], rel["build_date"]))
    w("")
    unver = [im for im in rel["images"] if not im["verified_on_hardware"]["verified"]]
    if rel["prerelease"]:
        w("> **WARNING: preview, pre-release.** The following images have **not been booted on real hardware** and may not boot at all:")
        w(">")
        for im in unver:
            w("> - `%s`: %s" % (im["name"], im["verified_on_hardware"]["text"] or "not verified"))
        w(">")
        w("> Previews are kept apart from the verified release `%s` on purpose: GitHub's `releases/latest/download/...` "
          "links never point at a pre-release, so the stable links only ever serve hardware-verified images." % rel["tag"].replace("-preview", ""))
        w(">")
        w("> Use them for bring-up only, next to a serial console and someone who can fix the build.")
        w("")
    w("## What is in this release")
    w("")
    w("| File | What it is | Size | Verified on hardware |")
    w("| --- | --- | --- | --- |")
    for im in rel["images"]:
        ver = ("yes: " + im["verified_on_hardware"]["text"]) if im["verified_on_hardware"]["verified"] else "**NO**: " + (im["verified_on_hardware"]["text"] or "not verified")
        for f in im["files"]:
            w("| `%s` | %s: %s | %s | %s |" % (f["name"], im["title"], ROLE_TEXT.get(f["role"], f["role"]), human(f["size"]), ver if f["role"] != "bmap" else "(as image)"))
    w("| `SHA256SUMS` | sha256 of every file above | | |")
    w("| `manifest.json` | machine-readable list: board, variant, commit, pinned source revisions, tool versions, sizes, checksums | | |")
    w("")
    if rel["prerelease"]:
        w("A board moves from the preview stream to the verified release when `verified_on_hardware` is set to true in "
          "`tools/release/images.json`, after someone has booted it. The version is in this page, in `manifest.json` and "
          "in `SHA256SUMS`.")
    else:
        w("Every image in this release has been booted on hardware. File names carry no version, so "
          "`https://github.com/%s/releases/latest/download/<file>` always points at the newest verified release. The version "
          "is in this page, in `manifest.json` and in `SHA256SUMS`." % repo)
    w("")
    w("## Flash an image")
    w("")
    w("1. Download the `.img.xz` for your board (and `SHA256SUMS`) into one folder.")
    w("2. Linux or macOS: `tools/flash-sd.sh imx8mp-variscite-alpine.img.xz` (from a clone of the repository). It verifies the checksum, "
      "lists only removable disks, asks you to type the device name, writes, syncs and ejects.")
    w("3. Windows: open Raspberry Pi Imager (\"Use custom\") or balenaEtcher, choose the `.xz` file directly, choose the SD card, write. "
      "Check the checksum first: `certutil -hashfile <file> SHA256` and compare with `SHA256SUMS`.")
    w("4. Set the boot switch to SD, open the serial console, power on. Per-board details are in the "
      "[download guide](%s/docs/downloads/)." % pages)
    w("")
    if any(im["image_kind"] == "kernel-bundle" for im in rel["images"]):
        w("The Jetson kernel bundle is not an SD-card image and contains nothing from NVIDIA's driver package or root "
          "filesystem; how to apply it is in the download guide and in the bundle's `README.txt`.")
        w("")
    w("Check a download by hand: `grep imx8mp-variscite-alpine.img.xz SHA256SUMS | sha256sum -c -` on Linux, "
      "`grep imx8mp-variscite-alpine.img.xz SHA256SUMS | shasum -a 256 -c -` on macOS.")
    w("")
    w("## Licences and redistribution")
    w("")
    w("These images contain third-party software under its own licences, including vendor firmware under vendor licence "
      "terms. They are for **your own use**; do not redistribute them before you have reviewed "
      "[the licence table](%s/docs/image-licences/). Source for the GPL parts is reachable through the pinned commits in "
      "`manifest.json`." % pages)
    w("")
    for im in rel["images"]:
        if im["redistribution"]:
            w("- `%s`: %s" % (im["name"], im["redistribution"]))
    w("")
    w("## Reproducibility")
    w("")
    w("Sources and downloads are pinned (see the revisions below), but the images are **not yet bit-for-bit reproducible**: "
      "the same commit built twice gives different bytes. The checksums in `SHA256SUMS` identify exactly this build. "
      "See [reproducible builds](%s/docs/reproducible-builds/)." % pages)
    w("")
    w("<details><summary>Pinned source revisions per image</summary>")
    w("")
    for im in rel["images"]:
        w("**%s**" % im["name"])
        w("")
        if im["sources"]:
            w("| Component | Revision or sha256 |")
            w("| --- | --- |")
            for s in im["sources"]:
                w("| %s | `%s` |" % (s["component"], s.get("rev") or s.get("sha256") or s.get("ref") or s.get("url", "")))
        else:
            w("(none recorded)")
        w("")
    w("</details>")
    w("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("indir")
    ap.add_argument("outdir")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--pages-url")
    a = ap.parse_args()
    cfg = matrix.load()
    repo = a.repo or cfg["repo"]
    pages = (a.pages_url or cfg["pages"]).rstrip("/")

    paths = find_manifests(a.indir)
    images = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            m = json.load(fh)
        if m.get("kind") == "image":
            images.append((os.path.dirname(p), m))
    if not images:
        print("combine: no image manifests under %s" % a.indir, file=sys.stderr)
        return 1
    images.sort(key=lambda t: t[1]["name"])
    commits = {m["git_commit"] for _, m in images}
    if len(commits) != 1:
        print("combine: the images were built from different commits: %s" % ", ".join(sorted(commits)), file=sys.stderr)
        return 1

    streams = []
    ok, preview = split_streams([m for _, m in images])
    dirs = {m["name"]: d for d, m in images}
    for stream, group, tag, pre in (("stable", ok, a.tag, False), ("preview", preview, a.tag + "-preview", True)):
        if not group:
            continue
        out = os.path.join(a.outdir, stream)
        os.makedirs(out, exist_ok=True)
        files, sums = [], {}
        for im in group:
            for f in im["files"]:
                if f["name"] in sums:
                    continue
                dst = os.path.join(out, f["name"])
                shutil.copyfile(os.path.join(dirs[im["name"]], f["name"]), dst)
                if sha_file(dst) != f["sha256"]:
                    print("combine: %s does not match its manifest" % f["name"], file=sys.stderr)
                    return 1
                sums[f["name"]] = f["sha256"]
                files.append(f)
        with open(os.path.join(out, "SHA256SUMS"), "w", encoding="utf-8") as fh:
            for n in sorted(sums):
                fh.write("%s  %s\n" % (sums[n], n))
        rel = {
            "schema": 1, "kind": "release", "stream": stream, "tag": tag,
            "version": a.tag[1:] if a.tag[:1] == "v" and a.tag[1:2].isdigit() else a.tag,
            "git_commit": group[0]["git_commit"],
            "build_date": max(m["build_date"] for m in group),
            "prerelease": pre, "repo": repo, "images": group,
            "files": sorted(files, key=lambda f: f["name"]),
        }
        if pre:  # which board/variant is unverified, and why it is here
            rel["unverified"] = [{"name": m["name"], "board": m["board"], "variant": m["variant"],
                                  "reason": m["verified_on_hardware"]["text"] or "not verified on hardware"} for m in group]
        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(rel, fh, indent=2)
            fh.write("\n")
        with open(os.path.join(out, "RELEASE_NOTES.md"), "w", encoding="utf-8") as fh:
            fh.write(notes(rel, pages, repo, cfg))
        streams.append((stream, tag, len(group), len(files)))
        print("combine: %s release %s: %d image(s), %d file(s), prerelease=%s" % (stream, tag, len(group), len(files), str(pre).lower()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
