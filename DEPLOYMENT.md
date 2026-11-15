# aux / pxe — command bundle

Timestamp: 2026-10-13 | Version: 5.0.8

Author & Credits: https://www.alawise.es/1-s

## Changes in 5.0.8

PXE branding is uppercase with original local 5x7 pixel glyphs, terminal green
and a CSS underscore cursor. Plain text remains available without CSS/JavaScript;
reduced-motion preferences keep the cursor steady. AUX and TEC logos retain
their existing lowercase designs. The prebuilt font is bundled; generation does
not fetch fonts or require fontTools. Its optional rebuild source is fonts/build-pxe-font.py.

iso-guide.html is a full single-page ISO construction chapter with the AUX Rescue
manifesto, requested package inventory, build commands, acceptance and publishing
steps. iso/manifest.json describes the existing Fedora 44 5.0.1-dev.5 recipe and
source hashes; compiled ISO size, hash and installed RPMs stay null until measured.
Names aux-rescue.iso / aux-rescue-version-architecture.iso are classified as
assistance, while actual boot files and aux.assist still gate automatic PXE.

tec-502.html and tec/TROUBLESHOOTING.md provide local diagnostics for the existing
FPM Unix socket; no remote service or SELinux policy was changed. TEC 5.0.8 ships
the local font, updated navigation and a pool with PATH and worker output logging.
Preserve JSON/private configuration when updating; inspect the actual server log
before choosing a 502 repair. Nginx still uses the ntp1.1-s.eu certificate paths.

## Changes in 5.0.6

Generation no longer treats BIN, EFI or ISO files inside an image's prepared
directory as separate catalogue downloads. The original files remain browsable
through that image's contents pages, including unsupported boot media such as
DBAN. The crawl identifies prepared directories from the neighbouring ISO/archive
filename rather than relying only on known installer directory layouts.

Permission helpers now inspect the containing filesystem's ST_RDONLY flag before
chown/chmod, including files and subdirectories below a mount point. Mount-point
checks alone did not protect DBAN's isolinux.bin when it was discovered as a
standalone resource. Read-only media retain their original modes; writable managed
files still receive the selected ownership and public modes. Other permission
errors remain visible.

To fix an existing installation, update generate.sh and src/common.py together
from this bundle, preserving local fast-boot.json and URL lists, then rerun
generate.sh. No new ISO download or RAM/disk redeployment is required.

## Changes in 5.0.5

`light-url.txt` selects 20 netinstall/minimal/tool resources for RAM.
`heavy-url.txt` selects 11 desktop Live/full-install resources for disk, including
both Arch ISO filenames so identical aliases do not consume RAM twice. The small
Arch iPXE clients remain in the light list. The lists are editable deployment
choices, not a size guarantee or proof of PXE support. No new upstream URLs were
added; Ubuntu and Boot Repair remain excluded.

Both download and deploy accept `--list light|heavy` or `--url-file PATH`.
Download merges source records across runs; it does not discard the other list's
labels. Deploy selects exactly the listed filenames from the existing cache and
reports missing files as failures without fetching them. `--only` can narrow a
list further. FTP still replicates the complete public tree/cache and rejects list
selection. Generate crawls RAM links and disk directories together, independent
of either list. No script invokes another script.

`url.txt` remains the combined compatibility snapshot. An unfiltered deploy still
scans the complete cache without a list. Edit the split lists for the mixed flow;
keep the combined snapshot in sync only if using the legacy all-resources flow.
Relative `light_url_file` / `heavy_url_file` settings resolve beside the JSON;
explicit CLI paths resolve from the current working directory.

The combined Nginx example uses `/etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem`
and `privkey.pem` for AUX/PXE/TEC. That directory name does not establish which
domains are covered: inspect subjectAltName before installing/reloading it.

## Changes in 5.0.4

The default URL list omits Ubuntu and Boot Repair (31 source resources). Existing
downloads, public links and RAM copies are not removed automatically: deploy reads
the cache, and generate crawls the public tree. The operations guide documents
unmounting and quarantining those files outside the webroot before regenerating.
The Ubuntu chroot instructions remain available.

