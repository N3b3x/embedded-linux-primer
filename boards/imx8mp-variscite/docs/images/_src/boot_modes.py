"""docs/images/boot-modes.svg - which medium the Boot ROM reads, from the boot switch (generated)."""
from kit import *

W, H = 1400, 800
GREEN = "#6ee7b7"
b = [marker_defs({"a": "#93c5fd", "f": "#fb7185", "u": "#5eead4"})]
b.append(title("Which medium does the Boot ROM read?",
               "The boot switch on the carrier sets BOOT_MODE. The ROM tries that one medium and, if it finds nothing valid, falls back to USB."))

# ---- the ROM ------------------------------------------------------------------
RX, RY, RW, RH = 32, 112, 250, 560
b.append(card(RX, RY, RW, RH, "Boot ROM", "boot", "microchip", sub="mask ROM", head=44))
b.append(lines(RX + 16, RY + 76, ["The first code that runs. It is", "burned into the chip and can never", "be overwritten, so USB recovery", "always works."], size=12.5, gap=19, color=MUTED))
steps = [("1", "read BOOT_MODE", "the pins the boot switch sets"),
         ("2", "try that one medium", "read the container at a fixed place"),
         ("3", "nothing valid?", "serial download over USB")]
for i, (n, t, s) in enumerate(steps):
    y = RY + 192 + i * 78
    b.append(badge(RX + 30, y + 14, n, ROLE["boot"][3]))
    b.append(text(RX + 52, y + 12, t, size=14, weight=800))
    b.append(text(RX + 52, y + 31, s, size=12, color=MUTED))
b.append(rect(RX + 14, RY + 436, RW - 28, 100, fill="#050a14", stroke="#334155", rx=10, sw=1.2))
b.append(text(RX + 28, RY + 460, "On this board, per the SPL log:", size=11.5, color=MUTED))
b.append(text(RX + 28, RY + 482, "Boot Stage: Primary boot", size=11.5, mono=True, color="#6ee7b7"))
b.append(text(RX + 28, RY + 500, "image offset 0x8000  (SD)", size=11.5, mono=True, color="#6ee7b7"))
b.append(text(RX + 28, RY + 518, "Boot Stage: USB boot (uuu)", size=11.5, mono=True, color="#5eead4"))

# ---- three rows ----------------------------------------------------------------
CX1, CW1 = 340, 240      # switch chips
CX2, CW2 = 640, 300      # medium
CX3, CW3 = 1000, 368     # where in it
ROWS = {"sd": (112, 118), "emmc": (262, 210), "usb": (540, 132)}


def chip_sw(y, h, label, sub, role):
    strong, soft, fill, border = ROLE[role]
    out = rect(CX1, y, CW1, h, fill=fill, stroke=border, rx=14, sw=1.8)
    out += text(CX1 + 16, y + 28, "boot switch", size=11.5, color=MUTED)
    out += text(CX1 + 16, y + 54, label, size=19, weight=800, color=soft)
    out += text(CX1 + 16, y + 76, sub, size=12, color=MUTED)
    return out


def medium(y, h, name, sub, lines_, ic):
    out = rect(CX2, y, CW2, h, fill=PANEL, stroke=ROLE["hw"][3], rx=14, sw=1.6)
    out += icon(ic, CX2 + 14, y + 14, 24, "#cbd5e1")
    out += text(CX2 + 48, y + 31, name, size=15, weight=800)
    out += text(CX2 + 48, y + 50, sub, size=12, color=MUTED)
    for i, ln in enumerate(lines_):
        out += text(CX2 + 16, y + 78 + i * 19, ln, size=12, color="#cbd5e1", mono=True)
    return out


def where(x, y, w, h, head, rows, role="fw", tag=None):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, y, w, h, fill=fill, stroke=border, rx=12, sw=1.6)
    out += text(x + 14, y + 26, head, size=14, weight=800, color=soft)
    for i, r in enumerate(rows):
        out += text(x + 14, y + 46 + i * 16, r, size=12, color=TEXT if i == 0 else MUTED)
    if tag:
        out += chip(x + 14, y + h - 27, tag, "boot", size=11)
    return out


