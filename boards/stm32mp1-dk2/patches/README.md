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