RAM preflight now counts the compressed copy, page-rounded extraction size and
a 16 MiB margin. ZIP budgets also allow for extracting embedded ISO files. A
matching, already prepared RAM tree is reused without budgeting a second copy.
The verbose SPACE line reports additional space and current tmpfs availability.
This protects against the observed archive failure before its RAM copy starts;
it does not reserve space against concurrent consumers of the same tmpfs.

An optional 40G remount is a temporary quota increase, not extra physical RAM.
Check free -h first; /tmp's separate quota is not spare space inside /dev/shm.
Keep memory for the kernel and other services. Read-only ISO loop mounts normally
report 100% full; inspect the parent tmpfs rather than treating that as an error.

## Changes in 5.0.3

AUX and PXE now include FTP deployment and permission instructions plus chroot
guides for Fedora, Debian, Ubuntu, Gentoo and Arch. Generated `operations.html`
and `chroot-all.html` keep every step open for Links without JavaScript. Existing
installation rescue and a new root in RAM are separate manual procedures; none
of the three server commands mounts client disks or enters a chroot.

`--user` and `--group` (also JSON settings `owner` / `group`) select ownership
for managed files. Running as root defaults to root:nginx when the nginx group
exists; otherwise it uses the process group. Unprivileged execution uses the
current user/group and rejects an owner/group it cannot assign. Public directories
are 0755, files 0644 and executable scripts 0755. Cached downloads and generated
files are repaired when reused. Writable extracted trees retain executable files
but lose setuid/setgid bits. External symlink targets and read-only ISO mounts are
not modified. Existing private cache metadata directories retain their modes;
download's cache root is traversable, and mount deployment prepares that traversal
for its public file links. Private TEC JSON is unrelated and remains protected.

FTP attempts SITE CHMOD 0755 on the published directories and 0644 on renamed
files. Unsupported SITE CHMOD is reported once; hosting umask then controls modes.
A permission denial stops publication rather than claiming successful permission
repair. The remote owner is the FTP account; local chown cannot change it.

iPXE selection now uses cyan text on indigo, distinct from indigo on cyan rows.
The palette uses basic ANSI only: BIOS/EFI text consoles can interpret RGB
parameters as attribute resets, producing grey on black. Native ANSI blue is
the text-console approximation of indigo. The script explicitly reapplies and
clears its console with `console --keep`.
A client without colour commands prints a diagnostic; USB 1.1.1 includes both
CONSOLE_CMD and a compiled contrasting default palette. Regenerate menu.ipxe to
update the server palette; use the new USB if the current iPXE client lacks it.

Two selectable URL lists, one persistent cache, three independent programs. Each Bash script contains its own Python task body and its own `main()`. `src/common.py` supplies shared configuration, validation, locking and file utilities; it never selects or runs a task. Unpack the ZIP to retain that utility file and the generation templates. Nginx is managed separately.

| Command | Reads | Writes |
| --- | --- | --- |
| `bash download.sh` | `url.txt` | Files in the persistent `cache` |
| `bash deploy.sh ram` | The same cached files | RAM copies, read-only ISO mounts, public file/directory symlinks |
| `bash deploy.sh disk` | The same cached files | Physical copies and extracted directories in `output` |
| `bash generate.sh` | Public units in `output`, including nested directories and RAM links | AUX/PXE indexes, menus, catalog, checksums and sitemaps |

Unfiltered deployment scans the cache, including files no longer listed in `url.txt`. Explicit `--list`/`--url-file` deployment selects only the listed filenames. Generation scans the published filesystem. Download records supply optional source labels; they do not decide whether a file exists or is bootable. Deployment and generation work without the URL list and never download anything.

## Run

Edit `light-url.txt` / `heavy-url.txt` for the mixed flow, or `url.txt` for all resources: one HTTP(S) URL per line; blank lines and `#` comments are allowed. Filenames must be distinct. SourceForge `/download` redirects keep the original image filename. The supplied URLs retain the earlier source list; their current remote availability is not asserted.

Set paths and host URLs in `fast-boot.json`:

| Setting | Default |
| --- | --- |
| `cache` | `/var/www/aux.1-s.es/isos` — existing persistent downloads |
| `output` | `/var/www/aux.1-s.es/html` — published files shared by the two hosts |
| `ram_dir` | `/dev/shm/aux-fast-boot` — existing tmpfs |
| `base_url` | `https://aux.1-s.es` — visual catalog |
| `pxe_url` | `http://pxe.1-s.es` — Excalibur text catalog, PXE and individual image files |
| `download_url` | `https://b.1-s.es` — Bastion complete file downloads; `https://b.1-s.eu` is an alternative base |
| `url_file` | `url.txt` — default download only |
| `light_url_file` | `light-url.txt` — `--list light` |
| `heavy_url_file` | `heavy-url.txt` — `--list heavy` |
| `jobs` | `4` |

```bash
sudo bash download.sh --list light --verbose
sudo bash deploy.sh ram --list light --verbose
sudo bash download.sh --list heavy --verbose
sudo bash deploy.sh disk --list heavy --verbose
sudo bash generate.sh --verbose
```

`--config PATH` selects another configuration. CLI flags override settings. Paths inside JSON are relative to the JSON file. `--output /path/to/html` publishes another unit root; it must be served at the configured URLs. Generate crawls subdirectories and intended directory symlinks inside that root, with cycle detection. A mount outside the root must first have a public directory link under it.

```bash
bash download.sh --dry-run
bash deploy.sh ram --dry-run
bash generate.sh --dry-run
bash download.sh --list light --only fedora --jobs 2
bash deploy.sh ram --list light --only fedora
bash generate.sh
```

`--dry-run` is read-only and performs no downloads, mounts or DNS lookups. `--only` filters the selected command; omit it on final generation to include every published unit.

The operational scripts are `download.sh`, `deploy.sh ram|disk` and `generate.sh`. Each runs directly for independent review and testing.

Each command exposes `--help`, `--dry-run` and `--version`. There is no `--stage` option: the script being executed defines the task. Download-specific flags belong to `download.sh`; deployment accepts the positional target `ram` or `disk`. Generation uses its own `--live-url` flag when needed.

`TESTING.md` contains an isolated review procedure and the automated checks. `download.sh` runs without the deploy/generate files or visual assets. `deploy.sh` runs without the downloader, generator, URL list or templates. `generate.sh` runs without the downloader, deployer or URL list, using its own templates and the real public files. Optional source files are copied into the generated download bundle only when present.

Requirements: Bash, Python 3.12+, curl, bsdtar for ISO extraction/wrapped ISO archives, and util-linux for mounting. RAM deployment requires root and an existing tmpfs. Physical disk extraction needs write access to the target. No stage installs packages or changes Nginx, DNS, DHCP, SELinux or systemd.

## Two servers: Bastion and Excalibur

| Server | Role | Selection |
| --- | --- | --- |
| Bastion · France | Complete ISOs, archives and standalone payload downloads | Default download link and default wget/curl commands |
| Excalibur · Canada | AUX/PXE portals, network boot, mounted/extracted image files | Always used by PXE and the contents browser; optional complete-download mirror |

Each catalog row and command page has ordinary HTML links for both servers and the original URL. Server selection works without JavaScript in Links/Lynx; the visual catalog also has a global selector. Boot recipes never use `download_url`, including Ubuntu's full-ISO boot argument. This is explicit download routing, with manual mirror selection; no health-based automatic failover is implied.

`generate.sh --download-url https://b.1-s.es` sets Bastion. A prefix is supported, for example `https://b.1-s.eu/isos`. For a public Excalibur resource at `releases/image.iso`, Bastion must serve the identical file at `<download_url>/releases/image.iso`. Keep filenames, relative paths and bytes identical. `download.sh` downloads to the cache on the machine where it runs; it does not upload to Bastion. Copy the complete payload files to Bastion separately using your hosting transfer access, preserving relative paths. Do not copy RAM symlinks, the extracted directories or Excalibur's web application. `generate.sh` is an offline filesystem crawl and does not assert Bastion availability from a successful Excalibur deployment.

