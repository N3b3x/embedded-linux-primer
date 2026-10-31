#!/usr/bin/env python3
"""Read tools/release/images.json and print what the release workflow needs. Standard library only.

    matrix.py                              GitHub Actions matrix JSON for every enabled board/variant
    matrix.py -b imx8mp-variscite          ... only that board (repeat -b, or comma-separate)
    matrix.py -b stm32mp2-dk -v alpine     ... only that variant of that board
    matrix.py --github-output FILE         also append  matrix=...  and  has_jobs=true|false  to FILE
    matrix.py --list                       a table of every entry, enabled or not
    matrix.py --repro                      matrix of boards with cheap steps for the reproducibility check
    matrix.py --assets BOARD VARIANT       tab-separated  src  name  compress  role  optional  (for make-assets.sh)
    matrix.py --entry BOARD VARIANT        the merged board+variant entry as JSON (for the other scripts)

Disabled boards and variants (`"enabled": false`) are skipped. Asking for one by name is an error,
so a typo in a workflow input never silently builds nothing. Adding a board or a variant is one JSON
entry in images.json; no script changes.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "images.json")


def load(path=CONFIG):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def split(values):
    out = []
    for v in values or []:
        out += [x.strip() for x in v.replace(" ", ",").split(",") if x.strip()]
    return [x for x in out if x not in ("all", "*")]


def merged(cfg, board, variant):
    """Board fields plus variant fields, variant winning; `variants` itself is dropped."""
    b = cfg["boards"][board]
    v = b["variants"][variant]
    e = {k: val for k, val in b.items() if k != "variants"}
    e.update(v)
    e["board"] = board
    e["variant"] = variant
    e["board_enabled"] = b.get("enabled", True)
    e["variant_enabled"] = v.get("enabled", True)
    e["enabled"] = e["board_enabled"] and e["variant_enabled"]
    e["name"] = "%s-%s" % (board, variant)
    # verification: a boolean plus a free-text hardware description; a variant may override the board's
    flag = v["verified_on_hardware"] if "verified_on_hardware" in v else b.get("verified_on_hardware", False)
    note = v.get("verified_note", "") if "verified_on_hardware" in v else b.get("verified_note", "")
    if not isinstance(flag, bool):
        sys.exit("matrix.py: %s/%s: verified_on_hardware must be true or false" % (board, variant))
    e["verified_on_hardware"] = {"verified": flag, "text": note}
    return e


def entries(cfg, boards=None, variants=None, include_disabled=False):
    boards, variants = split(boards), split(variants)
    for b in boards:
        if b not in cfg["boards"]:
            sys.exit("matrix.py: unknown board '%s' (known: %s)" % (b, ", ".join(sorted(cfg["boards"]))))
    known_variants = {v for b in cfg["boards"].values() for v in b["variants"]}
    for v in variants:
        if v not in known_variants:
            sys.exit("matrix.py: unknown variant '%s' (known: %s)" % (v, ", ".join(sorted(known_variants))))
    out = []
    for bname in sorted(cfg["boards"]):
        if boards and bname not in boards:
            continue
        for vname in sorted(cfg["boards"][bname]["variants"]):
            if variants and vname not in variants:
                continue
            e = merged(cfg, bname, vname)
            if not e["enabled"] and not include_disabled:
                if boards and variants:  # asked for this exact pair
                    why = e.get("disabled_reason") or cfg["boards"][bname].get("disabled_reason") or "disabled"
                    sys.exit("matrix.py: %s/%s is disabled in images.json: %s" % (bname, vname, why))
                continue
            out.append(e)
    return out


def matrix_item(e):
    r = e.get("runner", {})
    return {
        "name": e["name"],
        "board": e["board"],
        "variant": e["variant"],
        "dir": e["dir"],
        "kind": e["kind"],
        "build": "\n".join(e["build"]),
        "disk_gb": r.get("disk_gb", 20),
        "timeout": min(360, int(r.get("minutes", 60) * 2 + 15)),  # twice the estimate plus slack; 360 min is the job limit
        "arch": r.get("arch", "x86_64"),
        "standard_runner": bool(r.get("standard_runner", True)),
        "verified": bool(e["verified_on_hardware"].get("verified")),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-b", "--board", action="append", help="board name(s), comma separated; default all enabled")
    ap.add_argument("-v", "--variant", action="append", help="variant name(s), comma separated; default all enabled")
    ap.add_argument("--github-output", help="append matrix= and has_jobs= to this file ($GITHUB_OUTPUT)")
    ap.add_argument("--list", action="store_true", help="table of all entries")
    ap.add_argument("--repro", action="store_true", help="matrix of the boards that define cheap steps for the reproducibility check")
    ap.add_argument("--assets", nargs=2, metavar=("BOARD", "VARIANT"))
    ap.add_argument("--entry", nargs=2, metavar=("BOARD", "VARIANT"))
    ap.add_argument("--config", default=CONFIG)
    a = ap.parse_args()
    cfg = load(a.config)

    if a.assets or a.entry:
        b, v = a.assets or a.entry
        if b not in cfg["boards"] or v not in cfg["boards"][b]["variants"]:
            sys.exit("matrix.py: unknown %s/%s" % (b, v))
        e = merged(cfg, b, v)
        if a.entry:
            json.dump(e, sys.stdout, indent=2)
            print()
        else:
            for d in e["deploy"]:
                print("\t".join([d["src"], d["name"], d.get("compress", "none"), d.get("role", "file"), "1" if d.get("optional") else "0"]))
        return 0

    if a.list:
        for e in entries(cfg, a.board, a.variant, include_disabled=True):
            print("%-34s %-8s %-15s %-8s %s" % (e["name"], "enabled" if e["enabled"] else "disabled", e["kind"],
                                               "verified" if e["verified_on_hardware"].get("verified") else "UNVERIFIED",
                                               e["title"]))
        return 0

    if a.repro:  # one item per enabled board that has a "repro" section (the cheap steps: firmware, bootloader)
        seen, items = set(), []
        for e in entries(cfg, a.board, a.variant):
            r = e.get("repro")
            if r and e["board"] not in seen:
                seen.add(e["board"])
                items.append({"board": e["board"], "dir": e["dir"], "commands": "\n".join(r["commands"]), "outputs": " ".join(r["outputs"])})
        text = json.dumps({"include": items}, separators=(",", ":"))
        print(text)
        if a.github_output:
            with open(a.github_output, "a", encoding="utf-8") as fh:
                fh.write("repro_matrix=%s\nhas_repro=%s\n" % (text, "true" if items else "false"))
        return 0

    items = [matrix_item(e) for e in entries(cfg, a.board, a.variant)]
    doc = {"include": items}
    text = json.dumps(doc, separators=(",", ":"))
    print(json.dumps(doc, indent=2) if sys.stdout.isatty() else text)
    if a.github_output:
        with open(a.github_output, "a", encoding="utf-8") as fh:
            fh.write("matrix=%s\nhas_jobs=%s\n" % (text, "true" if items else "false"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
