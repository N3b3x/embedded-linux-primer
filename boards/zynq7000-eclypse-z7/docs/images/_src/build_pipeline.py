"""docs/images/build-pipeline.svg - what ./build.sh all does (generated)."""
from kit import *

W, H = 1400, 800
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("What ./build.sh all does: sources in, one SD card image out",
               "Two source trees and one hardware-design file go in, built with one pinned 32-bit Arm compiler. Everything lands in build/deploy/; image.sh stitches it together without root."))

COLX = [40, 360, 830, 1090]
COLW = [290, 440, 230, 270]
for x, w, t in zip(COLX, COLW, ["SOURCES (pinned)", "STEPS", "ARTIFACTS  build/deploy/", "RESULT"]):
    b.append(text(x, 120, t, size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.3"'))
    b.append(rect(x, 128, w, 2, fill=LINE, rx=1))

def small_src(y, name, sub, role, ic, filled=False, h=76):
    return (card(COLX[0], y, COLW[0], h, name, role, ic, filled_icon=filled, head=32)
            + text(COLX[0] + 14, y + 50, sub, size=11, mono=True, color=MUTED)
            + text(COLX[0] + 14, y + 66, "", size=11))

R1, R2, R3 = 142, 432, 544
# --- row 1: the U-Boot step with its three inputs
b.append(small_src(R1, "U-Boot v2026.07", "git @ ece349ad", "boot", "rocket"))
b.append(small_src(R1 + 92, "ps7_init_gpl.c + .h", "hardware design · sha256 b7f74d49…", "fw", "file-cog"))
b.append(small_src(R1 + 184, "zynq-eclypse-z7.dts", "custom/dts · also in the kernel", "rootfs", "file-text"))
b.append(rect(COLX[1], R1, COLW[1], 266, fill=PANEL, stroke=ROLE["boot"][3], rx=12, sw=1.5))
b.append(badge(COLX[1] + 24, R1 + 28, 1, "#e2e8f0", r=12))
b.append(text(COLX[1] + 48, R1 + 33, "./build.sh uboot", size=14, weight=800, mono=True))
b.append(lines(COLX[1] + 24, R1 + 66, [
    "ps7: extract the two files from the hardware",
    "     design, CRLF → LF, () → (void)",
    "copy the DTS into arch/arm/dts, apply patches/",
    "defconfig + config/uboot/*.config, add",
    "     CONFIG_XILINX_PS_INIT_FILE=<those files>",
    "one make builds:",
    "     spl/u-boot-spl → spl/boot.bin (mkimage",
    "     -T zynqimage) and u-boot.img (a FIT)",
], size=11.5, gap=20, color=TEXT))
for yy in (R1 + 38, R1 + 130, R1 + 222):
    b.append(arrow(COLX[0] + COLW[0] + 2, yy, COLX[1] - 4, yy, A, "a", width=2.6))
# artifacts of row 1
for i, (n, sz) in enumerate([("BOOT.BIN", "131,676 B · the SPL in a Zynq boot image"), ("u-boot.img", "1.1 MB · U-Boot proper as a FIT")]):
    y = R1 + 30 + i * 110
    strong, soft, fill, border = ROLE["boot"]
    b.append(rect(COLX[2], y, COLW[2], 80, fill=fill, stroke=border, rx=10, sw=1.3))
    b.append(text(COLX[2] + 12, y + 32, n, size=14, mono=True, weight=700, color=soft))
    b.append(text(COLX[2] + 12, y + 56, sz, size=10.5, color=MUTED))
    b.append(arrow(COLX[1] + COLW[1] + 2, y + 40, COLX[2] - 4, y + 40, A, "a", width=2.6))
# --- row 2: kernel
b.append(small_src(R2, "Linux 6.18.58", "tarball · multi_v7_defconfig", "normal", "linux", True))
b.append(rect(COLX[1], R2, COLW[1], 96, fill=PANEL, stroke=ROLE["normal"][3], rx=12, sw=1.5))
b.append(badge(COLX[1] + 24, R2 + 28, 2, "#e2e8f0", r=12))
b.append(text(COLX[1] + 48, R2 + 33, "./build.sh kernel", size=14, weight=800, mono=True))
b.append(lines(COLX[1] + 24, R2 + 58, ["defconfig + fragment; patches/ and the same", "DTS go in; make zImage modules + the DTB"], size=11.5, gap=18, color=TEXT))
b.append(arrow(COLX[0] + COLW[0] + 2, R2 + 38, COLX[1] - 4, R2 + 38, A, "a", width=2.6))
strong, soft, fill, border = ROLE["normal"]
b.append(rect(COLX[2], R2, COLW[2], 80, fill=fill, stroke=border, rx=10, sw=1.3))
b.append(text(COLX[2] + 12, R2 + 30, "kernel.tar.gz", size=14, mono=True, weight=700, color=soft))
b.append(text(COLX[2] + 12, R2 + 52, "zImage, DTB, modules", size=10.5, color=MUTED))
b.append(arrow(COLX[1] + COLW[1] + 2, R2 + 40, COLX[2] - 4, R2 + 40, A, "a", width=2.6))
# --- row 3: rootfs
b.append(small_src(R3, "Debian trixie · Alpine 3.24", "armhf via qemu · armv7 download", "rootfs", "boxes"))
b.append(rect(COLX[1], R3, COLW[1], 96, fill=PANEL, stroke=ROLE["rootfs"][3], rx=12, sw=1.5))
b.append(badge(COLX[1] + 24, R3 + 28, 3, "#e2e8f0", r=12))
b.append(text(COLX[1] + 48, R3 + 33, "./build.sh rootfs", size=14, weight=800, mono=True))
b.append(lines(COLX[1] + 24, R3 + 58, ["mmdebstrap (armhf, qemu-user) or the Alpine", "minirootfs plus a serial login → rootfs.tar"], size=11.5, gap=18, color=TEXT))
b.append(arrow(COLX[0] + COLW[0] + 2, R3 + 38, COLX[1] - 4, R3 + 38, A, "a", width=2.6))
strong, soft, fill, border = ROLE["rootfs"]
b.append(rect(COLX[2], R3, COLW[2], 80, fill=fill, stroke=border, rx=10, sw=1.3))
b.append(text(COLX[2] + 12, R3 + 30, "rootfs.tar", size=14, mono=True, weight=700, color=soft))
b.append(arrow(COLX[1] + COLW[1] + 2, R3 + 40, COLX[2] - 4, R3 + 40, A, "a", width=2.6))
# --- image
IT, IH = R1, R3 + 80 - R1
b.append(rect(COLX[3], IT, COLW[3], IH, fill="#0d1a33", stroke="#fcd34d", rx=14, sw=1.6))
b.append(badge(COLX[3] + 24, IT + 28, 4, "#e2e8f0", r=12))
b.append(text(COLX[3] + 46, IT + 33, "./build.sh image", size=15, weight=800, mono=True, color="#fcd34d"))
b.append(lines(COLX[3] + 16, IT + 70, [
    "fakeroot + mke2fs -d:",
    "  rootfs + modules → ext4",
    "mkfs.vfat + mcopy into a FAT:",
    "  BOOT.BIN, u-boot.img, zImage,",
    "  DTB, extlinux/extlinux.conf",
    "truncate + sfdisk: MBR table",
    "dd FAT → partition 1",
    "dd ext4 → partition 2",
    "bmaptool create → .bmap",
], size=11.5, gap=26, color=TEXT))
for yy in (R1 + 70, R1 + 180, R2 + 40, R3 + 40):
    b.append(path_arrow([(COLX[2] + COLW[2] + 2, yy), (COLX[3] - 4, yy)], A, "a", width=2.6))
ry = IT + IH + 24
b.append(arrow(COLX[3] + COLW[3] / 2, IT + IH + 2, COLX[3] + COLW[3] / 2, ry - 4, A, "a", width=2.6))
b.append(rect(COLX[3], ry, COLW[3], 62, fill=ROLE["boot"][2], stroke=ROLE["boot"][3], rx=12, sw=1.6))
b.append(text(COLX[3] + 14, ry + 26, "sdcard.img  (+ .bmap)", size=13.5, weight=800, mono=True, color="#93c5fd"))
b.append(text(COLX[3] + 14, ry + 47, "→ ./build.sh flash -d /dev/sdX", size=11.5, mono=True, color=MUTED))
b.append(caption(H - 40, "Dry run: ./build.sh --dry-run all | less -R prints every command with the reason it exists. Each step also runs alone."))
b.append(caption(H - 18, "Arm GNU Toolchain 14.3 (sha256-pinned): arm-none-linux-gnueabihf builds the SPL, U-Boot proper and the kernel. Source trees are checked out once into build/src/ and left alone."))
write("build-pipeline.svg", W, H,
      "Build pipeline: the board's ps7_init files, U-Boot and the device tree are built by the uboot step into BOOT.BIN and u-boot.img; the Linux kernel "
      "and the same device tree are built by the kernel step into zImage, DTB and modules; a Debian armhf or Alpine armv7 rootfs is built by the "
      "rootfs step; the image step assembles all of them into an MBR sdcard.img with fakeroot, mke2fs, mkfs.vfat, mtools, sfdisk and dd.",
      "".join(b))
