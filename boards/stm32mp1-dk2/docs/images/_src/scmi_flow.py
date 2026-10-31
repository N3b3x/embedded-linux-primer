"""docs/images/scmi-flow.svg - how Linux switches on the SD card's supply on this SoC (generated)."""
from kit import *

W, H = 1400, 960
A = "#e5edf7"
b = [marker_defs({"t": "#5eead4", "r": "#fb7185", "a": A, "g": "#94a3b8"})]
b.append(title("Linux wants the SD card's supply on: the trip through the secure world",
               "On this board the secure world owns the clock tree and the power chip. Linux asks OP-TEE over SCMI, which is why the SD card works with the stock device tree."))

# lanes
LANES = [
    ("mmci driver", "Linux · non-secure SVC", "normal", "microchip", 130),
    ("scmi-regulator", "Linux regulator core", "normal", "cog", 360),
    ("arm_scmi · optee", "Linux transport", "normal", "network", 590),
    ("OP-TEE monitor", "smc handler · monitor mode", "secure", "shield-check", 820),
    ("OP-TEE SCMI server", "secure SVC", "secure", "lock", 1050),
    ("STPMIC1", "power chip on I2C4", "hw", "zap", 1280),
]
LW = 200
for (n, sub, role, ic, cx) in LANES:
    b.append(card(cx - LW / 2, 100, LW, 56, n, role, ic, head=34))
    b.append(text(cx, 148, sub, size=11, color=MUTED, anchor="middle"))
    strong = ROLE[role][3]
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.6" stroke-dasharray="3 6"/>' % (cx, 162, cx, 770, strong))
X = {i: LANES[i][4] for i in range(len(LANES))}

def msg(i, j, y, label, color="#5eead4", m="t", sub=None, dash=None):
    out = arrow(X[i] + (6 if j > i else -6), y, X[j] - (6 if j > i else -6), y, color, m, width=2.8, dash=dash)
    mid = (X[i] + X[j]) / 2
    out += text(mid, y - 10, label, size=11.5, weight=700, color=color, anchor="middle")
    if sub:
        out += text(mid, y + 17, sub, size=10.5, color=MUTED, anchor="middle")
    return out

def selfnote(i, y, s1, s2=None, color="#5eead4", w=212):
    h = 44 if s2 else 28
    out = rect(X[i] - w / 2, y - 18, w, h, fill="#0b1729", stroke=color, rx=8, sw=1.2)
    out += text(X[i], y + 1, s1, size=10.5, weight=700, color=color, anchor="middle")
    if s2:
        out += text(X[i], y + 18, s2, size=10, color=MUTED, anchor="middle")
    return out

y = 200
STEP = 54
b.append(badge(40, y, 1, "#5eead4"))
b.append(msg(0, 1, y, "regulator_get / regulator_enable(vmmc)", sub="mmci_probe() needs the card's supply"))
y += STEP + 8
b.append(badge(40, y, 2, "#5eead4"))
b.append(selfnote(1, y, "vmmc-supply = <&scmi_v3v3>", "an SCMI voltage domain", w=214))
y += STEP
b.append(badge(40, y, 3, "#5eead4"))
b.append(msg(1, 2, y, "voltage domain enable", sub="protocol 0x17, VOLTD_SCMI_STPMIC1_BUCK4"))
y += STEP
b.append(badge(40, y, 4, "#5eead4"))
b.append(selfnote(2, y, "SCMI message in shared memory", "PTA-SCMI cmd 1: PROCESS_SMT_CHANNEL", w=214))
y += STEP
b.append(badge(40, y, 5, "#5eead4"))
b.append(msg(2, 3, y, "smc  OPTEE_SMC_CALL_WITH_ARG", sub="the monitor switches to the secure world"))
y += STEP
b.append(badge(40, y, 6, "#fb7185"))
b.append(selfnote(3, y, "sm_smc_entry", "save NS context, run the thread", color="#fb7185", w=200))
y += STEP + 8
b.append(badge(40, y, 7, "#fb7185"))
b.append(msg(3, 4, y, "pta/scmi.c → scmi_server", color="#fb7185", m="r", sub="table row \"buck4\" = v3v3"))
y += STEP
b.append(badge(40, y, 8, "#fb7185"))
b.append(msg(4, 5, y, "set the buck4 rail on", color="#fb7185", m="r", sub="secure driver on I2C4"))
y += 50
b.append(msg(4, 3, y, "status in the shared buffer", color="#fb7185", m="r", dash="6 4"))
y += 36
b.append(msg(3, 2, y, "smc returns to the normal world", color="#fb7185", m="r", dash="6 4"))
y += 36
b.append(msg(2, 1, y, "returns 0", dash="6 4"))
y += 36
b.append(msg(1, 0, y, "supply on; the probe goes on", dash="6 4"))

# explanation panels
py = 790
b.append(rect(40, py, 640, 130, fill=PANEL, stroke=LINE, rx=10))
b.append(text(56, py + 24, "Why does a regulator need a round trip?", size=13, weight=800))
b.append(lines(56, py + 46, [
    "The power chip (STPMIC1) is on I2C4, which the kernel's tree disables: \"I2C4 is managed",
    "by OP-TEE\". Every rail Linux uses is an SCMI voltage domain whose id OP-TEE maps to a",
    "rail name in plat-stm32mp1/scmi_server.c. OP-TEE's STM32MP15 server serves voltage domains;",
    "its STM32MP25 server does not, which is the 64-bit board's SD-card problem.",
], size=11.5, gap=18))
b.append(code(700, py, 660, [
    ("firmware {", "#cbd5e1"),
    ("    optee { compatible = \"linaro,optee-tz\"; method = \"smc\"; };", "#fcd34d"),
    ("    scmi { compatible = \"linaro,scmi-optee\";", "#fcd34d"),
    ("        scmi_clk:   protocol@14 { … };   /* clocks   */", "#5eead4"),
    ("        scmi_reset: protocol@16 { … };   /* resets   */", "#5eead4"),
    ("        scmi_voltd: protocol@17 { … };   /* voltage domains */", "#5eead4"),
], size=10.5, gap=16, title_s="arch/arm/boot/dts/st/stm32mp15-scmi.dtsi (abridged)"))
b.append(caption(H - 14, "Sequence from stm32mp157f-dk2-scmi.dtsi (&sdmmc1), drivers/regulator/scmi-regulator.c, drivers/firmware/arm_scmi/transports/optee.c, core/pta/scmi.c and plat-stm32mp1/scmi_server.c."))
write("scmi-flow.svg", W, H,
      "Sequence of a regulator request: the mmci driver asks for the SD card's supply; the SCMI regulator driver sends a voltage-domain message for "
      "VOLTD_SCMI_STPMIC1_BUCK4; the arm_scmi OP-TEE transport issues an smc with the PTA-SCMI process-channel command; the OP-TEE monitor enters the secure "
      "world; OP-TEE's SCMI server looks the domain up and drives the STPMIC1 power chip over I2C4; the status returns through the monitor and the shared "
      "buffer to Linux.",
      "".join(b))
