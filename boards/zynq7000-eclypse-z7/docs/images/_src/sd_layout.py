"""docs/images/sd-layout.svg - the SD card and its boot files, byte for byte (generated)."""
from kit import *

W, H = 1400, 930
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("What is on the SD card, and who reads each file",
               "An MBR disk with two partitions, written by scripts/image.sh. The BootROM only understands MBR + FAT, so the layout is not a free choice."))

# ---- the disk as a strip (NOT to scale: p1 is fixed, p2 depends on the rootfs) --------------------
TX, TW = 40, 1320
ty, th = 150, 64
b.append(text(TX, ty - 18, "THE DISK, LEFT TO RIGHT (not to scale: p1 is 300 MiB, p2 is as large as its content, or the whole card after --expand)", size=11, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))
b.append(rect(TX, ty, TW, th, fill="#0a1424", stroke=LINE, rx=8, sw=1.2))
x_mbr, x_p1, x_p2 = TX, TX + 56, TX + 56 + 640
b.append(text(x_mbr + 28, ty + 36, "MBR", size=11, color=MUTED, anchor="middle", weight=700))
b.append(rect(x_p1, ty, 640, th, fill=ROLE["boot"][0], stroke=ROLE["boot"][3], rx=3, sw=1))
b.append(rect(x_p2, ty, TX + TW - x_p2, th, fill=ROLE["rootfs"][0], stroke=ROLE["rootfs"][3], rx=3, sw=1))
b.append(text(x_p1 + 320, ty + 28, "p1  FAT32 \"BOOT\"", size=15, weight=800, color="#fff", anchor="middle"))
b.append(text(x_p1 + 320, ty + 48, "starts at 1 MiB, 300 MiB long", size=12, color="#dbeafe", anchor="middle"))
b.append(text(x_p2 + 310, ty + 28, "p2  ext4 \"rootfs\"", size=15, weight=800, color="#fff", anchor="middle"))
b.append(text(x_p2 + 310, ty + 48, "starts at 301 MiB, to the end", size=12, color="#ede9fe", anchor="middle"))
for xx, lab, anc in ((x_mbr, "0", "start"), (x_p1, "1 MiB · sector 2048", "start"), (x_p2, "301 MiB · sector 616448", "start")):
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (xx, ty + th, xx, ty + th + 8, FAINT))
    b.append(text(xx, ty + th + 22, lab, size=11, color=MUTED, anchor=anc, mono=True))

# ---- cards ----------------------------------------------------------------------------------
cy = 290
cards = [
    ("MBR  (sector 0)", "hw", "512 bytes", [
        ("disk signature", "0x5a796e71"),
        ("entry 1", "FAT32 (type 0c), active, start 2048, 614400 sectors"),
        ("entry 2", "Linux (type 83), start 616448"),
        ("read by", "BootROM (finds partition 1), the kernel (PARTUUID)"),
    ]),
    ("p1  BOOT  (FAT32)", "boot", "300 MiB", [
        ("BOOT.BIN", "BootROM loads it into OCM: the SPL"),
        ("u-boot.img", "the SPL loads it into DDR"),
        ("extlinux/extlinux.conf", "U-Boot's distro boot reads it"),
        ("zImage, zynq-eclypse-z7.dtb", "U-Boot loads both, boots"),
    ]),
    ("p2  rootfs  (ext4)", "rootfs", "rest of card", [
        ("/sbin/init  /usr  /etc …", "the distribution"),
        ("/lib/modules/6.18.58-custom", "drivers built as modules"),
        ("/boot/config-6.18.58-custom", "the kernel's .config"),
        ("/boot/firmware", "mount point of p1 on the running board"),
    ]),
]
cw = 428
for i, (name, role, size, rows) in enumerate(cards):
    x = 40 + i * (cw + 18)
    b.append(card(x, cy, cw, 214, name, role, None, sub=size))
    for j, (k, v) in enumerate(rows):
        yy = cy + 66 + j * 36
        b.append(text(x + 14, yy, k, size=12, weight=800, mono=True, color=ROLE[role][1] if role != "hw" else "#cbd5e1"))
        b.append(text(x + 14, yy + 16, v, size=11.5, color=MUTED))

