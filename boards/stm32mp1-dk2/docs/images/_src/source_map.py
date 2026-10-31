"""docs/images/source-map.svg - the source files that run, in order (generated).

Every path below was checked against the pinned trees (see config/stm32mp157f-dk2.conf).
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
        ("plat/st/stm32mp1/bl2_plat_setup.c", "bl2_platform_setup(): stm32mp1_ddr_probe(); loads the images; parses the OP-TEE header"),
        ("drivers/st/ddr/stm32mp1_ddr.c", "stm32mp1_ddr_probe(): bring up the DDR3 controller and PHY (no firmware blob)"),
        ("plat/st/stm32mp1/plat_bl2_mem_params_desc.c", "which image goes where; BL32 entry in secure SVC mode, BL33 in non-secure SVC"),
        ("fdts/stm32mp15-fw-config.dtsi", "OP-TEE base, U-Boot base, and the TZC-400 regions (top 32 MiB secure)"),
    ]),
    ("secure", "optee_os", "OP-TEE", [
        ("core/arch/arm/plat-stm32mp1/conf.mk", "CFG_TZDRAM_START=0xde000000 (512 MB flavours); pager on; CFG_SCMI_MSG_DRIVERS"),
        ("core/arch/arm/plat-stm32mp1/main.c", "platform init: early console on UART4; SCMI memory set-up; prints the platform banner"),
        ("core/arch/arm/sm/sm_a32.S", "sm_smc_entry(): the secure monitor's smc handler (there is no BL31)"),
        ("core/arch/arm/dts/stm32mp157c-dk2-scmi.dts", "the board as the secure world sees it (compiled into the OP-TEE image)"),
        ("core/arch/arm/plat-stm32mp1/scmi_server.c", "the clock, reset and voltage-domain tables the SCMI server answers for"),
        ("core/pta/scmi.c", "the pseudo trusted application Linux and U-Boot call to deliver SCMI messages"),
    ]),
    ("boot", "u-boot", "U-Boot", [
        ("arch/arm/mach-stm32mp/stm32mp1/cpu.c", "from the ROM's boot context sets env boot_device (serial, usb, mmc ...) and boot_instance"),
        ("include/configs/stm32mp15_st_common.h", "bootcmd_stm32mp: boot_targets=mmc<boot_instance>, then run distro_bootcmd"),
        ("include/config_distro_bootcmd.h", "scan_dev_for_boot_part: bootable partitions; prefixes \"/ /boot/\"; extlinux/extlinux.conf"),
        ("cmd/sysboot.c", "do_sysboot(): parse extlinux.conf, load zImage and DTB"),
        ("cmd/bootz.c", "do_bootz(): hand the DTB to the kernel in r2 and jump"),
        ("drivers/firmware/scmi/optee_agent.c", "U-Boot is an SCMI client of OP-TEE too (CONFIG_SCMI_FIRMWARE in stm32mp15_defconfig)"),
    ]),
    ("normal", "linux-6.18.58", "Linux", [
        ("arch/arm/boot/dts/st/stm32mp15-scmi.dtsi", "firmware { optee { ... } scmi { compatible = \"linaro,scmi-optee\" ... } }"),
        ("drivers/firmware/arm_scmi/transports/optee.c", "one SCMI message becomes one call into OP-TEE"),
        ("drivers/regulator/scmi-regulator.c", "scmi_regulator_probe(): the SD card's supply (scmi_v3v3) is an SCMI voltage domain"),
        ("drivers/mmc/host/mmci.c · mmci_stm32_sdmmc.c", "mmci_probe(): the SD card controller"),
        ("drivers/tty/serial/stm32-usart.c", "the ttySTM0 console (UART4) and its earlycon"),
        ("init/main.c", "kernel_init() -> run_init_process(\"/sbin/init\")"),
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
b.append(caption(y + 30, "grep -rn \"STM32MP_OPTEE_BASE\" build/src/trusted-firmware-a/plat/st/ · grep -rn \"scan_dev_for_boot_part\" build/src/u-boot/include/"))
write("source-map.svg", W, H,
      "Source files that run during boot, in order: in trusted-firmware-a the BL2 files for the FIP lookup, DDR3 set-up and image placement; "
      "in optee_os the platform configuration, the secure monitor's smc entry, the SCMI server tables and its pseudo trusted application; "
      "in u-boot the boot-device detection, the distro boot script, sysboot and bootz; and in linux the SCMI device tree, the SCMI over OP-TEE "
      "transport, the SCMI regulator driver, the SD card and serial drivers, and kernel_init.",
      "".join(b))
