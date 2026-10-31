"""docs/images/build-pipeline.svg - what ./build.sh all does (generated)."""
from kit import *

W, H = 1400, 940
A = "#e5edf7"
b = [marker_defs({"a": A, "f": "#fcd34d", "v": "#c4b5fd", "t": "#5eead4", "u": "#93c5fd"})]
b.append(title("What ./build.sh all does: NVIDIA's release in, a flash package out",
               "No SD-card image is assembled. The result is a Linux_for_Tegra/ tree plus the signed images that NVIDIA's tool generates from it."))

# ---- row 1: downloads --------------------------------------------------------
DL = [("Driver package", "Jetson_Linux_r36.4.3_aarch64.tbz2", "715 MB", "flash tools · firmware binaries · stock kernel", False),
      ("Sample root filesystem", "Tegra_Linux_Sample-Root-Filesystem…tbz2", "1.8 GB", "Ubuntu 22.04 (jammy) arm64 userland", False),
      ("Public sources", "public_sources.tbz2", "226 MB", "kernel · NVIDIA modules · device trees", True),
      ("Reference toolchain", "aarch64--glibc--stable-2022.08-1", "140 MB", "GCC 11.3 · runs on x86-64 only", True)]
b.append(text(32, 100, "./build.sh fetch   (every file verified against a pinned sha256)", size=12.5, weight=700, color=MUTED))
for i, (nm, fn, sz, what, opt) in enumerate(DL):
    x = 32 + i * 333
    b.append(card(x, 112, 315, 104, nm, "fw", ic="download", sub=sz, dashed=opt))
    b.append(text(x + 14, 162, fn, size=10.8, mono=True, color="#fcd34d"))
    b.append(text(x + 14, 184, what, size=12, color=TEXT))
    b.append(text(x + 14, 203, "only for your own kernel" if opt else "always needed", size=11, color=MUTED if opt else "#6ee7b7", weight=700))

# ---- row 2: steps ------------------------------------------------------------
STEPS = [
    ("rootfs", "./build.sh rootfs", "rootfs", "package", 32, 440,
     ["sudo tar xpf sample-rootfs -C rootfs/", "· keeps owners and permissions", "sudo ./apply_binaries.sh", "· NVIDIA libraries + stock kernel modules,", "· extlinux.conf, initrd",
      "sudo ./tools/l4t_create_default_user.sh", "· login account: no first-boot wizard"]),
    ("kernel", "./build.sh kernel", "normal", "hammer", 504, 440,
     ["extract kernel_src · oot_modules · display", "apply patches/source/*.patch", "make defconfig + config/kernel/*.cfg",
      "make Image dtbs modules      (kernel)", "make modules dtbs   (NVIDIA out-of-tree)", "install → rootfs/lib/modules, kernel/Image,", "· kernel/dtb/, rebuild the initrd"]),
]
for nm, cmd, role, ic, x, w, rows in STEPS:
    b.append(card(x, 262, w if nm == "rootfs" else 392, 232, cmd, role, ic=ic))
    b.append(lines(x + 14, 318, rows, size=11.8, gap=21, mono=True, color="#cbd5e1"))
# image step
b.append(card(924, 262, 422, 232, "./build.sh image", "boot", ic="package"))
b.append(lines(938, 318, ["sudo l4t_initrd_flash.sh --no-flash", "· -p -c flash_t234_qspi.xml", "· --external-device nvme0n1p1 (or sd, usb)", "· -c flash_l4t_t234_nvme.xml",
                          "· jetson-orin-nano-devkit-super internal", "builds signed QSPI images, the APP", "rootfs image and the flashing initrd"], size=11.8, gap=21, mono=True, color="#cbd5e1"))
# arrows downloads -> steps
b.append(arrow(190, 218, 190, 258, "#fcd34d", "f", width=3))
b.append(arrow(523, 218, 400, 258, "#fcd34d", "f", width=3))
b.append(arrow(856, 218, 700, 258, "#fcd34d", "f", width=3, dash="7 5"))
b.append(arrow(1189, 218, 760, 258, "#fcd34d", "f", width=3, dash="7 5"))
# step -> step
b.append(arrow(472, 380, 500, 380, A, "a", width=3))
b.append(arrow(896, 380, 920, 380, A, "a", width=3))

