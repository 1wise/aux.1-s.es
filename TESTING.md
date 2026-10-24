# Review and test the three commands

Timestamp: 2026-10-13 | Version: 5.0.8

Author & Credits: https://www.alawise.es/1-s

The task implementations are inside `download.sh`, `deploy.sh` and `generate.sh`, between the `AUXPY` markers. The shell header locates the adjacent files and passes arguments to Python. Every task defines its own `main()`; none imports or executes another task. `src/common.py` contains only shared utilities. `fast-boot.json` is a configuration file.

## Read and inspect

```bash
bash -n download.sh deploy.sh generate.sh
bash download.sh --help
bash deploy.sh --help
bash generate.sh --help
```

The Python bodies can be inspected or compiled without running their commands:

```bash
python3 - <<'PY'
from pathlib import Path
for nom in ('download.sh', 'deploy.sh', 'generate.sh'):
    cuerpo = Path(nom).read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
    compile(cuerpo, nom, 'exec')
    print(nom, 'syntax OK')
PY
```

## Use an isolated target

Create a scratch configuration so testing does not write into the live webroot. Relative paths are resolved beside this configuration. The URLs below label generated links only; they do not publish the scratch directories.

```bash
pth_prb="$(mktemp -d)"
cat > "${pth_prb}/config.json" <<'JSON'
{
  "cache": "cache",
  "output": "html",
  "url_file": "url.txt",
  "base_url": "https://aux.example.test",
  "pxe_url": "http://pxe.example.test",
  "jobs": 1
}
JSON
```

Put one chosen, small HTTP(S) payload URL in `${pth_prb}/url.txt`. Use a distinct filename with a supported extension. Test the verbose download first:

```bash
bash download.sh --config "${pth_prb}/config.json" --dry-run
bash download.sh --config "${pth_prb}/config.json" 2>&1 | tee "${pth_prb}/download.log"
```

Expected: the cache contains the payload and `downloads.json`; `html` has not been created by download. Re-running reuses a valid cached file. An unsuccessful refresh returns a nonzero exit and retains the earlier valid payload.

Test physical deployment separately:

```bash
bash deploy.sh disk --config "${pth_prb}/config.json" --dry-run
bash deploy.sh disk --config "${pth_prb}/config.json"
```

Expected: `html` contains the physical payload and, for ISO/archive inputs, the prepared contents. No download or page generation occurs. ISO extraction requires `bsdtar`.

Generate from that deployment:

```bash
bash generate.sh --config "${pth_prb}/config.json" --dry-run
bash generate.sh --config "${pth_prb}/config.json"
```

Expected: AUX/PXE indexes, catalog, checksums, supported iPXE entries and sitemaps reflect the actual public files. Removing the URL list does not stop deployment or generation. If no deployed files remain, generation produces an empty catalog, not links to missing images.

For RAM, use a dedicated existing tmpfs directory and adequate free memory:

```bash
pth_ram="$(mktemp -d /dev/shm/aux-test.XXXXXX)"
sudo bash deploy.sh ram --config "${pth_prb}/config.json" --ram-dir "${pth_ram}"
bash generate.sh --config "${pth_prb}/config.json"
```

Expected: public payload and content links point into this RAM directory. Inspect the mounts with `findmnt`. Before deleting the test directory, unmount any ISO mounts underneath it. RAM copies and mounts disappear after reboot; the persistent cache remains available for another deploy.

## Automated checks

For the 6.0.0-dev.3 optional API terminals also run `python3 iso-assist/test_ai.py`,
`python3 iso-assist/test_sources.py` and `python3 verify-v6.py`. Fourteen AI fixture
checks cover request formats, authorization headers, TLS validation, redirect
refusal, output parsing, hidden credential input, context reset, public packaging
and GRUB/iPXE selections. The two optional service units pass systemd-analyze verify.
No provider account or API quota is used; actual API calls and dev.3 hardware boot
remain pending. The user's earlier Cari/GSM menu and T report is tracked separately
in CHECKLIST-6.json, without assuming a version, hash, firmware or remote session.

From the complete source bundle, build the static preview and run the checks:

```bash
python3 build.py
python3 verify.py
node verify-portal.cjs
```

