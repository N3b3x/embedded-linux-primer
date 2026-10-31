"""docs/images/boot-chain.svg - every stage from power-on to login (generated)."""
from kit import *

W, H = 1400, 984
A = "#e5edf7"
RED = "#fb7185"
b = [marker_defs({"a": A, "r": RED})]
b.append(title("How the STM32MP157F-DK2 boots, and what this repository builds for each stage",
               "Power-on to login prompt: each stage loads the next. There is no BL31 on this 32-bit chip: OP-TEE is the secure monitor and stays resident."))

CW, GAP, X0, Y0, CH = 244, 22, 40, 150, 392
SECURE_N = 3

# world bands
sec_w = SECURE_N * CW + (SECURE_N - 1) * GAP + 32
b.append(rect(24, 104, sec_w - 2, 450, fill="#14080f", stroke="#5b1a2e", rx=18, sw=1.4))
b.append(text(44, 128, "SECURE WORLD  ·  secure SVC / monitor mode", size=12.5, weight=800, color="#fb7185",
              extra=' letter-spacing="1.2"'))
nx = 24 + sec_w + 4
b.append(rect(nx, 104, 1376 - nx, 450, fill="#06140f", stroke="#0f4d43", rx=18, sw=1.4))
b.append(text(nx + 20, 128, "NORMAL WORLD  ·  non-secure SVC / USR", size=12.5, weight=800, color="#5eead4",
              extra=' letter-spacing="1.2"'))

STAGES = [
    # num, title, icon, role, pill, runs_from, bullets, built_from(list)
    (1, "Boot ROM", "microchip", "hw", "secure · privileged",
     ("internal ROM", ""),
     ["samples the BOOT pins", "finds GPT partition fsbl1", "checks the STM32 header,", "copies BL2 into SYSRAM"],
     ["silicon", "(nothing to build)"]),
    (2, "TF-A BL2", "cpu", "boot", "secure · privileged",
     ("SYSRAM 0x2FFE9000", "256 KiB on-chip RAM"),
     ["sets up clocks, PMIC, DDR3", "programs the TZC-400 firewall", "reads the FIP from 'fip'", "loads OP-TEE and U-Boot"],
     ["trusted-firmware-a", "tf-a-stm32mp157f-dk2.stm32"]),
    (3, "OP-TEE OS", "lock", "secure", "secure SVC + monitor",
     ("SYSRAM + DDR 0xDE000000", "32 MiB secure RAM"),
     ["monitor: routes every SMC", "PSCI: CPU on/off, reset", "SCMI server: clocks, resets,", "regulators; trusted apps"],
     ["optee_os", "3 tee-*_v2.bin in fip.bin"]),
    (4, "U-Boot", "rocket", "boot", "non-secure SVC",
     ("DDR 0xC0100000", "relocates itself"),
     ["scans the bootable partition", "reads /boot/extlinux/", "  extlinux.conf", "loads zImage + DTB, bootz"],
     ["u-boot", "u-boot-nodtb.bin in fip.bin"]),
    (5, "Linux 6.18", "linux", "normal", "SVC kernel · USR apps",
     ("DDR 0xC2000000", "kernel_addr_r"),
     ["asks OP-TEE for clocks", "and for the SD card supply", "mounts root by PARTUUID,", "login on ttySTM0"],
     ["linux-6.18.58 tarball", "zImage + DTB + rootfs"]),
]
cxs = []
for i, (n, name, ic, role, pill_s, rf, bl, bf) in enumerate(STAGES):
    x = X0 + i * (CW + GAP) + (4 if i >= SECURE_N else 0)
    cxs.append(x)
    strong, soft, fill, border = ROLE[role]
    b.append(card(x, Y0, CW, CH, name, role, ic, filled_icon=(ic == "linux")))
    b.append(badge(x + CW - 22, Y0 + 20, n, "#e2e8f0", r=11))
    b.append(chip(x + 12, Y0 + 52, pill_s, role if role != "hw" else "secure"))
    b.append(text(x + 14, Y0 + 106, "RUNS FROM", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, Y0 + 126, rf[0], size=12.5, weight=800, mono=True))
    if rf[1]:
        b.append(text(x + 14, Y0 + 143, rf[1], size=11, color=MUTED))
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (x + 14, Y0 + 156, x + CW - 14, Y0 + 156, LINE))
    for j, t in enumerate(bl):
        if not t.startswith("  "):
            b.append('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (x + 18, Y0 + 180 + j * 24 - 4, soft))
        b.append(text(x + 30 if not t.startswith("  ") else x + 38, Y0 + 180 + j * 24, t.strip(), size=11.5))
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (x + 14, Y0 + 288, x + CW - 14, Y0 + 288, LINE))
    b.append(text(x + 14, Y0 + 312, "BUILT FROM", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, Y0 + 334, bf[0], size=12, mono=True, weight=700))
    b.append(text(x + 14, Y0 + 353, bf[1], size=11, mono=True, color=MUTED))
    if i < 4:
        ax = x + CW
        b.append(arrow(ax + 2, Y0 + 70, ax + GAP + (4 if i == SECURE_N - 1 else 0) - 3, Y0 + 70, A, "a", width=3))

