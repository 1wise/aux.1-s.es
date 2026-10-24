#!/usr/bin/env bash

# ==============================================================================
# fast-boot.sh   03/11/2026 00:00 
# FULL PHYSICAL DEPLOYMENT - HEAVY DUTY MODE (OVH / GCP) + NATIVE PXE
# Author: https://www.alawise.es/1-s (1-s.eu) | Environment: Debian Forky
# ENGINE: Multi-Arch (amd64/arm64/raspi), Live Systems, Flat Physical Extraction.
# STRUCTURE: Absolute Flat Root (1 ISO = 1 Folder in root).
# RULES: Sys Vars (Catalan abbrev), App Vars (Spanish abbrev), UI/Comments (English).
# ==============================================================================

# System Variables (Catalan abbreviated)
DIR_TREB="/var/www/html/boot"
DIR_ARREL="/var/www"

# Colors (Clean ASCII Terminal)
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 [SYS-OPS] Starting Total Multi-Arch Deployment Sync in $DIR_TREB...${NC}"

# 1. Check dependencies (Added 7z for stubborn hybrid ISOs fallback)
for cmd_obj in wget curl tar unzip rsync stat bsdtar numfmt xz 7z; do
    if ! command -v $cmd_obj &> /dev/null; then
        echo -e "${RED}❌ Missing $cmd_obj. Install with: apt install libarchive-tools curl coreutils xz-utils unzip wget 7zip $cmd_obj${NC}"
        exit 1
    fi
done

# Check PXE dependencies (iPXE only, memdisk removed for native hardware compatibility)
if [ ! -f "/usr/lib/ipxe/ipxe.efi" ]; then
    echo -e "${YELLOW}⚠️  Installing native Debian iPXE packages...${NC}"
    apt update -y && apt install -y ipxe
fi

# ==============================================================================
# 2. RAW DOWNLOAD URLS (x86_64, aarch64/arm64, rpi, Live Systems)
# Strictly ISOs and Archives to prevent flat-folder collisions.
# Native BINs used for memtest to avoid RAM injections on old i3/i5.
# ==============================================================================
RAW_URLS="
# --- 1. DEBIAN ECOSYSTEM (Testing/Trixie & Stable 13.3) ---
https://cdimage.debian.org/cdimage/weekly-live-builds/amd64/iso-hybrid/debian-testing-amd64-live-gnome.iso
https://cdimage.debian.org/cdimage/weekly-live-builds/amd64/iso-hybrid/debian-testing-amd64-live-xfce.iso
https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/debian-live-13.3.0-amd64-gnome.iso
https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/debian-live-13.3.0-amd64-xfce.iso
https://cdimage.debian.org/cdimage/daily-builds/daily/current/amd64/iso-cd/debian-testing-amd64-netinst.iso
https://cdimage.debian.org/cdimage/daily-builds/daily/current/arm64/iso-cd/debian-testing-arm64-netinst.iso
https://cdimage.debian.org/cdimage/release/13.3.0/amd64/iso-cd/debian-13.3.0-amd64-netinst.iso
https://cdimage.debian.org/cdimage/release/13.3.0/arm64/iso-cd/debian-13.3.0-arm64-netinst.iso

# --- 2. FEDORA ECOSYSTEM (41 Live Workstation & Server Netboot) ---
https://download.fedoraproject.org/pub/fedora/linux/releases/41/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-41-1.4.iso
https://download.fedoraproject.org/pub/fedora/linux/releases/41/Workstation/aarch64/iso/Fedora-Workstation-Live-aarch64-41-1.4.iso
https://download.fedoraproject.org/pub/fedora/linux/releases/41/Server/x86_64/iso/Fedora-Server-netinst-x86_64-41-1.4.iso
https://download.fedoraproject.org/pub/fedora/linux/releases/41/Server/aarch64/iso/Fedora-Server-netinst-aarch64-41-1.4.iso

# --- 3. UBUNTU ECOSYSTEM (Plucky 25.10 & Noble 24.04 LTS) ---
https://releases.ubuntu.com/25.10/ubuntu-25.10-desktop-amd64.iso
https://releases.ubuntu.com/25.10/ubuntu-25.10-live-server-amd64.iso
https://old-releases.ubuntu.com/releases/plucky/ubuntu-25.04-live-server-arm64.iso
https://releases.ubuntu.com/24.04/ubuntu-24.04.4-desktop-amd64.iso
https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso
https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04.4-live-server-arm64.iso
https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz

