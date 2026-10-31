"""docs/images/storage-layout.svg - what lives where on the QSPI-NOR flash and the root device (generated)."""
from kit import *

W, H = 1400, 930
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Where everything lives: two storage devices, not one SD card",
               "Sizes are read from NVIDIA's partition files: bootloader/generic/cfg/flash_t234_qspi.xml and tools/kernel_flash/flash_l4t_t234_nvme.xml."))

# ============================ left: QSPI-NOR ======================================
LX, LW = 32, 660
b.append(card(LX, 100, LW, 44, "QSPI-NOR flash on the module", "fw", ic="microchip", sub="64 MiB · always the boot device"))
# proportional bar
bx, by, bw, bh = LX, 160, LW, 44
segs = [("", 1.0, "hw", ""), ("chain A  30.75 MiB", 30.75, "fw", ""), ("chain B  30.75 MiB", 30.75, "boot", ""), ("", 1.5, "hw", "")]
tot = sum(s[1] for s in segs)
x = bx
for nm, mib, role, _ in segs:
    w = bw * mib / tot
    strong, soft, fill, border = ROLE[role]
    b.append(rect(x, by, w - 2, bh, fill=strong, rx=6 if w > 20 else 2))
    if nm:
        b.append(text(x + w / 2, by + 27, nm, size=12.5, weight=800, color="#fff", anchor="middle"))
    x += w
b.append(text(bx, by + 62, "BCT 1 MiB", size=11, color=MUTED))
b.append(text(bx + bw, by + 62, "+ UEFI variables, UEFI FTW, reserved, backup GPT, version info (≈1.4 MiB)", size=11, color=MUTED, anchor="end"))

# chain A table
b.append(text(LX, 262, "One boot chain (the B_ copy is identical in layout)", size=13.5, weight=800, color=TEXT))
CH = [("A_mb1", "512 KiB", "boot"), ("A_psc_bl1", "256 KiB", "boot"), ("A_MB1_BCT", "128 KiB", "boot"), ("A_MEM_BCT", "256 KiB", "boot"),
      ("A_mb2", "512 KiB", "boot"), ("A_cpu-bootloader", "3.5 MiB", "boot"), ("A_secure-os", "4 MiB", "secure"), ("A_eks", "256 KiB", "secure"),
      ("A_bpmp-fw", "1.5 MiB", "fw"), ("A_bpmp-fw-dtb", "4 MiB", "fw"), ("A_psc-fw", "768 KiB", "fw"), ("A_spe-fw", "576 KiB", "fw"),
      ("A_rce-fw", "1 MiB", "fw"), ("A_dce-fw", "5 MiB", "fw"), ("A_adsp-fw", "2 MiB", "fw"), ("A_pva-fw", "256 KiB", "fw"),
      ("A_mts-mce", "512 KiB", "fw"), ("A_tsec-fw", "1 MiB", "fw"), ("A_nvdec", "1 MiB", "fw"), ("A_xusb-fw", "256 KiB", "fw"),
      ("A_sc7 · A_pscrf · A_mb2rf", "192+192+128 KiB", "fw"), ("A_smm-fw", "2 MiB", "fw"), ("A_reserved_on_boot", "1.06 MiB", "hw")]
half = (len(CH) + 1) // 2
for i, (nm, sz, role) in enumerate(CH):
    col, row = (0, i) if i < half else (1, i - half)
    x = LX + col * 334
    y = 278 + row * 33
    strong, soft, fill, border = ROLE[role]
    b.append(rect(x, y, 326, 28, fill=fill, stroke=border, rx=7, sw=1.2))
    b.append(text(x + 10, y + 19, nm, size=11.3, mono=True, color=soft, weight=700))
    b.append(text(x + 318, y + 19, sz, size=11.3, color=TEXT, anchor="end"))
yl = 278 + half * 33 + 14
for i, (nm, role) in enumerate([("MB1 / MB2 / UEFI", "boot"), ("secure OS · keys", "secure"), ("other cores' firmware", "fw"), ("reserved", "hw")]):
    b.append(chip(LX + i * 160, yl, nm, role, size=11))
