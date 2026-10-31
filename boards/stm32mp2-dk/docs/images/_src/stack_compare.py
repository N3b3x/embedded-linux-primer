"""docs/images/stack-compare.svg - the mainline stack next to ST's stack (generated)."""
from kit import *

W, H = 1400, 944
A = "#e5edf7"
b = [marker_defs({"a": A})]
b.append(title("Two software stacks for one board",
               "STACK=mainline builds every project from upstream; STACK=st builds ST's own branches of the same projects, plus ST's device trees."))

LX, LW = 40, 460          # left card
MX, MW = 520, 360         # middle: why they differ
RX, RW = 900, 460         # right card
y0 = 112
b.append(text(LX, y0, "STACK=mainline  (the default)", size=15, weight=800, color="#5eead4"))
b.append(text(MX, y0, "WHAT DIFFERS, AND WHY IT MATTERS", size=11.5, weight=800, color=FAINT, extra=' letter-spacing="1.2"'))
b.append(text(RX, y0, "STACK=st  (ST's set: the control)", size=15, weight=800, color="#fcd34d"))
b.append(rect(LX, y0 + 10, LW, 2, fill="#14b8a6", rx=1))
b.append(rect(MX, y0 + 10, MW, 2, fill=LINE, rx=1))
b.append(rect(RX, y0 + 10, RW, 2, fill="#f59e0b", rx=1))

ROWS = [
    # role, left (title, sub, lines), middle (heading, lines), right (title, sub, lines)
    ("secure",
     ("TF-A v2.15.0", "upstream", [
         "review.trustedfirmware.org, commit da738d5e",
         "board tree: TF-A's own fdts/stm32mp257f-dk",
         "PSA_FWU_SUPPORT=0, LOG_LEVEL=20"]),
     ("Different firmware, different board tree", [
         "BL2 and BL31 are described by ST's tree in",
         "one stack and by TF-A's own copy in the",
         "other: clocks, DDR, firewalls (RIF)."]),
     ("TF-A v2.10-stm32mp-r3", "ST", [
         "github.com/STMicroelectronics, commit 41575b25",
         "board tree: dt-stm32mp ...-ca35tdcid-ostl",
         "PSA_FWU_SUPPORT=1, DEBUG=1, LOG_LEVEL=40"])),
    ("secure",
     ("OP-TEE 4.11.0", "upstream + SCP-firmware", [
         "SCMI server: clocks and resets only",
         "no PMIC driver, no voltage domains",
         "no regulator for the SD card to ask for"]),
     ("The SD card's supply comes from OP-TEE", [
         "Linux asks OP-TEE for vdd_sdcard over SCMI.",
         "Only ST's OP-TEE answers; with 4.11 the",
         "mainline stack needs a workaround tree."]),
     ("OP-TEE 4.0.0-stm32mp-r3", "ST", [
         "own SCMI server: clocks, resets, voltage",
         "domains and regulators (PMIC on I2C7)",
         "CFG_STM32MP_PROFILE=secure_and_system_services"])),
    ("boot",
     ("U-Boot v2026.07", "upstream", [
         "distro boot reads /boot/extlinux/extlinux.conf",
         "board tree: the copy of Linux's DT it carries",
         "environment in partition u-boot-env"]),
     ("Same boot method in both", [
         "Both read extlinux.conf from the bootable",
         "partition, so one image recipe serves both:",
         "root=PARTUUID, earlycon, console=ttySTM0."]),
     ("U-Boot v2023.10-stm32mp-r3", "ST", [
         "distro boot reads /boot/extlinux/extlinux.conf",
         "board tree: ST's ostl tree (EXT_DTS)",
         "environment in partition u-boot-env"])),
    ("normal",
     ("Linux 6.18.58", "kernel.org tarball", [
         "defconfig + config/kernel/*.cfg",
         "DTB: stm32mp257f-dk-primer (fixed 3.3 V",
         "SD supplies), the stock DTB as 2nd entry"]),
     ("Same board, two kernel trees", [
         "The 6.18 tree describes the SD supply as an",
         "SCMI regulator that OP-TEE 4.11 lacks. ST's",
         "tree and ST's OP-TEE were made together."]),
     ("Linux 6.6 (ST tree)", "git tag v6.6-stm32mp-r3", [
         "defconfig + ST fragments 01 to 04",
         "DTB: stm32mp257f-dk-ca35tdcid-ostl (SCMI",
         "regulators), etnaviv blacklisted"])),
    ("rootfs",
     ("Device trees: 4 copies", "one per project", [
         "TF-A, OP-TEE, U-Boot and Linux each carry",
         "their own DK description",
         "custom/dts holds the one workaround"]),
     ("One description, or four", [
         "ST keeps all four in one repository, so",
         "firmware and kernel agree by construction.",
         "Upstream keeps them apart and hopes."]),
     ("Device trees: 1 repository", "dt-stm32mp, commit 6e8d9fa1", [
         "stm32mp2/a35-td/{tf-a,optee,u-boot,linux}",
         "read by all four builds",
         "nothing to patch"])),
    ("fw",
     ("SD card: 5 partitions", "fsbla1 at 1 MiB", [
         "fsbla1, fsbla2, fip, u-boot-env, rootfs",
         "BL2 finds the FIP by its partition type",
         "no FWU metadata"]),
     ("BL2 looks for its FIP differently", [
         "With firmware-update support BL2 first reads",
         "a metadata record that names the active FIP",
         "partition; without it BL2 looks for the type."]),
     ("SD card: 8 partitions", "fsbla1 at 17 KiB", [
         "fsbla1, fsbla2, metadata1/2, fip-a/b,",
         "u-boot-env, rootfs: ST's own layout",
         "metadata.bin names fip-a (PARTUUID 4fd84c93)"])),
]
RH, RP = 100, 112
for i, (role, L, M, R) in enumerate(ROWS):
    y = 134 + i * RP
    for (x, w, d) in ((LX, LW, L), (RX, RW, R)):
        t, sub, rows = d
        b.append(card(x, y, w, RH, t, role, None, sub=sub, head=34))
        b.append(lines(x + 14, y + 56, rows, size=12, gap=17, color=TEXT))
    # middle: heading + three lines
    b.append(text(MX, y + 28, M[0], size=13, weight=800, color=TEXT))
    b.append(lines(MX, y + 52, M[1], size=11.8, gap=17, color=MUTED))