After publishing the files on Bastion, verify a real payload URL and Range support from your shell:

```bash
curl -fI 'https://b.1-s.es/EXACT-FILENAME.iso'
curl -fsS --range 0-0 --max-filesize 1 -D - -o /dev/null 'https://b.1-s.es/EXACT-FILENAME.iso'
```

The Range check should return `206 Partial Content` with `Content-Range`. Verify the complete file against the trusted checksum after downloading.

The generated `contents.html` lists deployed image trees by Distros and Tools. `contents/<resource-id>/index.html` and its directory pages provide plain HTML links to original files on Excalibur, plus `files.tsv` for CLI use. These indexes are written outside the mounted/extracted image; kernels, initrds, SquashFS paths and image contents remain unchanged. Internal directory links are followed with cycle protection; links escaping the image and private dotfiles are excluded. Public `.treeinfo` and `.discinfo` are listed when present; the Nginx metadata exception documented below still applies. Each host's sitemap contains only that host's URLs.

The shared numbered hierarchy is Distros → distribution → Netinstall, Install or Live, followed by Tools → tool family. Netinstall identifies small network installation media and netboot clients; Install includes full installer images and Ubuntu live-server. Only branches with catalog resources are shown, with stable numbering: Netinstall .1, Install .2, Live .3. Gentoo has a Chroot environment branch; entering a chroot requires an already running Linux environment, and no unsupported boot command is generated. The visual catalog, plain Links-compatible terminal catalog, image browser and real iPXE submenus share this hierarchy. iPXE lists only complete supported boot recipes compatible with the client architecture and firmware; Back and Escape return to the parent menu. Existing upper visual panels are retained for later use.

The terminal portal uses the original GitHub project's navy background and cyan menu headings, with amber ISO links, violet directory links and pink binaries. Its numbered hierarchy uses native HTML details/summary controls. `cli.html` opens the Distros root with compact family menus; `cli-all.html` opens every branch. Both contain the same direct download, mirror, commands and contents links without JavaScript. Use All expanded in text browsers that do not support disclosure controls. No PHP request routing or browser scripts are needed for these options.

## Deploy the Bastion replica over FTP

FTP is another independent target of `deploy.sh`. It neither downloads nor generates pages. Prepare html locally with the existing RAM/disk and generate stages, then merge **the contents** of html and the complete cached payloads into the existing FTP webroot. For example, `html/assets/style.css` becomes `/assets/style.css`, `html/index.php` becomes `/index.php` and `isos/fedora.iso` becomes `/fedora.iso`. The remote site has no wrapping `html/` or `isos/` directory. Nested public paths are preserved.

First inspect the merge without connecting or writing:

```bash
sudo bash deploy.sh ftp \
  --output /var/www/aux.1-s.es/html \
  --cache /var/www/aux.1-s.es/isos \
  --ram-dir /dev/shm/aux-pxe \
  --ftp-root / \
  --dry-run
```

Then upload, substituting the FTP account's hostname and username:

```bash
sudo bash deploy.sh ftp \
  --output /var/www/aux.1-s.es/html \
  --cache /var/www/aux.1-s.es/isos \
  --ram-dir /dev/shm/aux-pxe \
  --ftp-host HOST_FTP \
  --ftp-user USUARIO_FTP \
  --ftp-root / \
  --verbose
```

The FTP root is relative to the account's virtual filesystem. `/` must be the directory served by `b.1-s.es` and `b.1-s.eu`; if hosting maps the website to `/www` or another directory, use that existing directory as `--ftp-root`. The FTP hostname may differ from the HTTP domain. Default port is 21. Explicit FTPS protects the control and data connections and verifies the server certificate. For an account supporting plain FTP only, select `--no-ftp-tls` explicitly. No silent downgrade occurs.

The password is requested through a hidden terminal prompt. An unattended session can provide `AUX_FTP_PASSWORD` through its environment; no password argument or configuration key is accepted. Optional nonsecret JSON keys are `ftp_host`, `ftp_user`, `ftp_port`, `ftp_root` and `ftp_tls`. `AUX_FTP_HOST` and `AUX_FTP_USER` are also accepted. The current local configuration is preserved by update ZIPs.

