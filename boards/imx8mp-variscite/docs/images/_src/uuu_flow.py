"""docs/images/uuu-flow.svg - ./build.sh uuu emmc, step by step between the PC, the ROM, the SPL and U-Boot (generated)."""
from kit import *

W, H = 1400, 1330
USB, FB, WR, GO = "#5eead4", "#93c5fd", "#fcd34d", "#e5edf7"
LX = {"host": 170, "rom": 440, "spl": 710, "uboot": 980, "emmc": 1250}   # lane centres
LW = 232

b = [marker_defs({"usb": USB, "fb": FB, "wr": WR, "go": GO})]
b.append(title("./build.sh uuu emmc, step by step",
               "The PC talks to the Boot ROM, then to the SPL, then to U-Boot's fastboot gadget, which does the eMMC writes. Time runs downward."))


def lane(key, name, sub, role, ic, filled=False):
    cx = LX[key]
    strong, soft, fill, border = ROLE[role]
    out = rect(cx - LW / 2, 96, LW, 62, fill=strong, stroke=border, rx=14, sw=2)
    out += icon(ic, cx - LW / 2 + 14, 112, 30, "#ffffff", filled=filled)
    out += text(cx - LW / 2 + 54, 124, name, size=15.5, weight=800, color="#ffffff")
    out += text(cx - LW / 2 + 54, 144, sub, size=12, color="#e2e8f0")
    out += '<line x1="%d" y1="160" x2="%d" y2="%d" stroke="%s" stroke-width="2" stroke-dasharray="2 7" stroke-linecap="round"/>' % (
        cx, cx, H - 24, border)
    return out


b.append(lane("host", "PC · uuu", "build/deploy/uuu-emmc.uuu", "normal", "terminal"))
b.append(lane("rom", "Boot ROM", "mask ROM · USB 1fc9:0146", "hw", "microchip"))
b.append(lane("spl", "U-Boot SPL", "on-chip RAM · EL3", "boot", "cpu"))
b.append(lane("uboot", "U-Boot", "DDR · fastboot 1fc9:0152", "boot", "rocket"))
b.append(lane("emmc", "On-module eMMC", "mmc 2 · mmcblk2", "hw", "database"))


def note(cx, y, w, rows, role, ic=None, h=None):
    strong, soft, fill, border = ROLE[role]
    h = h or 18 + 18 * len(rows)
    out = rect(cx - w / 2, y, w, h, fill=PANEL, stroke=border, rx=10, sw=1.5)
    tx = cx - w / 2 + 14
    if ic:
        out += icon(ic, tx, y + h / 2 - 11, 22, soft)
        tx += 32
    for i, ln in enumerate(rows):
        out += text(tx, y + 23 + 18 * i, ln, size=12.5, color=TEXT if i == 0 else MUTED, weight=600 if i == 0 else 400)
    return out


def msg(frm, to, y, label, kind, n, dx=0):
    color = {"usb": USB, "fb": FB, "wr": WR, "go": GO}[kind]
    x1, x2 = LX[frm], LX[to]
    d = 1 if x2 > x1 else -1
    out = arrow(x1 + d * 14, y, x2 - d * 10, y, color, kind)
    out += pill((x1 + x2) / 2 + dx, y - 18, label, color, size=11.5)
    out += badge(x1 + d * 14, y, n, color)
    return out


def section(y, h, label, role):
    strong, soft, fill, border = ROLE[role]
    return (rect(40, y, 1320, h, fill="none", stroke=soft, rx=14, sw=1.4, dash="8 6")
            + rect(56, y - 13, len(label) * 7.4 + 24, 26, fill=BG, stroke=soft, rx=13, sw=1.4)
            + text(68, y + 5, label, size=12.5, weight=800, color=soft))


