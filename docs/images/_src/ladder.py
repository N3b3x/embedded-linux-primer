"""docs/images/customization-ladder.svg - where a change goes, and what it costs when it is wrong (generated)."""
from kit import *

W, H = 1400, 900
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Where does my change go? The customization ladder",
               "Start at the top rung that can do the job. Each step up costs a longer rebuild and a worse failure when you get it wrong."))

# (role, rung name, example, where in a board directory, rebuild, if wrong, recovery)
RUNGS = [
    ("normal", "Application / service", "run my program at boot", "scripts/rootfs/ hook", "seconds", "service fails", "edit and reboot"),
    ("rootfs", "Root filesystem", "add a package, a user, a config file", "scripts/rootfs/ · packages", "a minute", "no login", "re-flash the rootfs"),
    ("rootfs", "Device tree", "enable a UART or I²C sensor", "custom/dts/", "seconds", "device missing or early hang", "boot the old .dtb"),
    ("normal", "Kernel config", "enable a driver, a filesystem, a feature", "config/kernel/*.cfg", "minutes (ccache)", "no boot or missing device", "re-flash /boot"),
    ("normal", "Kernel patch", "fix or add driver code", "patches/kernel/", "minutes", "oops or no boot", "re-flash /boot"),
    ("boot", "Bootloader environment", "boot order, console, kernel args", "uEnv.txt · extlinux.conf · env", "seconds", "no kernel found", "fix it at the prompt"),
    ("boot", "Bootloader patch / config", "new boot source, new board variant", "patches/uboot/ · defconfig", "minutes", "board stops at the ROM", "boot another medium"),
    ("secure", "Secure firmware", "TF-A, OP-TEE, DDR, secure services", "patches/atf/ · optee", "minutes", "no serial output at all", "other medium or USB boot"),
    ("hw", "Boot ROM, fuses", "lock to signed images only", "vendor tools; NOT in this repo", "n/a", "a bricked board, forever", "none: one-time fuses"),
]
# header
cols = [(300, "EXAMPLE"), (560, "WHERE IT LIVES"), (850, "REBUILD"), (990, "WHEN IT GOES WRONG"), (1200, "WAY BACK")]
for x, t in cols:
    b.append(text(x, 112, t, size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))
y = 124
n = len(RUNGS)
for i, (role, name, ex, where, rebuild, wrong, back) in enumerate(RUNGS):
    strong, soft, fill, border = ROLE[role]
    h = 70
    # rungs get narrower toward the bottom (safer) and the strip darkens toward the top
    b.append(rect(32, y, 1336, h, fill=fill, stroke=border, rx=12, sw=1.3))
    b.append(rect(32, y, 250, h, fill=strong, rx=12))
    b.append(badge(58, y + 35, i + 1, "#ffffff", r=12))
    b.append(text(82, y + 41, name, size=14.5, weight=800, color="#ffffff"))
    b.append(text(300, y + 41, ex, size=12.5, color=TEXT))
    b.append(text(560, y + 41, where, size=12, color=soft, mono=True))
    b.append(text(850, y + 41, rebuild, size=12.5, color=TEXT))
    danger = "#fda4af" if i >= 6 else (TEXT if i < 5 else "#fcd34d")
    b.append(text(990, y + 41, wrong, size=12.5, color=danger, weight=700 if i >= 7 else 400))
    b.append(text(1200, y + 41, back, size=12.5, color=MUTED))
    y += h + 8
b.append(arrow(18, 190, 18, 700, "#fca5a5", "a", width=1))  # placeholder removed below
b.pop()
b.append(caption(y + 14, "Rung 1 is the cheapest to try, rung 9 cannot be undone. Rule of thumb: use the lowest-numbered rung that can do the job."))
b.append(caption(y + 34, "Every board directory has the same folders for these rungs (see docs/board-contract.md), so the answer to 'where does this go?' is the same on every board."))
write("customization-ladder.svg", W, H,
      "The customization ladder, from the cheapest change to the most dangerous: application and service, root filesystem, device tree, kernel "
      "config, kernel patch, bootloader environment, bootloader patch or config, secure firmware, and finally the boot ROM and security fuses. "
      "For each rung the example, the folder it lives in, the rebuild time, what happens when it goes wrong and the way back.",
      "".join(b))