b.append(text(LX, yl + 48, "Two complete chains give fail-safe boot-firmware updates (NVIDIA: 'bootloader redundancy is enabled by default').", size=11.8, color=MUTED))
b.append(text(LX, yl + 66, "UEFI is 3.5 MiB: a custom logo or extra drivers must still fit.", size=11.8, color=MUTED))

# ============================ right: root device =================================
RX, RW = 730, 638
b.append(card(RX, 100, RW, 44, "Root device: SD card · NVMe SSD · USB drive", "rootfs", ic="hard-drive", sub="one GPT, written by the flash tool"))
ROWS = [("primary_gpt", "19.5 KiB", "hw", "partition table"),
        ("A_kernel", "128 MiB", "normal", "kernel for 'boot from partitions'"),
        ("A_kernel-dtb", "768 KiB", "rootfs", "device tree for it"),
        ("A_reserved_on_user", "31.6 MiB", "hw", ""),
        ("B_kernel · B_kernel-dtb · B_reserved…", "≈160 MiB", "hw", "second copy of the three above"),
        ("recovery kernel + dtb", "tool-sized", "normal", "recovery boot mode"),
        ("esp", "64 MiB", "boot", "FAT: EFI\\BOOT\\BOOTAA64.efi = L4TLauncher"),
        ("recovery_alt · dtb_alt · esp_alt", "≈ 64 MiB+", "hw", "spare copies"),
        ("UDA", "400 MiB", "fw", "user data area (mounted by you, or left empty)"),
        ("reserved", "479.5 MiB", "hw", ""),
        ("APP", "the rest", "rootfs", "ext4 root filesystem: /boot/Image, /boot/extlinux, /lib/modules …"),
        ("secondary_gpt", "", "hw", "backup partition table at the end")]
y = 160
for i, (nm, sz, role, what) in enumerate(ROWS):
    strong, soft, fill, border = ROLE[role]
    big = nm == "APP"
    h = 44 if not big else 58
    b.append(rect(RX, y, RW, h, fill=fill, stroke=border, rx=9, sw=2 if big else 1.3))
    b.append(text(RX + 14, y + 20, nm, size=12.4, mono=True, weight=700, color=soft))
    b.append(text(RX + RW - 14, y + 20, sz, size=12, color=TEXT, anchor="end", weight=700 if big else 400))
    if what:
        b.append(text(RX + 14, y + 37, what, size=11.4, color=MUTED if not big else TEXT))
    y += h + 6
# what the OS actually reads
yy = y + 4
b.append(rect(RX, yy, RW, 88, fill=PANEL, stroke="#14b8a6", rx=10, sw=1.4))
b.append(text(RX + 14, yy + 22, "Default boot path (L4TDefaultBootMode = 1):", size=12.2, weight=800, color="#5eead4"))
b.append(text(RX + 14, yy + 42, "UEFI → esp:\\EFI\\BOOT\\BOOTAA64.efi (L4TLauncher)", size=11.6, color=TEXT, mono=True))
b.append(text(RX + 14, yy + 60, "→ APP:/boot/extlinux/extlinux.conf → /boot/Image + /boot/initrd", size=11.6, color=TEXT, mono=True))
b.append(text(RX + 14, yy + 78, "The kernel partitions serve the other boot modes; the flash tool fills them anyway.", size=11.6, color=TEXT))

b.append(caption(H - 40, "Compare with an SD-card board: there, one file (sdcard.img) holds the bootloader at a fixed offset and one ext4 partition. Here the boot firmware is on the module,"))
b.append(caption(H - 20, "so you can swap the root device, wipe it, or boot from NVMe without touching the firmware: the device only holds the OS."))
write("storage-layout.svg", W, H,
      "Storage layout of the Orin Nano Developer Kit. Left: the 64 MiB QSPI-NOR flash on the module holds the boot configuration table and two complete "
      "boot chains, A and B, each with MB1, MB2, UEFI, the secure OS and the firmware of the other processors. Right: the root device (SD card, NVMe "
      "SSD or USB drive) holds a GPT with kernel and kernel-dtb partitions for slots A and B, recovery partitions, a 64 MiB EFI system partition "
      "with L4TLauncher, a 400 MiB user data area and the APP partition, which is the ext4 root filesystem.",
      "".join(b))
