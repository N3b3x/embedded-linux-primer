---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# Embedded Linux Primer

<p class="tagline">Build the whole software stack of an embedded Linux board from source, one small, readable board directory at a time. No Yocto. Every command explained.</p>

[Start with the concepts](docs/01-what-is-an-embedded-linux-board.md){ .md-button .md-button--primary }
[Pick a board](docs/04-choosing-a-board.md){ .md-button }
[Source on GitHub](https://github.com/N3b3x/embedded-linux-primer){ .md-button }

<div class="chips">
<span class="chip boot">U-Boot</span>
<span class="chip secure">TF-A · OP-TEE</span>
<span class="chip normal">Linux 6.18 LTS</span>
<span class="chip rootfs">Debian · Alpine</span>
<span class="chip fw">pinned · checksummed · reproducible</span>
</div>

</div>

![The six layers of every embedded Linux board](docs/images/embedded-linux-stack.svg)

## Choose a board

<div class="grid cards" markdown>

- :material-chip:{ .lg .middle } **NXP i.MX 8M Plus**

    ---

    Variscite DART, VAR-SOM and SMARC modules. SD-card image, or USB with `uuu` into the eMMC.
    The reference board: the most complete documentation, verified on hardware.

    [:octicons-arrow-right-24: Open the board](boards/imx8mp-variscite/index.md)

- :material-chip:{ .lg .middle } **STM32MP2 (STM32MP257F-DK)**

    ---

    64-bit. All-upstream stack or ST's own tested set. Shows the secure-world boot chain,
    SCMI and a GPT SD image.

    [:octicons-arrow-right-24: Open the board](boards/stm32mp2-dk/index.md)

- :material-chip:{ .lg .middle } **STM32MP1 (STM32MP157F-DK2)**

    ---

    The 32-bit sibling. Read it next to the MP2 to see which parts of a boot chain are the SoC and
    which are the family.

    [:octicons-arrow-right-24: Open the board](boards/stm32mp1-dk2/index.md)

- :material-chip:{ .lg .middle } **Zynq-7000 (Eclypse Z7)**

    ---

    U-Boot's SPL as the first loader, `BOOT.BIN`, and an FPGA beside the CPU. No secure world.
    Zmod add-ons come after the first boot.

    [:octicons-arrow-right-24: Open the board](boards/zynq7000-eclypse-z7/index.md)

- :material-chip:{ .lg .middle } **NVIDIA Jetson Orin Nano**

    ---

    Developer Kit with NVIDIA's Jetson Linux. The other flashing model: boot
    firmware in QSPI, flashed over USB recovery mode.

    [:octicons-arrow-right-24: Open the board](boards/jetson-orin-nano/index.md)

- :material-download:{ .lg .middle } **Ready-built images**

    ---

    Download an SD-card image and flash it from Windows, macOS or Linux, without building anything.

    [:octicons-arrow-right-24: Download and flash](docs/downloads.md)

</div>

## How to read this site

<div class="grid cards" markdown>

- :material-layers-triple:{ .lg .middle } **Concepts first**

    ---

    Six layers, two build models, three boot chains: the vocabulary that makes every board
    directory readable.

    [:octicons-arrow-right-24: Reading order](docs/index.md)

- :material-console:{ .lg .middle } **Same commands everywhere**

    ---

    `deps`, `info`, `all`, `flash`, and `--dry-run` to read the whole recipe without running it.

    [:octicons-arrow-right-24: The board contract](docs/board-contract.md)

- :material-stairs:{ .lg .middle } **Where does my change go?**

    ---

    Nine rungs from "run my app" to "burn the fuses", with the cost of each mistake.

    [:octicons-arrow-right-24: The customization ladder](docs/01-what-is-an-embedded-linux-board.md#which-layers-will-you-touch)

</div>

## Explore the diagrams

Every diagram opens in a viewer you can zoom, pan and step through. The ones marked
**walkthrough** dim everything except the part being explained.

<div class="dv-featured" data-limit="6"></div>

[Browse all diagrams](diagrams/index.md){ .md-button .md-button--primary }

## Two ways software reaches a board

![Two ways software reaches a board](docs/images/build-models.svg)
