"""docs/images/ps-pl-map.svg - the Zynq-7000: processing system, programmable logic, and the board (generated)."""
from kit import *

W, H = 1400, 880
A = "#e5edf7"
b = [marker_defs({"a": A, "f": "#fcd34d"})]
b.append(title("One chip, two halves: the processing system (PS) and the programmable logic (PL)",
               "The XC7Z020 on the Eclypse Z7. This build boots and uses the PS only; the PL is an FPGA that stays empty until someone loads a design."))

# ---- PS panel
PX, PY, PW, PH = 40, 112, 640, 470
b.append(rect(PX, PY, PW, PH, fill="#06140f", stroke="#0f4d43", rx=18, sw=1.4))
b.append(text(PX + 20, PY + 28, "PS  ·  PROCESSING SYSTEM  (hard silicon, always there)", size=12.5, weight=800, color="#5eead4", extra=' letter-spacing="1.1"'))
def blk(x, y, w, h, name, sub, role="hw", ic=None):
    strong, soft, fill, border = ROLE[role]
    o = rect(x, y, w, h, fill=fill, stroke=border, rx=10, sw=1.3)
    o += text(x + 12, y + 24, name, size=13, weight=800, color=soft)
    if sub:
        o += text(x + 12, y + 43, sub, size=11, color=MUTED)
    return o