yb = 134 + 6 * RP + 6
b.append(rect(LX, yb, 1320, 74, fill=PANEL, stroke=LINE, rx=10))
b.append(text(LX + 18, yb + 26, "How to use the two", size=13.5, weight=800))
b.append(text(LX + 18, yb + 48, "Boot STACK=st first, or whenever the mainline image is silent. If it reaches a login, the board, the switches, the card and the serial cable are fine, "
             "and the fault is in the mainline stack.", size=12.5, color=TEXT))
b.append(text(LX + 18, yb + 66, "If both are silent, the fault is shared: check the boot switches, the serial port and the supply before you change any software (docs/14-first-boot-checklist.md).",
             size=12.5, color=MUTED))
b.append(caption(H - 34, "Versions, commits and flags: config/stm32mp257f-dk.conf (mainline) and config/stack-st.conf (ST). Neither stack has been booted on a physical board by the authors."))
b.append(caption(H - 14, "ST's set is the combination a bench-proven configuration booted on this kit. Chapter docs/15-two-stacks.md has the table behind this picture."))
write("stack-compare.svg", W, H,
      "The two software stacks of the STM32MP257F-DK board side by side: STACK=mainline builds TF-A 2.15, OP-TEE 4.11, U-Boot 2026.07 and Linux 6.18 from the upstream projects "
      "with a workaround device tree for the SD card supply and a five-partition SD layout; STACK=st builds ST's TF-A 2.10, OP-TEE 4.0, U-Boot 2023.10 and Linux 6.6 with ST's "
      "device trees, whose SCMI regulators ST's OP-TEE serves, and ST's eight-partition SD layout with firmware-update metadata.",
      "".join(b))