# ---- A: ROM -> SPL -> U-Boot over USB ----------------------------------------------
b.append(section(190, 480, "A · SERIAL DOWNLOAD: THE BOOT ROM TAKES THE BOOT IMAGE FROM THE PC", "normal"))
b.append(note(LX["host"], 214, 226, ["./build.sh uuu emmc", "checks lsusb for 1fc9:0146"], "normal", "terminal"))
b.append(note(LX["rom"], 214, 244, ["boot switch = SD, no card", "ROM falls back to USB"], "boot", "power"))
b.append(msg("host", "rom", 336, "SDPS: boot -f imx-boot.bin", "usb", 1))
b.append(msg("rom", "spl", 398, "starts the SPL", "go", 2))
b.append(note(LX["spl"], 416, 236, ["SPL trains the LPDDR4", "then asks the ROM for more"], "boot", "memory-stick"))
b.append(msg("host", "spl", 512, "rest of imx-boot.bin: DDR firmware, BL31, U-Boot", "usb", 3))
b.append(msg("spl", "uboot", 584, "BL31 + U-Boot start", "go", 4))
b.append(note(LX["uboot"], 600, 250, ["prints: Boot from USB for", "mfgtools, then runs fastboot 0"], "boot", "scroll-text"))
b.append(note(LX["host"], 596, 226, ["uuu waits up to 120 s", "for the next USB device"], "normal", "clock"))

# ---- B: fastboot ----------------------------------------------------------------------
b.append(section(710, 490, "B · U-BOOT'S FASTBOOT: THE PC DRIVES, U-BOOT WRITES THE eMMC", "boot"))
b.append(msg("host", "uboot", 786, "FB: ucmd setenv fastboot_dev mmc ; mmc dev ${emmc_dev}", "fb", 5))
b.append(msg("host", "uboot", 862, "FB: flash -raw2sparse -bmap all sdcard.img", "fb", 6))
b.append(msg("uboot", "emmc", 906, "user area: MBR · 32 KiB copy · p1", "wr", 7))
b.append(note(LX["host"], 884, 226, ["only blocks with data go", "over USB (the .bmap)"], "normal", "package"))
b.append(msg("host", "uboot", 982, "FB: download -f imx-boot.bin", "fb", 8))
b.append(msg("uboot", "emmc", 1026, "mmc write → boot0 and boot1, offset 0", "wr", 9))
b.append(msg("uboot", "emmc", 1090, "mmc partconf 2 1 1 0", "wr", 10))
b.append(note(LX["emmc"] - 6, 1104, 212, ["EXT_CSD boot config", "= boot0, boot ack on"], "hw", "settings-2"))
b.append(msg("host", "uboot", 1178, "FB: done", "fb", 11))

# ---- outro ---------------------------------------------------------------------------
b.append(rect(40, 1272, 1320, 44, fill=PANEL, stroke=ROLE["secure"][3], rx=12, sw=1.5))
b.append(icon("power", 58, 1283, 22, ROLE["secure"][1]))
b.append(text(92, 1300, "Now you: power off, boot switch → eMMC, power on. The ROM reads boot0 at offset 0, the SPL starts, U-Boot mounts /dev/mmcblk2p1.",
              size=13, weight=700, color=TEXT))

# legend
lx = 40
legend = [("usb", USB, "USB stream to the ROM / SPL"), ("fb", FB, "fastboot command from the PC"),
          ("wr", WR, "U-Boot writes the eMMC"), ("go", GO, "software starts the next stage")]
for i, (k, c, t) in enumerate(legend):
    x = 40 + i * 330
    b.append(arrow(x, 1236, x + 40, 1236, c, k, width=3))
    b.append(text(x + 52, 1240, t, size=12, color=TEXT))

write("uuu-flow.svg", W, H,
      "Sequence of ./build.sh uuu emmc between the PC running uuu, the Boot ROM, the U-Boot SPL, U-Boot and the on-module eMMC. "
      "With the boot switch on SD and no card, the ROM falls back to USB serial download (1fc9:0146). uuu streams imx-boot.bin to it "
      "with SDPS. The ROM starts the SPL, which trains the LPDDR4 and asks for the rest of the image: DDR firmware, TF-A BL31 and U-Boot. "
      "U-Boot sees it was started from USB and runs fastboot (1fc9:0152). The PC then sends fastboot commands: it selects mmc 2, writes "
      "the SD-card image to the eMMC user area, downloads imx-boot.bin and has U-Boot write it to boot0 and boot1 at offset 0, and sets "
      "the eMMC boot configuration to boot0 with mmc partconf. After the script the user powers off, sets the boot switch to eMMC and boots.",
      "".join(b))
