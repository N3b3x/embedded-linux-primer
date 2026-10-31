"""docs/images/boot-chain.svg - every stage from power-on to login (generated)."""
from kit import *

W, H = 1400, 984
A = "#e5edf7"
RED = "#fb7185"
b = [marker_defs({"a": A, "r": RED})]
b.append(title("How the STM32MP257F-DK boots, and what this repository builds for each stage",
               "Power-on to login prompt: each stage loads the next. BL31 and OP-TEE stay resident after Linux is up."))

CW, GAP, X0, Y0, CH = 200, 22, 40, 150, 392

# world bands
b.append(rect(24, 104, 4 * CW + 3 * GAP + 32 - 2, 450, fill="#14080f", stroke="#5b1a2e", rx=18, sw=1.4))
b.append(text(44, 128, "SECURE WORLD  ·  EL3 / S-EL1", size=12.5, weight=800, color="#fb7185",
              extra=' letter-spacing="1.2"'))
nx = 24 + 4 * CW + 3 * GAP + 32 + 4
b.append(rect(nx, 104, 1376 - nx, 450, fill="#06140f", stroke="#0f4d43", rx=18, sw=1.4))
b.append(text(nx + 20, 128, "NORMAL WORLD  ·  NS-EL1 / EL0", size=12.5, weight=800, color="#5eead4",
              extra=' letter-spacing="1.2"'))

STAGES = [
    # num, title, icon, role, pill, runs_from, bullets, built_from(list), dashed
    (1, "Boot ROM", "microchip", "hw", "EL3 · secure",
     ("internal ROM", ""),
     ["samples the BOOT pins", "finds GPT partition fsbla1", "checks the STM32 header,", "copies BL2 into SYSRAM"],
     ["silicon", "(nothing to build)"]),
    (2, "TF-A BL2", "cpu", "boot", "EL3 · secure",
     ("SYSRAM 0x0E017000", "256 KiB on-chip RAM"),
     ["trains the LPDDR4 (DDR FW)", "sets the RISAF firewalls", "reads the FIP from 'fip'", "loads BL31, OP-TEE, U-Boot"],
     ["trusted-firmware-a", "tf-a-stm32mp257f-dk.stm32"]),
    (3, "TF-A BL31", "shield-check", "secure", "EL3 · secure monitor",
     ("SYSRAM 0x0E000000", "stays resident"),
     ["routes every SMC", "PSCI: CPU on/off, reset", "starts OP-TEE first,", "then exits to U-Boot"],
     ["trusted-firmware-a", "bl31 inside fip.bin"]),
    (4, "OP-TEE OS", "lock", "secure", "S-EL1 · trusted OS",
     ("DDR 0x82000000", "32 MiB reserved"),
     ["SCMI server: clocks", "and resets for Linux", "trusted apps, secure keys", "owns the firewall setup"],
     ["optee_os + scp-firmware", "tee-pager_v2.bin in fip.bin"]),
    (5, "U-Boot", "rocket", "boot", "EL1 · non-secure",
     ("DDR 0x84000000", "relocates itself"),
     ["scans the bootable partition", "reads /boot/extlinux/", "  extlinux.conf", "loads Image + DTB, booti"],
     ["u-boot", "u-boot-nodtb.bin in fip.bin"]),
    (6, "Linux 6.18", "linux", "normal", "EL1 kernel · EL0 apps",
     ("DDR 0x8a000000", "kernel_addr_r"),
     ["asks OP-TEE for clocks", "mounts root by PARTUUID", "runs /sbin/init", "serial login: ttySTM0"],
     ["linux-6.18.58 tarball", "Image + DTB + rootfs"]),
]
for i, (n, name, ic, role, pill_s, rf, bl, bf) in enumerate(STAGES):
    x = X0 + i * (CW + GAP) + (4 if i >= 4 else 0)
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
        b.append('<circle cx="%g" cy="%g" r="3" fill="%s"/>' % (x + 18, Y0 + 180 + j * 24 - 4, soft)) if not t.startswith("  ") else None
        b.append(text(x + 30 if not t.startswith("  ") else x + 38, Y0 + 180 + j * 24, t.strip(), size=11.5))
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1"/>' % (x + 14, Y0 + 288, x + CW - 14, Y0 + 288, LINE))
    b.append(text(x + 14, Y0 + 312, "BUILT FROM", size=10, weight=800, color=FAINT, extra=' letter-spacing="1"'))
    b.append(text(x + 14, Y0 + 334, bf[0], size=12, mono=True, weight=700))
    b.append(text(x + 14, Y0 + 353, bf[1], size=11, mono=True, color=MUTED))
    if i < 5:
        ax = x + CW
        b.append(arrow(ax + 2, Y0 + 70, ax + GAP + (4 if i == 3 else 0) - 3, Y0 + 70, A, "a", width=3))

# who loads whom
b.append(text(X0, Y0 + CH + 36, "WHO LOADS WHOM", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(X0, Y0 + CH + 44, 1320, 2, fill=LINE, rx=1))
rows = [
    ("ROM → BL2", "copies BL2 from partition fsbla1 into SYSRAM and jumps to it (BL2 is built with RESET_TO_BL2: it runs at EL3 straight after the ROM)."),
    ("BL2 → all the rest", "BL2 opens the FIP (found by partition TYPE GUID 19d5df83-…, or the name 'fip'), loads BL31 into SYSRAM, OP-TEE into DDR, U-Boot and its DTB into DDR."),
    ("BL31 → OP-TEE → U-Boot", "BL31 runs OP-TEE once so it can initialise (and serve SCMI), gets control back, then ERETs to U-Boot at non-secure EL1 (STM32MP_BL33_EL1=1)."),
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
cx = [X0 + i * (CW + GAP) + (4 if i >= 4 else 0) for i in range(6)]
b.append(bar(X0, cx[2] - 12, ry + 24, "hw", "Boot ROM, BL2: finished (SYSRAM is reused)"))
b.append(bar(cx[2], X0 + 1320, ry + 62, "secure", "BL31 stays at EL3 for good: every SMC goes through it; PSCI (CPU on/off, suspend, reset) is served from SYSRAM"))
b.append(bar(cx[3], X0 + 1320, ry + 100, "secure", "OP-TEE stays at S-EL1, reached through BL31: SCMI server (clocks, resets) and trusted applications"))
b.append(bar(cx[4], cx[5] - 12, ry + 138, "boot", "U-Boot: gone after booti"))
b.append(bar(cx[5], X0 + 1320, ry + 176, "normal", "Linux + your applications"))

b.append(caption(H - 38, "Addresses: BL2/BL31 from plat/st/stm32mp2/stm32mp2_def.h and the linker map of this build; OP-TEE and U-Boot from fdts/stm32mp257f-dk-ca35tdcid-fw-config.dtsi,"))
b.append(caption(H - 18, "STM32MP_BL33_BASE and u-boot include/configs/stm32mp25_common.h (kernel_addr_r). Red = secure world, blue = boot stages, teal = Linux, slate = hardware."))
write("boot-chain.svg", W, H,
      "STM32MP257F-DK boot chain: the Boot ROM loads TF-A BL2 from the fsbla1 partition into on-chip SYSRAM; BL2 trains the LPDDR4 memory "
      "and loads BL31, OP-TEE and U-Boot from the FIP; BL31 stays resident as the EL3 secure monitor; OP-TEE runs at S-EL1 and serves SCMI "
      "clock and reset requests; U-Boot runs at non-secure EL1, reads extlinux.conf and starts the Linux kernel.",
      "".join(b))
