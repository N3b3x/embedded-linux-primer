"""docs/images/boot-chain.svg - every stage from power-on to login (generated)."""
from kit import *

W, H = 1400, 930
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("How the Eclypse Z7 boots, and what this repository builds for each stage",
               "Power-on to login prompt on a Zynq-7000: four stages, no secure monitor. U-Boot's SPL does the job that Xilinx's FSBL does elsewhere."))

CW, GAP, X0, Y0, CH = 308, 28, 40, 112, 408

STAGES = [
    (1, "BootROM", "microchip", "hw", "Cortex-A9 · secure state",
     ("on-chip ROM", "128 KiB, in the silicon"),
     ["latches the mode pins (JP5)", "reads the MBR, finds the", "  first FAT partition", "opens BOOT.BIN, checks its", "  header, copies it to OCM"],
     ["silicon", "(nothing to build)"]),
    (2, "U-Boot SPL", "cog", "boot", "BOOT.BIN · first stage",
     ("OCM 0x00000000", "on-chip RAM, 192 KiB max"),
     ["ps7_init: PLLs, DDR3L, clocks,", "  MIO pins (UART, SD, GbE)", "starts the UART and the SD host", "loads u-boot.img from the FAT", "  partition into DDR, jumps"],
     ["u-boot  (spl/boot.bin)", "+ ps7_init_gpl.c of the board"]),
    (3, "U-Boot", "rocket", "boot", "u-boot.img · bootloader",
     ("DDR 0x04000000", "relocates to the top of RAM"),
     ["scans mmc 0, the bootable FAT", "reads /extlinux/extlinux.conf", "loads zImage at 0x02000000", "  and the DTB at 0x01F00000", "bootz: jump into the kernel"],
     ["u-boot  (u-boot.img)", "+ custom/dts DTB inside"]),
    (4, "Linux 6.18", "linux", "normal", "SVC mode · apps in user mode",
     ("DDR 0x00008000", "zImage unpacks itself"),
     ["parses the device tree (DTB)", "mounts root=PARTUUID=…-02", "runs /sbin/init", "serial login on ttyPS0", "(PL stays unconfigured)"],
     ["linux-6.18.58 tarball", "zImage + DTB + rootfs"]),
]
for i, (n, name, ic, role, pill_s, rf, bl, bf) in enumerate(STAGES):
    x = X0 + i * (CW + GAP)
    strong, soft, fill, border = ROLE[role]
    b.append(card(x, Y0, CW, CH, name, role, ic, filled_icon=(ic == "linux")))
    b.append(badge(x + CW - 22, Y0 + 20, n, "#e2e8f0", r=11))
    b.append(chip(x + 12, Y0 + 52, pill_s, role))
    b.append(text(x + 14, Y0 + 106, "RUNS FROM", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, Y0 + 126, rf[0], size=12.5, weight=800, mono=True))
    b.append(text(x + 14, Y0 + 143, rf[1], size=11, color=MUTED))
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (x + 14, Y0 + 156, x + CW - 14, Y0 + 156, LINE))
    for j, t in enumerate(bl):
        if not t.startswith("  "):
            b.append('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (x + 18, Y0 + 180 + j * 24 - 4, soft))
        b.append(text(x + 30 if not t.startswith("  ") else x + 38, Y0 + 180 + j * 24, t.strip(), size=12))
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (x + 14, Y0 + 316, x + CW - 14, Y0 + 316, LINE))
    b.append(text(x + 14, Y0 + 340, "BUILT FROM", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, Y0 + 362, bf[0], size=12, mono=True, weight=700))
    b.append(text(x + 14, Y0 + 381, bf[1], size=11, mono=True, color=MUTED))
    if i < 3:
        ax = x + CW
        b.append(arrow(ax + 2, Y0 + 70, ax + GAP - 3, Y0 + 70, A, "a", width=3))

# who loads whom
ly = Y0 + CH + 40
b.append(text(X0, ly, "WHO LOADS WHOM", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(X0, ly + 8, 1320, 2, fill=LINE, rx=1))
rows = [
    ("ROM → SPL", "copies BOOT.BIN's payload (129,436 bytes here) from FAT into on-chip RAM at address 0 and jumps there. The SD card is chosen by JP5 = SD, latched at power-on."),
    ("SPL → U-Boot", "SPL runs ps7_init first (without it there is no DRAM), then opens u-boot.img by name on the same FAT partition and loads it to 0x04000000."),
    ("U-Boot → Linux", "distro boot reads /extlinux/extlinux.conf; its LINUX, FDT and APPEND lines say which kernel, which device tree and which command line."),
]
for k, (a1, a2) in enumerate(rows):
    yy = ly + 38 + k * 26
    b.append(text(X0, yy, a1, size=12.5, weight=800, color="#93c5fd"))
    b.append(text(X0 + 150, yy, a2, size=12.5))

# what stays in memory
ry = ly + 138
b.append(text(X0, ry, "STILL RUNNING WHEN YOU SEE THE LOGIN PROMPT", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(X0, ry + 8, 1320, 2, fill=LINE, rx=1))
def bar(x1, x2, yy, role, s, dashed=False):
    strong, soft, fill, border = ROLE[role]
    return (rect(x1, yy, x2 - x1, 28, fill=strong if not dashed else fill, stroke=border, rx=14, dash="6 4" if dashed else None)
            + text(x1 + 16, yy + 19, s, size=12, weight=700, color="#ffffff" if not dashed else soft))
cx = [X0 + i * (CW + GAP) for i in range(4)]
b.append(bar(X0, cx[3] - 12, ry + 24, "hw", "BootROM, SPL and U-Boot: finished. OCM and the DDR they used are reused by Linux."))
b.append(bar(cx[3], X0 + 1320, ry + 62, "normal", "Linux + your applications"))
b.append(bar(X0, X0 + 1320, ry + 100, "hw", "Programmable logic (PL): never configured in this build. UART, SD card and Ethernet are PS peripherals on MIO pins, so they work without it.", dashed=True))

b.append(caption(H - 38, "Addresses: CONFIG_SPL_TEXT_BASE=0x0 and CONFIG_TEXT_BASE=0x4000000 (xilinx_zynq_virt_defconfig), kernel_addr_r and fdt_addr_r (include/configs/zynq-common.h), kernel text at 0x8000."))
b.append(caption(H - 18, "There is no TF-A, no OP-TEE and no PSCI: the Zynq-7000 starts its Cortex-A9s in the secure state and Linux brings the second core up through the SCU and SLCR registers."))
write("boot-chain.svg", W, H,
      "Eclypse Z7 boot chain: the Zynq BootROM reads BOOT.BIN from the first FAT partition of the SD card into on-chip RAM; that file is U-Boot's SPL, "
      "which runs the PS7 initialisation (clocks, DDR3L, MIO pins), then loads u-boot.img into DDR; U-Boot reads extlinux.conf and starts the Linux "
      "kernel with a device tree; the programmable logic stays unconfigured.",
      "".join(b))
