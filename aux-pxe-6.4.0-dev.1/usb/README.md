# iPXE USB client

Timestamp: 2026-10-13 | Version: 1.1.1

Author & Credits: https://www.alawise.es/1-s

iPXE project: https://ipxe.org — upstream source and licences: https://github.com/ipxe/ipxe

`aux-ipxe-usb.img` is a hybrid ISO/USB disk image for BIOS and x86_64 UEFI.
Its first screen is a visible GRUB menu with a **5-second timeout**. The default
entry loads iPXE, performs DHCP and chains `http://pxe.1-s.es/menu.ipxe`.
The server menu offers chapter 0 assistance and starts its latest complete
compatible image after 60 seconds; any key stops that server timer. Remote access
still requires client consent inside the assistance ISO. HTTP and HTTPS are enabled.
A Ctrl-B prompt and a shell on failure keep diagnostics available. No Linux ISO
payloads or private credentials are stored on this USB.

USB 1.1.1 includes CONSOLE_CMD and a compiled default palette: cyan menus with
blue/indigo text and an inverse selected row. The generated server menu overrides
the colours with basic ANSI commands compatible with firmware text consoles.
RGB sequences reset attributes on some BIOS/EFI text consoles, causing grey on
black; the menu avoids them. Updating menu.ipxe fixes selection on
compatible clients; reflash this image when an older iPXE client lacks colour
commands. `colour support unavailable` is now reported rather than ignored.

The custom UEFI executable is unsigned. Firmware must allow this unsigned client, or an administrator must provide a signed and trusted boot chain. The image has not been validated on every physical machine, network adapter or firmware. `build-info.json` records the exact upstream commit, configuration and binary hashes; `SHA256SUMS` verifies the delivered bytes.

## Write the image

Inspect the device list and unmount the USB partitions before writing. Replace `/dev/sdX` with the whole USB device selected from that list. The write erases the USB's existing contents; a partition such as `/dev/sdX1` is not the image target.

```bash
lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS
cd usb
sha256sum -c SHA256SUMS
sudo dd if=aux-ipxe-usb.img of=/dev/sdX bs=4M status=progress conv=fsync
```

## Rebuild separately

The optional builder never runs the server downloader, deployment or generator. It does not install packages, configure Nginx, alter SELinux or write block devices. A dedicated source checkout is pinned to an upstream commit. Requirements are Git, Bash, Python 3, GCC, binutils, make, Perl, liblzma headers, mtools, xorriso and GRUB rescue tools with both BIOS and x86_64 UEFI modules.

On Fedora, the build dependencies can be installed with:

```bash
sudo dnf install git gcc binutils make perl python3 xz-devel mtools xorriso \
  grub2-tools-extra grub2-pc-modules grub2-efi-x64-modules
bash usb/build.sh
```

Change the URL explicitly when building for a different mirror:

```bash
bash usb/build.sh --menu-url http://pxe.1-s.es/menu.ipxe --jobs 4
```

`usb/grub.cfg` controls the first menu and its 5-second timer; `usb/bootstrap.ipxe.in`
controls network startup. Rebuild after changing either file. The bootstrap,
GRUB configuration, metadata and builder accompany the image. GNU GRUB is GPLv3+:
https://www.gnu.org/software/grub/ . iPXE retains its upstream licences;
the pinned source repository provides its attribution and licence files.

## Diagnose `chain`

At the iPXE prompt, the command is `dhcp`. Separating fetch from execution helps identify which step fails:

```text
dhcp
imgfetch --name aux_menu http://pxe.1-s.es/menu.ipxe
imgstat
chain aux_menu
```

Record the entire error, including its `https://ipxe.org/…` code. An HTTP error, TLS failure and a firmware/image-trust refusal require different fixes. Rebuilding a USB does not grant Nginx access to denied server files. For server checks, inspect the HTTP response, Nginx logs and SELinux AVC records for the exact failing path.

Builder source 1.1.2 reads pxe_url and jobs from fast-boot.json (or --config). Explicit --menu-url and --jobs override them. The distributed prebuilt image remains 1.1.1 until a new build is compiled and validated. The 32 GB cloning design is specified in NEXT-KEY.md.
