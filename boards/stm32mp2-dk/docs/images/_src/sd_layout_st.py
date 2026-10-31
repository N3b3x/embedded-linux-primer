"""docs/images/sd-layout-st.svg - the SD card of STACK=st, ST's own layout (generated)."""
from kit import *

W, H = 1400, 880
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("STACK=st: the SD card in ST's own layout",
               "Eight partitions, back to back from 17 KiB. BL2 first reads a small metadata record that says which of two FIP partitions to load."))

# ---- the proportional tape: 0 .. 18 MiB, then the rootfs -----------------------------------
TX, TW = 40, 1320
MIB = 18.0
def px(mib):
    return TX + (mib / MIB) * (TW - 190)
ty, th = 150, 64
b.append(text(TX, ty - 18, "FIRST 18 MIB, TO SCALE", size=11, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))
b.append(rect(TX, ty, px(MIB) - TX, th, fill="#0a1424", stroke=LINE, rx=8, sw=1.2))

K = 1.0 / 1024.0          # one KiB in MiB
PARTS = [
    # name, start KiB, size KiB, role
    ("fsbla1", 17, 256, "boot"),
    ("fsbla2", 273, 256, "boot"),
    ("metadata1", 529, 256, "fw"),
    ("metadata2", 785, 256, "fw"),
    ("fip-a", 1041, 4096, "secure"),
    ("fip-b", 5137, 4096, "secure"),
    ("u-boot-env", 9233, 512, "fw"),
]
for (name, st, sz, role) in PARTS:
    strong, soft, fill, border = ROLE[role]
    x1, x2 = px(st * K), px((st + sz) * K)
    b.append(rect(x1, ty, max(x2 - x1, 4), th, fill=strong, stroke=border, rx=2, sw=1))
    if sz >= 4096:
        b.append(text((x1 + x2) / 2, ty + 38, name, size=14, weight=800, color="#fff", anchor="middle"))
rx1 = px(16.0)
b.append(rect(rx1, ty, TX + TW - rx1, th, fill=ROLE["rootfs"][0], stroke=ROLE["rootfs"][3], rx=6, sw=1.2))
b.append(text(rx1 + 16, ty + 28, "rootfs", size=15, weight=800, color="#fff"))
b.append(text(rx1 + 16, ty + 48, "16 MiB → end of the card", size=12, color="#ede9fe"))
b.append(text((px(9.8) + px(16.0)) / 2, ty + 38, "unused", size=11, color=FAINT, anchor="middle"))
for m in (0, 1, 5, 9, 16):
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (px(m), ty + th, px(m), ty + th + 8, FAINT))
    b.append(text(px(m), ty + th + 22, ("%g MiB" % m) if m else "0", size=11, color=MUTED, anchor="middle", mono=True))
b.append(text(px(0.0), ty + th + 44, "fsbla1 starts at 17 KiB = sector 34, right after the GPT", size=11, color="#93c5fd", mono=True))

# ---- callout cards ----------------------------------------------------------------------------
CARDS = [
    ("1-2  fsbla1, fsbla2", "boot", "sector 34 and 546", "256 KiB each",
     "Boot ROM", "BL2 twice. The ROM takes fsbla1, and fsbla2 if the first copy is bad. Sector 34 is the first one after the GPT; ST's own image starts here."),
    ("3-4  metadata1, metadata2", "fw", "sector 1058 and 1570", "256 KiB each, 120 bytes used",
     "BL2", "The FWU metadata, written twice: 1 image per bank, 2 banks, bank 0 active. It names the PARTUUID of the FIP partition to load."),
    ("5  fip-a", "secure", "sector 2082", "4 MiB, PARTUUID 4fd84c93-…",
     "BL2, if bank 0 is active", "fip.bin (3.0 MB in this build): BL31, OP-TEE 4.0, U-Boot 2023.10, DDR firmware and ST's device trees."),
    ("6  fip-b", "secure", "sector 10274", "4 MiB, PARTUUID 09c54952-…",
     "BL2, if bank 1 is active", "The same fip.bin. Only a firmware update would switch banks; here it is a spare copy that is never read."),
    ("7  u-boot-env", "fw", "sector 18466", "512 KiB",
     "U-Boot", "U-Boot's environment, found by the partition name. Erased on every flash, because a stale copy would survive."),
    ("8  rootfs", "rootfs", "sector 32768", "rest of the card",
     "U-Boot, then Linux", "ext4, bootable flag, PARTUUID 6d70326b-…-0001. Holds /boot/extlinux/extlinux.conf, Image, the ostl device tree and modules."),
]
cy = 290
cw, gap = 211, 10
for i, (t, role, sec, size, who, what) in enumerate(CARDS):
    x = 40 + i * (cw + gap)
    b.append(card(x, cy, cw, 262, t, role, None, head=44))
    b.append(text(x + 14, cy + 70, "STARTS AT", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, cy + 88, sec, size=12.5, weight=800, mono=True))
    b.append(text(x + 14, cy + 108, size, size=10.5, color=MUTED))
    b.append(text(x + 14, cy + 134, "READ BY", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, cy + 152, who, size=12, weight=700))
    words, line, k = what.split(), "", 0
    for wd in words:
        if len(line) + len(wd) + 1 > 31:
            b.append(text(x + 14, cy + 178 + k * 15, line, size=11, color=MUTED)); line = wd; k += 1
        else:
            line = (line + " " + wd).strip()
    b.append(text(x + 14, cy + 178 + k * 15, line, size=11, color=MUTED))