# --- 4. ARCH & ALPINE (Rolling & Lightweight) ---
https://ftp.rediris.es/mirror/archlinux/iso/2026.03.01/archlinux-x86_64.iso
https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/x86_64/alpine-standard-3.23.3-x86_64.iso
https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/alpine-standard-3.23.3-aarch64.iso
https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/alpine-rpi-3.23.3-aarch64.tar.gz

# --- 5. GENTOO (Sources & LiveGUI) ---
https://distfiles.gentoo.org/releases/amd64/autobuilds/20260215T164556Z/livegui-amd64-20260215T164556Z.iso
https://distfiles.gentoo.org/releases/amd64/autobuilds/20260215T164556Z/install-amd64-minimal-20260215T164556Z.iso

# --- 6. TOOLS, MISC & KALI ---
https://cdimage.kali.org/current/kali-linux-2025.4-installer-purple-amd64.iso
https://cdimage.kali.org/current/kali-linux-2025.4-installer-netinst-amd64.iso
https://cdimage.kali.org/current/kali-linux-2025.4-installer-netinst-arm64.iso
https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso
https://downloads.sourceforge.net/project/clonezilla/clonezilla_live_stable/3.1.2-22/clonezilla-live-3.1.2-22-amd64.iso
https://downloads.sourceforge.net/project/gparted/gparted-live-stable/1.6.0-1/gparted-live-1.6.0-1-amd64.iso
https://sysresccd.org/downloads/systemrescue-11.00-amd64.iso
https://github.com/netbootxyz/netboot.xyz/releases/latest/download/netboot.xyz.kpxe
https://github.com/netbootxyz/netboot.xyz/releases/latest/download/netboot.xyz.efi
https://github.com/netbootxyz/netboot.xyz/releases/latest/download/netboot.xyz-arm64.efi
https://downloads.sourceforge.net/project/boot-repair-cd/boot-repair-disk-64bit.iso
https://www.memtest.org/download/v7.20/mt86plus_7.20_32.iso.zip
https://www.memtest.org/download/v7.20/mt86plus_7.20_64.iso.zip
https://www.memtest.org/download/v7.20/mt86plus_7.20_64.grub.iso.zip
https://downloads.sourceforge.net/project/dban/dban/dban-2.3.0/dban-2.3.0_i586.iso
https://downloads.sourceforge.net/project/supergrub2/2.06s1/super_grub2_disk_hybrid_2.06s1.iso
"

UNIQUE_URLS=$(echo "$RAW_URLS" | grep -Eo 'https?://[^ ]+' | sort -u)

echo -e "\n${YELLOW}⬇️  Syncing Arsenal (Absolute Flat Root)...${NC}"