The Python checks use temporary directories, a local HTTP fixture and tiny payloads. They verify real download progress, cache reuse, failed refresh preservation, command independence, RAM/disk publication, loss of RAM contents, crawling, boot file gates, sitemap hosts and ordinary HTML download links. Permissions checks deploy and generate with `umask 077`, repair matching managed trees/copies, preserve external symlink targets, skip mounted directories and verify other-user read/search bits through the complete target paths. A mocked ISO mount verifies the command arguments; an actual mount and a BIOS/UEFI/ARM network boot still require server and client checks. Node is needed only for the visual portal behavior test, not for the operational scripts.

## USB image validation

The shipped 4.2.0 project image was booted as a read-only USB storage device in QEMU, using SeaBIOS and x86_64 OVMF separately with an emulated e1000 adapter. Both clients displayed the embedded AUX URL and HTTP/HTTPS features, entered the diagnostic console, acquired DHCP and executed an isolated HTTP menu through a 302 redirect. No ISO or operating system was booted during this check. The public AUX endpoint and its TLS path still require a client-side check on the intended network; the isolated VM check does not establish that every physical adapter, firmware or Live recipe works.

The publication tests verify the image's MBR signature, byte-preserving copy, checksums, public read/traversal permissions, AUX/PXE links, host sitemaps and bundle contents. They also generate from a minimal installation without `usb/` to check that no missing image is advertised. Rebuilding the client remains an explicit `bash usb/build.sh` step.

## Fedora media validation

The 4.2.1 fix was checked against the ISO directory records of the deployed Fedora Server netinstall 44 and Fedora Workstation Live 44 x86_64 images, read using HTTP byte ranges. The netinstall ISO contains `images/install.img` and the `images/pxeboot` kernel/initrd pair, with no `.treeinfo`. The Live ISO contains `boot/x86_64/loader/linux`, `initrd` and `LiveOS/squashfs.img`. This metadata inspection does not constitute a complete ISO checksum or an operating-system boot test.

Regression fixtures cover netinstall without `.treeinfo` on x86_64 and ARM64, custom stage2 metadata taking precedence over Live/fallback paths, Fedora 44 loader layouts, original GRUB/SquashFS path settings, unchanged deployed contents, path-escape rejection and missing-runtime diagnostics. Matching Fedora mirror tree metadata was also inspected to confirm the Server `os/` installation-source layout. Generation does not fetch remote metadata; it remains an independent crawl of the deployed filesystem.

A separate local extraction check constructed small Rock Ridge/Joliet ISO fixtures and ran the real `deploy.sh disk` with `bsdtar`, followed by generation. Every fixture path, hidden metadata file and byte matched the original input; the copied ISO bytes also matched. The deployed netinstall and Live GRUB configurations used for this investigation were compared with their corresponding original ISO files and matched. Large runtime images were not completely rehashed through HTTP, and full Fedora installer/Live boots remain client-side checks.

## Bastion routing and image files (4.3.0)

The regression suite covers default Bastion downloads with nested paths, explicit Excalibur/source choices, Ubuntu ISO boot arguments staying on Excalibur, shared Distros/Tools classification, same-host sitemaps and plain HTML contents navigation. Its image fixture includes a RAM-style directory link, original kernel/initrd/SquashFS paths, escaped filenames, directory cycles and an out-of-tree link. Generated indexes never modify the image tree. wget/curl resume is exercised against a local HTTP redirect and Range server. Remote mirror availability and real-machine OS boot tests are separate from these checks.

Version 4.4.0 adds separate Netinstall, Install and Live branches under each distribution, Gentoo Chroot and tool families. Tests verify unique resource placement, stable numbering, complete iPXE label destinations, parent navigation, unsupported Gentoo exclusion and matching HTML anchor targets. Browser logic checks family/subtype filtering combined with architecture selection. The terminal portal remains plain HTML without JavaScript dependencies. The upper visual panels are retained; no AI chat integration is included.

## 5.0.8 validation

