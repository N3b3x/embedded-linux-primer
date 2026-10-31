"""docs/images/bootbin-anatomy.svg - what BOOT.BIN contains and what ps7_init does (generated)."""
from kit import *

W, H = 1400, 900
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Inside BOOT.BIN, and what the SPL's first call (ps7_init) does",
               "BOOT.BIN is 131,676 bytes in this build: a 2,240-byte Zynq boot header and the SPL. Its first job is to make the DDR3L usable."))

# ---- left: the byte map ---------------------------------------------------------------------------
LX, LW = 40, 600
b.append(text(LX, 120, "THE FILE, BYTE BY BYTE", size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.3"'))
b.append(rect(LX, 128, LW, 2, fill=LINE, rx=1))
# header
b.append(rect(LX, 148, LW, 330, fill=PANEL, stroke=ROLE["fw"][3], rx=12, sw=1.5))
b.append(rect(LX, 148, LW, 36, fill=ROLE["fw"][0], rx=12))
b.append(rect(LX, 166, LW, 18, fill=ROLE["fw"][0]))
b.append(text(LX + 14, 172, "Zynq boot header", size=14.5, weight=800, color="#fff"))
b.append(text(LX + LW - 12, 172, "0x000 - 0x8BF", size=11.5, color="#fde68a", anchor="end", mono=True))
fields = [
    ("0x000", "8 × 0xEAFFFFFE", "interrupt vectors: branch-to-self"),
    ("0x020", "0xAA995566", "width detection: the BootROM checks the bus width"),
    ("0x024", "'XNLX'  0x584C4E58", "image identifier"),
    ("0x028", "0x00000000", "encryption: none"),
    ("0x030", "0x000008C0", "image offset: where the payload starts"),
    ("0x034", "0x0002025C", "image size in bytes (131,676, the whole file)"),
    ("0x03C", "0x00000000", "image load: the SPL runs at address 0 (OCM)"),
    ("0x048", "0xFD164EC9", "header checksum (~ sum of 0x20 - 0x44)"),
    ("0x0A0", "256 × (-1, -1)", "register-init list: unused, ps7_init does the work"),
]
for i, (off, val, what) in enumerate(fields):
    yy = 208 + i * 29
    b.append(text(LX + 14, yy, off, size=11.5, mono=True, color=FAINT))
    b.append(text(LX + 78, yy, val, size=11.5, mono=True, weight=700, color="#fcd34d"))
    b.append(text(LX + 270, yy, what, size=11, color=TEXT))
# payload
b.append(rect(LX, 490, LW, 150, fill=PANEL, stroke=ROLE["boot"][3], rx=12, sw=1.5))
b.append(rect(LX, 490, LW, 36, fill=ROLE["boot"][0], rx=12))
b.append(rect(LX, 508, LW, 18, fill=ROLE["boot"][0]))
b.append(text(LX + 14, 514, "the SPL (spl/u-boot-spl.bin)", size=14.5, weight=800, color="#fff"))
b.append(text(LX + LW - 12, 514, "0x8C0 - end", size=11.5, color="#dbeafe", anchor="end", mono=True))
b.append(lines(LX + 14, 552, [
    "129,436 bytes of ARM code and data plus U-Boot's SPL device tree:",
    "  ps7_init_gpl.o (the register writes), the UART and SD drivers,",
    "  a FAT reader, a FIT parser; linked to run at address 0.",
    "The BootROM copies it into OCM, so it must stay under 192 KiB.",
], size=11.8, gap=19, color=TEXT))
b.append(rect(LX, 652, LW, 74, fill="#0f192d", stroke=LINE, rx=10))
b.append(lines(LX + 14, 676, [
    "No FSBL, no bitstream, no U-Boot proper in this file. Those are:",
    "  u-boot.img: a separate FAT file the SPL loads by name,",
    "  the PL bitstream: not used for the first boot (docs/13).",
], size=11.8, gap=19, color=MUTED))

# ---- right: what ps7_init does -------------------------------------------------------------------------
RX, RW = 700, 660
b.append(text(RX, 120, "ps7_init(), THE FIRST THING THE SPL DOES (board_init_f in arch/arm/mach-zynq/spl.c)", size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.1"'))
b.append(rect(RX, 128, RW, 2, fill=LINE, rx=1))
STEPS = [
    ("1", "MIO", "ps7_mio_init_data", "mux the 54 MIO pins: UART0 on 14/15, SD0 on 40-45, Ethernet RGMII on 16-27, USB on 28-39, QSPI on 1-6", "boot"),
    ("2", "PLLs", "ps7_pll_init_data", "start ARM, DDR and IO PLLs from the 33.3333 MHz PS_CLK and wait for lock", "boot"),
    ("3", "Clocks", "ps7_clock_init_data", "dividers for the CPUs, the DDR, the UART, SD and Ethernet; the PL clock FCLK0", "boot"),
    ("4", "DDR", "ps7_ddr_init_data", "program the DDR controller for DDR3, 32-bit data bus, 1 GiB; poll the DCI calibration and the controller until DDR is up", "secure"),
    ("5", "Peripherals", "ps7_peripherals_init_data", "UART and QSPI controller registers, SMC timing, DDR termination, the PL power-on-reset registers; then lock the SLCR again", "boot"),
]
for i, (n, name, arr, what, role) in enumerate(STEPS):
    y = 148 + i * 84
    strong, soft, fill, border = ROLE[role]
    b.append(rect(RX, y, RW, 72, fill=PANEL, stroke=border, rx=12, sw=1.4))
    b.append(rect(RX, y, 130, 72, fill=strong, rx=12))
    b.append(rect(RX + 100, y, 30, 72, fill=strong))
    b.append(badge(RX + 24, y + 36, n, "#e2e8f0", r=12))
    b.append(text(RX + 48, y + 41, name, size=15, weight=800, color="#fff"))
    b.append(text(RX + 146, y + 26, arr + "[]", size=11.5, mono=True, weight=700, color=soft))
    words, line, k = what.split(), "", 0
    for wd in words:
        if len(line) + len(wd) + 1 > 64:
            b.append(text(RX + 146, y + 46 + k * 16, line, size=11.5, color=TEXT)); line = wd; k += 1
        else:
            line = (line + " " + wd).strip()
    b.append(text(RX + 146, y + 46 + k * 16, line, size=11.5, color=TEXT))
    if i < 4:
        b.append(arrow(RX + 65, y + 74, RX + 65, y + 82, A, "a", width=2.4))
b.append(rect(RX, 580, RW, 146, fill="#0f192d", stroke=LINE, rx=10))
b.append(text(RX + 14, 604, "Why this is a table of register writes", size=13, weight=800))
b.append(lines(RX + 14, 628, [
    "Each array is a list of EMIT_WRITE / EMIT_MASKWRITE / EMIT_MASKPOLL records:",
    "  an address, a mask and a value. ps7_config() walks the list and does them.",
    "The file holds three copies (silicon 1.0, 2.0, 3.0); ps7_init() reads the chip's",
    "  revision and picks one. Vivado generates all of it from the board preset.",
], size=11.8, gap=19, color=MUTED))
# arrow between the halves
b.append(path_arrow([(LX + LW + 4, 560), (RX - 6, 560)], A, "a", width=2.6, label="calls", lx=(LX + LW + RX) / 2, ly=560))

# ---- bottom: what ends up where ------------------------------------------------------------------------
y = 752
b.append(text(40, y, "AFTER ps7_init", size=12, weight=800, color=MUTED, extra=' letter-spacing="1.3"'))
b.append(rect(40, y + 8, 1320, 2, fill=LINE, rx=1))
b.append(lines(40, y + 34, [
    "The SPL initialises its console (you see \"U-Boot SPL 2026.07…\"), sets up the SD host, opens u-boot.img on the FAT partition and jumps to it in DDR.",
    "ps7_init does NOT configure the programmable logic. The PL needs a bitstream, which this build does not load.",
], size=12.5, gap=22, color=TEXT))
b.append(caption(H - 38, "Header layout: tools/zynqimage.c; values read from this build's spl/boot.bin with mkimage -l and a hex dump. The 192 KiB limit is CONFIG_SPL_MAX_SIZE=0x30000."))
b.append(caption(H - 18, "ps7_init_gpl.c: generated by Vivado 2019.1 for Digilent's Eclypse Z7 preset; this file is downloaded, not committed (docs/03-uboot-spl.md). Pins: UG585 and the Eclypse Z7 reference manual."))
write("bootbin-anatomy.svg", W, H,
      "What is inside BOOT.BIN: a 2,240-byte Zynq boot header (width detection word, XNLX identifier, image offset 0x8C0, image size, load address 0, checksum) "
      "followed by the U-Boot SPL; and what the SPL's first call, ps7_init, does: set the MIO pin muxes, start the PLLs, set the clock dividers, "
      "initialise the DDR3L controller and enable the peripherals; the programmable logic is not configured.",
      "".join(b))
