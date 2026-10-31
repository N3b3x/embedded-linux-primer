# 07 · Flashing the board and first boot

[Docs](README.md) › **07 · Flashing & first boot**

> **Status:** these steps follow NVIDIA's Quick Start and the R36.4.3 tool sources. They have **not yet been run on a
> board by the authors of this repository**. If a step differs from what you see, [09 · Troubleshooting](09-troubleshooting.md) lists the
> messages the tools print and what they mean.

## 1. Choose the root device

| `-d` | Storage | NVIDIA's command (Quick Start, Orin Nano Developer Kit) | Target name |
| --- | --- | --- | --- |
| `nvme` (default) | M.2 NVMe SSD in the carrier | `… --external-device nvme0n1p1 -c …flash_l4t_t234_nvme.xml -p "-c …flash_t234_qspi.xml" --network usb0 jetson-orin-nano-devkit internal` | `/dev/nvme0n1p1` |
| `sd` | microSD card, **64 GB or larger** | same with `--external-device mmcblk0p1` | `/dev/mmcblk0p1` |
| `usb` | USB drive, **64 GB or larger** | same with `--external-device sda1` | `/dev/sda1` |

For the Super configuration NVIDIA gives the same commands with `jetson-orin-nano-devkit-super` as the board name, which is what the
scripts use by default. `./build.sh info` prints the exact line for your setting. Only the chosen device is written: an NVMe drive
and an SD card can both be installed, but the boot order is set so the one you flashed is tried first
([01 §4](01-boot-flow.md)).

## 2. Put the board in Force Recovery Mode

NVIDIA's procedure for the Jetson Orin Nano Developer Kit:

1. **Disconnect the power cable**, so the kit is off.
2. Put a jumper on the **12-pin button header**, shorting the **REC** and **GND** pins.
3. Connect the kit's **USB-C port** to the PC.
4. **Reconnect the power cable.** Nothing needs to happen on the board: in recovery mode it waits for the host.
5. On the PC: `lsusb -d 0955:`. Expect one line such as

   ```text
   Bus 001 Device 014: ID 0955:7523 NVidia Corp.
   ```

   The four digits after `0955:` say which module you have: `7523` Orin Nano 8GB (P3767-0003 and -0005), `7623` Orin Nano 4GB,
   `7323` / `7423` Orin NX 16GB / 8GB. NVIDIA's tool uses the same list. `./build.sh flash --check` does this check for you.

Practical points: NVIDIA warns that a poor USB cable can make flashing fail, so use a data-capable, good-quality USB-C cable; prefer a
direct port over a hub; and make sure only **one** Jetson is in recovery mode (the tool refuses otherwise). NVIDIA's tool also installs two `udev` rules for the run (`99-l4t-host.rules`, `10-l4t-usb-msd.rules`): they keep NetworkManager
away from the board's USB Ethernet interface and hide its USB block devices from desktop auto-mounters, and it removes them again when it exits.

## 3. Flash

```bash
./build.sh flash
```

It prints the plan and asks:

```text
  Board configuration : jetson-orin-nano-devkit-super
  Root device         : nvme  (/dev/nvme0n1p1 on the board)
  Will overwrite      : the 64 MiB QSPI-NOR boot flash on the module
                        AND the whole nvme device attached to the board
  Package             : from ./build.sh image
Flash the Jetson now? [y/N]
```

Then NVIDIA's tool runs through the steps drawn in [11 · Recovery mode](11-recovery-and-usb-flash.md): build the flashing
environment, boot the recovery initrd over USB, start the flash, write. The console shows `Step 1`, `Step 2`, … banners; the full log is
also written to `build/work/Linux_for_Tegra/initrdlog/` and to `build/logs/flash-*.log`. It ends with `Success`, and the kit
reboots on its own.

If you did not run `./build.sh image` first, the flash command generates the package itself and flashes it in one go
(`flash --full` forces that).

## 4. After flashing

1. **Remove the jumper.** While it is fitted the board enters recovery mode on every power-up.
2. Power-cycle if the board did not reboot by itself.
3. **First boot.** With the account created by the scripts there is no setup wizard. Within a minute or so you reach a login
   (on the monitor, if one is attached on the DisplayPort output). Log in as `jetson` (password `jetson`, a bench default).
4. Find the board's address: `ip -4 addr` on the board, or look at your router's list. Then `ssh jetson@<address>`.

### What a healthy first login shows

```bash
uname -r                             # 5.15.148-tegra
cat /proc/device-tree/model          # NVIDIA Jetson Orin Nano … Super (the model string of the dts)
cat /proc/cmdline                    # root=PARTUUID=…
lsblk -o NAME,SIZE,PARTLABEL,MOUNTPOINT
sudo nvbootctrl dump-slots-info      # firmware slot info
sudo nvpmodel -q                     # power mode (Super: 25W by default, see 12)
```

If you applied the device-tree example from [04](04-kernel.md): `cat /proc/device-tree/primer,build`.

### If nothing appears on the monitor

- Check the DisplayPort cable and monitor input, and wait a minute.
- Press **ESC** at power-up when asked *Press ESCAPE for boot options*: UEFI's menu shows the boot devices it found
  (*Boot Manager*) and lets you pick the one you flashed.
- Use a serial console or SSH over Ethernet. For the debug serial port consult NVIDIA's Developer Kit User Guide; the kernel console is `ttyTCU0` at 115200.
- Without an account (if you removed that step), oem-config runs headless over the **USB-C port** as a serial device on the PC
  (`/dev/ttyACM0`): [05 §3](05-rootfs.md).

## 5. Flashing another device later

Changing `-d` and flashing again is enough. The flash overwrites the QSPI firmware with the same content and writes the new device. To put an
OS on a second drive without touching the first, you can also use NVIDIA's `--external-only` option (documented in the
Developer Guide's *Flashing to an External Storage Device*); this repository does not wrap it.

Next: [08 · Customizing](08-customizing.md) · Prev: [06 · Flash package](06-flash-package.md)
