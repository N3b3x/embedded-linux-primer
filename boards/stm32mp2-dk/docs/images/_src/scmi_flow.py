"""docs/images/scmi-flow.svg - how Linux turns on a clock on this SoC (generated)."""
from kit import *

W, H = 1400, 1000
A = "#e5edf7"
b = [marker_defs({"t": "#5eead4", "r": "#fb7185", "a": A, "g": "#94a3b8"})]
b.append(title("Linux wants the SD card clock on: the trip through the secure world",
               "On this SoC the secure world owns the root and bus clocks. Linux's RCC driver builds gates and dividers on top of them, and asks OP-TEE over SCMI."))

# lanes
LANES = [
    ("mmci driver", "Linux · EL1", "normal", "microchip", 130),
    ("clk-stm32mp25", "Linux RCC driver · EL1", "normal", "cog", 360),
    ("clk-scmi · arm_scmi", "Linux · EL1", "normal", "network", 590),
    ("TF-A BL31", "monitor · EL3", "secure", "shield-check", 820),
    ("OP-TEE core", "SCMI server · S-EL1", "secure", "lock", 1050),
    ("RCC", "clock hardware", "hw", "clock", 1280),
]
LW = 200
for (n, sub, role, ic, cx) in LANES:
    b.append(card(cx - LW / 2, 100, LW, 56, n, role, ic, head=34))
    b.append(text(cx, 148, sub, size=11, color=MUTED, anchor="middle"))
    strong = ROLE[role][3]
    b.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.6" stroke-dasharray="3 6"/>' % (cx, 162, cx, 800, strong))
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
STEP = 62
b.append(badge(40, y, 1, "#5eead4"))
b.append(msg(0, 1, y, "clk_prepare_enable(ck_ker_sdmmc1)", sub="mmci_probe() needs its kernel clock"))
y += STEP + 8
b.append(badge(40, y, 2, "#5eead4"))
b.append(selfnote(1, y, "the gate's parent is flexgen_51", "an SCMI clock: enable the parent first"))
y += STEP
b.append(badge(40, y, 3, "#5eead4"))
b.append(msg(1, 2, y, "clk_enable(parent)", sub="scmi_clk_enable()"))
y += STEP
b.append(badge(40, y, 4, "#5eead4"))
b.append(selfnote(2, y, "SCMI clock protocol 0x14", "CLOCK_CONFIG_SET (0x7): enable", w=214))
y += STEP
b.append(badge(40, y, 5, "#5eead4"))
b.append(msg(2, 3, y, "smc  OPTEE_SMC_CALL_WITH_ARG", sub="PTA-SCMI cmd 1: PROCESS_SMT_CHANNEL"))
y += STEP
b.append(badge(40, y, 6, "#fb7185"))
b.append(msg(3, 4, y, "opteed_smc_handler → ERET", color="#fb7185", m="r", sub="save normal-world context, enter S-EL1"))
y += STEP + 8
b.append(badge(40, y, 7, "#fb7185"))
b.append(selfnote(4, y, "pta/scmi.c → scmi_server", "scmi_clock → optee_clock", color="#fb7185", w=200))
y += STEP
b.append(badge(40, y, 8, "#fb7185"))
b.append(msg(4, 5, y, "enable the flexgen output", color="#fb7185", m="r", sub="secure-world access to RCC"))
y += 50
b.append(msg(4, 3, y, "status in the shared buffer; smc return", color="#fb7185", m="r", dash="6 4"))
y += 36
b.append(msg(3, 2, y, "return to NS-EL1", color="#fb7185", m="r", dash="6 4"))
y += 36
b.append(msg(2, 1, y, "returns 0", dash="6 4"))
y += 36
b.append(msg(1, 0, y, "gate bit set; probe goes on", dash="6 4"))

# explanation panels
py = 830
b.append(rect(40, py, 640, 120, fill=PANEL, stroke=LINE, rx=10))
b.append(text(56, py + 24, "Why does a clock need a round trip?", size=13, weight=800))
b.append(lines(56, py + 46, [
    "The roots of the clock tree (HSE, HSI, the ICN bus clocks, the FLEXGEN outputs) are owned by",
    "OP-TEE. The rcc node in the kernel device tree lists them as inputs coming from scmi_clk;",
    "Linux only manages the gates and dividers below them (drivers/clk/stm32/clk-stm32mp25.c).",
    "SCMI = Arm's System Control and Management Interface: a message protocol, here over smc.",
], size=11.5, gap=18))
b.append(code(700, py, 660, [
    ("firmware {", "#cbd5e1"),
    ("    optee { compatible = \"linaro,optee-tz\"; method = \"smc\"; };", "#fcd34d"),
    ("    scmi { compatible = \"linaro,scmi-optee\";", "#fcd34d"),
    ("        scmi_clk:   protocol@14 { … };   /* clocks   */", "#5eead4"),
    ("        scmi_reset: protocol@16 { … };   /* resets   */", "#5eead4"),
    ("        scmi_voltd: protocol@17 { … };   /* voltage domains (see docs/09) */", "#5eead4"),
], size=10.5, gap=16, title_s="arch/arm64/boot/dts/st/stm32mp251.dtsi (abridged)"))
b.append(caption(H - 14, "Sequence from drivers/clk/stm32/clk-stm32mp25.c (ck_ker_sdmmc1, parent FLEXGEN_51), drivers/clk/clk-scmi.c, drivers/firmware/arm_scmi/transports/optee.c, core/pta/scmi.c and scmi_server.c."))
write("scmi-flow.svg", W, H,
      "Sequence of a clock request: the mmci driver calls clk_prepare_enable; the STM32MP25 RCC driver enables the gate and its SCMI parent; clk-scmi builds an SCMI clock config message; the arm_scmi OP-TEE "
      "transport issues an smc with the PTA-SCMI process-channel command; TF-A BL31 forwards it to OP-TEE at S-EL1; OP-TEE's SCMI server writes "
      "the RCC registers; the status returns through BL31 and the shared buffer to Linux.",
      "".join(b))
