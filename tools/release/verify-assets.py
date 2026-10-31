#!/usr/bin/env python3
"""Re-check release assets: every checksum, every size, and the manifest schema. Standard library only.

    verify-assets.py DIR [--quick]

DIR holds either one image (manifest.json written by make-assets.sh), a release (manifest.json written
by combine.py, with SHA256SUMS), or a directory of such directories (the downloaded CI artifacts).
Checked, for every manifest found:
  * the schema: required keys and their types, sha256 values are 64 hex digits
  * every listed file exists, has the listed size and compressed sha256
  * every <file>.sha256 next to it agrees; SHA256SUMS (if present) lists exactly the listed files
  * for .xz assets: the decompressed stream has the listed raw size and raw sha256 (skip with --quick)
  * a .bmap's ImageSize equals the raw size of the image it belongs to
Exit status 0 only when nothing is wrong.
"""
import argparse
import hashlib
import json
import lzma
import os
import re
import sys

HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_REQUIRED = {
    "schema": int, "kind": str, "board": str, "variant": str, "name": str, "title": str, "tag": str,
    "version": str, "git_commit": str, "source_date_epoch": int, "build_date": str, "build_command": list,
    "sources": list, "tools": dict, "verified_on_hardware": dict, "redistribution": str, "licence_ids": list,
    "files": list,
}
FILE_REQUIRED = {"name": str, "role": str, "size": int, "sha256": str, "compression": str,
                 "raw_name": str, "raw_size": int, "raw_sha256": str}
RELEASE_REQUIRED = {"schema": int, "kind": str, "tag": str, "version": str, "git_commit": str,
                    "prerelease": bool, "images": list, "files": list}
CHUNK = 1 << 20


class Report:
    def __init__(self):
        self.errors = []
        self.checked = 0

    def err(self, where, msg):
        self.errors.append("%s: %s" % (where, msg))


