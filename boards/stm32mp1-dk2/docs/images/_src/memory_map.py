"""docs/images/memory-map.svg - on-chip SRAM and DDR, as the boot chain uses them (generated)."""
from kit import *

W, H = 1400, 760
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Where things live in memory during boot",
               "Two address ranges matter: 256 KiB of on-chip SYSRAM (BL2 and OP-TEE's pager), and the 512 MiB of DDR3 that starts at 0xC000_0000."))

def block(x, y, w, h, role, name, addr, note=None, dashed=False):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, y, w, h, fill=fill if dashed else strong, stroke=border, rx=8, sw=1.4, dash="6 4" if dashed else None, opacity=None)
    out += text(x + 14, y + 22, name, size=13, weight=800, color=soft if dashed else "#fff")
    out += text(x + w - 14, y + 22, addr, size=11.5, mono=True, color=soft if dashed else "#fff", anchor="end")
    for k, ln in enumerate((note or "").split("\n")):
        out += text(x + 14, y + 42 + k * 16, ln, size=11, color=MUTED if dashed else "#e2e8f0")
    return out

# ---- SYSRAM --------------------------------------------------------------------------------
LX, LW = 40, 560
b.append(text(LX, 112, "ON-CHIP SYSRAM  0x2FFC0000 – 0x30000000  (256 KiB)", size=12, weight=800, color=MUTED, extra=' letter-spacing="1"'))
b.append(rect(LX, 124, LW, 560, fill="#0a1424", stroke=LINE, rx=10))
# top = high address
sy = 134
b.append(block(LX + 10, sy, LW - 20, 70, "hw", "Last page: non-secure, fw-config", "0x2FFFF000", "4 KiB. BL2 reads fw-config here; TF-A's docs call it the \"SCMI mailbox\"\n(OP-TEE uses it for SCMI only if CFG_STM32MP1_SCMI_SHM_SYSRAM=y; off by default)", dashed=True))
b.append(block(LX + 10, sy + 80, LW - 20, 150, "boot", "BL2 image", "0x2FFE9000", "STM32MP_BL2_SIZE 0x16000 (88 KB), up to the last page. Entry point 0x2FFE9000\nin the header of this build; the ROM copies the whole .stm32 payload\n(209,060 bytes after the 256-byte header) to 0x2FFC2500 and jumps to the entry"))
b.append(block(LX + 10, sy + 240, LW - 20, 70, "rootfs", "BL2 device tree", "0x2FFE2000", "BL2's own DTB (28 KiB reserved, STM32MP_BL2_DTB_SIZE): clocks, DDR, PMIC"))
b.append(block(LX + 10, sy + 320, LW - 20, 150, "secure", "OP-TEE header + pager", "0x2FFC0000", "STM32MP_OPTEE_BASE: BL2 loads tee-header and tee-pager here, below its own device tree.\nOP-TEE then owns the whole 256 KiB (CFG_TZSRAM_START 0x2FFC0000, size 0x40000)\nand pages the rest of itself in from secure DDR.\nOP-TEE stays for the whole life of the system."))
b.append(text(LX + 14, sy + 502, "0x2FFC0000 = STM32MP_SYSRAM_BASE · size 0x40000 (MP15) · NS page = last 4 KiB", size=11, color=MUTED, mono=True))
b.append(text(LX + 14, sy + 524, "plat/st/stm32mp1/stm32mp1_def.h, stm32mp1_fip_def.h; BL2 address confirmed in the linker map of this build", size=11, color=MUTED))

# ---- DDR ----------------------------------------------------------------------------------
RX, RW = 640, 720
b.append(text(RX, 112, "DDR  0xC0000000 – 0xE0000000  (512 MiB DDR3, drawn NOT to scale)", size=12, weight=800, color=MUTED, extra=' letter-spacing="1"'))
b.append(rect(RX, 124, RW, 560, fill="#0a1424", stroke=LINE, rx=10))
dy = 134
rows = [
    ("secure", "OP-TEE secure RAM (TZDRAM)", "0xDE000000", "32 MiB (CFG_TZDRAM_START/SIZE = 0xDE000000 / 0x02000000): the top of the 512 MiB, firewalled by the TZC-400.\nReserved from Linux as optee@de000000, no-map", 66, False),
    ("boot", "free DDR", "...", "after bootz the kernel runs from here; Linux owns everything not reserved", 44, True),
    ("rootfs", "kernel_addr_r ... ramdisk_addr_r", "0xC2000000 ...", "U-Boot's load addresses: zImage at 0xC2000000, DTB at 0xC4000000 (fdt_addr_r),\nscript 0xC4100000, extlinux.conf text 0xC4200000, overlays 0xC4300000, ramdisk 0xC4400000", 76, False),
    ("rootfs", "U-Boot's DTB (hw-config)", "0xC0500000", "BL2 puts u-boot.dtb here (up to 256 KiB), U-Boot reads it at start", 54, False),
    ("boot", "U-Boot as loaded (BL33)", "0xC0100000", "u-boot-nodtb.bin, up to 4 MiB (STM32MP_BL33_MAX_SIZE); U-Boot then relocates itself to\nthe top of the non-secure DDR.", 66, False),
    ("hw", "start of DDR", "0xC0000000", "STM32MP_DDR_BASE. The kernel's own memory node: memory@c0000000, 0x20000000 bytes", 54, True),
]
yy = dy
for role, name, addr, note, h, dashed in rows:
    b.append(block(RX + 10, yy, RW - 20, h, role, name, addr, note, dashed))
    yy += h + 10
b.append(code(RX + 10, yy + 6, RW - 20, [
    ("DDR_BASE        0xC0000000  plat/st/stm32mp1/stm32mp1_def.h", "#cbd5e1"),
    ("BL33_BASE       DDR_BASE + 0x100000 = 0xC0100000   BL33_MAX_SIZE 0x400000", "#93c5fd"),
    ("HW_CONFIG_BASE  BL33_BASE + BL33_MAX_SIZE = 0xC0500000", "#c4b5fd"),
    ("OP-TEE          fdts/stm32mp15-fw-config.dtsi: DDR_SIZE 0x20000000 - 0x02000000 = 0xDE000000", "#fda4af"),
], size=10.5, gap=17, title_s="where the numbers come from"))
b.append(caption(H - 18, "U-Boot addresses: include/configs/stm32mp15_common.h (__KERNEL_ADDR_R, __FDT_ADDR_R ...). Kernel reservation: arch/arm/boot/dts/st/stm32mp157f-dk2-scmi.dtsi."))
write("memory-map.svg", W, H,
      "Memory map during boot: in the 256 KiB on-chip SYSRAM at 0x2FFC0000, OP-TEE's header and pager at the bottom, BL2's device tree at 0x2FFE2000, "
      "BL2 at 0x2FFE9000 and a non-secure last page for fw-config; in the 512 MiB of DDR3 from 0xC0000000, U-Boot loaded at 0xC0100000 with its "
      "device tree at 0xC0500000, U-Boot's load addresses for the kernel and device tree at 0xC2000000 and 0xC4000000, and OP-TEE's 32 MiB of secure "
      "RAM at the top, 0xDE000000, reserved from Linux.",
      "".join(b))
