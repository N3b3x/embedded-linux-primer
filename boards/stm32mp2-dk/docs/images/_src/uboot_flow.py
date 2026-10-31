"""docs/images/uboot-bootflow.svg - how U-Boot finds and starts Linux (generated)."""
from kit import *

W, H = 1400, 860
A = "#e5edf7"
b = [marker_defs({"a": A, "o": "#fcd34d"})]
b.append(title("How U-Boot finds Linux on this board",
               "No boot script is written by hand: ST's default environment runs U-Boot's generic \"distro boot\", which looks for /boot/extlinux/extlinux.conf."))

STEPS = [
    ("1", "boot_device, boot_instance", "boot", "arch/arm/mach-stm32mp/stm32mp2/cpu.c",
     ["U-Boot asks the ROM's boot context where it was loaded from:", "SD card = boot_device mmc; boot_instance says which SDMMC controller."]),
    ("2", "bootcmd = run bootcmd_stm32mp", "boot", "configs/stm32mp25_defconfig · BOOTDELAY=1",
     ["After a 1 s countdown (any key stops it: prompt \"STM32MP> \"):", "bootcmd_stm32mp prints \"Boot over mmc0!\"."]),
    ("3", "boot_targets = mmc<boot_instance>", "boot", "include/configs/stm32mp25_st_common.h",
     ["Only the device we booted from is tried.", "Then: run distro_bootcmd."]),
    ("4", "scan_dev_for_boot_part", "fw", "include/config_distro_bootcmd.h",
     ["part list mmc N -bootable devplist  → partitions with the bootable flag.", "If there are none, devplist = 1 (partition 1, our BL2: not a filesystem!)."]),
    ("5", "for prefix in \"/ /boot/\"", "fw", "include/config_distro_bootcmd.h",
     ["Is there <prefix>extlinux/extlinux.conf?  Yes: run sysboot.", "(No? then boot.scr.uimg / boot.scr is tried; we do not ship one.)"]),
    ("6", "sysboot → booti", "normal", "cmd/sysboot.c · cmd/booti.c",
     ["Reads extlinux.conf: LINUX → kernel_addr_r 0x8A000000, FDT → fdt_addr_r 0x90000000,", "APPEND → bootargs. Then: booti 0x8A000000 - 0x90000000. Linux starts."]),
]
y = 120
for i, (n, name, role, where, desc) in enumerate(STEPS):
    strong, soft, fill, border = ROLE[role]
    h = 96
    b.append(rect(40, y, 860, h, fill=fill, stroke=border, rx=12, sw=1.5))
    b.append(rect(40, y, 56, h, fill=strong, rx=12))
    b.append(text(68, y + 56, n, size=26, weight=800, anchor="middle", color="#fff"))
    b.append(text(116, y + 28, name, size=15, weight=800, mono=True, color=soft))
    b.append(text(116, y + 48, where, size=11, mono=True, color=MUTED))
    for k, d in enumerate(desc):
        b.append(text(116, y + 68 + k * 16 - 2, d, size=11.5, color=TEXT))
    if i < len(STEPS) - 1:
        b.append(arrow(68, y + h + 2, 68, y + h + 14, A, "a", width=3))
    y += h + 16

# right column: the file U-Boot reads + gotchas
b.append(code(930, 120, 430, [
    ("DEFAULT linux", "#fcd34d"),
    ("TIMEOUT 10", "#fcd34d"),
    ("LABEL linux", "#fcd34d"),
    ("  LINUX /boot/Image", "#5eead4"),
    ("  FDT /boot/stm32mp257f-dk-primer.dtb", "#c4b5fd"),
    ("  APPEND root=PARTUUID=6d70326b-0000-4000-", "#93c5fd"),
    ("         8000-000000000001 console=ttySTM0,", "#93c5fd"),
    ("         115200 rootwait rw", "#93c5fd"),
], size=11.5, gap=19, title_s="/boot/extlinux/extlinux.conf"))
b.append(rect(930, 330, 430, 230, fill=PANEL, stroke="#f59e0b", rx=12, sw=1.5))
b.append(icon("scan-search", 946, 344, 22, "#fcd34d"))
b.append(text(978, 361, "If it does not boot, read the log", size=14, weight=800, color="#fcd34d"))
b.append(lines(946, 392, [
    "\"Scanning mmc 0:5...\"   a partition is being tried",
    "\"Found /boot/extlinux/extlinux.conf\"  step 5 worked",
    "\"Retrieving file: /boot/Image\"        sysboot is loading",
    "nothing after \"Boot over mmc0!\"?  no bootable flag,",
    "wrong boot_instance, or the rootfs is not ext4.",
    "Stop autoboot and try by hand:",
], size=11.5, gap=19, color=TEXT))
b.append(code(946, 508, 398, [
    ("STM32MP> part list mmc 0", "#cbd5e1"),
    ("STM32MP> ls mmc 0:5 /boot", "#cbd5e1"),
], size=11, gap=16))
b.append(rect(930, 580, 430, 206, fill=PANEL, stroke=LINE, rx=12))
b.append(text(946, 604, "Why the bootable flag matters", size=13, weight=800))
b.append(lines(946, 628, [
    "scripts/image.sh sets the GPT attribute LegacyBIOSBootable",
    "(bit 2) on the rootfs partition only. U-Boot's \"part list",
    "-bootable\" reads exactly that bit (disk/part_efi.c). Without",
    "it U-Boot would scan partition 1 = fsbla1, which holds BL2.",
], size=11.5, gap=19))
b.append(caption(H - 16, "Everything on this page is stock U-Boot v2026.07: nothing here is specific to this repository except the contents of extlinux.conf and the partition flags."))
write("uboot-bootflow.svg", W, H,
      "U-Boot boot flow: read boot_device and boot_instance from the ROM context, run bootcmd_stm32mp after a one second delay, set boot_targets to "
      "the SD card, scan the bootable partition for /boot/extlinux/extlinux.conf with distro boot, then sysboot loads the kernel Image and device "
      "tree and booti starts Linux.",
      "".join(b))
