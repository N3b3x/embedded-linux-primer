"""docs/images/build-models.svg - the two ways a board gets its software (generated)."""
from kit import *

W, H = 1400, 830
A = "#e5edf7"
b = [marker_defs({"a": A, "r": "#fb7185", "t": "#5eead4", "f": "#fcd34d"})]
b.append(title("Two ways software reaches a board",
               "Which one you get is decided by the silicon vendor's boot ROM and tooling, not by you. Everything else in the stack is the same."))


def panel(x, title_s, sub, role, ic):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, 100, 668, 632, fill=fill, stroke=border, rx=16, sw=1.8)
    out += rect(x, 100, 668, 64, fill=strong, rx=16)
    out += rect(x, 140, 668, 24, fill=strong, rx=0)
    out += icon(ic, x + 20, 118, 28, "#ffffff")
    out += text(x + 60, 128, title_s, size=18, weight=800, color="#ffffff")
    out += text(x + 60, 150, sub, size=12.5, color="#e2e8f0")
    return out


def step(x, y, n, t, d, role="hw", w=628, cmd=None):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, y, w, 70, fill=PANEL, stroke=border, rx=12, sw=1.4)
    out += badge(x + 26, y + 35, n, strong, r=12)
    out += text(x + 52, y + 28, t, size=14, weight=800, color=soft)
    out += text(x + 52, y + 50, d, size=12, color=MUTED)
    if cmd:
        out += text(x + w - 14, y + 28, cmd, size=11.5, color=TEXT, mono=True, anchor="end")
    return out


# ---- left: SD-card image model ----------------------------------------------
x = 32
b.append(panel(x, "SD-card image model", "i.MX 8M Plus  ·  STM32MP257F-DK", "boot", "hard-drive"))
L = [
    ("1", "Build the pieces", "boot firmware, U-Boot, kernel, rootfs: each into build/deploy/", "fw", "./build.sh all"),
    ("2", "Assemble ONE disk image", "bootloader at a fixed offset or partition, then the rootfs", "fw", "image.sh"),
    ("3", "Write the image to an SD card", "the PC only needs a card reader; no vendor tool", "rootfs", "./build.sh flash"),
    ("4", "Move the card, set the boot switch", "the Boot ROM reads the card by itself", "hw", "switch → SD"),
    ("5", "Power on", "ROM → firmware → U-Boot → Linux, all from the card", "normal", "serial 115200"),
]
yy = 184
for n, t, d, role, cmd in L:
    b.append(step(x + 20, yy, n, t, d, role, cmd=cmd))
    if n != "5":
        b.append(arrow(x + 334, yy + 72, x + 334, yy + 96, A, "a", width=2.4))
    yy += 100
b.append(rect(x + 20, 684, 628, 38, fill="#050a14", stroke="#334155", rx=10))
b.append(text(x + 34, 708, "Fix a mistake: re-flash the card. The ROM runs first, so a bad card cannot brick it.", size=12.5, color="#5eead4", weight=700))

# ---- right: vendor flash model ---------------------------------------------------
x = 700
b.append(panel(x, "Vendor-flash model", "Jetson Orin Nano  (also: many QSPI/eMMC-only SoCs)", "secure", "usb"))
R = [
    ("1", "Download the vendor's board support package", "signed boot firmware + flashing tools + sample rootfs", "fw", "./build.sh fetch"),
    ("2", "Add your parts into its staging tree", "your kernel, device tree, rootfs changes", "rootfs", "kernel · rootfs"),
    ("3", "Put the board in recovery mode", "jumper/button + USB cable: the Boot ROM now waits for the host", "hw", "lsusb"),
    ("4", "The vendor tool flashes it over USB", "boot firmware into on-board flash, OS into SD/NVMe/eMMC", "secure", "./build.sh flash"),
    ("5", "Reboot", "firmware now lives in the board's own flash, not on a card", "normal", "serial 115200"),
]
yy = 184
for n, t, d, role, cmd in R:
    b.append(step(x + 20, yy, n, t, d, role, cmd=cmd))
    if n != "5":
        b.append(arrow(x + 334, yy + 72, x + 334, yy + 96, A, "a", width=2.4))
    yy += 100
b.append(rect(x + 20, 684, 628, 38, fill="#050a14", stroke="#334155", rx=10))
b.append(text(x + 34, 708, "Fix a mistake: flash again. Recovery mode lives in the ROM (until you burn fuses).", size=12.5, color="#fda4af", weight=700))

b.append(caption(774, "Why it matters: the SD-card model lets you iterate with one cheap card and see the whole build as one image. The vendor-flash model needs a Linux x86-64 host"))
b.append(caption(794, "and the vendor's tools, but the boot firmware sits in on-board flash, so it can be signed and updated as a unit, separately from the OS storage."))
write("build-models.svg", W, H,
      "Two ways software reaches a board. SD-card image model: build the pieces, assemble one disk image, write it to an SD card, set the boot "
      "switch, power on. Vendor-flash model: download the vendor's board support package, add your kernel and rootfs into its staging tree, put "
      "the board into USB recovery mode, flash with the vendor tool, reboot.",
      "".join(b))
