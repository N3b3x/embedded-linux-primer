"""docs/images/emmc-layout.svg - what is where in the on-module eMMC (generated)."""
from kit import *

W, H = 1400, 800
b = [marker_defs({"a": "#93c5fd", "w": "#fcd34d"})]
b.append(title("What is where in the on-module eMMC",
               "Three hardware areas. The ROM reads the container from the one that EXT_CSD names; the user area holds the partition table and the root filesystem."))

BX, BW = 250, 1110   # bar start and width (the bars are schematic, not to scale)


def area(y, h, name, sub, linux, uboot, role="hw"):
    strong, soft, fill, border = ROLE[role]
    out = text(32, y + 24, name, size=16, weight=800)
    out += text(32, y + 44, sub, size=12, color=MUTED)
    out += text(32, y + 66, linux, size=11.5, mono=True, color="#93c5fd")
    out += text(32, y + 84, uboot, size=11.5, mono=True, color="#fcd34d")
    out += rect(BX, y, BW, h, fill=PANEL, stroke=border, rx=10, sw=1.6)
    return out


def seg(x, y, w, h, label, sub, role, dim=False, dash=False):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, y, w, h, fill=fill if dim else strong, stroke=border, rx=6, sw=1.4, dash="6 4" if dash else None,
               opacity=None)
    out += text(x + w / 2, y + h / 2 - 2, label, size=12.5, weight=800, anchor="middle", color=soft if dim else "#fff")
    if sub:
        out += text(x + w / 2, y + h / 2 + 15, sub, size=11, anchor="middle", color=soft if dim else "#e2e8f0")
    return out


def off(x, y, s, color=MUTED, anchor="start"):
    return text(x, y, s, size=11.5, mono=True, color=color, anchor=anchor)


# ---- SD card for comparison -----------------------------------------------------------
y = 112
b.append(area(y, 70, "SD card", "what ./build.sh flash writes", "/dev/mmcblk1", "mmc 1"))
b.append(seg(BX + 8, y + 10, 40, 50, "MBR", "", "hw"))
b.append(seg(BX + 56, y + 10, 190, 50, "imx-boot.bin", "ROM reads it here", "fw"))
b.append(seg(BX + 254, y + 10, 70, 50, "env", "", "secure", dim=True, dash=True))
b.append(seg(BX + 332, y + 10, BW - 348, 50, "p1 · ext4 \"root\"", "/boot (Image.gz, dtbs) and the OS", "rootfs"))
b.append(off(BX + 56, y + 80, "32 KiB"))
b.append(off(BX + 254, y + 80, "7 MiB"))
b.append(off(BX + 332, y + 80, "8 MiB"))
b.append(off(BX + 8, y + 80, "0"))

# ---- eMMC ---------------------------------------------------------------------------------
b.append(text(32, 236, "ON-MODULE eMMC  (uSDHC3, /dev/mmcblk2, U-Boot mmc 2)", size=12.5, weight=800, color=ROLE["boot"][1],
              extra=' letter-spacing="1.2"'))
b.append('<line x1="32" y1="246" x2="1368" y2="246" stroke="%s" stroke-width="1.2" stroke-dasharray="4 5"/>' % LINE)

y = 262
b.append(area(y, 78, "boot0", "hardware boot partition 1, 4 MiB", "/dev/mmcblk2boot0", "mmc dev 2 1", "boot"))
b.append(seg(BX + 8, y + 10, 250, 58, "imx-boot.bin", "starts at byte 0", "fw"))
b.append(seg(BX + 266, y + 10, BW - 282, 58, "free", "", "hw", dim=True))
b.append(off(BX + 8, y + 94, "0 (not 32 KiB)", "#fcd34d"))

