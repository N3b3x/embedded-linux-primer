"""docs/images/zmod-loading-order.svg - where a Zmod ADC fits and in which order the work goes (generated)."""
from kit import *

W, H = 1400, 830
A = "#e5edf7"
b = [marker_defs({"a": A, "f": "#fcd34d", "n": "#5eead4"})]
b.append(title("Where the Zmod ADC fits: PS boots first, then a PL design, then a driver",
               "The Zmod connectors are wired to the FPGA fabric, not to the processors. Nothing about them works until a bitstream and a driver exist. This is a map, not a build."))

# ---- top: the hardware path ----------------------------------------------------------------------------
y0 = 112
b.append(text(40, y0, "THE HARDWARE PATH OF A SAMPLE", size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.3"'))
b.append(rect(40, y0 + 8, 1320, 2, fill=LINE, rx=1))
CY, CH = y0 + 28, 150
cols = [
    (40, 232, "Zmod Scope pod", "hw", "cpu", ["ADC 1410: 2 channels, 14 bit,", "100 MS/s, on a SYZYGY pod", "plugged into port A or B"]),
    (310, 232, "SYZYGY port A / B", "hw", "arrow-right-left", ["wired to the PL, one I/O bank", "each; VADJ set by the platform", "MCU after it reads the pod's DNA"]),
    (580, 270, "PL: your design", "fw", "microchip", ["Zmod ADC controller IP", "(AXI-Lite registers, stream out)", "AXI DMA (stream → memory)", "needs a loaded bitstream"]),
    (888, 232, "AXI HP/GP + IRQ_F2P", "fw", "layers", ["registers: PS reads/writes them", "samples: DMA writes into DDR", "interrupts reach the GIC"]),
    (1158, 202, "PS: Linux", "normal", "linux", ["DMA driver + ADC driver", "device-tree node(s)", "app reads /dev/iio:device0"]),
]
for i, (x, w, name, role, ic, rows) in enumerate(cols):
    b.append(card(x, CY, w, CH, name, role, ic, filled_icon=(ic == "linux"), head=36))
    for j, r in enumerate(rows):
        b.append(text(x + 14, CY + 62 + j * 20, r, size=11.5, color=TEXT))
    if i < 4:
        nx = cols[i + 1][0]
        b.append(arrow(x + w + 2, CY + 75, nx - 4, CY + 75, A, "a", width=2.6))
b.append(text(40, CY + CH + 24, "The amber stages do not exist until steps 2 and 3 below. The PS side (UART, SD, Ethernet) is untouched by any of this: it is why the first boot needs no bitstream.", size=12, color=MUTED))

# ---- bottom: the order of work -----------------------------------------------------------------------------
y1 = CY + CH + 56
b.append(text(40, y1, "THE ORDER OF WORK", size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.3"'))
b.append(rect(40, y1 + 8, 1320, 2, fill=LINE, rx=1))
STEPS = [
    ("1", "PS boots", "this repository", "boot", ["BOOT.BIN + u-boot.img + zImage + DTB,", "login on ttyPS0, Ethernet up.", "Do this first and keep it as the", "known-good fallback."], "done by ./build.sh all"),
    ("2", "PL design", "Vivado, outside this repo", "fw", ["PS preset of the board + Digilent's", "Zmod ADC IP + AXI DMA; export a", ".bit and the hardware handoff", "(addresses and IRQs)."], "Digilent publishes starters"),
    ("3", "Load it", "bitstream → fabric", "fw", ["Convert .bit to a byte-swapped .bin", "(bootgen). Load BEFORE Linux probes", "the PL nodes: U-Boot, or an FSBL-style", "BOOT.BIN, or Linux fpga_manager."], "firmware goes to /lib/firmware"),
    ("4", "Describe it", "device tree", "rootfs", ["Nodes for the DMA engine and the ADC", "at the addresses of step 2: static", "(bitstream loaded earlier) or an", "overlay (loaded at runtime)."], "reg, interrupts, dmas = <&dma 1>"),
    ("5", "Driver", "kernel", "normal", ["xilinx_dma (already in this kernel) +", "an IIO driver for the ADC controller,", "or Digilent's UIO + axidma approach.", "Then read samples from user space."], "the one piece nobody ships in mainline"),
]
sw, gap = 250, 17.5
for i, (n, name, sub, role, rows, foot) in enumerate(STEPS):
    x = 40 + i * (sw + gap)
    strong, soft, fill, border = ROLE[role]
    b.append(card(x, y1 + 28, sw, 236, "%s  %s" % (n, name), role, None, head=36))
    b.append(text(x + 14, y1 + 28 + 58, sub, size=11.5, mono=True, color=soft, weight=700))
    for j, r in enumerate(rows):
        b.append(text(x + 14, y1 + 28 + 88 + j * 20, r, size=11.5, color=TEXT))
    b.append(text(x + 14, y1 + 28 + 214, foot, size=11, color=MUTED))
    if i < 4:
        b.append(arrow(x + sw + 1, y1 + 28 + 18, x + sw + gap - 2, y1 + 28 + 18, A, "a", width=2.4))
b.append(rect(40, y1 + 308, 1320, 80, fill="#0f192d", stroke=LINE, rx=10))
b.append(lines(56, y1 + 334, [
    "Why this order: a node whose hardware is not configured makes Linux hang on its first register access, so the bitstream must be in the fabric before the driver probes.",
    "And a Zmod pod is not hot-swappable: power the board off before you plug or unplug one (reference manual, section 8).",
], size=12.5, gap=24, color=TEXT))
b.append(caption(H - 34, "Facts: Eclypse Z7 reference manual (Zmod ports, SmartVIO, I2C), Digilent's Eclypse-Z7-OS project (Zmod ADC design, DMA via xilinx_axidma and UIO), UG585 (PS-PL interfaces)."))
b.append(caption(H - 14, "A bench-proven configuration drives the Zmod Scope with xilinx_dma plus a small IIO driver, one DMA channel per ADC, and loads the bitstream through the kernel's FPGA manager after boot."))
write("zmod-loading-order.svg", W, H,
      "Where the Zmod ADC fits: a Zmod Scope pod on a SYZYGY port is wired to the programmable logic, where a bitstream provides the ADC controller and an AXI DMA; "
      "AXI and interrupts connect them to the processing system and Linux. The order of work is: boot the PS first, build a PL design, load its bitstream before "
      "the kernel probes it, add device-tree nodes, then a driver.",
      "".join(b))
