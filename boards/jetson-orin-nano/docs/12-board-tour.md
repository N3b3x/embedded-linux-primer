# 12 · Board tour: module, carrier, "Super" and power modes

[Docs](README.md) › **12 · Board tour**

This is not a datasheet: for connectors, pin names and electrical limits use NVIDIA's *Jetson Orin Nano Developer Kit User Guide* and the
module datasheet. It is the tour of what the **software** knows about the kit, all of it checkable in the files you downloaded.

## 1. Two boards in one

| Part | Name | Role |
| --- | --- | --- |
| **Module** | Jetson Orin Nano (P3767) | the SoC, memory, QSPI-NOR boot flash and power circuitry on one small board. **No eMMC**: the OS must live on storage you attach to the carrier |
| **Carrier** | Developer Kit carrier (P3768) | connectors, the microSD slot, the M.2 slot(s), USB, networking, the 40-pin and 12-pin headers, camera connectors, the DisplayPort output |

That split is why the software has two device-tree layers (`tegra234-p3767-0000.dtsi` for the module,
`tegra234-p3768-0000.dtsi` for the carrier), two kinds of boot configuration (module BCTs vs the carrier's pinmux), and why NVIDIA's board
names are products of both: `p3768-0000-p3767-0000-a0.conf`.

## 2. The module variants the tools know

From `p3767.conf.common` (which device tree and BPMP tree each module SKU gets in the standard configuration) and the *Quick Start*:

| P3767 SKU | Product | `lsusb` ID | Standard DTB | Super DTB |
| --- | --- | --- | --- | --- |
| -0000 | Orin NX 16GB | `0955:7323` | `…p3767-0000-nv` | `…-0000-nv-super` |
| -0001 | Orin NX 8GB | `0955:7423` | `…-0001-nv` | `…-0001-nv-super` |
| -0003 | Orin Nano 8GB | `0955:7523` | `…-0003-nv` | `…-0003-nv-super` |
| -0004 | Orin Nano 4GB | `0955:7623` | `…-0004-nv` | `…-0004-nv-super` |
| **-0005** | **Orin Nano 8GB, developer kit module** | `0955:7523` | `…-0005-nv` | `…-0005-nv-super` |

(All DTB names start with `tegra234-p3768-0000+p3767-` and end with `.dtb`.) NVIDIA lists the development module (-0005) as sold only in the
developer kit; the others are production modules for other carriers.

## 3. What "Super" means in the files

In JetPack 6.2 NVIDIA added the *Super* configuration: a higher power budget and extra clock steps. In software that is concrete:

| Where | Standard | Super |
| --- | --- | --- |
| Board file | `jetson-orin-nano-devkit.conf` | `jetson-orin-nano-devkit-super.conf` (`p3767_super_overlay()`) |
| Kernel DTB | `…-nv.dtb` | `…-nv-super.dtb` |
| BPMP device tree | `tegra234-bpmp-3767-0003-3509-a02.dtb` (for -0005) | `tegra234-bpmp-3767-0003-3768-super.dtb` |
| CPU operating points | the table in `tegra234-p3767-0000.dtsi` contains `opp-1510400000 /* Max CPU freq for Orin Nano */` and `opp-1984000000 /* Max CPU freq for ONX */` | `…-nv-super.dts` does `/delete-node/ &{/opp-table-cluster0/opp-1510400000};` (and for clusters 1 and 2) |
| `nvpmodel` modes | the `nvpmodel_p3767_xxxx.conf` files | the `…_super.conf` files |

You can see it: `diff` the two `.dts` files of your module in `source/hardware/nvidia/t23x/nv-public/nv-platform/`.

## 4. Power modes: `nvpmodel`, `jetson_clocks`, `tegrastats`

`apply_binaries.sh` installs NVIDIA's `nvidia-l4t-nvpmodel` (modes) and `nvidia-l4t-tools` (`jetson_clocks`, `tegrastats`, `nv_fuse_read.sh`
and others).

```bash
sudo nvpmodel -q                  # current mode (name and ID)
sudo nvpmodel -m 1                # switch to mode ID 1 (the nvpmodel service applies the saved mode at boot)
sudo jetson_clocks                # pin clocks at their maximum for the current mode (benchmarking)
tegrastats                        # live CPU, GPU, memory, power and temperature
```

The mode tables are plain text in `/etc/nvpmodel/` on the board. In the R36.4.3 files for the 8GB Orin Nano (SKU 0003):

| Configuration | Mode IDs (name) | Default |
| --- | --- | --- |
| standard (`nvpmodel_p3767_0003.conf`) | 0 = `15W`, 1 = `7W` | 0 |
| Super (`nvpmodel_p3767_0003_super.conf`) | 0 = `15W`, 1 = `25W`, 2 = `MAXN_SUPER` | 1 (`25W`) |

For the NX 16GB in Super configuration the file lists `MAXN_SUPER`, `10W`, `15W`, `25W`. Check yours with
`cat /etc/nvpmodel.conf` and `sudo nvpmodel -q --verbose`. The `nvpmodel.service` unit applies the saved mode at boot.
Heat and the power supply matter in the higher modes: use the supply that came with the kit and a heatsink/fan.

## 5. Header pins, cameras, display

- **40-pin header** (I²C, SPI, UART, PWM, I²S): `sudo /opt/nvidia/jetson-io/jetson-io.py` (package `nvidia-l4t-jetson-io`) configures the
  pins by function or by pin, and writes a device-tree overlay.
- **Camera (CSI):** NVIDIA's camera stack (`nvidia-l4t-camera`, the `nvarguscamerasrc` GStreamer element) ships in the rootfs; the
  sensor drivers and overlays are under `nvidia-oot/` and `hardware/…/overlay/`. Sensor choice and overlays are covered by NVIDIA's *Camera Development* chapters.
- **Display:** the kit has a DisplayPort output; the NVIDIA display driver is one of the out-of-tree modules (`nvdisplay`).
- **Storage:** microSD slot, NVMe M.2 slot, USB ([07](07-flashing-and-booting.md)).
- **Debug UART / serial console:** the kernel console is `ttyTCU0` at 115200. Which physical pins carry it is in NVIDIA's User Guide.

## 6. Reading the hardware from the running system

```bash
cat /proc/device-tree/model
cat /sys/devices/soc0/*    2>/dev/null          # SoC family/revision as exposed by the kernel
ls /proc/device-tree/chosen
lsblk -o NAME,SIZE,TYPE,TRAN,MODEL
lsusb ; lspci
dmesg | grep -i -E "nvme|mmc|tegra|nvgpu|nvdisp"
sudo nvbootctrl dump-slots-info
```

Next: [13 · SD card vs vendor flash](13-sd-card-vs-vendor-flash.md) · Prev: [11 · Recovery mode](11-recovery-and-usb-flash.md)
