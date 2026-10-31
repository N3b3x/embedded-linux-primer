"""docs/images/boot-chain.svg - power-on to login on the Orin Nano (generated)."""
from kit import *

W, H = 1400, 1010
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Jetson Orin Nano boot chain: from power-on to login",
               "Everything above Linux is firmware stored in the module's QSPI-NOR flash. NVIDIA ships it as binaries: you configure it, you do not compile it."))

# (role, name, sub, runs_on, stored_in, lines, owner chip, chip role)
ROWS = [
    ("hw", "BootROM + PSC ROM", "hard-wired in the SoC", "BPMP · PSC", "mask ROM",
     ["BootROM starts as the BPMP leaves reset, initializes the boot media (QSPI-NOR) and",
      "loads BR-BCT, PSC-BL1, MB1 and MB1-BCT. PSCROM holds the NVIDIA/OEM keys and",
      "authenticates the next stage on the BPMP (MB1) and on the PSC (PSC-BL1)."],
     "silicon", "hw"),
    ("boot", "MB1", "Microboot 1", "BPMP", "A_mb1 · A_MB1_BCT · A_MEM_BCT",
     ["Platform setup: pinmux, GPIO, pad voltages, firewalls. Initializes the SDRAM from the",
      "Memory BCT, loads the firmware that brings up the CPU complex, programs the PMIC",
      "rail for the CPUs, creates memory carveouts, then loads MB2."],
     "NVIDIA binary", "fw"),
    ("boot", "MB2", "Microboot 2", "CCPLEX (CPU cores)", "A_mb2",
     ["Next-stage bootloader on the CPU complex. The same component is what receives",
      "images from the host while flashing (cold-boot flashing and RCM boot)."],
     "NVIDIA binary", "fw"),
    ("boot", "UEFI", "CPU bootloader (CPUBL)", "CCPLEX", "A_cpu-bootloader (3.5 MiB)",
     ["EDK2-based. Applies the .dtbo overlays shipped in kernel/dtb (L4TConfiguration,",
      "BootOrder…), chooses the boot device from DefaultBootPriority, starts the OS loader.",
      "The secure OS (OP-TEE) lives next to it in A_secure-os (4 MiB)."],
     "NVIDIA/edk2-nvidia (public source)", "fw"),
    ("boot", "L4TLauncher", "UEFI's default OS loader", "CCPLEX", "esp:\\EFI\\BOOT\\BOOTAA64.efi",
     ["Shipped default (L4TDefaultBootMode = 1): load the kernel, initrd and DTB named in",
      "/boot/extlinux/extlinux.conf on the root filesystem. Other modes read the kernel and",
      "DTB from the kernel / kernel-dtb partitions, or start GRUB."],
     "NVIDIA binary", "fw"),
    ("normal", "Linux 5.15.148-tegra", "kernel + initrd", "CCPLEX", "rootfs: /boot/Image · /boot/initrd",
     ["Gets the device tree and a command line with root=PARTUUID=… The initrd mounts the root",
      "filesystem on SD, NVMe or USB, and the kernel starts /sbin/init (systemd)."],
     "built by this repo", "normal"),
    ("rootfs", "Ubuntu 22.04 userland", "systemd → login", "CCPLEX", "APP partition (ext4)",
     ["NVIDIA's L4T libraries (CUDA-independent core, display, camera, multimedia) sit on top",
      "of the Ubuntu base. First boot ends at a login prompt for the user you created."],
     "assembled by this repo", "rootfs"),
]

y = 104
RH = 114
for i, (role, name, sub, runs, stored, lns, owner, orole) in enumerate(ROWS):
    strong, soft, fill, border = ROLE[role]
    h = 98 if len(lns) == 2 else RH - 10
    b.append(rect(32, y, 1000, h, fill=fill, stroke=border, rx=14, sw=1.6))
    b.append(rect(32, y, 210, h, fill=strong, rx=14))
    b.append(badge(32 + 22, y + 22, i + 1, strong if role != "hw" else "#94a3b8"))
    b.append(text(137, y + h / 2 - 2, name, size=16.5 if len(name) < 14 else 14.5, weight=800, anchor="middle", color="#fff"))
    b.append(text(137, y + h / 2 + 18, sub, size=11.5, anchor="middle", color="#e2e8f0"))
    b.append(chip(258, y + 10, "runs on  " + runs, role))
    b.append(text(258 + len("runs on  " + runs) * 6.9 + 36, y + 25, "stored: " + stored, size=11.5, color=soft, mono=True))
    b.append(lines(258, y + 54, lns, size=12.2, gap=18))
    # owner chip, right aligned
    ow = len(owner) * 6.6 + 24
    b.append(chip(1032 - ow - 12, y + h - 28, owner, orole, size=11))
    if i < len(ROWS) - 1:
        b.append(arrow(137, y + h + 1, 137, y + h + 14, A, "a", width=2.6))
    y += h + 14

