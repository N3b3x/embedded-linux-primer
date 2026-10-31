#!/usr/bin/env python3
"""Write site/assets/releases.json for the "Latest builds" view of the documentation site.

    fetch-releases.py [--output site/assets/releases.json] [--repo OWNER/NAME] [--limit 20]

Reads the repository's releases through the GitHub API and, for each release that carries the
release-level manifest.json (written by tools/release/combine.py), the list of images in it.
Uses GITHUB_TOKEN or GH_TOKEN when set (an internal or private repository needs one).

With no token, no network, or any API error it still writes a VALID file with an empty release list
and a reason in "error", and exits 0: the docs build must never fail because releases cannot be read.
Standard library only.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
API = "https://api.github.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def request(url, token, accept="application/vnd.github+json", follow=True):
    headers = {"Accept": accept, "User-Agent": "embedded-linux-primer-docs", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    return opener.open(urllib.request.Request(url, headers=headers), timeout=30)


def get_json(url, token):
    with request(url, token) as r:
        return json.load(r)


def get_asset_json(repo, asset_id, token):
    """Download a (small) JSON release asset. The API answers with a redirect to a pre-signed URL, which
    must be fetched WITHOUT the Authorization header, so the redirect is followed by hand."""
    url = "%s/repos/%s/releases/assets/%s" % (API, repo, asset_id)
    try:
        request(url, token, accept="application/octet-stream", follow=False)
        raise RuntimeError("expected a redirect")
    except urllib.error.HTTPError as ex:
        if ex.code not in (301, 302, 303, 307, 308) or not ex.headers.get("Location"):
            raise
        with urllib.request.urlopen(urllib.request.Request(ex.headers["Location"], headers={"User-Agent": "embedded-linux-primer-docs"}), timeout=60) as r:
            return json.load(r)


def convert(repo, rel, manifest, is_latest):
    base = "https://github.com/%s" % repo
    out = {
        "tag": rel["tag_name"],
        "name": rel.get("name") or rel["tag_name"],
        "published_at": rel.get("published_at") or rel.get("created_at"),
        "url": rel["html_url"],
        "prerelease": bool(rel.get("prerelease")),
        "stream": "preview" if rel.get("prerelease") else "stable",
        "latest": is_latest,
        "files": [{"name": a["name"], "size": a["size"], "url": "%s/releases/download/%s/%s" % (base, rel["tag_name"], a["name"])}
                  for a in rel.get("assets", [])],
        "images": [],
    }
    for im in (manifest or {}).get("images", []):
        verified = im.get("verified_on_hardware", {})
        for f in im.get("files", []):
            if f.get("role") == "bmap":
                continue
            entry = {
                "board": im.get("board"), "variant": im.get("variant"), "name": im.get("name"),
                "board_title": im.get("board_title") or im.get("board"), "title": im.get("title"),
                "version": im.get("version"), "build_date": im.get("build_date"), "commit": im.get("git_commit"),
                "file": f["name"], "size": f["size"], "sha256": f["sha256"], "role": f.get("role"),
                "verified": bool(verified.get("verified")), "verified_text": verified.get("text", ""),
                "url": "%s/releases/download/%s/%s" % (base, rel["tag_name"], f["name"]),
                "redistribution": im.get("redistribution", ""),
            }
            if is_latest:  # the stable link only means "this" while this is the latest non-pre-release
                entry["latest_url"] = "%s/releases/latest/download/%s" % (base, f["name"])
            for g in im.get("files", []):
                if g.get("role") == "bmap" and g["raw_name"] == f["raw_name"] + ".bmap":
                    entry["bmap_url"] = "%s/releases/download/%s/%s" % (base, rel["tag_name"], g["name"])
            out["images"].append(entry)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", default=os.path.join(ROOT, "site", "assets", "releases.json"))
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()

    repo = a.repo
    if not repo:
        try:
            with open(os.path.join(HERE, "images.json"), encoding="utf-8") as fh:
                repo = json.load(fh)["repo"]
        except (OSError, ValueError, KeyError):
            repo = "N3b3x/embedded-linux-primer"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    doc = {
        "schema": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "repo_url": "https://github.com/%s" % repo,
        "releases_url": "https://github.com/%s/releases" % repo,
        "actions_url": "https://github.com/%s/actions/workflows/images.yml" % repo,
        "releases": [],
    }
    try:
        releases = get_json("%s/repos/%s/releases?per_page=%d" % (API, repo, min(max(a.limit, 1), 100)), token)
        latest_seen = False
        for rel in releases:
            if rel.get("draft"):
                continue
            is_latest = not rel.get("prerelease") and not latest_seen
            latest_seen = latest_seen or is_latest
            manifest = None
            asset = next((x for x in rel.get("assets", []) if x["name"] == "manifest.json"), None)
            if asset:
                try:
                    manifest = get_asset_json(repo, asset["id"], token)
                except (urllib.error.URLError, OSError, ValueError, RuntimeError) as ex:
                    print("fetch-releases: manifest of %s unreadable: %s" % (rel["tag_name"], ex), file=sys.stderr)
            doc["releases"].append(convert(repo, rel, manifest, is_latest))
    except (urllib.error.URLError, OSError, ValueError, KeyError) as ex:
        why = "no network" if isinstance(ex, urllib.error.URLError) and not isinstance(ex, urllib.error.HTTPError) else str(ex)
        if isinstance(ex, urllib.error.HTTPError) and ex.code in (401, 403, 404) and not token:
            why = "HTTP %d: the repository is not public and no GITHUB_TOKEN/GH_TOKEN was provided" % ex.code
        doc["releases"] = []
        doc["error"] = why
        print("fetch-releases: writing an empty list (%s)" % why, file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    tmp = a.output + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    os.replace(tmp, a.output)
    print("fetch-releases: %d release(s) -> %s" % (len(doc["releases"]), os.path.relpath(a.output, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