# row A: SD
y, h = ROWS["sd"]
b.append(chip_sw(y, h, "SD", "carrier switch position", "hw"))
b.append(medium(y, h, "SD card slot", "uSDHC2 · U-Boot mmc 1 · /dev/mmcblk1", ["raw read, no filesystem"], "hard-drive"))
b.append(where(CX3, y, CW3, h, "imx-boot.bin at 32 KiB", ["the layout of sdcard.img", "(docs/06 · ./build.sh flash)"], "fw"))
# row B: eMMC
y, h = ROWS["emmc"]
b.append(chip_sw(y, h, "eMMC", "carrier switch position", "hw"))
b.append(medium(y, h, "On-module eMMC", "uSDHC3 · U-Boot mmc 2 · /dev/mmcblk2",
                ["EXT_CSD PARTITION_CONFIG", "BOOT_PARTITION_ENABLE:", "1 or 2 → boot0 or boot1", "0 → the user area"], "database"))
b.append(where(CX3, y, CW3, 96, "boot0 / boot1 at offset 0",
               ["the container starts at the very first byte", "of the hardware boot partition"], "fw", "./build.sh uuu emmc"))
b.append(where(CX3, y + 112, CW3, 98, "user area at 32 KiB",
               ["same offset as on SD: the copy inside", "sdcard.img, if no boot partition is enabled"], "fw", "dd sdcard.img · Variscite installer"))
# row C: USB
y, h = ROWS["usb"]
b.append(chip_sw(y, h, "serial download", "(USB), or a fallback", "normal"))
b.append(medium(y, h, "USB OTG port", "the port the PC's cable goes to", ["USB ID 1fc9:0146", "no storage is read"], "usb"))
b.append(where(CX3, y, CW3, h, "the host PC sends the boot image", ["uuu: SDPS: boot -f imx-boot.bin", "the SPL starts from USB, not from a disk"], "normal", "./build.sh uuu emmc | boot"))

# ---- arrows ----------------------------------------------------------------------
for key, ycenter in (("sd", 171), ("emmc", 367), ("usb", 606)):
    b.append(arrow(RX + RW + 4, ycenter, CX1 - 6, ycenter, "#93c5fd", "a", width=2.6))
    b.append(arrow(CX1 + CW1 + 4, ycenter, CX2 - 6, ycenter, "#93c5fd", "a", width=2.6))
b.append(arrow(CX2 + CW2 + 4, 171, CX3 - 6, 171, "#93c5fd", "a", width=2.6))
b.append(arrow(CX2 + CW2 + 4, 330, CX3 - 6, 310, "#93c5fd", "a", width=2.6))
b.append(arrow(CX2 + CW2 + 4, 400, CX3 - 6, 420, "#93c5fd", "a", width=2.6))
b.append(arrow(CX2 + CW2 + 4, 606, CX3 - 6, 606, "#5eead4", "u", width=2.6))
# fallback
b.append(arrow(CX1 + CW1 / 2, 474, CX1 + CW1 / 2, 536, "#fb7185", "f", width=2.6, dash="7 5"))
b.append(pill(CX1 + CW1 / 2 + 150, 505, "no card / no valid image", "#fb7185", size=11.5, mono=False))
b.append(text(CX3, 700 - 6, "", size=1))

# ---- what happens next --------------------------------------------------------------
NY = 700
b.append(rect(32, NY, 1336, 78, fill=PANEL, stroke=ROLE["boot"][3], rx=14, sw=1.6))
b.append(icon("arrow-right-left", 50, NY + 22, 26, "#93c5fd"))
b.append(text(90, NY + 30, "After the ROM it is the same software everywhere: SPL → TF-A BL31 → U-Boot.", size=14.5, weight=800))
b.append(text(90, NY + 52, "U-Boot asks the ROM where it came from: SD → mmcdev 1 · root=/dev/mmcblk1p1,   eMMC → mmcdev 2 · root=/dev/mmcblk2p1,   USB → it starts fastboot and waits for uuu.", size=12.5, color=MUTED))
b.append(text(90, NY + 69, "The imx-boot.bin is the same file in all three cases; only the offset the ROM reads it from differs (32 KiB or 0).", size=12.5, color=MUTED))

write("boot-modes.svg", W, H,
      "Decision diagram of the i.MX 8M Plus Boot ROM on the Variscite carriers. The boot switch selects one medium. With the switch on SD "
      "the ROM reads imx-boot.bin at 32 KiB of the SD card. With the switch on eMMC it reads the eMMC boot partition boot0 or boot1 at "
      "offset 0 when the eMMC boot configuration enables one, otherwise the user area at 32 KiB. With serial download, or as a fallback "
      "when the chosen medium has no valid image such as an empty SD slot, it waits on the USB OTG port for a host running uuu. After "
      "the ROM the same SPL, TF-A and U-Boot run, and U-Boot picks root=/dev/mmcblk1p1, /dev/mmcblk2p1 or fastboot from where it came from.",
      "".join(b))