Public RAM/cache links are materialized as bytes. Set `--ram-dir` to the directory actually used during RAM deployment. Broken links, directory cycles, links outside html/cache/RAM roots, file/directory conflicts and differing html/cache copies stop the preflight. Matching public payload links and cache files are uploaded once. Cache metadata, locks, backups, private dotfiles and temporary `.part`/`.tmp` files are excluded; public `.treeinfo` and `.discinfo` remain included. `--only` is rejected because a full public catalog must not be uploaded with a filtered payload set.

Uploads use passive binary transfers and content-addressed temporary `.aux-upload-<sha256>.part` names. Rerunning after an interruption resumes that same content if the server supports SIZE and REST/STOR. A complete file is size-checked and renamed over its final path; source hashes are checked again before publication. Existing public files remain until rename succeeds; unrelated remote files are not deleted. Re-running a successful deployment uploads complete files again. Remote SHA-256 is not calculated by FTP; SIZE verifies length, not a remote checksum. Remote servers must support the rename operation, including replacing an existing destination. Individual files publish atomically when supported by the server; the full website is not an atomic release. Catalog entry points are sent after payloads/assets.

The replica retains the generated Excalibur URLs for PXE and individual image files; it does not rewrite catalog links or regenerate a Bastion-specific sitemap. Generated AUX/PXE sitemaps retain their existing host roles. Do not put FTP credentials or unrelated private files inside the public html directory.

## Download progress

Verbose output is the default: timestamp, file number, filename, source, progress bar, bytes, current speed, ETA, resume, SHA-256 verification and an elapsed-time summary. Complete lines remain readable through SSH and `tee`.

```bash
sudo bash download.sh 2>&1 | tee download.log
```

Valid cached files are reused. `--refresh` fetches again. Interrupted transfers keep `.part` files and resume with `If-Range` when the server supplied an ETag or Last-Modified validator. A failed refresh preserves the previous valid file and returns a failure status. HTML error pages and invalid containers are rejected.

`--checksums /path/to/trusted-SHA256SUMS` compares listed files during download, deployment and generation. Authenticate that input separately using the distribution's signed checksums. Generated `SHA256SUMS` records local bytes.

## RAM and disk

RAM deployment copies cached payloads into tmpfs. Both the download file and its mounted/extracted directory receive public symlinks. Files remain browsable through the prepared HTTP directory listing. It checks space before copying; extracted archives also need free space in tmpfs. tmpfs can use swap.

RAM copies and mounts disappear on reboot. The disk cache remains. Run `deploy.sh ram` and `generate.sh` again to restore them. No automatic boot service is installed.

Disk deployment copies the payload and extracts its contents into physical directories. This result persists across reboot and can be uploaded as a complete webroot. `deploy.sh disk --mode mount` is an optional disk-backed mounting variant; its mounts need restoring after reboot.

A cache lock prevents concurrent commands. Managed payloads/trees can be updated or switched between targets. Unmanaged files are preserved. Previous generated pages are backed up in `cache/backups/`; old payloads are not deleted automatically.

## Original media paths and Fedora network boot

ISO mounts expose the original image tree. Disk deployment extracts that tree with `bsdtar`; it does not flatten directories, rename kernel/initrd/SquashFS files or rewrite bootloader configuration. A boot ISO is not a complete mirror repository: package files and repository metadata remain at the matching origin mirror unless separately mirrored.

Fedora Server netinstall 44 has `images/pxeboot/vmlinuz`, `images/pxeboot/initrd.img` and `images/install.img`, without `.treeinfo` in the ISO. Generation accepts this layout, matching Anaconda's documented/source fallback, and uses `inst.stage2=<public-image-tree>/`. `inst.repo` retains the origin mirror, release, edition and architecture, converting the ISO directory to its matching `os/` directory. A public tree's `.treeinfo` takes precedence when present; a missing file named by that metadata is reported rather than silently replaced.