# ---- extlinux + why ---------------------------------------------------------------------------
y2 = 530
b.append(text(40, y2, "WHAT U-BOOT READS FROM p1", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(40, y2 + 8, 1320, 2, fill=LINE, rx=1))
b.append(code(40, y2 + 24, 600, [
    ("DEFAULT linux", "#fcd34d"),
    ("TIMEOUT 10", "#fcd34d"),
    ("LABEL linux", "#fcd34d"),
    ("  LINUX /zImage", "#5eead4"),
    ("  FDT /zynq-eclypse-z7.dtb", "#c4b5fd"),
    ("  APPEND root=PARTUUID=5a796e71-02 console=ttyPS0,115200", "#93c5fd"),
    ("         rootwait rw earlycon", "#93c5fd"),
], size=11.5, gap=19, title_s="/extlinux/extlinux.conf (written by image.sh)"))
b.append(rect(660, y2 + 24, 700, 192, fill=PANEL, stroke=LINE, rx=10))
b.append(text(676, y2 + 48, "Why these rules", size=13, weight=800))
b.append(lines(676, y2 + 72, [
    "• BootROM: MBR only; the first FAT16/FAT32 partition; the file must be",
    "  called BOOT.BIN, in the root directory. No GPT, no ext4.",
    "• SPL: opens u-boot.img by name on that same partition.",
    "• U-Boot: scans the partition with the active flag first, then looks for",
    "  /extlinux/extlinux.conf; paths in it are relative to the FAT root.",
    "• Linux: root=PARTUUID=<disk signature>-02 finds p2 on any mmcblk number.",
], size=12, gap=19, color=TEXT))

# ---- later with a bitstream ----------------------------------------------------------------------
y3 = y2 + 232
b.append(rect(40, y3, 1320, 90, fill="#0f192d", stroke=ROLE["fw"][3], rx=10, sw=1.4, dash="7 5"))
b.append(text(58, y3 + 26, "LATER, WITH A BITSTREAM FOR THE PL: THE LAYOUT STAYS", size=11.5, weight=800, color="#fcd34d", extra=' letter-spacing="1.2"'))
b.append(text(58, y3 + 48, "Only BOOT.BIN is swapped (./build.sh flash --firmware-only): Xilinx route = FSBL + .bit + u-boot.elf packed by bootgen into one BOOT.BIN, same name, same place.", size=12.5, color=TEXT))
b.append(text(58, y3 + 70, "Or keep this BOOT.BIN and add system.bit.bin next to zImage; U-Boot (fpga load) or Linux (/lib/firmware, fpga_manager) programs the PL. See docs/13 and docs/03.", size=12.5, color=TEXT))
b.append(caption(H - 34, "Sizes and the disk signature: config/eclypse-z7.conf. BootROM rules: UG585 chapter 6 (boot and configuration) and the Eclypse Z7 reference manual, section 2 (boot modes)."))
b.append(caption(H - 14, "U-Boot looks for extlinux.conf with boot_prefixes \"/ /boot/\" (include/config_distro_bootcmd.h); the file lives in /extlinux/ because the FAT root is the prefix \"/\"."))
write("sd-layout.svg", W, H,
      "SD card layout: an MBR disk with a 300 MiB FAT32 partition labelled BOOT from 1 MiB, holding BOOT.BIN for the BootROM, u-boot.img for the SPL, "
      "extlinux/extlinux.conf, zImage and the device tree for U-Boot, and an ext4 rootfs partition from 301 MiB that holds the root filesystem and the "
      "kernel modules.",
      "".join(b))