61 command/catalog tests, portal behavior checks, 11 ISO source tests and the
TEC account/request integration check pass. Nginx's six-name HTTP/HTTPS routing
fixture passes, and the updated TEC PHP entry passes php -l. ISO guide anchors
and 8 command blocks, plus 3 diagnostic command blocks, pass syntax checks.
The single-page guide has over 2,800 words including the package inventory and
keeps all content accessible without JavaScript. The recipe manifest has 94
requested packages, current source hashes and null compiled-image measurements.
Public ISO ZIP packaging is restricted to declared recipe files.

AUX Rescue filename tests require the actual aux.assist media marker before
60-second automatic assistance boot. The original local 5x7 font was inspected
through a rendered PXE_ sample. Browser QA was unavailable; live CSS animation
and complete page layout still need browser inspection. No new Linux ISO was
compiled or booted. PHP-FPM itself and Excalibur's 502/socket/logs were not
accessed; the diagnostic page describes the required server checks.

## 5.0.6 validation

59 command/catalog tests and portal behavior checks pass. A DBAN fixture
reproduces the former extra isolinux.bin catalogue entry; generation now retains
only the parent ISO and an independent public EFI client. Internal BIN, EFI and
nested ISO files remain linked in Browse contents. A read-only filesystem fixture
raises EROFS on any attempted chmod below the image directory: generation completes
and writes its menu/sitemap without changing those image bytes. A separate check
covers both file ownership and subdirectory modes below a read-only mount boundary.
Writable-tree permissions and the mixed RAM/disk workflow remain covered.

Read-only behavior is simulated with ST_RDONLY and an EROFS guard; no new real ISO
mount or client hardware boot was performed on this host. Browser QA was unavailable;
plain HTML and portal behavior checks passed.

## 5.0.5 validation

57 command/catalog tests and portal behavior checks pass. The new mixed fixture
performs real HTTP downloads from two lists, preserves both source records on
cache reuse, publishes one archive to tmpfs and another to disk, and generates
both contents browsers and iPXE recipes together. Unselected files stay private;
missing selected files are reported without any deploy-time download. Relative
JSON list paths, compatibility without lists, conflicting selectors and complete
FTP selection are covered. The two source lists are disjoint and cover the same
31 source resources. Both files are included in the command ZIP.

The combined Nginx configuration passes nginx -t and six-name HTTP/HTTPS routing
checks with a temporary certificate, including CSS/iPXE MIME and TEC separation.
The actual ntp1.1-s.eu certificate SANs and Excalibur configuration/reload remain
server-side checks. Browser QA was unavailable in this environment; portal logic
and plain HTML instruction checks passed.

## 5.0.4 validation

The source catalogue excludes Ubuntu/Boot Repair and contains 31 resources.
53 tests pass, including a compressed archive whose download fits in tmpfs but
whose extracted tree does not. The test verifies rejection before copying or
publishing. Existing RAM reuse and independent download/deploy/generate tests
remain passing. The capacity/quarantine instructions are manual server operations;
no Excalibur mount, quota or stored payload was changed by this publication.

## 5.0.3 validation

52 command/catalog tests and the portal behavior checks pass. Added cases cover
cached payload permission repair, selected owner/group across all three phases,
no-follow link ownership, optional versus denied FTP SITE CHMOD, and all five
chroot guides in JavaScript-free HTML. The FTP button emits only the FTP command.
Published command examples were checked with Bash syntax validation; disk mounts
and new distribution roots were not executed on this build host.

The USB 1.1.1 image is rebuilt with CONSOLE_CMD and distinct default selection
colours. QEMU USB boots passed in BIOS and x86_64 UEFI. A VGA screenshot reproduced
grey text when RGB sequences were used; basic ANSI removed the attribute resets
and produced cyan rows with a blue selection bar and contrasting text. An arrow
keypress moved selection to the next item. The script reapplies its palette with
console --keep and reports missing colour support. Physical client firmware/
console behaviour still needs checking on Cari.

## 5.0.2 validation

48 catalogue/command tests and the portal behavior checks pass. Chapter 0 tests
check numeric version ordering, final versus dev releases, complete recipe and
firmware gating, and timer cancellation. TEC email/phone/JSON/approval tests
use a simulated MTA; no real mail is sent. The 11 ISO source tests pass; compiling
and booting the Fedora Live image remains a separate Fedora task.

