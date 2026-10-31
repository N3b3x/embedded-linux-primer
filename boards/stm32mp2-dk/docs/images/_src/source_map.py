"""docs/images/source-map.svg - the source files that run, in order (generated).

Every path below was checked against the pinned trees (see config/stm32mp257f-dk.conf).
"""
from kit import *

W = 1400
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("The code that runs, in order: power-on to /sbin/init",
               "The files to open when you want to understand or change a step. Paths are inside build/src/ after ./build.sh firmware and ./build.sh kernel."))

STEPS = [
    ("boot", "trusted-firmware-a", "BL2", [
        ("plat/st/common/bl2_io_storage.c", "finds the FIP: partition type GUID first, then the name \"fip\""),
        ("plat/st/stm32mp2/bl2_plat_setup.c", "bl2_platform_setup(): stm32mp2_ddr_probe(), then stm32mp2_risaf_init()"),
        ("drivers/st/ddr/stm32mp2_ram.c", "stm32mp2_ddr_probe(): bring up the LPDDR4 controller and PHY"),
        ("plat/st/stm32mp2/plat_bl2_mem_params_desc.c", "which image goes where; BL33_MODE is MODE_EL1 when STM32MP_BL33_EL1=1"),
        ("fdts/stm32mp257f-dk-ca35tdcid-fw-config.dtsi", "OP-TEE at 0x82000000, 32 MiB (load-address, reg)"),
    ]),
    ("secure", "trusted-firmware-a", "BL31", [
        ("bl31/bl31_main.c", "generic start-up of the resident monitor; ends by running the next image"),
        ("plat/st/stm32mp2/bl31_plat_setup.c", "bl31_early_platform_setup2(): UART console; bl31_plat_arch_setup(): stm32mp_gic_init()"),
        ("services/spd/opteed/opteed_main.c", "opteed_setup() / opteed_init() / opteed_smc_handler(): the OP-TEE dispatcher"),
        ("plat/st/common/stm32mp_svc_setup.c", "the STM32 SiP service (its own UUID), reachable through smc"),
    ]),
    ("secure", "optee_os, scp-firmware", "OP-TEE", [
        ("core/arch/arm/plat-stm32mp2/conf.mk", "CFG_TZDRAM_START=0x82000000; SCMI server product stm32mp2; 64-bit TAs only"),
        ("core/arch/arm/plat-stm32mp2/main.c", "plat_console_init(): early UART console; maps the GIC; prints the platform banner"),
        ("core/arch/arm/dts/stm32mp257f-dk.dts", "the board as the secure world sees it (compiled into the OP-TEE image)"),
        ("core/lib/scmi-server/scmi_server.c", "scmi_server_initialize(): the SCMI server runs inside the OP-TEE core"),
        ("core/pta/scmi.c", "the pseudo trusted application Linux and U-Boot call to deliver SCMI messages"),
        ("scp-firmware/product/optee/stm32mp2/fw/config_scmi.c", "wires SCMI clock and reset requests to OP-TEE's own clock and reset drivers"),
    ]),
    ("boot", "u-boot", "U-Boot", [
        ("arch/arm/mach-stm32mp/stm32mp2/cpu.c", "from the ROM's boot context sets env boot_device (serial, usb, mmc …) and boot_instance"),
        ("include/configs/stm32mp25_st_common.h", "bootcmd_stm32mp: boot_targets=mmc<boot_instance>, then run distro_bootcmd"),
        ("include/config_distro_bootcmd.h", "scan_dev_for_boot_part: bootable partitions; prefixes \"/ /boot/\"; extlinux/extlinux.conf"),
        ("cmd/sysboot.c", "do_sysboot(): parse extlinux.conf, load Image and DTB"),
        ("cmd/booti.c", "do_booti(): hand the DTB to the kernel in x0 and jump"),
        ("drivers/firmware/scmi/optee_agent.c", "U-Boot is an SCMI client of OP-TEE too (scmi node in arch/arm/dts/stm32mp25-u-boot.dtsi)"),
    ]),
    ("normal", "linux-6.18.58", "Linux", [
        ("arch/arm64/boot/dts/st/stm32mp251.dtsi", "firmware { optee { … } scmi { compatible = \"linaro,scmi-optee\" … } }"),
        ("drivers/firmware/arm_scmi/transports/optee.c", "scmi_optee_send_message(): one SCMI message becomes one call into OP-TEE"),
        ("drivers/clk/clk-scmi.c", "scmi_clk_enable(): clk_enable() on an SCMI clock ends here"),
        ("drivers/mmc/host/mmci.c · mmci_stm32_sdmmc.c", "mmci_probe(): the SD card controller (its supply is an SCMI regulator)"),
        ("drivers/tty/serial/stm32-usart.c", "stm32_usart_serial_probe(): the ttySTM0 console"),
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

b.append(caption(y + 10, "Open any of them with:  less build/src/<repo>/<path>.  Handy searches:  grep -rn \"scmi-optee\" build/src/linux-6.18.58/drivers/firmware/arm_scmi/ ·"))
b.append(caption(y + 30, "grep -rn \"BL33_MODE\" build/src/trusted-firmware-a/plat/st/ · grep -rn \"scan_dev_for_boot_part\" build/src/u-boot/include/"))
write("source-map.svg", W, H,
      "Source files that run during boot, in order: in trusted-firmware-a the BL2 files for the FIP lookup, DDR training and image placement; "
      "the BL31 monitor and the OP-TEE dispatcher; in optee_os and scp-firmware the platform configuration, the SCMI server and its pseudo "
      "trusted application; in u-boot the boot-device detection, the distro boot script, sysboot and booti; and in linux the device tree, the "
      "SCMI over OP-TEE transport, the SCMI clock driver, the SD card and serial drivers, and kernel_init.",
      "".join(b))
