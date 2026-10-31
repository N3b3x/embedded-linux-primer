#!/usr/bin/env python3
"""Prepare the PS7 initialisation files for U-Boot's SPL.

usage: ps7_prepare.py <source> <output-dir>

<source> is one of
  * a ps7_init_gpl.c file (ps7_init_gpl.h is expected next to it),
  * a directory that contains ps7_init_gpl.c and ps7_init_gpl.h,
  * a zip archive that contains them: a Vivado/Vitis hardware handoff (.hdf, .xsa).

The two files are written to <output-dir> with two mechanical changes that make them compile
as part of U-Boot (and nothing else is touched; the register values are exactly Vivado's):

  1. Windows line endings (CRLF) become Unix line endings.
  2. Old-style empty parameter lists at column 0, "int ps7_init()" and "ps7_debug()", become
     "(void)". Vivado writes the old style; U-Boot compiles with -Werror=strict-prototypes.
     Calls inside function bodies are indented and stay as they are.

The script prints what it did and a sha256 of each result, and refuses a source that does not
look like a Zynq-7000 PS7 initialisation (it must write the SLCR unlock key to 0xF8000008).
"""
import hashlib
import os
import re
import sys
import zipfile

WANT = ("ps7_init_gpl.c", "ps7_init_gpl.h")
PROTO = re.compile(r'^((?:[A-Za-z_]\w*[ \t*]+)*[A-Za-z_]\w*)[ \t]*\([ \t]*\)([ \t]*(?:;|\{)?[ \t]*)$', re.M)


def read_sources(src):
    out = {}
    if os.path.isdir(src):
        for name in WANT:
            hits = [os.path.join(r, name) for r, _, fs in os.walk(src) if name in fs]
            if len(hits) != 1:
                sys.exit("%s: expected exactly one %s, found %d" % (src, name, len(hits)))
            out[name] = open(hits[0], "rb").read()
    elif zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for name in WANT:
                hits = [n for n in z.namelist() if n.split("/")[-1] == name]
                if len(hits) != 1:
                    sys.exit("%s: expected exactly one %s in the archive, found %d" % (src, name, len(hits)))
                out[name] = z.read(hits[0])
    elif os.path.isfile(src):
        d = os.path.dirname(os.path.abspath(src))
        base = os.path.basename(src)
        if base != "ps7_init_gpl.c":
            sys.exit("%s: a single file must be named ps7_init_gpl.c (give the directory, or the .hdf/.xsa)" % src)
        for name in WANT:
            path = os.path.join(d, name)
            if not os.path.isfile(path):
                sys.exit("%s: missing next to %s" % (name, src))
            out[name] = open(path, "rb").read()
    else:
        sys.exit("%s: not a file, directory or archive" % src)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    files = read_sources(src)
    os.makedirs(dst, exist_ok=True)
    for name in WANT:
        text = files[name].decode("latin-1").replace("\r\n", "\n")
        text, n = PROTO.subn(r"\1(void)\2", text)
        if name.endswith(".c") and "0XF8000008" not in text.upper():
            sys.exit("%s does not look like a Zynq-7000 ps7_init (no write to SLCR_UNLOCK 0xF8000008)" % name)
        with open(os.path.join(dst, name), "w", encoding="latin-1", newline="\n") as f:
            f.write(text)
        print("%s: %d empty parameter list(s) made (void), sha256 %s" % (
            name, n, hashlib.sha256(text.encode("latin-1")).hexdigest()))


main()