y = 372
b.append(area(y, 78, "boot1", "hardware boot partition 2, 4 MiB", "/dev/mmcblk2boot1", "mmc dev 2 2", "boot"))
b.append(seg(BX + 8, y + 10, 250, 58, "imx-boot.bin", "second copy, starts at byte 0", "fw"))
b.append(seg(BX + 266, y + 10, BW - 282, 58, "free", "", "hw", dim=True))

y = 482
b.append(area(y, 78, "user area", "all the rest, 29 GiB here", "/dev/mmcblk2", "mmc dev 2 0", "rootfs"))
b.append(seg(BX + 8, y + 10, 40, 58, "MBR", "", "hw"))
b.append(seg(BX + 56, y + 10, 190, 58, "imx-boot.bin", "copy, unused while boot0 is on", "fw", dim=True, dash=True))
b.append(seg(BX + 254, y + 10, 70, 58, "env", "1 MiB", "secure", dim=True, dash=True))
b.append(seg(BX + 332, y + 10, BW - 348, 58, "p1 · ext4 \"root\"  →  /dev/mmcblk2p1", "grow it to the whole eMMC on the board (docs/16)", "rootfs"))
b.append(off(BX + 56, y + 94, "32 KiB"))
b.append(off(BX + 254, y + 94, "7 MiB"))
b.append(off(BX + 332, y + 94, "8 MiB"))
b.append(off(BX + 8, y + 94, "0"))

y = 598
b.append(rect(32, y, 218, 50, fill="none", stroke="none"))
b.append(text(32, y + 20, "rpmb", size=16, weight=800))
b.append(text(32, y + 40, "replay-protected, 4 MiB", size=12, color=MUTED))
b.append(rect(BX, y + 4, BW, 40, fill=PANEL2, stroke=ROLE["hw"][3], rx=10, sw=1.2, dash="6 4"))
b.append(text(BX + 16, y + 30, "/dev/mmcblk2rpmb · not used by this build (secure storage with OP-TEE, docs/13)", size=12.5, color=MUTED))

# ---- EXT_CSD panel -----------------------------------------------------------------------
y = 668
b.append(rect(32, y, 1336, 112, fill="#050a14", stroke="#334155", rx=14, sw=1.4))
b.append(icon("settings-2", 50, y + 16, 24, "#93c5fd"))
b.append(text(86, y + 34, "Which area does the ROM read?  EXT_CSD[179] PARTITION_CONFIG, written by  mmc partconf 2 1 1 0", size=14, weight=800))
b.append(text(86, y + 58, "BOOT_PARTITION_ENABLE = 1  →  boot0        = 2  →  boot1        = 7  →  user area        = 0  →  not enabled (the ROM boots the user area at 32 KiB)", size=12.5, mono=True, color="#cbd5e1"))
b.append(text(86, y + 80, "BOOT_ACK = 1: the eMMC sends the boot acknowledge.     PARTITION_ACCESS = 0: afterwards, reads and writes go to the user area.", size=12.5, mono=True, color="#cbd5e1"))
b.append(text(86, y + 100, "Read it on the board:  mmc extcsd read /dev/mmcblk2 | grep PARTITION_CONFIG     ·     in U-Boot:  mmc partconf 2", size=12.5, mono=True, color="#93c5fd"))

write("emmc-layout.svg", W, H,
      "Layout of the Variscite on-module eMMC for this repository. The SD card layout is shown for comparison: imx-boot.bin at 32 KiB, "
      "U-Boot's saved environment at 7 MiB, and the ext4 root partition from 8 MiB. The eMMC has three hardware areas. The boot "
      "partitions boot0 and boot1 hold imx-boot.bin starting at byte 0. The user area holds the partition table, a copy of imx-boot.bin "
      "at 32 KiB that is unused while a boot partition is enabled, the U-Boot environment at 7 MiB and the root partition from 8 MiB. "
      "The RPMB partition is not used. The EXT_CSD PARTITION_CONFIG field, set with mmc partconf, selects boot0, boot1 or the user area "
      "for the Boot ROM.",
      "".join(b))
