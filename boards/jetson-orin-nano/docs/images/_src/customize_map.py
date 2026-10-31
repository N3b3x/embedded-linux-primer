"""docs/images/customize-map.svg - where each kind of change goes and where it ends up (generated)."""
from kit import *

W, H = 1400, 900
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Where your changes go",
               "Pick the row that matches what you want to change. Each row says which file to edit, what to re-run, and which part of the board is rewritten."))

# (what[], edit[], how[], run[], lands, rewritten, role)
ROWS = [
    (["a kernel option"], ["config/kernel/my.cfg"], ["CONFIG_FOO=y, one per line"], ["./build.sh kernel"],
     "kernel/Image + rootfs/lib/modules", "kernel partition and APP", "normal"),
    (["a driver or kernel", "source change"], ["patches/source/0001-….patch"], ["patch -p1, relative to", "build/work/Linux_for_Tegra/source"], ["./build.sh kernel"],
     "kernel/Image + modules", "kernel partition and APP", "normal"),
    (["a device tree node", "or property"], ["patches/source/0002-….patch"], ["files under source/hardware/", "nvidia/t23x/nv-public/…"], ["./build.sh kernel"],
     "kernel/dtb/*.dtb", "kernel-dtb partition", "rootfs"),
    (["which DTB the kernel", "boots with"], ["rootfs/boot/extlinux/", "extlinux.conf"], ["add an FDT /boot/….dtb line", "(NVIDIA: 'DTB Support')"], ["./build.sh image"],
     "APP:/boot/extlinux/", "APP (root filesystem)", "rootfs"),
    (["UEFI boot order", "or boot mode"], ["ROOT_DEVICE, BOOT_ORDER_OVERLAY", "(or kernel/dtb/L4TConfiguration.dtbo)"], ["config variables, or dtc -I dtb", "-O dts, edit, convert back"], ["./build.sh image", "./build.sh flash"],
     "QSPI-NOR (UEFI variables)", "boot firmware, A and B", "boot"),
    (["hostname, user,", "password"], ["config/local.conf"], ["TARGET_HOSTNAME, TARGET_USER,", "TARGET_PASSWORD"], ["clean, rootfs, image"],
     "rootfs/etc/…", "APP (root filesystem)", "rootfs"),
    (["packages, files,", "services"], ["build/work/Linux_for_Tegra/", "rootfs/"], ["sudo chroot (qemu) or copy", "files in as root"], ["./build.sh image"],
     "rootfs/…", "APP (root filesystem)", "rootfs"),
    (["pinmux, pad voltage", "(your own carrier)"], ["a copy of the board .conf", "+ bootloader/generic/BCT/*.dtsi"], ["new BOARD name, new MB1-BCT", "dtsi files (docs/08 §6)"], ["BOARD=… ./build.sh", "image && flash"],
     "QSPI-NOR (MB1-BCT)", "boot firmware, A and B", "fw"),
]
HEAD = [("I want to change…", 32, 226), ("Edit…", 270, 290), ("How", 572, 286), ("Then run", 870, 220), ("It lands in…", 1102, 266)]
y = 100
for name, x, w in HEAD:
    b.append(rect(x, y, w, 30, fill="#26344f", rx=7))
    b.append(text(x + 12, y + 20, name, size=12.5, weight=800, color=TEXT))
y += 38
for what, edit, how, run, lands, rewritten, role in ROWS:
    strong, soft, fill, border = ROLE[role]
    h = 66
    b.append(rect(32, y, 226, h, fill=strong, rx=9))
    for i, ln in enumerate(what):
        b.append(text(46, y + (28 if len(what) == 2 else 38) + i * 19, ln, size=13, weight=800, color="#fff"))
    b.append(rect(270, y, 290, h, fill=fill, stroke=border, rx=9, sw=1.3))
    for i, ln in enumerate(edit):
        b.append(text(282, y + (28 if len(edit) == 2 else 38) + i * 19, ln, size=11.2, mono=True, color=soft, weight=700))
    b.append(rect(572, y, 286, h, fill=PANEL, stroke=LINE, rx=9))
    for i, ln in enumerate(how):
        b.append(text(584, y + (28 if len(how) == 2 else 38) + i * 19, ln, size=11.5, color=TEXT))
    b.append(rect(870, y, 220, h, fill=PANEL2, stroke="#334155", rx=9))
    for i, ln in enumerate(run):
        b.append(text(882, y + (28 if len(run) == 2 else 38) + i * 19, ln, size=11.4, mono=True, color="#93c5fd"))
    b.append(rect(1102, y, 266, h, fill=PANEL, stroke=border, rx=9, sw=1.3))
    b.append(text(1114, y + 27, lands, size=11.8, color=TEXT, weight=700))
    b.append(text(1114, y + 48, "→ " + rewritten, size=11.4, color=MUTED))
    for xa in (258, 560, 858, 1090):
        b.append(arrow(xa + 1, y + h / 2, xa + 11, y + h / 2, A, "a", width=2))
    y += h + 8

b.append(rect(32, y + 6, 1336, 78, fill="#06231f", stroke="#14b8a6", rx=12, sw=1.5))
b.append(icon("rocket", 48, y + 20, 26, "#5eead4"))
b.append(text(86, y + 30, "Fast loop for kernel work", size=13.5, weight=800, color="#5eead4"))
b.append(text(86, y + 50, "In the default boot mode the kernel comes from the root filesystem (/boot/Image, selected by /boot/extlinux/extlinux.conf).", size=11.5, color=TEXT))
b.append(text(86, y + 68, "On a running board: scp the new Image and modules, keep the old kernel as a second extlinux entry, reboot. No recovery mode.", size=11.5, color=TEXT))
b.append(caption(H - 18, "Exact commands for each row: docs/08-customizing.md. A change that lands in 'boot firmware' rewrites the QSPI-NOR flash, which needs recovery mode again."))
write("customize-map.svg", W, H,
      "Where changes go: a kernel option goes in config/kernel; a driver or device tree change is a patch in patches/source; the DTB choice is a line in "
      "extlinux.conf; UEFI boot order and mode are set with a config variable or the L4TConfiguration overlay and need the QSPI flash rewritten; user and "
      "hostname are config variables; packages and files go into the rootfs directory; pinmux for a custom carrier goes in a new board config and BCT files "
      "and also rewrites the QSPI flash.",
      "".join(b))