Fedora Live 44 uses `boot/<architecture>/loader/linux` and `initrd`. Generation reads the original GRUB configuration and `.treeinfo` as data where available, then checks the actual files. `rd.live.dir` and `rd.live.squashimg` settings preserve the original relative SquashFS path. Only the public host/unit prefix changes for HTTP access; image contents are not extracted or repacked. `catalog.json` records `boot_files` and the configuration path. Unsupported or incomplete Live media remains downloadable, with an explicit `pxe_reason`, and is not advertised as hardware-verified.

When serving a mirror tree whose `.treeinfo` specifies a custom stage2 path, allow its public installer metadata before a generic Nginx dotfile-denial regex, in each relevant HTTP/HTTPS server block:

```nginx
location ~ /\.(?:treeinfo|discinfo)$ {
    try_files $uri =404;
    default_type text/plain;
}
```

Do not broadly expose other dotfiles. Anaconda can use the standard `images/install.img` fallback without `.treeinfo`; custom metadata paths need readable metadata. After installing the updated generator and `src/common.py`, run generation again against the existing deployed tree. No ISO download or redeployment is required when the original files are already present.

## Public permissions

Deployment creates public directories with mode `0755` and payload files with mode `0644`, even with `umask 077`. Extracted trees use `0755` directories and `0644` regular files; files that already have an execute bit retain execution with mode `0755`. RAM copies and their dedicated root receive the same readable modes. Rerunning deployment repairs permissions on matching managed copies and extracted trees without extracting them again. Permission normalization skips symlinks and read-only mounts.

Generation sets its public directories to `0755`, documents/assets to `0644`, downloadable shell scripts to `0755`, and the command ZIP to `0644`. Cache metadata and backup directories retain their existing directory policy. Existing ancestors of the configured roots are not changed: Nginx needs search access through every parent directory, including the actual target path of RAM links. The optional disk mount mode also requires readable cached payloads and a searchable cache path.

For the configured server roots, inspect their full paths before changing a parent:

```bash
namei -l /var/www/aux.1-s.es/html/index.php
namei -l /dev/shm/aux-pxe
```

After replacing the updated scripts and `src/common.py`, run the chosen deployment command and then generation again. Do not apply recursive permission changes through mounted ISO trees. Fedora SELinux labels are separate from Unix permissions; inspect Nginx errors and AVC denials if requests remain forbidden.

## Mount the Fedora assistance ISO on Excalibur

The USB key remains the small iPXE client. Excalibur hosts the expanded assistance ISO; iPXE fetches its kernel, initrd and modified `images/install.img` over HTTP. Do not substitute the original Fedora stage2 image: it does not contain the assistant.

Copy `pxe-fedora44-assist-0.1.0-x86_64.iso` to `/var/www/aux.1-s.es/isos/` and verify its SHA256:

```bash
cd /var/www/aux.1-s.es/isos
printf '%s  %s\n' 17b55b5237d76756e890cc017bed10a09220f553495970158e4a6d1932dbbc8a pxe-fedora44-assist-0.1.0-x86_64.iso | sha256sum -c -
```

From the command bundle directory, mount only this ISO read-only from persistent disk on Fedora with SELinux enabled:

```bash
sudo bash deploy.sh disk --mode mount \
  --cache /var/www/aux.1-s.es/isos \
  --output /var/www/aux.1-s.es/html \
  --only pxe-fedora44-assist \
  --mount-context system_u:object_r:httpd_sys_content_t:s0 --verbose

sudo bash generate.sh \
  --cache /var/www/aux.1-s.es/isos \
  --output /var/www/aux.1-s.es/html \
  --pxe-url http://pxe.1-s.es --verbose
```

`--mount-context` is optional and applies only to ISO mounts on a SELinux-enabled host. It labels the mounted filesystem for HTTP reads without changing ISO bytes or disabling SELinux. The webroot and its parent directories must already allow Nginx traversal. No recursive ownership change to `/var/www` is needed. Reusing a mount created with a different context requires deployment to remount it; the context is stored in the deployment state.

