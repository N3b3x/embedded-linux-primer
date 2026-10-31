"""docs/images/sd-layout.svg - the SD card, byte for byte (generated)."""
from kit import *

W, H = 1400, 846
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("What is on the SD card, and who reads each part",
               "A GPT disk written by scripts/image.sh. The Boot ROM and BL2 find their partitions by NAME and TYPE, so the exact offsets are ours to choose."))

# ---- the proportional tape: 0 .. 18 MiB, then a break and the rootfs -----------------------
TX, TW = 40, 1320          # tape x and width
MIB = 18.0                 # MiB shown to scale
def px(mib):               # position on the tape
    return TX + (mib / MIB) * (TW - 190)
ty, th = 150, 64
b.append(text(TX, ty - 18, "FIRST 18 MIB, TO SCALE", size=11, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))
b.append(rect(TX, ty, px(MIB) - TX, th, fill="#0a1424", stroke=LINE, rx=8, sw=1.2))

PARTS = [
    # name, start MiB, size MiB, role, type guid, start sector, size, read by
    ("fsbla1", 1.0, 0.25, "boot", "8DA63339-0007-60C0-C436-083AC8230908", "2048", "256 KiB",
     "Boot ROM", "BL2 (tf-a-stm32mp257f-dk.stm32), 175,080 bytes in this build"),
    ("fsbla2", 1.25, 0.25, "boot", "8DA63339-0007-60C0-C436-083AC8230908", "2560", "256 KiB",
     "Boot ROM (fallback)", "the same BL2, second copy"),
    ("fip", 1.5, 4.0, "secure", "19D5DF83-11B0-457B-BE2C-7559C13142A5", "3072", "4 MiB",
     "BL2", "fip.bin: BL31, OP-TEE, U-Boot, DDR firmware, DTBs (2.0 MB in this build)"),
    ("u-boot-env", 9.0, 0.5, "fw", "8DA63339-0007-60C0-C436-083AC8230908", "18432", "512 KiB",
     "U-Boot", "U-Boot environment: 2 copies at the end of this partition"),
]
for (name, st, sz, role, guid, sec, size, who, what) in PARTS:
    strong, soft, fill, border = ROLE[role]
    x1, x2 = px(st), px(st + sz)
    b.append(rect(x1, ty, max(x2 - x1, 5), th, fill=strong, stroke=border, rx=3, sw=1))
# rootfs
rx1 = px(16.0)
b.append(rect(rx1, ty, TX + TW - rx1, th, fill=ROLE["rootfs"][0], stroke=ROLE["rootfs"][3], rx=6, sw=1.2))
b.append(text(rx1 + 16, ty + 28, "rootfs", size=15, weight=800, color="#fff"))
b.append(text(rx1 + 16, ty + 48, "16 MiB → end of the card", size=12, color="#ede9fe"))
# gaps
b.append(text((px(0) + px(1.0)) / 2, ty + 36, "GPT", size=9.5, color=FAINT, anchor="middle"))
b.append(text((px(5.5) + px(9.0)) / 2, ty + 38, "unused", size=11, color=FAINT, anchor="middle"))
b.append(text((px(9.5) + px(16.0)) / 2, ty + 38, "unused", size=11, color=FAINT, anchor="middle"))
b.append(text(rx1 - 4, ty + th + 22, "16 MiB", size=11, color=MUTED, anchor="end", mono=True))
for m in (0, 1, 5.5, 9, 16):
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (px(m), ty + th, px(m), ty + th + 8, FAINT))
    if m not in (16,):
        b.append(text(px(m), ty + th + 22, ("%g MiB" % m) if m else "0", size=11, color=MUTED, anchor="middle", mono=True))

