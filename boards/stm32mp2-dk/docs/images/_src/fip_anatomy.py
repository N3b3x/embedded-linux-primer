"""docs/images/fip-anatomy.svg - what is inside fip.bin (generated, sizes from a real build)."""
from kit import *

W, H = 1400, 790
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Inside fip.bin: eight images behind one table of contents",
               "A Firmware Image Package is a ToC (a UUID per image, with offset and size) followed by the images. BL2 asks for each by UUID."))

TOTAL = 1999368
# name, offset, size, role, fiptool flag, make arg, loaded to, what
IMGS = [
    ("BL31",        0x1A0,    0xB530,   "secure", "--soc-fw",        "(built by all)",   "SYSRAM 0x0E000000", "TF-A's resident secure monitor"),
    ("OP-TEE hdr",  0xB6D0,   0x1C,     "secure", "--tos-fw",        "BL32=",              "DDR 0x82000000",    "28-byte header that tells BL31 how to start OP-TEE"),
    ("OP-TEE",      0xB6EC,   0xAC980,  "secure", "--tos-fw-extra1", "BL32_EXTRA1=",       "DDR 0x82000000",    "the trusted OS image (tee-pager_v2.bin), SCMI server inside"),
    ("U-Boot",      0xB806C,  0x1146A8, "boot",   "--nt-fw",         "BL33=",              "DDR 0x84000000",    "u-boot-nodtb.bin, the normal-world bootloader (BL33)"),
    ("fw-config",   0x1CC714, 0x326,    "rootfs", "--fw-config",     "(built from fdts/)", "SYSRAM 0x0E000000", "BL2's load plan: where each image goes"),
    ("U-Boot DTB",  0x1CCA3A, 0xFFD0,   "rootfs", "--hw-config",     "BL33_CFG=",          "DDR 0x84400000",    "u-boot.dtb, U-Boot's own device tree"),
    ("BL31 DTB",    0x1DCA0A, 0x31AE,   "rootfs", "--soc-fw-config", "(built from fdts/)", "for BL31",          "BL31's own device tree (SoC settings for the monitor)"),
    ("DDR FW",      0x1DFBB8, 0x8650,   "fw",     "--ddr-fw",        "STM32MP_DDR_FW_PATH", "SRAM1 0x0E040000",  "lpddr4_pmu_train.bin: the memory controller's training code"),
]

# ---- the bar ------------------------------------------------------------------------------
BX, BW, BY, BH = 40, 1320, 138, 56
b.append(text(BX, BY - 14, "fip.bin = %s bytes, drawn to scale (a few images are thinner than one pixel and are drawn 3 px wide)" % format(TOTAL, ","),
              size=11.5, color=MUTED))
b.append(rect(BX, BY, BW, BH, fill="#050a14", stroke=LINE, rx=6))
b.append(rect(BX, BY, max(3, 0x1A0 / TOTAL * BW), BH, fill="#94a3b8", rx=2))
mids = []
for (name, off, size, role, flag, mk, to, what) in IMGS:
    strong, soft, fill, border = ROLE[role]
    x = BX + off / TOTAL * BW
    w = max(3, size / TOTAL * BW)
    b.append(rect(x, BY, w, BH, fill=strong, stroke="#0b1220", rx=1, sw=0.6))
    mids.append(x + w / 2)
    if w > 120:
        b.append(text(x + w / 2, BY + 34, name, size=15, weight=800, color="#fff", anchor="middle"))
        b.append(text(x + w / 2, BY + 50, "%s KiB" % format(round(size / 1024, 1), ","), size=11, color="#fff", anchor="middle"))
b.append(text(BX, BY + BH + 20, "0", size=11, mono=True, color=MUTED))
b.append(text(BX + BW, BY + BH + 20, "0x1E8208", size=11, mono=True, color=MUTED, anchor="end"))
b.append(text(BX, BY + BH + 38, "ToC (416 bytes)", size=11, color=MUTED))

# ---- the table ----------------------------------------------------------------------------
TY = 250
cols = [("", 40), ("IMAGE", 70), ("OFFSET", 190), ("SIZE", 290), ("fiptool FLAG", 390), ("make ARGUMENT", 540),
        ("BL2 LOADS IT TO", 730), ("WHAT IT IS", 920)]
b.append(rect(40, TY, 1320, 30, fill=PANEL2, stroke=LINE, rx=8))
for (c, x) in cols[1:]:
    b.append(text(x, TY + 20, c, size=10.5, weight=800, color=FAINT, extra=' letter-spacing="1"'))
for i, (name, off, size, role, flag, mk, to, what) in enumerate(IMGS):
    y = TY + 38 + i * 38
    strong, soft, fill, border = ROLE[role]
    b.append(rect(40, y, 1320, 34, fill=PANEL, stroke=LINE, rx=8, sw=0.8))
    b.append(rect(40, y, 10, 34, fill=strong, rx=4))
    b.append(text(70, y + 22, name, size=13, weight=800, color=soft))
    b.append(text(190, y + 22, "0x%X" % off, size=12, mono=True))
    b.append(text(290, y + 22, format(size, ",") + " B", size=12, mono=True))
    b.append(text(390, y + 22, flag, size=12, mono=True, color="#93c5fd"))
    b.append(text(540, y + 22, mk, size=12, mono=True, color=MUTED))
    b.append(text(730, y + 22, to, size=12, mono=True))
    b.append(text(920, y + 22, what, size=11.5))

# ---- how it is made -------------------------------------------------------------------------
yy = TY + 38 + 8 * 38 + 16
b.append(code(40, yy, 640, [
    ("$ build/src/trusted-firmware-a/tools/fiptool/fiptool info build/deploy/fip.bin", "#cbd5e1"),
    ('EL3 Runtime Firmware BL31: offset=0x1A0, size=0xB530, cmdline="--soc-fw"', "#fda4af"),
    ('Secure Payload BL32 (Trusted OS): offset=0xB6D0, size=0x1C, cmdline="--tos-fw"', "#fda4af"),
    ('Non-Trusted Firmware BL33: offset=0xB806C, size=0x1146A8, cmdline="--nt-fw"', "#93c5fd"),
    ("…", "#64748b"),
], size=10.5, gap=17, title_s="Real output of ./build.sh firmware fip"))
b.append(rect(700, yy, 660, 118, fill=PANEL, stroke=LINE, rx=10))
b.append(text(716, yy + 24, "Three facts worth remembering", size=13, weight=800))
b.append(lines(716, yy + 48, [
    "• tee-pageable_v2.bin is 0 bytes here (OP-TEE paging is off), so it is not packed.",
    "• BL2 itself is NOT in the FIP: the Boot ROM loaded it from fsbla1 beforehand.",
    "• The FIP partition is 4 MiB; this FIP uses about 2.0 MB, U-Boot being the biggest part.",
], size=11.5, gap=20))
b.append(caption(H - 16, "Sizes and offsets are from the build described in docs/10-versions.md. UUIDs and flags: TF-A include/tools_share/firmware_image_package.h and plat/st/common/common.mk."))
write("fip-anatomy.svg", W, H,
      "Inside fip.bin: a table of contents followed by eight images: BL31, the OP-TEE header, the OP-TEE image, U-Boot, the fw-config device tree, "
      "U-Boot's device tree, BL31's device tree and the DDR training firmware, with their offsets, sizes, fiptool flags, make arguments and "
      "the address BL2 loads each one to.",
      "".join(b))
