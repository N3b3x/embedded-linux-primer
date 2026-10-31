"""docs/images/source-map.svg - the files that decide how the board boots, in boot order (generated)."""
from kit import *

W, H = 1400, 1190
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("The files to open, in boot order",
               "Paths are inside build/work/Linux_for_Tegra/ after ./build.sh fetch rootfs kernel. 'binary' means NVIDIA ships it compiled; there is nothing to read."))

STEPS = [
    ("hw", "BootROM · MB1", "NVIDIA binary + config", [
        ("bootloader/mb1_t234_prod.bin", "MB1 itself: binary, signed and encrypted by NVIDIA"),
        ("bootloader/generic/BCT/tegra234-mb1-bct-pinmux-p3767-dp-a03.dtsi", "MB1-BCT: pinmux for the module. Open it: it is a device tree source"),
        ("bootloader/generic/cfg/flash_t234_qspi.xml", "which firmware image goes into which QSPI-NOR partition, and how large"),
    ]),
    ("boot", "Board specification", "what flash.sh reads", [
        ("jetson-orin-nano-devkit-super.conf", "the board: picks the device tree (DTB_FILE), BPMP dtb, pinmux, layouts"),
        ("p3767.conf.common", "settings shared by every P3767 module (Orin Nano / NX)"),
        ("flash.sh · tools/kernel_flash/l4t_initrd_flash.sh", "the drivers: partition XML + .conf → signed images → flash"),
    ]),
    ("boot", "MB2 · UEFI · L4TLauncher", "NVIDIA binary", [
        ("bootloader/mb2_t234.bin · bootloader/uefi_jetson.bin", "MB2 and UEFI as shipped; UEFI source: github.com/NVIDIA/edk2-nvidia"),
        ("kernel/dtb/L4TConfiguration.dtbo · BootOrder*.dtbo", "UEFI settings as device-tree overlays: boot mode, boot device order"),
        ("bootloader/BOOTAA64.efi · bootloader/extlinux.conf", "L4TLauncher, and the extlinux.conf copied to <rootfs>/boot/extlinux/"),
    ]),
    ("secure", "Secure OS", "public source", [
        ("bootloader/tos-optee_t234.img", "the OP-TEE secure OS image (bootloader/SOURCE.tos-optee_t234.img names its sources: atf, nv-optee)"),
        ("source/atf_src.tbz2 · source/nvidia-jetson-optee-source.tbz2", "their sources: arm-trusted-firmware/ and optee/optee_os/"),
    ]),
    ("normal", "Linux kernel", "built by ./build.sh kernel", [
        ("source/kernel/Makefile", "NVIDIA's own build recipe: defconfig, Image, dtbs, modules; we unroll it"),
        ("source/kernel/kernel-jammy-src/arch/arm64/configs/defconfig", "the kernel configuration (Linux 5.15.148, '-tegra' local version)"),
        ("source/Makefile · nvidia-oot/ · nvgpu/ · nvdisplay/ · hwpm/", "the out-of-tree modules: GPU, display, camera, hardware performance"),
    ]),
    ("rootfs", "Device tree", "built by make dtbs", [
        ("source/hardware/nvidia/t23x/nv-public/nv-platform/tegra234-p3768-0000+p3767-0005-nv-super.dts", "the Orin Nano Super devkit: includes the -nv.dts and trims the CPU OPP table"),
        ("…/nv-platform/tegra234-p3768-0000+p3767-xxxx-nv-common.dtsi", "nodes shared by every module on this carrier: aliases, I2S, DMIC, thermal, camera"),
        ("…/nv-platform/tegra234-p3768-0000.dtsi · tegra234-p3767-0000.dtsi", "the carrier (P3768) and the module (P3767) layers"),
        ("source/kernel-devicetree/generic-dts/Makefile", "how the .dts files become kernel/dtb/*.dtb"),
    ]),
    ("rootfs", "User space", "assembled by ./build.sh rootfs", [
        ("apply_binaries.sh · nv_tegra/nv-apply-debs.sh", "installs NVIDIA's Debian packages and tarballs into rootfs/"),
        ("tools/l4t_create_default_user.sh · tools/l4t_update_initrd.sh", "the login account, and the initrd that must match the modules"),
    ]),
]
y = 100
for role, stage, who, files in STEPS:
    strong, soft, fill, border = ROLE[role]
    h = 22 + 36 * len(files) + 8
    b.append(rect(32, y, 1336, h, fill=fill, stroke=border, rx=14, sw=1.6))
    b.append(rect(32, y, 190, h, fill=strong, rx=14))
    b.append(text(127, y + h / 2 - 2, stage, size=15 if len(stage) < 16 else 13.5, weight=800, anchor="middle", color="#fff"))
    b.append(text(127, y + h / 2 + 18, who, size=11, anchor="middle", color="#e2e8f0"))
    for i, (f, what) in enumerate(files):
        yy = y + 24 + i * 36
        b.append(rect(240, yy - 17, 620, 30, fill="#050a14", stroke="#334155", rx=8))
        fs = 11.6 if len(f) < 70 else 9.4
        b.append(text(252, yy + 3, f, size=fs, mono=True, color=soft))
        b.append(text(876, yy + 3, what, size=11.6, color=TEXT))
    if role != "rootfs" or stage == "Device tree":
        b.append(arrow(127, y + h + 1, 127, y + h + 14, A, "a", width=2.6))
    y += h + 16

b.append(caption(y + 8, "Handy: grep -rn \"p3767\" build/work/Linux_for_Tegra/*.conf · grep -rn \"MAXN_SUPER\" build/work/Linux_for_Tegra/source/hardware/ · dtc -I dtb -O dts kernel/dtb/L4TConfiguration.dtbo"))
b.append(caption(y + 28, "Each file is explained, with what to change and where, in docs/15-source-tour.md."))
write("source-map.svg", W, H,
      "Files that decide how the Jetson Orin Nano boots, in boot order: the MB1 binary, its boot configuration table and the QSPI partition XML; the board "
      "specification files and the flash scripts; MB2, UEFI and L4TLauncher; the secure OS; the kernel Makefile, defconfig and NVIDIA's out-of-tree modules; "
      "the device tree sources of the Orin Nano Super developer kit; and the scripts that assemble the user space.",
      "".join(b))
