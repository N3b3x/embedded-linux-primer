"""docs/images/source-map.svg - the source files that run, in order (generated).

Every path below was checked against the pinned trees (see config/eclypse-z7.conf).
"""
from kit import *

W = 1400
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("The code that runs, in order: power-on to /sbin/init",
               "The files to open when you want to understand or change a step. Paths are inside build/src/ after ./build.sh uboot and ./build.sh kernel."))

STEPS = [
    ("hw", "silicon", "BootROM", [
        ("(not source: UG585 chapter 6)", "mode pins from JP5, MBR + FAT lookup, BOOT.BIN header check, copy to OCM at address 0"),
    ]),
    ("boot", "u-boot (SPL)", "SPL", [
        ("arch/arm/mach-zynq/u-boot-spl.lds", "links the SPL to run in the on-chip RAM (CONFIG_SPL_TEXT_BASE=0x0)"),
        ("arch/arm/mach-zynq/spl.c", "board_init_f(): ps7_init(); spl_boot_device(): reads the boot-mode register (SD → MMC1)"),
        ("board/xilinx/zynq/Makefile", "compiles CONFIG_XILINX_PS_INIT_FILE (our ps7_init_gpl.c) into the SPL as ps_init_gpl.o"),
        ("common/spl/spl_mmc.c · spl_fat.c", "spl_mmc_load(): mounts the FAT partition, fat_read_file(\"u-boot.img\")"),
        ("common/spl/spl_fit.c", "u-boot.img is a FIT image: SPL picks the U-Boot image and the device tree"),
        ("scripts/Makefile.xpl · tools/zynqimage.c", "spl/boot.bin = mkimage -T zynqimage of the SPL: the header the BootROM reads"),
    ]),
    ("boot", "u-boot", "U-Boot", [
        ("board/xilinx/zynq/board.c", "board_late_init(): boot_targets from the boot mode; env_get_location(): FAT"),
        ("include/configs/zynq-common.h", "kernel_addr_r=0x2000000, fdt_addr_r=0x1f00000, BOOT_TARGET_DEVICES"),
        ("include/config_distro_bootcmd.h", "scan_dev_for_boot_part, boot_prefixes \"/ /boot/\", scan_dev_for_extlinux"),
        ("cmd/sysboot.c · boot/pxe_utils.c", "do_sysboot(): parse extlinux.conf, load zImage and the DTB"),
        ("cmd/bootz.c", "do_bootz(): hand the DTB to the kernel in r2 and jump to the zImage"),
        ("drivers/mmc/zynq_sdhci.c · drivers/serial/serial_zynq.c", "the SD host and the UART, in U-Boot proper"),
    ]),
    ("normal", "linux-6.18.58", "Linux", [
        ("arch/arm/boot/dts/xilinx/zynq-7000.dtsi", "the SoC: both A9 cores, clkc, uart0, sdhci0, gem0, devcfg; our DTS #includes it"),
        ("arch/arm/mach-zynq/common.c · slcr.c · platsmp.c", "machine setup; the SLCR; zynq_smp_ops starts the second core"),
        ("drivers/clk/zynq/clkc.c", "zynq_clock_init(): the PS clock tree from ps-clk-frequency"),
        ("drivers/tty/serial/xilinx_uartps.c", "cdns_uart_probe(): the ttyPS0 console"),
        ("drivers/mmc/host/sdhci-of-arasan.c", "sdhci_arasan_probe(): the SD card controller that holds the rootfs"),
        ("drivers/net/ethernet/cadence/macb_main.c", "macb_probe(): the GEM Ethernet MAC (PHY driver: drivers/net/phy/realtek)"),
        ("drivers/fpga/zynq-fpga.c", "zynq_fpga_probe(): the FPGA manager that can load a bitstream later (a module here)"),
        ("init/main.c", "kernel_init() → run_init_process(\"/sbin/init\")"),
    ]),
]
H = 100 + sum(30 + 38 * len(f) + 28 for _, _, _, f in STEPS) + 60
y = 100
for role, repo, stage, files in STEPS:
    strong, soft, fill, border = ROLE[role]
    h = 30 + 38 * len(files)
    b.append(rect(32, y, 1336, h, fill=fill, stroke=border, rx=14, sw=1.6))
    b.append(rect(32, y, 170, h, fill=strong, rx=14))
    b.append(text(117, y + h / 2 - 4, stage, size=18, weight=800, anchor="middle", color="#fff"))
    b.append(text(117, y + h / 2 + 18, repo, size=11, mono=True, anchor="middle", color="#e2e8f0"))
    for i, (f, what) in enumerate(files):
        yy = y + 32 + i * 38
        b.append(rect(220, yy - 16, 560, 30, fill="#050a14", stroke="#334155", rx=8))
        b.append(text(234, yy + 4, f, size=12, mono=True, color=soft))
        b.append(text(800, yy + 4, what, size=12, color=TEXT))
    if stage != "Linux":
        b.append(arrow(117, y + h + 2, 117, y + h + 24, A, "a", width=3))
    y += h + 28

b.append(caption(y + 10, "Open any of them with:  less build/src/<repo>/<path>.  Handy searches:  grep -rn \"XILINX_PS_INIT_FILE\" build/src/u-boot/board build/src/u-boot/arch ·"))
b.append(caption(y + 30, "grep -rn \"zynq_slcr_get_boot_mode\" build/src/u-boot/ · grep -rn \"scan_dev_for_boot_part\" build/src/u-boot/include/"))
write("source-map.svg", W, H,
      "Source files that run during boot, in order: the BootROM in silicon; in u-boot the SPL linker script, the SPL start-up that calls ps7_init and picks the "
      "boot device, the Makefile that compiles the board's PS7 init file, the SD and FAT loaders and the zynqimage wrapper; U-Boot proper's board code, "
      "environment defaults, distro boot script, sysboot and bootz; and in linux the Zynq device tree, machine code, clock, UART, SD, Ethernet and FPGA "
      "manager drivers, and kernel_init.",
      "".join(b))
