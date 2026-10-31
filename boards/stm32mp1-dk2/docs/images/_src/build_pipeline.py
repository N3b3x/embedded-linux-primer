"""docs/images/build-pipeline.svg - what ./build.sh all does (generated)."""
from kit import *

W, H = 1400, 812
A = "#e5edf7"
b = [marker_defs({"a": A, "o": "#fcd34d"})]
b.append(title("What ./build.sh all does: sources in, one SD card image out",
               "Four source trees go in, built with two pinned Arm compilers. Everything lands in build/deploy/; scripts/image.sh stitches it together without root."))

# columns: sources | steps | artifacts | image
COLX = [40, 360, 800, 1090]
COLW = [290, 410, 260, 270]
for x, w, t in zip(COLX, COLW, ["SOURCES (pinned)", "STEPS", "ARTIFACTS  build/deploy/", "RESULT"]):
    b.append(text(x, 120, t, size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.3"'))
    b.append(rect(x, 128, w, 2, fill=LINE, rx=1))

# --- sources ---
SRC = [
    ("OP-TEE 4.11.0", "git  f54190f2", "secure", "lock", "trusted OS, monitor, SCMI server"),
    ("U-Boot v2026.07", "git  ece349ad", "boot", "rocket", "stm32mp15_defconfig"),
    ("TF-A v2.15.0", "git  da738d5e", "secure", "shield-check", "BL2 only (no BL31 here)"),
    ("TF-A tools/fiptool", "built from the same tree", "secure", "package", "host tool that writes the FIP"),
    ("Linux 6.18.58", "kernel.org tarball", "normal", "linux", "multi_v7_defconfig + config/kernel/*.cfg"),
    ("Debian trixie / Alpine 3.24", "armhf / armv7 userland", "rootfs", "boxes", "userland"),
]
sy = 142
for i, (n, sub, role, ic, note) in enumerate(SRC):
    y = sy + i * 88
    b.append(card(COLX[0], y, COLW[0], 76, n, role, ic, filled_icon=(ic == "linux"), head=34))
    b.append(text(COLX[0] + 14, y + 52, sub, size=11.5, mono=True, color=MUTED))
    b.append(text(COLX[0] + 14, y + 68, note, size=11, color=TEXT))

# --- steps ---
STEPS = [
    ("firmware optee", "make PLATFORM=stm32mp1, dts stm32mp157c-dk2-scmi", 1),
    ("firmware uboot", "stm32mp15_defconfig, DEVICE_TREE=st/stm32mp157c-dk2-scmi", 2),
    ("firmware tfa", "BL2 with STM32 header, AARCH32_SP=optee", 3),
    ("firmware fip", "fiptool packs OP-TEE (3 files), U-Boot, DTBs", 4),
    ("kernel", "multi_v7_defconfig → zImage, DTB, modules", 5),
    ("rootfs", "mmdebstrap (Debian) or Alpine minirootfs → rootfs.tar", 6),
]
stepy = {}
for i, (cmd, what, n) in enumerate(STEPS):
    y = sy + i * 88
    stepy[i] = y
    b.append(rect(COLX[1], y, COLW[1], 76, fill=PANEL, stroke="#3b82f6" if i < 5 else ("#14b8a6" if i == 5 else "#8b5cf6"), rx=12, sw=1.5))
    b.append(badge(COLX[1] + 24, y + 26, n, "#e2e8f0", r=12))
    b.append(text(COLX[1] + 48, y + 31, "./build.sh " + cmd, size=14, weight=800, mono=True))
    b.append(text(COLX[1] + 48, y + 54, what, size=11.5, color=MUTED))
    b.append(arrow(COLX[0] + COLW[0] + 2, y + 38, COLX[1] - 4, y + 38, A, "a", width=2.6))

# --- artifacts ---
ART = [
    ("tee-{header,pager,pageable}_v2.bin", "44 B + 74,648 B + 364,544 B", "secure"),
    ("u-boot-nodtb.bin   u-boot.dtb", "1.1 MB + 112 KB", "boot"),
    ("tf-a-stm32mp157f-dk2.stm32", "209,316 B", "boot"),
    ("fip.bin", "1,650,422 B · packs the three above", "secure"),
    ("kernel.tar.gz  (zImage, dtb, modules)", "", "normal"),
    ("rootfs.tar", "", "rootfs"),
]
for i, (n, sz, role) in enumerate(ART):
    y = sy + i * 88
    strong, soft, fill, border = ROLE[role]
    b.append(rect(COLX[2], y + 8, COLW[2], 60, fill=fill, stroke=border, rx=10, sw=1.3, dash="6 4" if sz is None else None))
    b.append(text(COLX[2] + 12, y + 34, n, size=11, mono=True, weight=700, color=soft))
    if sz:
        b.append(text(COLX[2] + 12, y + 54, sz, size=11, color=MUTED))
    b.append(arrow(COLX[1] + COLW[1] + 2, y + 38, COLX[2] - 4, y + 38, A, "a", width=2.6))

# --- image step ---
iy = sy + 2 * 88
ih = 3 * 88 + 64
IT = sy + 2 * 88 - 4
b.append(rect(COLX[3], IT, COLW[3], 4 * 88 + 6, fill="#0d1a33", stroke="#fcd34d", rx=14, sw=1.6))
b.append(text(COLX[3] + 16, IT + 28, "./build.sh image", size=15, weight=800, mono=True, color="#fcd34d"))
b.append(lines(COLX[3] + 16, IT + 58, [
    "fakeroot + mke2fs -d:",
    "  rootfs + kernel → ext4",
    "  + /boot/extlinux/extlinux.conf",
    "truncate + sfdisk:",
    "  GPT, 5 partitions",
    "dd BL2 → fsbl1, fsbl2",
    "dd fip.bin → fip",
    "dd ext4 → rootfs",
    "bmaptool create → .bmap",
], size=11.5, gap=24, color=TEXT))
b.append(path_arrow([(COLX[2] + COLW[2] + 2, sy + 2 * 88 + 38), (COLX[3] - 4, sy + 2 * 88 + 38)], A, "a", width=2.6))
b.append(path_arrow([(COLX[2] + COLW[2] + 2, sy + 3 * 88 + 38), (COLX[3] - 4, sy + 3 * 88 + 38)], A, "a", width=2.6))
b.append(path_arrow([(COLX[2] + COLW[2] + 2, sy + 4 * 88 + 38), (COLX[3] - 4, sy + 4 * 88 + 38)], A, "a", width=2.6))
b.append(path_arrow([(COLX[2] + COLW[2] + 2, sy + 5 * 88 + 38), (COLX[3] - 4, sy + 5 * 88 + 38)], A, "a", width=2.6))
# result
ry = IT + 4 * 88 + 6 + 30
b.append(arrow(COLX[3] + COLW[3] / 2, IT + 4 * 88 + 8, COLX[3] + COLW[3] / 2, ry - 10, A, "a", width=2.6))
b.append(rect(COLX[3], ry - 8, COLW[3], 66, fill=ROLE["boot"][2], stroke=ROLE["boot"][3], rx=12, sw=1.6))
b.append(text(COLX[3] + 14, ry + 16, "sdcard.img  (+ .bmap)", size=13.5, weight=800, mono=True, color="#93c5fd"))
b.append(text(COLX[3] + 14, ry + 38, "→ ./build.sh flash -d /dev/sdX", size=11.5, mono=True, color=MUTED))
b.append(caption(H - 40, "Dry run: ./build.sh --dry-run all | less -R prints every command with the reason it exists. Each step also runs alone, e.g. ./build.sh firmware fip re-packs only the FIP."))
b.append(caption(H - 18, "Arm GNU Toolchain 14.3 (sha256-pinned): arm-none-eabi for TF-A and the OP-TEE core (no OS), arm-none-linux-gnueabihf for the kernel and U-Boot. Source trees are checked out once into build/src/ and left alone."))
write("build-pipeline.svg", W, H,
      "Build pipeline: the Arm toolchains, OP-TEE, U-Boot, TF-A, the Linux kernel and a Debian or Alpine rootfs are "
      "built by firmware, kernel and rootfs steps into tee, u-boot, BL2, fip.bin, kernel and rootfs artifacts, which the image step assembles "
      "into a GPT sdcard.img with fakeroot, mke2fs, sfdisk and dd.",
      "".join(b))
