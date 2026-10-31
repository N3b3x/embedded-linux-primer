"""docs/images/embedded-linux-stack.svg - the layers every embedded Linux board boots through (generated)."""
from kit import *

W, H = 1400, 872
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Every embedded Linux board is the same stack",
               "Six layers, started in this order. The names change from vendor to vendor; the jobs do not."))

ROWS = [
    ("1", "Boot ROM", "hw", "microchip",
     ["Mask ROM inside the SoC. Reads the boot-mode pins or fuses,", "finds the first loader on SD, eMMC, QSPI or USB, and runs it."],
     "silicon vendor", "never: burned into the chip", 6),
    ("2", "First-stage firmware + secure world", "secure", "shield-check",
     ["Starts the DRAM (training), then installs the secure monitor", "(TF-A) and optionally a trusted OS (OP-TEE). Stays resident."],
     "vendor, open source + blobs", "rarely: new silicon, security", 1),
    ("3", "Bootloader", "boot", "rocket",
     ["U-Boot or UEFI. Picks a kernel and a device tree from storage,", "builds the kernel command line, jumps. Then it is gone."],
     "U-Boot community + vendor fork", "sometimes: boot order, env", 2),
    ("4", "Kernel + device tree", "normal", "linux",
     ["Linux. The device tree (.dtb) tells it which hardware exists", "and where; drivers bind to the nodes."],
     "kernel.org + vendor fork", "often: config, device tree, drivers", 3),
    ("5", "Root filesystem", "rootfs", "hard-drive",
     ["Everything in /: init, shell, libraries, packages, services.", "Debian, Alpine, a vendor rootfs, or one you assemble."],
     "distribution or you", "constantly: it is the product", 4),
    ("6", "Your application", "normal", "box",
     ["The reason the board exists. Runs on top of all of the above", "and is the only layer that changes every week."],
     "you", "daily", 5),
]
COLS = [(350, "What it does"), (890, "Who provides it"), (1135, "How often you change it")]
for x, t in COLS:
    b.append(text(x, 112, t.upper(), size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))

y = 128
for n, name, role, ic, what, who, freq, level in ROWS:
    strong, soft, fill, border = ROLE[role]
    h = 98
    b.append(rect(32, y, 1336, h, fill=fill, stroke=border, rx=14, sw=1.4))
    b.append(rect(32, y, 300, h, fill=strong, rx=14))
    b.append(badge(62, y + 49, n, "#ffffff", r=13))
    b.append(icon(ic, 86, y + 37, 24, "#ffffff"))
    # wrap long names on two lines
    if len(name) > 22:
        head, tail = name.split(" + ") if " + " in name else (name, "")
        b.append(text(122, y + 44, head, size=15, weight=800, color="#ffffff"))
        b.append(text(122, y + 63, "+ " + tail, size=15, weight=800, color="#ffffff"))
    else:
        b.append(text(122, y + 54, name, size=16, weight=800, color="#ffffff"))
    b.append(lines(350, y + 40, what, size=13, gap=21, color=TEXT))
    b.append(text(890, y + 40, who, size=13, color=soft, weight=700))
    # change-frequency bar
    b.append(text(1135, y + 40, freq, size=12.5, color=TEXT))
    for k in range(6):
        on = k >= level
        b.append(rect(1135 + k * 38, y + 62, 32, 10, fill=strong if on else "#1e293b", rx=5))
    y += h + 10
    if n != "6":
        b.append(arrow(182, y - 9, 182, y + 1, A, "a", width=2.4))

b.append(rect(32, y + 6, 1336, 56, fill=PANEL, stroke=LINE, rx=12))
b.append(icon("hammer", 48, y + 22, 24, "#fcd34d"))
b.append(text(86, y + 30, "In this repository:", size=13.5, weight=800, color="#fcd34d"))
for cx, cmd, what in [(262, "./build.sh uboot", "layers 2–3"), (532, "./build.sh kernel", "layer 4"), (800, "./build.sh rootfs", "layer 5"), (1066, "./build.sh image", "glues 1–5 into one artifact")]:
    b.append(text(cx, y + 30, cmd, size=12.5, color=TEXT, mono=True))
    b.append(text(cx + len(cmd) * 7.8 + 10, y + 30, "→ " + what, size=12.5, color=MUTED))
b.append(text(86, y + 50, "Boards that flash over USB instead of an SD card (Jetson) swap the last step for NVIDIA's flash tool, but the six layers are the same.", size=12, color=MUTED))
write("embedded-linux-stack.svg", W, H,
      "The six layers of an embedded Linux board in boot order: the boot ROM in the silicon, first-stage firmware with the secure world "
      "(TF-A and OP-TEE), the bootloader (U-Boot or UEFI), the Linux kernel with its device tree, the root filesystem, and the application. "
      "Each row says who provides the layer and how often you change it, from never for the boot ROM to daily for the application.",
      "".join(b))