b.append(blk(PX + 20, PY + 48, 290, 78, "APU: 2 × Cortex-A9", "32-bit ARMv7, NEON, up to 667 MHz (-1 part)", "normal"))
b.append(blk(PX + 330, PY + 48, 290, 78, "L2 cache 512 KiB · OCM 256 KiB", "OCM: where the BootROM puts BOOT.BIN", "boot"))
b.append(blk(PX + 20, PY + 140, 600, 70, "DDR3/3L memory controller", "1 GiB on the Eclypse Z7 · needs ps7_init before first use", "secure"))
b.append(text(PX + 20, PY + 238, "PERIPHERALS ON THE 54 MIO PINS", size=10.5, weight=800, color=FAINT, extra=' letter-spacing="1.1"'))
periph = [("UART0", "MIO 14-15"), ("SD0", "MIO 40-45, 47"), ("GEM0", "MIO 16-27"), ("USB0", "MIO 28-39"), ("QSPI", "MIO 1-6, 8"), ("I2C1", "MIO 12-13")]
for i, (n, m) in enumerate(periph):
    x = PX + 20 + (i % 3) * 204
    y = PY + 252 + (i // 3) * 62
    b.append(blk(x, y, 192, 52, n, m, "hw"))
    b.append(text(x + 190 - 10, y + 24, "", size=10))
b.append(text(PX + 20, PY + 396, "also: SPI, CAN, GPIO, timers, watchdog, DMA, the FPGA manager (devcfg, loads PL bitstreams)", size=11.5, color=MUTED))
b.append(text(PX + 20, PY + 420, "Linux drives all of these with ordinary drivers; the device tree only says where they are.", size=11.5, color=TEXT))
b.append(text(PX + 20, PY + 444, "Enabled in custom/dts/zynq-eclypse-z7.dts: uart0, sdhci0, gem0, gpio0, i2c1, qspi, usb0, devcfg.", size=11.5, color=TEXT))

# ---- PL panel
LX, LY, LW, LH = 760, 112, 600, 470
b.append(rect(LX, LY, LW, LH, fill="#1c1405", stroke="#7c4a0a", rx=18, sw=1.4, dash="8 5"))
b.append(text(LX + 20, LY + 28, "PL  ·  PROGRAMMABLE LOGIC  (an FPGA, empty at power-on)", size=12.5, weight=800, color="#fcd34d", extra=' letter-spacing="1.1"'))
b.append(rect(LX + 20, LY + 48, LW - 40, 200, fill="#2a1b05", stroke=ROLE["fw"][3], rx=12, sw=1.3, dash="6 4"))
b.append(text(LX + 36, LY + 76, "your design, once a bitstream is loaded", size=13.5, weight=800, color="#fde68a"))
b.append(lines(LX + 36, LY + 102, [
    "XC7Z020: 53,200 LUTs · 106,400 flip-flops",
    "140 block RAMs · 220 DSP slices (Artix-7 class fabric)",
    "",
    "Examples: a Zmod ADC controller + AXI DMA,",
    "a custom accelerator, soft peripherals, glue logic.",
], size=12.5, gap=20, color=TEXT))
b.append(blk(LX + 20, LY + 266, 280, 60, "Clocks from the PS", "FCLK0-3; the board also feeds 125 MHz", "fw"))
b.append(blk(LX + 320, LY + 266, 260, 60, "Interrupts to the PS", "IRQ_F2P[15:0]: GIC SPI 29-36, 52-59", "fw"))
b.append(text(LX + 20, LY + 356, "THE FABRIC'S PINS ARE WIRED TO", size=10.5, weight=800, color=FAINT, extra=' letter-spacing="1.1"'))
b.append(blk(LX + 20, LY + 368, 180, 52, "Zmod port A", "SYZYGY, own I/O bank", "hw"))
b.append(blk(LX + 212, LY + 368, 180, 52, "Zmod port B", "SYZYGY, own I/O bank", "hw"))
b.append(blk(LX + 404, LY + 368, 176, 52, "Pmods, LEDs", "buttons, 125 MHz clock", "hw"))
b.append(text(LX + 20, LY + 446, "Nothing here exists until a bitstream is loaded: the I/O pins are unconfigured and no AXI slave answers.", size=11.5, color=MUTED))

# ---- AXI between
ay = PY + PH + 14
b.append(rect(PX, ay, LX + LW - PX, 64, fill=PANEL, stroke="#fcd34d", rx=12, sw=1.5))
b.append(text(PX + 18, ay + 26, "AXI interconnect between PS and PL", size=14, weight=800, color="#fcd34d"))
b.append(text(PX + 18, ay + 48, "GP ports (PS reads/writes PL registers) · HP ports (PL masters write straight into DDR) · ACP (coherent) · EMIO (PL-routed PS peripherals) · FCLK · IRQ_F2P", size=12, color=TEXT))
for x in (PX + 330, LX + 150):
    b.append(arrow(x, PY + PH - 4, x, ay + 2, "#fcd34d", "f", width=3))

# ---- how it differs
dy = ay + 90
b.append(text(40, dy, "HOW THIS DIFFERS FROM THE OTHER BOARDS OF THIS REPOSITORY", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(40, dy + 8, 1320, 2, fill=LINE, rx=1))
b.append(lines(40, dy + 34, [
    "• i.MX 8M Plus and STM32MP2 are 64-bit SoCs with a vendor boot chain (ATF, OP-TEE) and a fixed set of peripherals. The Zynq-7000 is 32-bit, has no secure monitor in this build,",
    "  and the first stage is ours: the SPL must configure the clocks and DDR itself, from a file generated for this board's hardware design.",
    "• Those SoCs have no FPGA. Here half the chip is a blank slate, and the hardware you will actually use (a Zmod ADC) lives in it: docs/13 explains the order of work.",
], size=12.5, gap=22, color=TEXT))
b.append(caption(H - 36, "Block sizes: the XC7Z020 entry of the project's sysdef (LUT 53,200 · FF 106,400 · BRAM 140 · DSP 220); MIO assignments: Eclypse Z7 reference manual and the Vivado board preset."))
b.append(caption(H - 16, "IRQ_F2P ranges: UG585 table 7-4 (GIC SPI 29-36 and 52-59). The PL accesses DDR through the HP ports; the Zynq-7000 has no IOMMU for them."))
write("ps-pl-map.svg", W, H,
      "The Zynq-7000 on the Eclypse Z7: the hard processing system with two Cortex-A9 cores, L2 cache, on-chip RAM, the DDR3 controller and peripherals on MIO pins "
      "(UART0, SD0, Ethernet GEM0, USB0, QSPI, I2C1), linked by AXI interconnect, clocks and interrupts to the programmable logic, an empty FPGA fabric whose pins "
      "go to the two Zmod ports and the Pmods.",
      "".join(b))