The combined vhost was tested with a real local Nginx, temporary TLS certificate
and ports. All six hostnames route to their intended roots. AUX/PXE stay available
over HTTP; TEC redirects to HTTPS. CSS/iPXE MIME types, public .treeinfo and private
path rejection are checked. Run `python3 nginx/test_vhosts.py` with system Nginx,
or use `--nginx /path/nginx --config-dir /path/nginx-config` for extracted tools.
This does not touch the installed server config or its certificate.

USB 1.1.0 booted as USB storage in QEMU SeaBIOS and OVMF x86_64, then executed an
HTTP menu after DHCP. A generated two-version assistance fixture selected the
latest version automatically after 60 seconds in both firmware modes; all palette
commands were accepted. The fixture only printed a marker, never opened SSH.
GRUB precedes iPXE with its visible 5-second menu. UEFI is unsigned; VM tests used
Secure Boot disabled. Hardware NIC, firmware and the real assistance rootfs still
require testing on the client machine.

Version 4.4.1 restores the original navy/cyan terminal palette and native nested disclosure menus. A regression verifies three menu levels, balanced disclosures, unique hierarchy anchors and identical direct links between compact and fully expanded views. Every resource retains all server choices and its commands link. The expanded view opens every branch without JavaScript. Actual Links rendering and browser visual QA were not available in this environment.

Version 4.5.0 adds the independent FTP deploy target. Tests cover the root merge, payload deduplication, differing-copy rejection, approved RAM links, metadata exclusion, private files, escaping links, cycles and read-only dry runs. A local FTP protocol server exercises actual passive binary transfers, directory creation, SIZE, REST/STOR resume, an interrupted transfer preserving the old public file, retry and rename. Credentials do not appear in command output. The fixture uses plain local FTP; real Bastion FTPS/TLS, account permissions, FTP webroot mapping and server rename behavior still require an account-level deployment test.

## 5.0.8 platform guides and catalog

Approved catalog: 22 light + 14 heavy, local assistance separate. Added Fedora/Debian host distinction for chroot, Debian live-build base recipe, four USB host workflows, and Debian Nginx/FPM configuration examples. Debian base ISO is not a port of the remote-assistance payload. No ISO compilation, physical USB writing, Debian FPM execution or server migration was performed. New rescue payloads remain download/browse-only until a supported boot recipe is validated. Budget figures are estimates, not measured quotas.

## 5.0.9 architecture and cloud catalog

Added Debian Bookworm i386 network media, Alpine x86 kernel/initramfs/modloop recipe, and Debian/Fedora QCOW2 cloud downloads. User architecture filter is separate from hardware gates; direct boot labels re-check hardware. U-Boot documentation is board-specific; no universal binary or hardware boot validation claimed. Debian netboot URL returned HTTP 200; cloud image names were checked against upstream directory indexes. RAM/disk sizes remain unmeasured estimates.

## 5.1.0 unified accounts, configuration and Alpine

65 AUX/PXE tests PASS. Node portal filters PASS. verify-routing.py executes the generated PHP index and checks exact Bastion CLI host matching, central TEC links, configurable iPXE timeout, license footer and pool config. TEC tests PASS for unique registration, hashed single-use email confirmation, authenticated request identity, full approved public profiles, manual approval, fixed-recipient admin mail with fake sendmail, legacy migration idempotence, passwords, account isolation and profile suspension. Nginx six-host routing/MIME checks PASS; PHP CLI syntax checked.

Alpine 3.24.2: all seven upstream images were downloaded and SHA256-matched in the earlier isolated run; real disk extraction found all original LTS boot file sets. Three archives contain 1,219,516,325 unpacked bytes. Unit tests cover all editions/architectures, same-image boot dependencies, matched repository branch, stale-partial cleanup and managed RAM link repair. Final catalog: 29 light + 20 heavy, local AUX Rescue separate.

The Site remains a static preview; production TEC PHP, DNS/OVH Multisite for p.1-s.es and server data migration were not applied remotely. No real administrator email was sent, no new ISO/USB was compiled and no physical boot was tested. The 32 GB USB and 500 GB SSD notes are a future specification, not a disk writer. Published USB 1.1.1 and Fedora recipe 5.0.1-dev.5 remain independently versioned. Browser QA was unavailable in this managed environment.