def sha_and_size(path, opener=open):
    h, n = hashlib.sha256(), 0
    with opener(path, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def check_types(obj, spec, where, rep):
    for k, t in spec.items():
        if k not in obj:
            rep.err(where, "missing key '%s'" % k)
        elif not isinstance(obj[k], t) or (t is int and isinstance(obj[k], bool)):
            rep.err(where, "key '%s' should be %s, is %s" % (k, t.__name__, type(obj[k]).__name__))


def check_file(d, f, where, rep, quick):
    check_types(f, FILE_REQUIRED, where, rep)
    if any(k not in f for k in FILE_REQUIRED):
        return
    for k in ("sha256", "raw_sha256"):
        if not HEX64.match(f[k]):
            rep.err(where, "%s of %s is not 64 lower-case hex digits" % (k, f["name"]))
    path = os.path.join(d, f["name"])
    if not os.path.isfile(path):
        rep.err(where, "listed file %s is missing" % f["name"])
        return
    sha, size = sha_and_size(path)
    rep.checked += 1
    if size != f["size"]:
        rep.err(where, "%s: size %d, manifest says %d" % (f["name"], size, f["size"]))
    if sha != f["sha256"]:
        rep.err(where, "%s: sha256 %s, manifest says %s" % (f["name"], sha, f["sha256"]))
    side = path + ".sha256"
    if os.path.isfile(side):
        with open(side, encoding="utf-8") as fh:
            parts = fh.read().split()
        if len(parts) != 2 or parts[0] != f["sha256"] or parts[1] != f["name"]:
            rep.err(where, "%s.sha256 disagrees with the manifest" % f["name"])
    if f["compression"] == "xz":
        if quick:
            return
        try:
            rsha, rsize = sha_and_size(path, opener=lzma.open)
        except (lzma.LZMAError, EOFError) as ex:
            rep.err(where, "%s: not a valid xz stream (%s)" % (f["name"], ex))
            return
        if rsize != f["raw_size"] or rsha != f["raw_sha256"]:
            rep.err(where, "%s: decompressed data is %d bytes / %s, manifest says %d / %s"
                    % (f["name"], rsize, rsha[:16], f["raw_size"], f["raw_sha256"][:16]))
    elif f["compression"] == "none":
        if f["raw_sha256"] != f["sha256"] or f["raw_size"] != f["size"]:
            rep.err(where, "%s is not compressed, yet raw and file checksums differ" % f["name"])
    else:
        rep.err(where, "%s: unknown compression '%s'" % (f["name"], f["compression"]))


def check_bmaps(d, files, where, rep):
    raw_sizes = {f["raw_name"]: f["raw_size"] for f in files if f["role"] == "image"}
    for f in files:
        if f["role"] != "bmap":
            continue
        img = f["raw_name"][:-len(".bmap")] if f["raw_name"].endswith(".bmap") else None
        path = os.path.join(d, f["name"])
        if img not in raw_sizes or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            m = re.search(r"<ImageSize>\s*(\d+)", fh.read())
        if not m:
            rep.err(where, "%s has no <ImageSize>: not a bmap file" % f["name"])
        elif int(m.group(1)) != raw_sizes[img]:
            rep.err(where, "%s describes an image of %s bytes, but %s is %d bytes" % (f["name"], m.group(1), img, raw_sizes[img]))


def check_sums_file(d, names, where, rep, require_exact):
    path = os.path.join(d, "SHA256SUMS")
    if not os.path.isfile(path):
        return
    listed = {}
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            m = re.match(r"^([0-9a-f]{64})  \*?(\S.*)$", line.rstrip("\n"))
            if not m:
                rep.err(where, "SHA256SUMS line %d is malformed" % ln)
                continue
            listed[m.group(2)] = m.group(1)
    for n, sha in listed.items():
        p = os.path.join(d, n)
        if not os.path.isfile(p):
            rep.err(where, "SHA256SUMS lists %s, which is not there" % n)
        elif sha_and_size(p)[0] != sha:
            rep.err(where, "SHA256SUMS: wrong checksum for %s" % n)
    if require_exact:
        for n in names:
            if n not in listed:
                rep.err(where, "SHA256SUMS does not list %s" % n)


def verify_manifest(path, rep, quick):
    d = os.path.dirname(path)
    where = os.path.relpath(path)
    try:
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError) as ex:
        rep.err(where, "cannot read: %s" % ex)
        return
    if not isinstance(m, dict) or m.get("schema") != 1:
        rep.err(where, "unsupported or missing schema (expected 1)")
        return
    if m.get("kind") == "image":
        check_types(m, IMAGE_REQUIRED, where, rep)
        if not isinstance(m.get("files"), list) or not m["files"]:
            rep.err(where, "no files listed")
            return
        if not re.match(r"^[0-9a-f]{7,64}$|^unknown$", str(m.get("git_commit", ""))):
            rep.err(where, "git_commit is not a commit id")
        v = m.get("verified_on_hardware", {})
        if not isinstance(v.get("verified"), bool) or not isinstance(v.get("text"), str):
            rep.err(where, "verified_on_hardware needs a boolean 'verified' and a string 'text'")
        for f in m["files"]:
            check_file(d, f, where, rep, quick)
        check_bmaps(d, m["files"], where, rep)
        check_sums_file(d, [f["name"] for f in m["files"]], where, rep, False)
    elif m.get("kind") == "release":
        check_types(m, RELEASE_REQUIRED, where, rep)
        names = []
        for f in m.get("files", []):
            check_file(d, f, where, rep, quick)
            names.append(f.get("name"))
        for im in m.get("images", []):
            if im.get("kind") != "image":
                rep.err(where, "an entry of 'images' is not an image manifest")
                continue
            check_types(im, IMAGE_REQUIRED, where + " (" + str(im.get("name")) + ")", rep)
        check_sums_file(d, names, where, rep, True)
        unverified = [im.get("name") for im in m.get("images", []) if not im.get("verified_on_hardware", {}).get("verified")]
        if m.get("stream") == "stable" and (m.get("prerelease") or unverified):
            rep.err(where, "the stable release must hold only verified images and not be a pre-release (unverified: %s)" % unverified)
        if m.get("stream") == "preview" and not m.get("prerelease"):
            rep.err(where, "the preview release must be a pre-release")
        if m.get("stream") == "preview" and not m.get("unverified"):
            rep.err(where, "the preview manifest must list the unverified images and why")
    else:
        rep.err(where, "kind must be 'image' or 'release'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--quick", action="store_true", help="do not decompress .xz files to check the raw sha256")
    a = ap.parse_args()
    rep = Report()
    found = []
    for dp, dn, fn in os.walk(a.dir):
        if dp[len(a.dir):].count(os.sep) > 3:
            dn[:] = []
        if "manifest.json" in fn:
            found.append(os.path.join(dp, "manifest.json"))
    if not found:
        print("verify-assets: no manifest.json under %s" % a.dir, file=sys.stderr)
        return 1
    for p in sorted(found):
        verify_manifest(p, rep, a.quick)
    for e in rep.errors:
        print("ERROR", e, file=sys.stderr)
    print("verify-assets: %d manifest(s), %d file(s) checked, %d problem(s)" % (len(found), rep.checked, len(rep.errors)))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