# ---- row 3: the tree -----------------------------------------------------------
ty = 548
b.append(rect(32, ty, 1314, 214, fill="#0c1d3d", stroke="#3b82f6", rx=16, sw=1.8))
b.append(icon("boxes", 50, ty + 14, 28, "#93c5fd"))
b.append(text(90, ty + 36, "build/work/Linux_for_Tegra/", size=17, weight=800, color="#93c5fd", mono=True))
b.append(text(430, ty + 36, "NVIDIA's own directory layout. Their scripts only work from inside it, so this tree is the real build artifact.", size=12.5, color=TEXT))
TREE = [("rootfs/", "the OS: Ubuntu + NVIDIA userspace + modules", "rootfs"),
        ("kernel/Image", "the kernel flashed to the 'kernel' partition", "normal"),
        ("kernel/dtb/*.dtb *.dtbo", "board device trees + UEFI overlays", "rootfs"),
        ("bootloader/", "MB1 · MB2 · UEFI · BPMP · SPE … binaries", "fw"),
        ("<board>.conf · flash.sh", "board spec, partition XMLs (bootloader/generic/cfg)", "boot"),
        ("tools/kernel_flash/", "l4t_initrd_flash.sh and the generated images/", "boot")]
for i, (nm, what, role) in enumerate(TREE):
    col, row = i % 3, i // 3
    x, y = 50 + col * 434, ty + 62 + row * 72
    strong, soft, fill, border = ROLE[role]
    b.append(rect(x, y, 418, 60, fill=fill, stroke=border, rx=10, sw=1.4))
    b.append(text(x + 14, y + 25, nm, size=13, mono=True, weight=700, color=soft))
    b.append(text(x + 14, y + 46, what, size=11.8, color=TEXT))
# arrows steps -> tree
b.append(arrow(250, 496, 250, 544, "#c4b5fd", "v", width=3))
b.append(arrow(700, 496, 700, 544, "#5eead4", "t", width=3))
b.append(arrow(1135, 496, 1135, 544, "#93c5fd", "u", width=3))

# ---- row 4: flash + board ---------------------------------------------------------
fy = 806
b.append(card(32, fy, 560, 92, "./build.sh flash", "secure", ic="usb", sub="needs the board in recovery mode"))
b.append(lines(46, fy + 62, ["sudo l4t_initrd_flash.sh --flash-only --network usb0", "boots a recovery initrd over USB, then writes everything"], size=11.8, gap=20, mono=True, color="#cbd5e1"))
b.append(card(660, fy, 686, 92, "Jetson Orin Nano Developer Kit", "hw", ic="microchip"))
b.append(lines(674, fy + 62, ["QSPI-NOR (64 MiB on the module): boot firmware, two copies (A_ and B_)",
                            "SD card, NVMe or USB drive: kernel, kernel-dtb, ESP, APP (the root filesystem)"], size=11.8, gap=20))
b.append(arrow(592, fy + 46, 656, fy + 46, A, "a", width=3))
b.append(arrow(700, 764, 300, fy - 4, A, "a", width=3))
b.append(text(618, 800, "the flash package", size=11.5, color=MUTED))

b.append(caption(H - 22, "Steps run as your user except where sudo is shown: root-owned files must be created as root. Everything is explained command by command in ./build.sh --dry-run all."))
write("build-pipeline.svg", W, H,
      "Build pipeline: four checksummed downloads (driver package, sample root filesystem, public sources, reference toolchain). The rootfs step "
      "unpacks the sample filesystem, applies NVIDIA's binaries and creates a login user. The kernel step builds the kernel, NVIDIA's out-of-tree "
      "modules and the device trees from public sources and installs them. The image step runs NVIDIA's initrd flash tool without flashing, to "
      "generate the flash package. Everything lives in the Linux_for_Tegra directory. The flash step then writes the QSPI-NOR flash and the "
      "SD, NVMe or USB drive over USB in recovery mode.",
      "".join(b))
