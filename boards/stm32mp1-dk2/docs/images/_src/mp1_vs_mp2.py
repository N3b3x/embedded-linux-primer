"""docs/images/mp1-vs-mp2.svg - the two STM32MP boards side by side (generated)."""
from kit import *

W = 1400
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("STM32MP157F-DK2 and STM32MP257F-DK: one family, two boot chains",
               "Same ROM-to-BL2-to-FIP idea and the same SD image rules; a shorter chain and a smaller memory on the 32-bit chip."))

SL, SW, SG = 40, 210, 12
def slot(i):
    return SL + i * (SW + SG)
STAGES = ["Boot ROM", "TF-A BL2", "TF-A BL31", "OP-TEE", "U-Boot", "Linux"]
ROLES = ["hw", "boot", "secure", "secure", "boot", "normal"]

def strip(y, label, sub, present, notes):
    out = text(SL, y - 12, label, size=14, weight=800)
    out += text(SL + 330, y - 12, sub, size=12, color=MUTED)
    for i, (n, r) in enumerate(zip(STAGES, ROLES)):
        x = slot(i)
        if present[i]:
            out += card(x, y, SW, 92, n, r, None, head=32)
            out += text(x + 12, y + 56, notes[i][0], size=11, color=TEXT)
            out += text(x + 12, y + 74, notes[i][1], size=11, color=MUTED)
        else:
            out += card(x, y, SW, 92, n, r, None, dashed=True, head=32)
            out += text(x + 12, y + 62, notes[i][0], size=11.5, color=MUTED)
    return out

N1 = [("32-bit Armv7-A", "ROM in the Cortex-A7"), ("SYSRAM 0x2FFE9000", "DDR3 driver inside"),
      ("none on this chip", ""), ("monitor + TEE + SCMI", "3 files, pager on"),
      ("DDR 0xC0100000", "bootz zImage"), ("ARCH=arm", "multi_v7_defconfig")]
N2 = [("64-bit ARMv8-A", "ROM in the Cortex-A35"), ("SYSRAM 0x0E017000", "needs DDR PHY firmware"),
      ("resident at EL3", "SYSRAM 0x0E000000"), ("TEE + SCMI (clock, reset)", "DDR 0x82000000"),
      ("DDR 0x84000000", "booti Image"), ("ARCH=arm64", "defconfig")]
b.append(strip(124, "STM32MP157F-DK2", "this board: 2 x Cortex-A7, 512 MiB DDR3", [1, 1, 0, 1, 1, 1], N1))
b.append(strip(262, "STM32MP257F-DK", "the 64-bit sibling: 2 x Cortex-A35, 4 GiB LPDDR4", [1, 1, 1, 1, 1, 1], N2))

# comparison table
TY = 396
b.append(rect(40, TY, 1320, 30, fill=PANEL2, stroke=LINE, rx=8))
for t, x in [("TOPIC", 56), ("SAME OR DIFFERENT", 250), ("STM32MP157F-DK2", 420), ("STM32MP257F-DK", 890)]:
    b.append(text(x, TY + 20, t, size=10.5, weight=800, color=FAINT, extra=' letter-spacing="1"'))
ROWS = [
    ("SD image format", "same", "GPT, rootless assembly, extlinux.conf on the bootable partition", "the same"),
    ("First-stage partition", "differs", "fsbl1, fsbl2 (ROM looks them up by name)", "fsbla1, fsbla2"),
    ("FIP lookup", "same", "type GUID 19d5df83-..., or the name fip; no FWU metadata", "the same"),
    ("FIP contents", "differs", "OP-TEE (3 files), U-Boot, 2 DTBs: 6 entries", "BL31, OP-TEE (2 files), U-Boot, 3 DTBs, DDR FW: 8 entries"),
    ("Firewalls", "differs", "ETZPC (peripherals) + TZC-400 (DDR)", "RIF: RIFSC, RISAB, RISAF"),
    ("SCMI server", "differs", "OP-TEE's own scmi-msg: clock, reset, voltage", "Arm SCP-firmware in OP-TEE: clock, reset only"),
    ("SD card supply", "differs", "served over SCMI: stock device tree boots", "not served: patched device tree boots"),
    ("Toolchains", "differs", "arm-none-eabi + arm-none-linux-gnueabihf", "aarch64-none-elf + aarch64-none-linux-gnu"),
    ("U-Boot", "differs", "stm32mp15_defconfig, tree st/stm32mp157c-dk2-scmi", "stm32mp25_defconfig, tree st/stm32mp257f-dk"),
    ("Root filesystem", "differs", "Debian armhf / Alpine armv7 (needs qemu on any PC but a 32-bit ARM one)", "Debian arm64 / Alpine aarch64"),
    ("Pinned releases", "same", "TF-A 2.15.0, OP-TEE 4.11.0, U-Boot 2026.07, Linux 6.18.58", "the same"),
]
for i, (topic, kind, a, c) in enumerate(ROWS):
    y = TY + 38 + i * 36
    b.append(rect(40, y, 1320, 32, fill=PANEL, stroke=LINE, rx=8, sw=0.8))
    role = "normal" if kind == "same" else "fw"
    b.append(rect(40, y, 10, 32, fill=ROLE[role][0], rx=4))
    b.append(text(64, y + 21, topic, size=12.5, weight=800))
    b.append(chip(244, y + 6, kind, role, size=10.5))
    b.append(text(420, y + 21, a, size=11.5))
    b.append(text(890, y + 21, c, size=11.5, color=MUTED if c == "the same" else TEXT))
H = TY + 38 + len(ROWS) * 36 + 50
b.append(caption(H - 20, "Green = the same on both boards, amber = differs. Facts from docs/14-the-stm32mp-family.md; both boards are built from the same upstream releases."))
write("mp1-vs-mp2.svg", W, H,
      "Comparison of the STM32MP157F-DK2 and STM32MP257F-DK boot chains: the 32-bit board has no BL31 and no DDR firmware, OP-TEE is its secure monitor and "
      "serves clocks, resets and voltage domains, and the SD card works with the stock device tree; the 64-bit board has a resident BL31, DDR training "
      "firmware, a clock-and-reset-only SCMI server and a patched device tree. Both share the GPT SD image rules, the FIP and the same pinned releases.",
      "".join(b))
