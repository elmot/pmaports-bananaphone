# Nokia 8110 4G (`nokia-argon`) Nura OS Development Guide

This guide covers maintaining this custom `pmaports` fork for HMDs 'Nokia 8110 4G' mobile phone, building Nura OS (`v26.06`) images with `pmbootstrap`, deploying kernel/DTS changes, and packaging custom applications (including Slint + Python apps under the `cage` Wayland UI).

---

## 1. Repository & Package Layout

In postmarketOS / Nura OS `pmaports`, **device packages** and **kernel packages** are separate:

- **Shared kernel package (`linux-postmarketos-qcom-msm8916`)**: [`pmaports-bananaphone/device/testing/linux-postmarketos-qcom-msm8916/APKBUILD`](pmaports-bananaphone/device/testing/linux-postmarketos-qcom-msm8916/APKBUILD)
  - Shared across Qualcomm MSM8909 / MSM8916 / MSM8939 devices (`pkgver=6.12.1`).
  - Kernel and Device Tree (`.dts` / `.dtsi`) patches belong here because `.dtb` files are compiled from the kernel tree during `make dtbs_install`.
- **Device package (`device-nokia-argon`)**: [`pmaports-bananaphone/device/testing/device-nokia-argon/APKBUILD`](pmaports-bananaphone/device/testing/device-nokia-argon/APKBUILD)
  - Holds board metadata (`deviceinfo`, `kernel-cmdline.conf`, `modules-initfs`, panel init sequence) and depends on `linux-postmarketos-qcom-msm8916`.
  - [`deviceinfo`](pmaports-bananaphone/device/testing/device-nokia-argon/deviceinfo) sets `deviceinfo_dtb="qcom-msm8905-nokia-argon"` and `deviceinfo_append_dtb="true"`, so `mkinitfs` appends the compiled `.dtb` directly to the kernel in `boot.img`.
- **Custom applications**: `pmaports-bananaphone/main/<app-name>/` (or `extra-repos/systemd/<app-name>/` for systemd-only services).

---

## 2. Committing DTS Changes to `pmaports-bananaphone`

1. If you edited kernel sources in `src/linux-msm8916/`, export the patch:
   ```bash
   git -C src/linux-msm8916 diff > docs/nokia-argon-audio-dts.patch
   ```
2. Copy the patch into the kernel package:
   ```bash
   cp docs/nokia-argon-audio-dts.patch \
      pmaports-bananaphone/device/testing/linux-postmarketos-qcom-msm8916/0001-nokia-argon-audio-dts.patch
   ```
3. In `pmaports-bananaphone/device/testing/linux-postmarketos-qcom-msm8916/APKBUILD`:
   - Increment `pkgrel` (e.g. `pkgrel=5` &rarr; `pkgrel=6`) so `apk` prefers your build over the upstream binary mirror.
   - Add `0001-nokia-argon-audio-dts.patch` to `source="..."`.
   - Update `sha512sums`:
     ```bash
     pmbootstrap checksum linux-postmarketos-qcom-msm8916
     ```
4. Commit and push to your GitHub fork:
   ```bash
   cd pmaports-bananaphone
   git add device/testing/linux-postmarketos-qcom-msm8916/APKBUILD \
           device/testing/linux-postmarketos-qcom-msm8916/0001-nokia-argon-audio-dts.patch
   git commit -m "linux-postmarketos-qcom-msm8916: enable nokia-argon internal audio DTS"
   git push
   ```

---

## 3. Building & Flashing Nura OS with `pmbootstrap`

`pmbootstrap` pulls untouched packages from the official Nura OS / postmarketOS binary mirrors and compiles only your modified packages from `pmaports-bananaphone`.

1. **Point `pmbootstrap` to your fork** (your config is in `~/.config/pmbootstrap_v3.cfg` with `device = nokia-argon`, `ui = cage`, `service_manager = systemd`):
   ```bash
   pmbootstrap config aports /home/elmot/hacking-nokia/pmaports-bananaphone
   ```
2. **Build the kernel package (`armv7`):**
   ```bash
   pmbootstrap build linux-postmarketos-qcom-msm8916 --arch=armv7 --force
   ```
3. **Build the full Nura OS image:**
   ```bash
   pmbootstrap install
   ```
   *(Add `--no-fde` to disable full-disk encryption, or `--add=<pkg>` to include custom packages.)*
4. **Boot or flash to the phone** (after rebooting to `fastboot` via `ssh elmot@172.16.42.1 "sudo reboot bootloader"`):
   ```bash
   # Safe RAM test boot (does not overwrite flash):
   pmbootstrap flasher boot

   # Permanent flash once verified:
   pmbootstrap flasher flash_kernel
   pmbootstrap flasher flash_rootfs --partition userdata
   ```

*(Optional)* If you also want to ship ALSA UCM/mixer defaults later, they belong in `device/testing/device-nokia-argon/` (with `pkgrel` bumped and `sha512sums` updated via `pmbootstrap checksum device-nokia-argon`).

---

## 4. Custom Applications & `cage` UI Integration (Slint + Python)

### Adding a Custom Package
Place your package in `pmaports-bananaphone/main/<your-app>/APKBUILD` (use `main/hello-world/` or `main/hello-world-rust/` as templates):
```bash
pmbootstrap checksum <your-app>
pmbootstrap build <your-app> --arch=armv7
pmbootstrap sideload <your-app>   # install onto running phone over SSH without reflashing
```
To include it in generated images, pass `pmbootstrap install --add=<your-app>` or add `<your-app>` to `depends` in `device/testing/device-nokia-argon/APKBUILD`.

### Integrating into `cage` UI
`cage` is a single-app Wayland kiosk compositor. [`cage-ui-session.sh`](pmaports-bananaphone/main/postmarketos-base-ui-cage/cage-ui-session.sh) sources all `/etc/cage-ui/*.sh` drop-ins and executes `$CAGE_UI_COMMAND`.

Have your package install `/etc/cage-ui/50-<your-app>.sh`:
```sh
export SLINT_BACKEND=winit-software   # safest default on 240x320; winit-femtovg uses Mesa Freedreno GLES
CAGE_UI_COMMAND="/usr/bin/<your-app>"
```

### Packaging Slint + Python on `armv7`
The `slint` Python package is a native Rust + PyO3 extension (not pure Python) and is not currently in `pmaports`:
1. **`main/py3-slint/APKBUILD`**: Build the `slint` Python wheel once for `armv7` using `cargo`, `maturin`, `python3-dev`, `py3-gpep517`, `py3-installer`, `wayland-dev`, `libxkbcommon-dev`, and `mesa-dev` (enable only Wayland + software/femtovg features to keep build time and size down), then `pmbootstrap sideload py3-slint`.
2. **`main/<your-app>/APKBUILD` (`arch="noarch"`)**: Depend on `python3 py3-slint` (plus a font package such as `font-dejavu`), install your `.py` + `.slint` files, `/usr/bin/<your-app>`, and `/etc/cage-ui/50-<your-app>.sh`.
3. **Fast dev loop**: Once `py3-slint` is sideloaded on the phone, `scp` `.py`/`.slint` edits to `/opt/<your-app>/`, point `/etc/cage-ui/50-<your-app>.sh` to `/usr/bin/python3 /opt/<your-app>/main.py`, and restart the UI session (`sudo systemctl restart tinydm`) instead of rebuilding `.apk`s on every change.
