# patches/

Put `*.patch` files (from `git format-patch` or `git diff`) in the subfolder of the component they change:

| Folder | Applied to | When |
| --- | --- | --- |
| `tf-a/` | `build/src/trusted-firmware-a` | `./build.sh firmware tfa` |
| `optee/` | `build/src/optee_os` | `./build.sh firmware optee` |
| `u-boot/` | `build/src/u-boot` | `./build.sh firmware uboot` |
| `kernel/` | `build/src/linux-<version>` | `./build.sh kernel` |

They are applied in file-name order, once per checkout (the names are remembered inside the checkout).
See `docs/08-customizing.md`.

With `./build.sh -s st` the same folders are `patches/st/tf-a/`, `patches/st/optee/`, `patches/st/u-boot/` and
`patches/st/kernel/`, applied to ST's checkouts in `build/src-st/` (the two host-tool fixes for U-Boot on a very new
host, [docs/09](../docs/09-troubleshooting.md), go in `patches/st/u-boot/`). Patches for one stack are never applied to
the other.