# right panel: firmware for the other processors
px, py, pw = 1062, 104, 306
b.append(rect(px, py, pw, 630, fill="#2a1b05", stroke="#f59e0b", rx=14, sw=1.6))
b.append(rect(px, py, pw, 40, fill=ROLE["fw"][0], rx=14))
b.append(rect(px, py + 24, pw, 16, fill=ROLE["fw"][0]))
b.append(icon("cpu", px + 12, py + 9, 22, "#fff"))
b.append(text(px + 44, py + 26, "Firmware for the other cores", size=13.5, weight=800, color="#fff"))
b.append(text(px + 14, py + 62, "Also in QSPI-NOR, loaded during the", size=11.8, color=TEXT))
b.append(text(px + 14, py + 79, "chain above. Partition → what it is for:", size=11.8, color=TEXT))
FW = [("A_bpmp-fw", "BPMP: boot & power mgmt"), ("A_bpmp-fw-dtb", "BPMP device tree"), ("A_psc-fw", "PSC: platform security"),
      ("A_spe-fw", "SPE: sensor processing engine"), ("A_rce-fw", "RCE: camera real-time core"), ("A_dce-fw", "DCE: display engine"),
      ("A_adsp-fw", "ADSP/APE: audio"), ("A_pva-fw", "PVA: vision accelerator"), ("A_mts-mce", "MCE: CPU-side firmware"),
      ("A_tsec-fw", "TSEC"), ("A_nvdec", "NVDEC video decoder"), ("A_xusb-fw", "USB 3 controller"), ("A_sc7", "SC7 (suspend) resume")]
for j, (pn, what) in enumerate(FW):
    yy = py + 100 + j * 31
    b.append(rect(px + 12, yy - 15, pw - 24, 26, fill="#050a14", stroke="#334155", rx=7))
    b.append(text(px + 22, yy + 3, pn, size=11, mono=True, color="#fcd34d"))
    b.append(text(px + 138, yy + 3, what, size=11, color=TEXT))
b.append(text(px + 14, py + 520, "Every partition exists twice, A_ and B_: two", size=11.8, color=TEXT))
b.append(text(px + 14, py + 537, "complete boot chains for fail-safe updates.", size=11.8, color=TEXT))
b.append(text(px + 14, py + 566, "Layout: docs/06 and docs/images/storage-layout.svg", size=11, color=MUTED))
b.append(text(px + 14, py + 590, "Names and sizes come from", size=11, color=MUTED))
b.append(text(px + 14, py + 606, "bootloader/generic/cfg/flash_t234_qspi.xml", size=10.5, color=MUTED, mono=True))

# legend / caption
b.append(caption(H - 74, "BPMP = boot & power management processor · PSC = platform security controller · CCPLEX = the CPU complex (the Arm cores that run Linux) · BCT = boot configuration table."))
b.append(caption(H - 52, "Stages 1-5 are NVIDIA's binaries; 'built by this repo' means ./build.sh compiles it from NVIDIA's public sources. The eMMC-less Orin Nano has no storage of its own"))
b.append(caption(H - 30, "except the 64 MiB QSPI-NOR: the OS always lives on the SD card, NVMe or USB drive you attach (see docs/13-sd-card-vs-vendor-flash.md)."))
write("boot-chain.svg", W, H,
      "Boot chain of the Jetson Orin Nano: BootROM and PSC ROM in the SoC load MB1 on the BPMP; MB1 initializes memory and loads MB2 on the "
      "CPU complex; then UEFI with the OP-TEE secure OS; UEFI starts L4TLauncher from the EFI system partition, which loads the Linux "
      "kernel, initrd and device tree named in extlinux.conf; Linux starts the Ubuntu userland. Firmware for the other processors "
      "(BPMP, PSC, SPE, RCE, DCE, ADSP, PVA, MCE) is stored in the same QSPI-NOR flash.",
      "".join(b))
