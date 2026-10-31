"""docs/images/boot-chains-compared.svg - three boot chains aligned by job (generated from docs/data/boot-chains.json)."""
import json
import os
import textwrap

from kit import *

DATA = json.load(open(os.path.join(HERE, "..", "..", "data", "boot-chains.json"), encoding="utf-8"))
COLS, BOARDS = DATA["columns"], DATA["boards"]

W = 1400
LABEL_W, X0, GAP = 190, 32, 14
colw = (W - 2 * X0 - LABEL_W - GAP * (len(COLS) - 1)) / len(COLS)
A = "#e5edf7"
CARD_H = 92

# stages stacked in one cell
rows_h = []
for b in BOARDS:
    most = max(sum(1 for s in b["stages"] if s["col"] == c["id"]) for c in COLS)
    rows_h.append(most * CARD_H + (most - 1) * 8 + 34)

H = 150 + sum(rows_h) + 24 * (len(BOARDS) - 1) + 90
body = [marker_defs({"a": A})]
NUM = {3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(len(BOARDS), str(len(BOARDS)))
body.append(title("%s boards, one chain" % NUM,
                  "The same five jobs in the same order. The names, the privilege levels and the place each one is stored change."))

# column headers
for i, c in enumerate(COLS):
    x = X0 + LABEL_W + i * (colw + GAP)
    body.append(text(x + colw / 2, 112, c["name"].upper(), size=12, weight=800, color=MUTED, anchor="middle", extra=' letter-spacing="1.2"'))
    if i:
        body.append(arrow(x - GAP - 4, 112, x - 2, 112, FAINT, "a", width=2))

y = 128
for b, rh in zip(BOARDS, rows_h):
    body.append(rect(X0 - 8, y - 8, W - 2 * X0 + 16, rh + 8, fill=PANEL2, stroke=LINE, rx=16, sw=1.2))
    body.append(text(X0 + 8, y + 24, b["name"], size=17, weight=800))
    body.append(text(X0 + 8, y + 44, b["model"], size=12, color=MUTED))
    for line_no, line in enumerate(textwrap.wrap(b["vendor"], 24)):
        body.append(text(X0 + 8, y + 64 + line_no * 16, line, size=11, color=FAINT))
    for i, c in enumerate(COLS):
        x = X0 + LABEL_W + i * (colw + GAP)
        stages = [s for s in b["stages"] if s["col"] == c["id"]]
        yy = y
        for s in stages:
            strong, soft, fill, border = ROLE[s["kind"]]
            dashed = s.get("optional")
            body.append(rect(x, yy, colw, CARD_H, fill=fill, stroke=border, rx=12, sw=1.6, dash="6 4" if dashed else None))
            body.append(text(x + 12, yy + 24, s["name"], size=14, weight=800, color=soft))
            for k, line in enumerate(textwrap.wrap(s["runs"], 31)[:3]):
                body.append(text(x + 12, yy + 44 + k * 16, line, size=11.5, color=TEXT))
            yy += CARD_H + 8
        if not stages:
            body.append(rect(x, y, colw, CARD_H, fill="none", stroke=LINE, rx=12, sw=1.2, dash="4 4"))
            body.append(text(x + colw / 2, y + 52, "not a separate stage", size=11.5, color=FAINT, anchor="middle"))
    y += rh + 24

body.append(caption(y + 4, "Dashed outline: optional, not part of the default build. Privilege levels: EL3 secure monitor, S-EL1 trusted OS, EL2 or EL1 non-secure."))
body.append(caption(y + 24, "The interactive version of this chart, with every stage's job, storage and build command, is on the page that shows it."))
write("boot-chains-compared.svg", W, int(H),
      "Boot chains of %d boards aligned by job: " % len(BOARDS) + "; ".join(
          "%s: %s" % (b["name"], ", then ".join(st["name"] for st in b["stages"])) for b in BOARDS) +
      ". The columns are the five jobs every chain has to do: Boot ROM, first loader, secure world, bootloader and kernel.",
      "".join(body))