Assistance versions appear first under **0. Remote assistance** in both catalogs
and iPXE, ordered newest first. Boot detection requires `aux.assist` in the media's
GRUB configuration and the original kernel, initrd and runtime paths. Live media
uses its own HTTP rootfs and RAM overlay; legacy installer rescue uses stage2.
The latest complete recipe compatible with client firmware/architecture is the
iPXE default after **60 seconds**. Any key stops the timer; returning or cancelling
does not restart it. Without a compatible deployed image the menu waits indefinitely.
Remote SSH still requires consent in the running ISO.

iPXE uses black background/green console text, cyan menus with indigo text, and
red startup/error messages. Indigo uses basic ANSI blue on firmware text consoles;
the script avoids RGB escape sequences which can reset their attributes.
The USB image first displays a GRUB menu for **5 seconds** before iPXE.

Check the published files before booting a client:

```bash
curl -fI http://pxe.1-s.es/pxe-fedora44-assist-0.1.0-x86_64/images/pxeboot/vmlinuz
curl -fI http://pxe.1-s.es/pxe-fedora44-assist-0.1.0-x86_64/images/pxeboot/initrd.img
curl -fI http://pxe.1-s.es/pxe-fedora44-assist-0.1.0-x86_64/images/install.img
curl -fsS http://pxe.1-s.es/menu.ipxe | grep 'aux.assist'
```

RAM remains an alternative: replace `disk --mode mount` with `ram --ram-dir /dev/shm/aux-pxe`. Provide sufficient tmpfs capacity for the 1.35 GB ISO, and label the tmpfs directory for HTTP traversal when SELinux requires it. Disk mounts and RAM mounts disappear after reboot: rerun deploy, then generate, before booting clients. The disk ISO remains in the cache.

After network boot the client selects the SysAdmin and explicitly authorizes SSH access with a public key. Port 2222 must be reachable over the intended intranet/VPN route. The client sees the shared terminal and can close access. This rescue assistance environment does not automatically install Fedora or configure a VPN.

## Optional USB client

`usb/aux-ipxe-usb.img` boots BIOS or x86_64 UEFI, obtains DHCP and chains the configured menu automatically. The custom UEFI executable is unsigned. `usb/README.md` covers writing the image, checksums, firmware requirements and diagnostics. `usb/build.sh` rebuilds this client independently; none of the three server commands runs it.

When the prebuilt image is present beside the source commands, generation publishes it at `downloads/usb/aux-ipxe-usb.img`, adds a normal download link to both catalogs and includes it in the command bundle and sitemaps. A minimal source/templates package without `usb/` still generates normally, without advertising a missing USB image.

## Generated files

| Host/output | Files |
| --- | --- |
| AUX visual index | `index.php`, `index.html`, explicit alias `index-aux.php` |
| PXE terminal index | `cli.html`, explicit alias `index-pxe.html` |
| Boot menu | `menu.ipxe`, grouped into Distros / Netboot & Install, Distros / Live and Tools, gated by architecture/firmware |
| Image files | `contents.html`, `contents/<id>/*.html`, `contents/<id>/files.tsv` |
| Inventory/downloads | `catalog.json`, `files/*.html`, `SHA256SUMS`, `downloads/isos.tsv` |
| AUX sitemap | `sitemaps.xml`, alias `sitemaps-aux.xml` |
| PXE sitemap | `sitemaps-pxe.xml` — contains only PXE host URLs |

Existing Nginx index mappings can continue using `index.php` for AUX and `cli.html` for PXE. Both catalogs and command pages have ordinary HTML links. PXE uses no JavaScript or external assets; inline terminal colors are optional in browsers that support CSS. Links can navigate the same HTML directly.

```bash
links http://pxe.1-s.es/
wget -c https://b.1-s.es/PUBLISHED_IMAGE.iso
curl -fL -C - -O https://b.1-s.es/PUBLISHED_IMAGE.iso
```

Nested file paths are preserved and URL-encoded. Download pages include explicit filenames, resumable commands, hashes and links into image contents. An orphan prepared tree can be browsed and considered for boot even when no ISO download file is published. Stale trees recorded against a different image hash are excluded until redeployed.