# ==============================================================================
# 3. DIRECT DOWNLOAD ENGINE AND IN-PLACE EXTRACTION
# ==============================================================================
for url_obj in $UNIQUE_URLS; do
    nom_arx=$(basename "$url_obj")
    rut_arx="$DIR_TREB/$nom_arx"
    
    echo -e "${CYAN}➜ Target: ${NC}$nom_arx"
    
    rm -f "$DIR_TREB"/download* "$DIR_TREB"/*use_mirror* 2>/dev/null
    
    mod_ant=$(stat -c %Y "$rut_arx" 2>/dev/null || echo "0")
    tam_loc=$(stat -c %s "$rut_arx" 2>/dev/null || echo "0")
    tam_rem=$(curl -sIL -A "Mozilla/5.0" "$url_obj" | grep -i '^content-length:' | tail -n 1 | awk '{print $2}' | tr -d '\r')
    
    # [SYS-OPS] SourceForge / Mirror Fake-Size Protection
    # Fixes infinite re-download loops for URLs that return small HTML redirect pages.
    if [[ -z "$tam_rem" ]] || [[ "$tam_rem" -lt 1000000 ]]; then
        if [[ "$tam_loc" -gt 50000000 ]]; then
            echo -e "  ${YELLOW}⚠️ Remote size hidden/small (Mirror issue). Assuming local cache is valid.${NC}"
            tam_rem="$tam_loc"
        fi
    fi
    
    # [SYS-OPS] Robust File Downloader with Fallback Cache
    if [[ -z "$tam_rem" ]]; then
        echo -e "  ${RED}⚠️ Remote file unreachable or 404.${NC}"
        if [[ "$tam_loc" -eq 0 ]]; then
            echo -e "  ${RED}❌ No local cache available. Skipping...${NC}\n"
            continue
        else
            echo -e "  ${GREEN}✅ Using existing local cache as fallback.${NC}"
        fi
    elif [[ "$tam_loc" != "$tam_rem" ]]; then
        echo -e "  ${YELLOW}⬇️ Downloading/Updating file directly to root...${NC}"
        if wget -q --show-progress -U "Mozilla/5.0" -O "$rut_arx.tmp" "$url_obj"; then
            mv "$rut_arx.tmp" "$rut_arx"
        else
            echo -e "  ${RED}❌ Download interrupted or failed. Cleaning up...${NC}"
            rm -f "$rut_arx.tmp"
            if [[ "$tam_loc" -eq 0 ]]; then 
                echo ""
                continue
            fi
        fi
    fi
    
    mod_nue=$(stat -c %Y "$rut_arx" 2>/dev/null || echo "0")
    tam_nue=$(stat -c %s "$rut_arx" 2>/dev/null || echo "0")
    
    # Extraction Logic (Exact Base Name in Root)
    ext_req=0
    if [[ "$mod_ant" != "$mod_nue" ]] || [[ "$tam_loc" != "$tam_nue" ]]; then ext_req=1; fi
    
    if [[ "$rut_arx" == *.iso ]] || [[ "$rut_arx" == *.img.xz ]]; then
        nom_iso=$(basename "$rut_arx" | sed -e 's/\.iso$//' -e 's/\.img\.xz$//')
        dir_ext="$DIR_TREB/$nom_iso"
        if [ ! -d "$dir_ext" ]; then ext_req=1; fi
    elif [[ "$rut_arx" == *.zip ]]; then
        nom_iso=$(basename "$rut_arx" .iso.zip)
        dir_ext="$DIR_TREB/$nom_iso"
        if [ ! -d "$dir_ext" ]; then ext_req=1; fi
    fi

    if [[ "$tam_nue" == "0" ]]; then
        echo -e "${RED}  ❌ Download failed.${NC}\n"
    elif [ "$ext_req" -eq 1 ]; then
        echo -e "${GREEN}  ✅ File processed or extraction forced.${NC}"
        
        if [[ "$rut_arx" == *.tar.gz ]]; then
            tar -xzf "$rut_arx" -C "$DIR_TREB"
        elif [[ "$rut_arx" == *.zip ]]; then
            echo -e "  ${YELLOW}📦 Extracting ZIP to $dir_ext...${NC}"
            unzip -q -o "$rut_arx" -d "$DIR_TREB"
            # Extract nested ISO (e.g., Memtest)
            for iso_unzip in "$DIR_TREB"/*.iso; do
                if [[ "$iso_unzip" == *"${nom_arx%.iso.zip}"* ]]; then
                    dir_ext="$DIR_TREB/$(basename "$iso_unzip" .iso)"
                    rm -rf "$dir_ext" && mkdir -p "$dir_ext"
                    bsdtar -xf "$iso_unzip" -C "$dir_ext" 2>/dev/null || true
                    
                    # [SYS-OPS] Fallback for stubborn Hybrid ISOs
                    if [ -z "$(ls -A "$dir_ext" 2>/dev/null)" ]; then
                        echo -e "  ${YELLOW}⚠️ bsdtar extracted nothing. Using 7z fallback...${NC}"
                        7z x -y "$iso_unzip" -o"$dir_ext" >/dev/null 2>&1
                    fi
                    chmod -R u+w "$dir_ext" 2>/dev/null || true
                fi
            done
        elif [[ "$rut_arx" == *.iso ]] || [[ "$rut_arx" == *.img.xz ]]; then
            echo -e "  ${YELLOW}💿 Extracting filesystem to: $dir_ext${NC}"
            rm -rf "$dir_ext" && mkdir -p "$dir_ext"
            bsdtar -xf "$rut_arx" -C "$dir_ext" 2>/dev/null || true
            
            # [SYS-OPS] Fallback for stubborn Hybrid ISOs (Clonezilla, SuperGrub, BootRepair)
            if [ -z "$(ls -A "$dir_ext" 2>/dev/null)" ]; then
                echo -e "  ${YELLOW}⚠️ bsdtar extracted nothing. Using 7z fallback...${NC}"
                7z x -y "$rut_arx" -o"$dir_ext" >/dev/null 2>&1
            fi
            chmod -R u+w "$dir_ext" 2>/dev/null || true
        fi
        echo "" 
    else
        echo -e "  ${GREEN}⏭️  File is up to date and extracted.${NC}\n"
    fi
done

# ==============================================================================
# 4. SMART MANUAL ISO INTERCEPTOR (DROP-IN TORRENT TYPE)
# ==============================================================================
shopt -s nullglob
for iso_man in "$DIR_TREB"/*.iso; do
    nom_iso=$(basename "$iso_man")
    dir_ext="$DIR_TREB/${nom_iso%.iso}"
    
    if [ ! -d "$dir_ext" ]; then
        echo -e "${CYAN}➜ Routing manual ISO (Torrent/Drop-in): ${NC}$nom_iso"
        echo -e "  ${YELLOW}💿 Extracting filesystem in place...${NC}"
        mkdir -p "$dir_ext"
        bsdtar -xf "$iso_man" -C "$dir_ext" 2>/dev/null || true
        
        # [SYS-OPS] Fallback for stubborn Hybrid ISOs
        if [ -z "$(ls -A "$dir_ext" 2>/dev/null)" ]; then
            echo -e "  ${YELLOW}⚠️ bsdtar extracted nothing. Using 7z fallback...${NC}"
            7z x -y "$iso_man" -o"$dir_ext" >/dev/null 2>&1
        fi
        chmod -R u+w "$dir_ext" 2>/dev/null || true
        echo ""
    fi
done
shopt -u nullglob

# ==============================================================================
# 5. STRICT FOLDER NORMALIZATION FOR SPECIFIC TOOLS
# ==============================================================================
cd "$DIR_TREB" || exit

# Memtest86+ Native Binary Extraction
for dir_mt in mt86plus_*; do
    if [ -d "$dir_mt" ]; then
        efi_file=$(find "$dir_mt" -type f -iname "*.efi" | head -n 1)
        if [ -n "$efi_file" ]; then cp -f "$efi_file" "$dir_mt/memtest.efi"; fi
        
        bin_file=$(find "$dir_mt" -type f -iname "*.bin" | head -n 1)
        if [ -n "$bin_file" ]; then cp -f "$bin_file" "$dir_mt/memtest.bin"; fi
    fi
done

# DBAN Rootfs normalization
for d in dban-*/; do 
    if [ -d "$d" ] && [ ! -d "$d/rootfs" ]; then
        mkdir -p "$d/rootfs"
        mv "$d"/* "$d/rootfs/" 2>/dev/null || true
    fi
done

cd - > /dev/null

# ==============================================================================
# 5.5. KERNEL NORMALIZATION (Fixes 404 Kernel errors in iPXE)
# ==============================================================================
echo -e "${YELLOW}⚙️  [SYS-OPS] Normalizing kernels for iPXE compatibility...${NC}"
find "$DIR_TREB" -maxdepth 3 -type d \( -name "live" -o -name "casper" -o -name "install.amd" -o -name "install.a64" -o -name "pxeboot" -o -name "boot" \) | while read -r dir_k; do
    [ ! -f "$dir_k/vmlinuz" ] && ls "$dir_k"/vmlinuz* >/dev/null 2>&1 && cp "$dir_k"/vmlinuz* "$dir_k/vmlinuz" 2>/dev/null | head -n 1
    [ ! -f "$dir_k/vmlinuz" ] && [ -f "$dir_k/linux" ] && cp "$dir_k/linux" "$dir_k/vmlinuz" 2>/dev/null
    [ ! -f "$dir_k/initrd.img" ] && ls "$dir_k"/initrd.img* >/dev/null 2>&1 && cp "$dir_k"/initrd.img* "$dir_k/initrd.img" 2>/dev/null | head -n 1
    [ ! -f "$dir_k/initrd.gz" ] && ls "$dir_k"/initrd.gz* >/dev/null 2>&1 && cp "$dir_k"/initrd.gz* "$dir_k/initrd.gz" 2>/dev/null | head -n 1
    [ ! -f "$dir_k/initrd" ] && ls "$dir_k"/initrd* >/dev/null 2>&1 && cp "$dir_k"/initrd* "$dir_k/initrd" 2>/dev/null | head -n 1
done

# ==============================================================================
# 6. SITEMAPS.XML GENERATOR (Direct Physical Scanning)
# ==============================================================================
echo -e "${YELLOW}🗺️  [SYS-OPS] Building XML map of the repository (Physical Architecture)...${NC}"
cat << 'EOF' > "$DIR_TREB/sitemaps.xml"
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://aux.1-s.eu/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
EOF

cd "$DIR_TREB" || exit
find . -maxdepth 1 -type d | sed 's|^./||' | grep -v "^\.$" | while read -r dir_arch; do
    echo "  <url>" >> "$DIR_TREB/sitemaps.xml"
    echo "    <loc>https://aux.1-s.eu/${dir_arch}/</loc>" >> "$DIR_TREB/sitemaps.xml"
    echo "    <changefreq>weekly</changefreq>" >> "$DIR_TREB/sitemaps.xml"
    echo "    <priority>0.8</priority>" >> "$DIR_TREB/sitemaps.xml"
    echo "  </url>" >> "$DIR_TREB/sitemaps.xml"
done
echo "</urlset>" >> "$DIR_TREB/sitemaps.xml"

# ==============================================================================
# 7. PXE ECOSYSTEM INJECTION AND MASTER MENU (FLAT PATHS)
# ==============================================================================
echo -e "\n${CYAN}🌐 [SYS-OPS] Deploying structured Multi-Arch iPXE Menu...${NC}"

if [ -f "/usr/lib/ipxe/ipxe.efi" ]; then
    cp /usr/lib/ipxe/ipxe.efi "$DIR_TREB/"
    cp /usr/lib/ipxe/undionly.kpxe "$DIR_TREB/"
fi

cat << 'EOF' > "$DIR_TREB/menu.ipxe"
#!ipxe

cpair --foreground 4 --background 0 0 ||
cpair --foreground 0 --background 4 6 ||
cpair --foreground 4 --background 0 6 ||

:start
menu [ 1-s.eu | ARSENAL CLOUD W.A.N. ]
item --gap -- ===================================================
item --gap -- [ 1. DEBIAN ECOSYSTEM ]
item debian_stable_x86 [>] Debian 13.3.0 Stable Netboot (x86_64)
item debian_stable_arm [>] Debian 13.3.0 Stable Netboot (aarch64)
item debian_forky_x86  [>] Debian Forky / Trixie Netboot (x86_64)
item debian_forky_arm  [>] Debian Forky / Trixie Netboot (aarch64)
item deb_live_gnm_13   [>] Debian 13.3.0 Live GNOME (RAM/HTTP)
item deb_live_xfc_13   [>] Debian 13.3.0 Live XFCE (RAM/HTTP)
item deb_live_gnm_tst  [>] Debian Testing Live GNOME (RAM/HTTP)
item deb_live_xfc_tst  [>] Debian Testing Live XFCE (RAM/HTTP)
item --gap --
item --gap -- [ 2. FEDORA ECOSYSTEM ]
item fedora_41_wrk_x86 [>] Fedora 41 Workstation Live (x86_64)
item fedora_41_wrk_arm [>] Fedora 41 Workstation Live (aarch64)
item fedora_41_srv_x86 [>] Fedora 41 Server Netboot (x86_64)
item fedora_41_srv_arm [>] Fedora 41 Server Netboot (aarch64)
item --gap --
item --gap -- [ 3. UBUNTU ECOSYSTEM ]
item ubuntu_2510_desk  [>] Ubuntu 25.10 Plucky Desktop Live (x86_64)
item ubuntu_2510_x86   [>] Ubuntu 25.10 Plucky Live Server (x86_64)
item ubuntu_2510_arm   [>] Ubuntu 25.10 Plucky Live Server (aarch64)
item ubuntu_2404_desk  [>] Ubuntu 24.04.4 Noble Desktop Live (x86_64)
item ubuntu_2404_x86   [>] Ubuntu 24.04.4 Noble Live Server (x86_64)
item ubuntu_2404_arm   [>] Ubuntu 24.04.4 Noble Live Server (aarch64)
item ubuntu_raspi      [>] Ubuntu 24.04.4 Server (Raspberry Pi aarch64)
item --gap --
item --gap -- [ 4. LIGHTWEIGHT & ROLLING ]
item arch              [>] Arch Linux Live/Netboot (x86_64)
item alpine_x86        [>] Alpine Linux Live (v3.23 LTS x86_64)
item alpine_arm        [>] Alpine Linux Live (v3.23 LTS aarch64)
item --gap --
item --gap -- [ 5. GENTOO LINUX ]
item gentoo_gui        [>] Gentoo LiveGUI (x86_64 HTTP Fetch)
item gentoo_min        [>] Gentoo Minimal Install (x86_64)
item --gap --
item --gap -- [ 6. TOOLS & RESCUE SUITE ]
item utils_menu        [+] Open Utilities and Rescue Menu...
item netbootxyz        [>] Launch Netboot.xyz (Global Bypass)
item --gap -- ===================================================
item shell             [>] iPXE Command Shell (Debug)
item reboot            [!] Reboot System
item exit              [X] Exit to local disk

choose target && goto ${target} || goto start

:utils_menu
menu [ 1-s.eu | TOOLS & RESCUE SUITE ]
item --gap -- --- KALI LINUX SUITE ---
item kali_live         [>] Kali Linux Live (Immediate Audit x86_64)
item kali_purple       [>] Install Kali Purple (Defensive/Blue Team x86_64)
item kali_net_amd      [>] Install Kali Netinst (x86_64)
item kali_net_arm      [>] Install Kali Netinst (aarch64)
item --gap --
item --gap -- --- SYSTEM TOOLS (Native HTTP Live) ---
item proxmox           [>] Proxmox VE 9.1 Installer (Hypervisor x86_64)
item gparted           [>] GParted Live (Partition Manager)
item clonezilla        [>] Clonezilla Live (Cloning and Backup)
item sysrescue         [>] SystemRescue CD (Root Toolkit)
item bootrepair        [>] Boot Repair CD (Repair GRUB/UEFI)
item --gap --
item --gap -- --- MEMTEST86+ (Native PXE Binaries) ---
item memtest64_efi     [>] Memtest86+ v7.20 (UEFI 64-bits EFI)
item memtest32_efi     [>] Memtest86+ v7.20 (UEFI 32-bits EFI)
item memtest64_bios    [>] Memtest86+ v7.20 (BIOS Legacy 64-bits Native BIN)
item memtest32_bios    [>] Memtest86+ v7.20 (BIOS Legacy 32-bits Native BIN)
item --gap --
item --gap -- --- BIOS LEGACY ONLY ---
item dban              [>] DBAN (Secure Disk Wipe - Native Boot)
item supergrub         [>] Super GRUB2 Disk (Force Boot - Sanboot)
item --gap -- ===================================================
item start             [<] Back to Main Menu

choose target && goto ${target} || goto utils_menu

# =========================================================================
# LOAD BLOCKS - DEBIAN
# =========================================================================
:debian_stable_x86
set base http://pxeboot.1-s.eu/debian-13.3.0-amd64-netinst/install.amd
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:debian_stable_arm
set base http://pxeboot.1-s.eu/debian-13.3.0-arm64-netinst/install.a64
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:debian_forky_x86
set base http://pxeboot.1-s.eu/debian-testing-amd64-netinst/install.amd
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:debian_forky_arm
set base http://pxeboot.1-s.eu/debian-testing-arm64-netinst/install.a64
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:deb_live_gnm_13
set base http://pxeboot.1-s.eu/debian-live-13.3.0-amd64-gnome/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/debian-live-13.3.0-amd64-gnome/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:deb_live_xfc_13
set base http://pxeboot.1-s.eu/debian-live-13.3.0-amd64-xfce/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/debian-live-13.3.0-amd64-xfce/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:deb_live_gnm_tst
set base http://pxeboot.1-s.eu/debian-testing-amd64-live-gnome/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/debian-testing-amd64-live-gnome/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:deb_live_xfc_tst
set base http://pxeboot.1-s.eu/debian-testing-amd64-live-xfce/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/debian-testing-amd64-live-xfce/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

# =========================================================================
# LOAD BLOCKS - FEDORA
# =========================================================================
:fedora_41_wrk_x86
set base http://pxeboot.1-s.eu/Fedora-Workstation-Live-x86_64-41-1.4/images/pxeboot
kernel ${base}/vmlinuz root=live:http://pxeboot.1-s.eu/Fedora-Workstation-Live-x86_64-41-1.4.iso ro rd.live.image ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:fedora_41_wrk_arm
set base http://pxeboot.1-s.eu/Fedora-Workstation-Live-aarch64-41-1.4/images/pxeboot
kernel ${base}/vmlinuz root=live:http://pxeboot.1-s.eu/Fedora-Workstation-Live-aarch64-41-1.4.iso ro rd.live.image ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:fedora_41_srv_x86
set base http://pxeboot.1-s.eu/Fedora-Server-netinst-x86_64-41-1.4/images/pxeboot
kernel ${base}/vmlinuz inst.repo=http://download.fedoraproject.org/pub/fedora/linux/releases/41/Server/x86_64/os/ ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:fedora_41_srv_arm
set base http://pxeboot.1-s.eu/Fedora-Server-netinst-aarch64-41-1.4/images/pxeboot
kernel ${base}/vmlinuz inst.repo=http://download.fedoraproject.org/pub/fedora/linux/releases/41/Server/aarch64/os/ ip=dhcp
initrd ${base}/initrd.img
boot || goto error

# =========================================================================
# LOAD BLOCKS - UBUNTU
# =========================================================================
:ubuntu_2510_desk
set base http://pxeboot.1-s.eu/ubuntu-25.10-desktop-amd64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-25.10-desktop-amd64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_2510_x86
set base http://pxeboot.1-s.eu/ubuntu-25.10-live-server-amd64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-25.10-live-server-amd64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_2510_arm
set base http://pxeboot.1-s.eu/ubuntu-25.04-live-server-arm64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-25.04-live-server-arm64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_2404_desk
set base http://pxeboot.1-s.eu/ubuntu-24.04.4-desktop-amd64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-24.04.4-desktop-amd64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_2404_x86
set base http://pxeboot.1-s.eu/ubuntu-24.04.4-live-server-amd64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-24.04.4-live-server-amd64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_2404_arm
set base http://pxeboot.1-s.eu/ubuntu-24.04.4-live-server-arm64/casper
kernel ${base}/vmlinuz ip=dhcp url=http://pxeboot.1-s.eu/ubuntu-24.04.4-live-server-arm64.iso
initrd ${base}/initrd
boot || goto error

:ubuntu_raspi
echo [!] Ubuntu Raspi is a preinstalled image, use it to flash SD/USB locally.
prompt Press any key to return...
goto utils_menu

# =========================================================================
# LOAD BLOCKS - ARCH/ALPINE
# =========================================================================
:arch
set base http://pxeboot.1-s.eu/archlinux-x86_64/arch/boot/x86_64
kernel ${base}/vmlinuz-linux initrd=initramfs-linux.img ip=dhcp archiso_http_srv=http://pxeboot.1-s.eu/archlinux-x86_64/
initrd ${base}/initramfs-linux.img
boot || goto error

:alpine_x86
set base http://pxeboot.1-s.eu/alpine-standard-3.23.3-x86_64/boot
kernel ${base}/vmlinuz-lts ip=dhcp modloop=http://pxeboot.1-s.eu/alpine-standard-3.23.3-x86_64/boot/modloop-lts alpine_repo=http://dl-cdn.alpinelinux.org/alpine/v3.23/main/
initrd ${base}/initramfs-lts
boot || goto error

:alpine_arm
set base http://pxeboot.1-s.eu/alpine-standard-3.23.3-aarch64/boot
kernel ${base}/vmlinuz-lts ip=dhcp modloop=http://pxeboot.1-s.eu/alpine-standard-3.23.3-aarch64/boot/modloop-lts alpine_repo=http://dl-cdn.alpinelinux.org/alpine/v3.23/main/
initrd ${base}/initramfs-lts
boot || goto error

# =========================================================================
# LOAD BLOCKS - GENTOO
# =========================================================================
:gentoo_gui
echo Loading Gentoo LiveGUI (HTTP Fetch)...
set base http://pxeboot.1-s.eu/livegui-amd64-20260215T164556Z/boot
kernel ${base}/vmlinuz root=/dev/ram0 init=/linuxrc looptype=squashfs loop=/image.squashfs cdroot initrd=initrd.img fetch=http://pxeboot.1-s.eu/livegui-amd64-20260215T164556Z/image.squashfs
initrd ${base}/initrd.img
boot || goto error

:gentoo_min
echo Loading Gentoo Minimal Install...
set base http://pxeboot.1-s.eu/install-amd64-minimal-20260215T164556Z/boot
kernel ${base}/vmlinuz root=/dev/ram0 init=/linuxrc looptype=squashfs loop=/image.squashfs cdroot initrd=initrd.img fetch=http://pxeboot.1-s.eu/install-amd64-minimal-20260215T164556Z/image.squashfs
initrd ${base}/initrd.img
boot || goto error

# =========================================================================
# LOAD BLOCKS - KALI LINUX SUITE
# =========================================================================
:kali_live
# Ajustado para que cargue desde la raíz con el nombre del archivo de torrent/manual
set base http://pxeboot.1-s.eu/kali-linux-2025.4-live-amd64/live
kernel ${base}/vmlinuz boot=live netboot=http components fetch=http://pxeboot.1-s.eu/kali-linux-2025.4-live-amd64/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:kali_purple
set base http://pxeboot.1-s.eu/kali-linux-2025.4-installer-purple-amd64/install.amd
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:kali_net_amd
set base http://pxeboot.1-s.eu/kali-linux-2025.4-installer-netinst-amd64/install.amd
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

:kali_net_arm
set base http://pxeboot.1-s.eu/kali-linux-2025.4-installer-netinst-arm64/install.a64
kernel ${base}/vmlinuz vga=788 --- quiet
initrd ${base}/initrd.gz
boot || goto error

# =========================================================================
# LOAD BLOCKS - NATIVE UTILITIES AND MEMTEST
# =========================================================================
:gparted
set base http://pxeboot.1-s.eu/gparted-live-1.6.0-1-amd64/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/gparted-live-1.6.0-1-amd64/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:clonezilla
set base http://pxeboot.1-s.eu/clonezilla-live-3.1.2-22-amd64/live
kernel ${base}/vmlinuz boot=live components fetch=http://pxeboot.1-s.eu/clonezilla-live-3.1.2-22-amd64/live/filesystem.squashfs ip=dhcp
initrd ${base}/initrd.img
boot || goto error

:sysrescue
set base http://pxeboot.1-s.eu/systemrescue-11.00-amd64/sysresccd/boot
kernel ${base}/x86_64/vmlinuz-linux archisobasedir=sysresccd archiso_http_srv=http://pxeboot.1-s.eu/systemrescue-11.00-amd64/ checksum ip=dhcp
initrd ${base}/intel_ucode.img
initrd ${base}/amd_ucode.img
initrd ${base}/x86_64/sysresccd.img
boot || goto error

:proxmox
set base http://pxeboot.1-s.eu/proxmox-ve_9.1-1/boot
kernel ${base}/linux26 vga=791 video=vesafb:ywrap,mtrr ramdisk_size=16777216 rw
initrd ${base}/initrd.mac
boot || goto error

:bootrepair
set base http://pxeboot.1-s.eu/boot-repair-disk-64bit/casper
kernel ${base}/vmlinuz.efi boot=casper netboot=url url=http://pxeboot.1-s.eu/boot-repair-disk-64bit.iso
initrd ${base}/initrd.lz
boot || goto error

:netbootxyz
chain --autofree http://boot.netboot.xyz/ipxe/netboot.xyz.efi || goto error

:memtest64_efi
chain http://pxeboot.1-s.eu/mt86plus_7.20_64/memtest.efi || goto error

:memtest32_efi
chain http://pxeboot.1-s.eu/mt86plus_7.20_32/memtest.efi || goto error

:memtest64_bios
echo Loading Native Multiboot Memtest Kernel...
kernel http://pxeboot.1-s.eu/mt86plus_7.20_64/memtest.bin
boot || goto error

:memtest32_bios
echo Loading Native Multiboot Memtest Kernel...
kernel http://pxeboot.1-s.eu/mt86plus_7.20_32/memtest.bin
boot || goto error

:dban
echo Loading Native DBAN Kernel...
set base http://pxeboot.1-s.eu/dban-2.3.0_i586/rootfs
kernel ${base}/dban.bzi nuke="dwipe" silent
boot || goto error

:supergrub
echo [!] SuperGRUB uses native BIOS sanboot (No RAM injection).
sanboot --no-describe http://pxeboot.1-s.eu/super_grub2_disk_hybrid_2.06s1.iso || goto error

:shell
shell
goto start

:reboot
reboot

:exit
exit

:error
echo [!] Critical load failure. Check server logs.
prompt Press any key to reload...
goto start
EOF

# ==============================================================================
# 8. NGINX PERMISSIONS REPAIR
# ==============================================================================
if [ -f "$DIR_ARREL/fix-perms.sh" ]; then
    echo -e "${YELLOW}🔒 [SYS-OPS] Executing fix-perms.sh...${NC}"
    bash "$DIR_ARREL/fix-perms.sh"
else
    chown -R www-data:www-data "$DIR_TREB"
    find "$DIR_TREB" -type d -exec chmod 755 {} \;
    find "$DIR_TREB" -type f -exec chmod 644 {} \;
fi

echo -e "\n${GREEN}🎉 Flat Multi-Arch Sync Completed! 100% Native Extract (No Memdisk).${NC}"
