"""docs/images/memory-map.svg - on-chip SRAM and DDR, as the boot chain uses them (generated)."""
from kit import *

W, H = 1400, 760
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Where things live in memory during boot",
               "Two address ranges matter: 256 KiB of on-chip SYSRAM (BL2 and BL31), and the 4 GiB of LPDDR4 that starts at 0x8000_0000."))

def block(x, y, w, h, role, name, addr, note=None, dashed=False):
    strong, soft, fill, border = ROLE[role]
    out = rect(x, y, w, h, fill=fill if dashed else strong, stroke=border, rx=8, sw=1.4, dash="6 4" if dashed else None, opacity=None)
    out += text(x + 14, y + 22, name, size=13, weight=800, color=soft if dashed else "#fff")
    out += text(x + w - 14, y + 22, addr, size=11.5, mono=True, color=soft if dashed else "#fff", anchor="end")
    for k, ln in enumerate((note or "").split("\\n")):
        out += text(x + 14, y + 42 + k * 16, ln, size=11, color=MUTED if dashed else "#e2e8f0")
    return out

# ---- SYSRAM --------------------------------------------------------------------------------
LX, LW = 40, 560
b.append(text(LX, 112, "ON-CHIP SYSRAM  0x0E000000 – 0x0E040000  (256 KiB)", size=12, weight=800, color=MUTED, extra=' letter-spacing="1"'))
b.append(rect(LX, 124, LW, 560, fill="#0a1424", stroke=LINE, rx=10))
# top = high address
sy = 134
b.append(block(LX + 10, sy, LW - 20, 70, "fw", "SRAM1: DDR PHY firmware", "0x0E040000 →", "lpddr4_pmu_train.bin is copied here, then loaded into the PHY (STM32MP_DDR_FW_BASE)"))
b.append(block(LX + 10, sy + 80, LW - 20, 150, "boot", "BL2 image", "0x0E017000", "this build: 0x0E017000 – 0x0E02CFE8 (90 KB of code and data)\\nThe ROM copies the .stm32 payload (174,568 bytes) to 0x0E002600 and jumps in"))
b.append(block(LX + 10, sy + 240, LW - 20, 70, "rootfs", "BL2 device tree", "0x0E011000", "BL2's own DTB (24 KiB reserved): clocks, DDR, which storage"))
b.append(block(LX + 10, sy + 320, LW - 20, 150, "secure", "BL31 (+ fw-config while BL2 runs)", "0x0E000000", "92 KiB are left for BL31 below BL2 (STM32MP_BL31_SIZE).\\nfw-config is also read to the start of SYSRAM (STM32MP_FW_CONFIG_BASE).\\nBL31 stays here for the whole life of the system."))
b.append(text(LX + 14, sy + 502, "0x0E000000 = STM32MP_SYSRAM_BASE · size 0x40000 · BL2 region 0x29000 (164 KiB)", size=11, color=MUTED, mono=True))
b.append(text(LX + 14, sy + 524, "plat/st/stm32mp2/stm32mp2_def.h; addresses of BL2 and its DTB confirmed in the linker map of this build", size=11, color=MUTED))

# ---- DDR ----------------------------------------------------------------------------------
RX, RW = 640, 720
b.append(text(RX, 112, "DDR  0x80000000 – 0x1_80000000  (4 GiB LPDDR4, drawn NOT to scale)", size=12, weight=800, color=MUTED, extra=' letter-spacing="1"'))
b.append(rect(RX, 124, RW, 560, fill="#0a1424", stroke=LINE, rx=10))
dy = 134
rows = [
    ("rootfs", "kernel_addr_r…ramdisk_addr_r", "0x8A000000 …", "U-Boot's load addresses: Image at 0x8A000000, DTB at 0x90000000 (fdt_addr_r),\\nscript 0x90100000, extlinux.conf text 0x90200000, overlays 0x90300000, ramdisk 0x90400000", 76, False),
    ("boot", "free DDR", "…", "after booti the kernel runs from here; Linux owns everything not reserved", 44, True),
    ("rootfs", "U-Boot's DTB (hw-config)", "0x84400000", "BL2 puts u-boot.dtb here (up to 256 KiB), U-Boot reads it at start", 54, False),
    ("boot", "U-Boot as loaded (BL33)", "0x84000000", "u-boot-nodtb.bin, up to 4 MiB (STM32MP_BL33_MAX_SIZE); U-Boot then relocates itself to\\nthe top of DDR. 0x84000000 is also kernel_comp_addr_r.", 76, False),
    ("secure", "OP-TEE (TZDRAM)", "0x82000000", "32 MiB (CFG_TZDRAM_START/SIZE = 0x82000000 / 0x02000000): secure, firewalled by RISAF", 54, False),
    ("hw", "reserved by the kernel DT", "0x80000000", "fw@80000000, 64 MiB, no-map: the kernel never touches 0x80000000 – 0x83FFFFFF\\n(this covers OP-TEE's 32 MiB)", 66, True),
]
yy = dy
for role, name, addr, note, h, dashed in rows:
    b.append(block(RX + 10, yy, RW - 20, h, role, name, addr, note, dashed))
    yy += h + 10
b.append(code(RX + 10, yy + 6, RW - 20, [
    ("DDR_BASE        0x80000000  plat/st/stm32mp2/stm32mp2_def.h", "#cbd5e1"),
    ("BL33_BASE       DDR_BASE + 0x04000000 = 0x84000000   BL33_MAX_SIZE 0x400000", "#93c5fd"),
    ("HW_CONFIG_BASE  BL33_BASE + BL33_MAX_SIZE = 0x84400000", "#c4b5fd"),
    ("OP-TEE          fdts/stm32mp257f-dk-ca35tdcid-fw-config.dtsi: 0x82000000 / 0x2000000", "#fda4af"),
], size=10.5, gap=17, title_s="where the numbers come from"))
b.append(caption(H - 18, "U-Boot addresses: include/configs/stm32mp25_common.h (__KERNEL_ADDR_R, __FDT_ADDR_R …). Kernel reservation: arch/arm64/boot/dts/st/stm32mp257f-dk.dts."))
write("memory-map.svg", W, H,
      "Memory map during boot: in the 256 KiB on-chip SYSRAM, BL31 at 0x0E000000, BL2's device tree at 0x0E011000 and BL2 at 0x0E017000, with the DDR "
      "training firmware in SRAM1 above; in DDR, a 64 MiB region at 0x80000000 reserved from the kernel that contains OP-TEE at 0x82000000, U-Boot "
      "loaded at 0x84000000 with its device tree at 0x84400000, and U-Boot's load addresses for the kernel and device tree at 0x8A000000 and 0x90000000.",
      "".join(b))