# ---- how BL2 picks the FIP + extlinux -----------------------------------------------------------
y2 = 586
b.append(text(40, y2, "HOW BL2 CHOOSES THE FIP, AND WHAT U-BOOT READS", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(40, y2 + 8, 1320, 2, fill=LINE, rx=1))
b.append(code(40, y2 + 24, 430, [
    ("1. read metadata1  (else metadata2)", "#fcd34d"),
    ("2. active bank = 0", "#fcd34d"),
    ("3. bank 0 image = PARTUUID 4fd84c93-…", "#fda4af"),
    ("4. load the partition with that PARTUUID", "#fda4af"),
    ("   = fip-a, then BL31, OP-TEE, U-Boot", "#fda4af"),
    ("without PSA_FWU_SUPPORT: look for type", "#9fb0c6"),
    ("GUID 19d5df83-… (the mainline stack)", "#9fb0c6"),
], size=11.5, gap=19, title_s="BL2 with PSA_FWU_SUPPORT=1"))
b.append(code(490, y2 + 24, 470, [
    ("DEFAULT linux", "#fcd34d"),
    ("TIMEOUT 30", "#fcd34d"),
    ("LABEL linux", "#fcd34d"),
    ("  LINUX /boot/Image", "#5eead4"),
    ("  FDT /boot/stm32mp257f-dk-ca35tdcid-ostl.dtb", "#c4b5fd"),
    ("  APPEND root=PARTUUID=6d70326b-0000-4000-8000-", "#93c5fd"),
    ("   000000000001 rootwait rw earlycon", "#93c5fd"),
    ("   modprobe.blacklist=etnaviv console=ttySTM0,115200", "#93c5fd"),
], size=11.5, gap=19, title_s="/boot/extlinux/extlinux.conf"))
b.append(rect(980, y2 + 24, 380, 190, fill=PANEL, stroke=LINE, rx=10))
b.append(text(996, y2 + 48, "What this layout is for", size=13, weight=800))
b.append(lines(996, y2 + 72, [
    "• the same partitions as ST's own SD image",
    "• names and GUIDs the ROM and BL2 expect",
    "• fsbla1 at 17 KiB, exactly as in ST's image,",
    "  so the Boot ROM sees what it sees there",
    "• one FIP in two places, one record that",
    "  names the active one",
    "• no rootflags= (ext4 rejects noatime there)",
], size=12, gap=19, color=TEXT))
b.append(caption(H - 34, "Sizes, GUIDs and PARTUUIDs: config/stack-st.conf and config/stm32mp257f-dk.conf. FWU metadata: U-Boot tools/mkfwumdata; BL2 side: plat/st/common/bl2_io_storage.c in ST's TF-A."))
b.append(caption(H - 14, "Compare with the mainline stack's five partitions in sd-layout.svg: the partition names, type GUIDs and the rootfs are the same; fip is split in two and the metadata is new."))
write("sd-layout-st.svg", W, H,
      "SD card layout of STACK=st, ST's own: GPT with fsbla1 at sector 34 and fsbla2 holding BL2, metadata1 and metadata2 holding the firmware-update metadata, "
      "fip-a and fip-b holding two copies of the FIP with fixed PARTUUIDs that the metadata names, u-boot-env for U-Boot's environment, and an ext4 rootfs from 16 MiB "
      "with /boot/extlinux/extlinux.conf, the kernel Image and ST's device tree.",
      "".join(b))