## Boot recipes

Generation checks the complete local file set for each supported recipe. A recipe check is separate from a successful BIOS/UEFI/ARM hardware boot.

| Media | Required files / behavior |
| --- | --- |
| Debian/Kali network installer | Actual netboot `linux` + `initrd.gz`; CD-ROM/netinst ISO initrds alone are not advertised as network installers |
| Debian-style Live / Clonezilla / GParted | `live/vmlinuz*`, `live/initrd*`, `live/filesystem.squashfs`; HTTP numeric IPv4 `fetch=` |
| Ubuntu / Boot Repair | Casper kernel/initrd, SquashFS and published ISO; an Ubuntu netboot archive requires the matching published server ISO |
| Fedora Live | `images/pxeboot` kernel/initrd and `LiveOS/squashfs.img`; dracut retrieves the published SquashFS |
| Fedora netinst | Kernel/initrd and the original stage2 image (`.treeinfo` when present, otherwise `images/install.img`); known upstream `/os/` trees provide packages, otherwise Anaconda uses its release repositories |
| Arch | Kernel, initramfs and `arch/x86_64/airootfs.sfs` or `.erofs`, with `archiso_http_srv=` |
| Native tools / boot clients | Local EFI/BIOS payloads, including discovered Memtest binaries; each menu item has matching firmware gating |

Kernel recipes name their initrd explicitly for EFI boot. When Fedora media includes `.treeinfo`, it must be accessible over HTTP; boot media without it uses Anaconda’s `images/install.img` fallback. Debian Live uses a numeric IPv4 URL; `--live-url http://SERVER_IP` provides it, otherwise generation resolves the PXE hostname. That IP endpoint must serve the same public tree. If resolution fails, those Live entries remain absent from the menu.

Unsupported/incomplete media remain downloadable and show their recipe status. No generic ISO-to-iPXE fallback is emitted. DBAN stays download-only. Secure Boot requires an appropriately trusted boot chain.

```text
dhcp
chain http://pxe.1-s.es/menu.ipxe
```

Primary references: iPXE https://ipxe.org/appnote/debian_preseed; Debian https://www.debian.org/releases/stable/amd64/ch04s05.en.html and https://manpages.debian.org/bookworm/live-boot-doc/live-boot.7.en.html; Anaconda https://anaconda-installer.readthedocs.io/en/latest/user-guide/boot-options.html; dracut https://dracut-ng.github.io/dracut/man/dracut.cmdline.7.html.

The hosted Site displays the source catalog and distributes this bundle. Downloads, deployment, crawling and hardware boot tests run on the actual Linux server.

## AUX / PXE navigation

The `PXE_` green pixel terminal wordmark under the AUX logo opens the configured PXE portal. The first text-catalog option is the `aux. /` link back to the visual portal. Both catalogs expose "Browse ISO files" and each deployed image has its own contents link. Directory, parent and image-index links stay on the current host; the wordmarks on a directory page can switch portals at that same directory. The same generated HTML tree is served by both Excalibur hostnames. Direct payload links still use Excalibur and complete-image downloads still default to Bastion. All navigation uses ordinary HTML anchors and works without CSS or JavaScript.

## Technician platform

TEC source is in tec/, distributed as tec-platform-5.0.8.zip. Unpack that ZIP into
`/var/www/aux.1-s.es/`; TEC public PHP lives in `web/`, alongside AUX/PXE `html/`
and the persistent `isos/` cache. Private JSON remains in `/var/lib/aux-assist`.
AUX/PXE generation links to https://tec.1-s.es and never writes into TEC's web/.
The combined vhost template is `nginx/aux-pxe-tec.conf.example`; it replaces the
separate vhosts and retains the full MIME table, including CSS and JavaScript.
Only html/ and web/ are public roots; cache metadata and parent administration
files are not served. The dedicated TEC pool uses `/run/php-fpm/tec.sock` and
`tec@1wise.es` through the local OVH relay. Keep AUX_ASSIST_* variable names.
See the TEC package's README, MAIL.md and pool/relay templates for installation.