# who loads whom
b.append(text(X0, Y0 + CH + 36, "WHO LOADS WHOM", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(X0, Y0 + CH + 44, 1320, 2, fill=LINE, rx=1))
rows = [
    ("ROM → BL2", "copies BL2 from partition fsbl1 into SYSRAM and jumps to it (BL2 is built with RESET_TO_BL2: it runs straight after the ROM)."),
    ("BL2 → OP-TEE, U-Boot", "BL2 opens the FIP (found by partition TYPE GUID 19d5df83-…, or the name 'fip') and loads OP-TEE (3 files) and U-Boot + its DTB."),
    ("OP-TEE → U-Boot", "BL2 jumps to OP-TEE; OP-TEE initialises (and starts serving SCMI), then returns to the normal world at U-Boot's entry point."),
]
for k, (a1, a2) in enumerate(rows):
    yy = Y0 + CH + 74 + k * 26
    b.append(text(X0, yy, a1, size=12.5, weight=800, color="#93c5fd"))
    b.append(text(X0 + 230, yy, a2, size=12.5))

# what stays in memory
ry = Y0 + CH + 172
b.append(text(X0, ry, "STILL IN MEMORY WHILE LINUX RUNS", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(X0, ry + 8, 1320, 2, fill=LINE, rx=1))
def bar(x1, x2, yy, role, s, dashed=False):
    strong, soft, fill, border = ROLE[role]
    return (rect(x1, yy, x2 - x1, 28, fill=strong if not dashed else fill, stroke=border, rx=14, dash="6 4" if dashed else None)
            + text(x1 + 16, yy + 19, s, size=12, weight=700, color="#ffffff" if not dashed else soft))
b.append(bar(X0, cxs[2] - 12, ry + 24, "hw", "Boot ROM, BL2: finished (SYSRAM is reused)"))
b.append(bar(cxs[2], X0 + 1320, ry + 62, "secure", "OP-TEE stays in the secure world for good: it is the monitor, so every SMC goes through it; it serves PSCI and SCMI"))
b.append(bar(cxs[3], cxs[4] - 12, ry + 100, "boot", "U-Boot: gone after bootz"))
b.append(bar(cxs[4], X0 + 1320, ry + 138, "normal", "Linux + your applications"))
b.append(bar(cxs[3], X0 + 1320, ry + 176, "secure", "No BL31 and no DDR firmware on this chip: the DDR3 driver is part of BL2", dashed=True))

b.append(caption(H - 38, "Addresses: BL2 from plat/st/stm32mp1/stm32mp1_fip_def.h and the linker map of this build; OP-TEE from fdts/stm32mp15-fw-config.dtsi and plat-stm32mp1/conf.mk;"))
b.append(caption(H - 18, "STM32MP_BL33_BASE (stm32mp1_def.h) and u-boot include/configs/stm32mp15_common.h (kernel_addr_r). Red = secure world, blue = boot stages, teal = Linux, slate = hardware."))
write("boot-chain.svg", W, H,
      "STM32MP157F-DK2 boot chain: the Boot ROM loads TF-A BL2 from the fsbl1 partition into on-chip SYSRAM; BL2 sets up the DDR3 memory "
      "and loads OP-TEE and U-Boot from the FIP; OP-TEE is both the secure monitor and the SCMI server for clocks, resets and regulators and "
      "stays resident; U-Boot runs in the non-secure world, reads extlinux.conf and starts the 32-bit Linux kernel. There is no BL31 on this chip.",
      "".join(b))