# ---- callout cards --------------------------------------------------------------------------
cy = 290
cw = 256
for i, (name, st, sz, role, guid, sec, size, who, what) in enumerate(PARTS + [("rootfs", 16.0, 0, "rootfs",
        "0FC63DAF-8483-4772-8E79-3D69D8477DE4", "32768", "rest of card", "U-Boot, then Linux", "ext4, label rootfs")]):
    x = 40 + i * (cw + 10)
    w = cw
    b.append(card(x, cy, w, 238, "%d  %s" % (i + 1, name), role, None, sub=size))
    b.append(text(x + 14, cy + 64, "starts at sector", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, cy + 82, sec, size=13, weight=800, mono=True))
    b.append(text(x + 14, cy + 106, "TYPE GUID", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, cy + 124, guid, size=9.5, mono=True, color=MUTED))
    b.append(text(x + 14, cy + 148, "READ BY", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, cy + 166, who, size=12.5, weight=700))
    for j, t in enumerate(_ for _ in [what]):
        # wrap manually at ~44 chars
        words, line, k = t.split(), "", 0
        for wd in words:
            if len(line) + len(wd) + 1 > 33:
                b.append(text(x + 14, cy + 188 + k * 15, line, size=11, color=MUTED)); line = wd; k += 1
            else:
                line = (line + " " + wd).strip()
        b.append(text(x + 14, cy + 188 + k * 15, line, size=11, color=MUTED))

# ---- what is inside rootfs + who finds what ---------------------------------------------------
y2 = 562
b.append(text(40, y2, "INSIDE THE ROOTFS PARTITION", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(40, y2 + 8, 1320, 2, fill=LINE, rx=1))
b.append(code(40, y2 + 24, 440, [
    ("/boot/extlinux/extlinux.conf", "#c4b5fd"),
    ("/boot/Image                      (the kernel)", "#5eead4"),
    ("/boot/stm32mp257f-dk-primer.dtb  (its device tree)", "#c4b5fd"),
    ("/boot/config-6.18.58-custom", "#cbd5e1"),
    ("/lib/modules/6.18.58-custom/…    (drivers as modules)", "#5eead4"),
    ("/etc/fstab  /sbin/init  /usr  /home …  (the distribution)", "#cbd5e1"),
], size=11.5, gap=19, title_s="ext4, label \"rootfs\", PARTUUID 6d70326b-…-000000000001"))
b.append(code(500, y2 + 24, 430, [
    ("DEFAULT linux", "#fcd34d"),
    ("TIMEOUT 10", "#fcd34d"),
    ("LABEL linux", "#fcd34d"),
    ("  LINUX /boot/Image", "#5eead4"),
    ("  FDT /boot/stm32mp257f-dk-primer.dtb", "#c4b5fd"),
    ("  APPEND root=PARTUUID=6d70326b-0000-4000-8000-", "#93c5fd"),
    ("         000000000001 console=ttySTM0,115200", "#93c5fd"),
    ("         rootwait rw", "#93c5fd"),
], size=11.5, gap=19, title_s="/boot/extlinux/extlinux.conf (written by image.sh)"))
b.append(rect(950, y2 + 24, 410, 190, fill=PANEL, stroke=LINE, rx=10))
b.append(text(966, y2 + 48, "Why these rules", size=13, weight=800))
b.append(lines(966, y2 + 72, [
    "• ROM: partition NAMED fsbla1 (then fsbla2)",
    "• BL2: partition of the FIP TYPE GUID, or named fip",
    "• U-Boot: the partition with the 'bootable' flag",
    "  (GPT attribute bit 2) is scanned first",
    "• Linux: root=PARTUUID=… finds rootfs on any",
    "  mmcblk number: SD is not always mmcblk0",
], size=12, gap=19, color=TEXT))
b.append(caption(H - 34, "Sizes and GUIDs: config/stm32mp257f-dk.conf. fsbla1/fsbla2/fip: names and GUID follow TF-A plat/st/common/bl2_io_storage.c and plat/st/common/include/stm32mp_efi.h."))
b.append(caption(H - 14, "U-Boot finds its environment by the partition name (u-boot,mmc-env-partition in arch/arm/dts/stm32mp257f-dk-u-boot.dtsi, env/mmc.c); raw offsets 0x900000/0x940000 are only the fallback."))
write("sd-layout.svg", W, H,
      "SD card layout: GPT with partition fsbla1 and fsbla2 at 1 MiB holding BL2 for the Boot ROM, partition fip holding the FIP for BL2, "
      "partition u-boot-env at 9 MiB for U-Boot's raw environment, and an ext4 rootfs partition from 16 MiB that holds /boot/extlinux/extlinux.conf, "
      "the kernel Image, the device tree and the root filesystem.",
      "".join(b))
