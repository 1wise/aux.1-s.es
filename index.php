<?php
/**
 * =========================================================================
 * 🚀 UNIFIED INDEX & LOGGER (aux.1-s.eu | minimaki | pxeboot)
 * MODE: HEAVY DUTY PUBLIC MIRROR (Flat Root Deployment + Kernel Exposing)
 * RULES: Sys Vars (Catalan abbrev), App Vars (Spanish abbrev), UI (English).
 * =========================================================================
 */

$log_file = 'access_log.txt';
$ip_cliente = $_SERVER['REMOTE_ADDR'];
$host_actual = $_SERVER['HTTP_HOST'];
$user_agent = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : 'CLI_OR_UNKNOWN';

// --- 1. ENRUTADOR DE TRÁFICO (MIRROR SELECTOR) ---
$mirror_arg = isset($_GET['mirror']) ? $_GET['mirror'] : '';
if (!empty($mirror_arg)) {
    $dl_url = "https://" . $mirror_arg;
} else {
    $dl_url = "https://aux.1-s.eu"; // Mirror por defecto
}

// --- 2. DETECCIÓN DE MAC PARA BETA TESTERS (VPC/Local 10.0.0.x) ---
function get_client_mac($ip) {
    $arp_res = @shell_exec("arp -n " . escapeshellarg($ip));
    if ($arp_res) {
        $lines = explode("\n", $arp_res);
        foreach($lines as $line) {
            if (strpos($line, $ip) !== false) {
                $cols = preg_split('/\s+/', trim($line));
                if (isset($cols[2]) && (strlen($cols[2]) == 17)) {
                    return strtoupper($cols[2]);
                }
            }
        }
    }
    return "WAN_OR_UNKNOWN";
}
$mac_cliente = get_client_mac($ip_cliente);

// --- 3. MOTOR DE LOGS ESTRUCTURADOS ---
function write_log($file, $ip, $mac, $host, $accion) {
    $timestamp = date('Y-m-d H:i:s');
    $log_entry = "[$timestamp] [$host] IP: $ip | MAC: $mac | ACTION: $accion" . PHP_EOL;
    @file_put_contents($file, $log_entry, FILE_APPEND);
}

// --- 4. INTERCEPTOR DE CLICS Y REDIRECCIÓN ---
if (isset($_GET['click']) && isset($_GET['url'])) {
    $target_name = $_GET['click'];
    $target_url = $_GET['url'];
    
    write_log($log_file, $ip_cliente, $mac_cliente, $host_actual, "DOWNLOAD_CLICK: $target_name");
    header("Location: " . $target_url);
    exit;
} else {
    write_log($log_file, $ip_cliente, $mac_cliente, $host_actual, "PAGE_VIEW");
}

// --- 5. SYSTEM SCANNER FUNCTIONS (Catalan / Spanish) ---
$dir_act = __DIR__;
$arx_ign = array('.', '..', 'index.php', 'index.html', 'sitemaps.xml', 'fix-perms.sh', 'fast-boot-total.sh', 'access_log.txt', 'menu.ipxe', 'favicon.png', 'aux-logo.png');

function obt_tam($rut_arc) {
    if (!file_exists($rut_arc)) return "0 B";
    $tam_byt = filesize($rut_arc);
    $uni_med = array('B', 'KB', 'MB', 'GB', 'TB');
    $fac_div = floor((strlen($tam_byt) - 1) / 3);
    if ($fac_div == 0) return $tam_byt . ' B';
    return sprintf("%.2f", $tam_byt / pow(1024, $fac_div)) . ' ' . $uni_med[$fac_div];
}

function obt_fec($rut_arc) {
    if (!file_exists($rut_arc)) return "N/A";
    return date("Y-m-d H:i", filemtime($rut_arc));
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- ========================================== -->
    <!-- 1. ESSENTIAL SEO FOR NETBOOT DIRECTORY     -->
    <!-- ========================================== -->
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($host_actual); ?> | aux.1-s.es - Auxiliary NetBoot Tools and Distro ISOs</title>
    <meta name="description" content="Comprehensive repository of Auxiliary NetBoot Tools, PXE boot files, extracted kernels, and Linux distribution ISOs. Optimized for fast network deployments of Debian Trixie and Forky.">
    <meta name="keywords" content="netboot, pxe, pxe boot, debian, trixie, forky, network boot, linux installer, distro isos, auxiliary tools, sysadmin, aux.1-s.eu, aux.1-s.es, linux deployment, vmlinuz">
    <meta name="author" content="1-s.eu Team">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://aux.1-s.eu/">

    <!-- ========================================== -->
    <!-- 2. OPEN GRAPH (Discord, LinkedIn, Slack)   -->
    <!-- ========================================== -->
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="aux.1-s.eu NetBoot Tools">
    <meta property="og:title" content="<?php echo htmlspecialchars($host_actual); ?> | aux.1-s.es - Auxiliary NetBoot Tools">
    <meta property="og:description" content="Access our repository of NetBoot images, pre-extracted kernels, and PXE tools for rapid Linux deployments, specializing in Debian Trixie/Forky.">
    <meta property="og:url" content="https://aux.1-s.eu/">
    <meta property="og:image" content="https://aux.1-s.eu/aux-logo.png">
    <meta property="og:image:alt" content="aux.1-s.eu NetBoot Logo">

    <!-- ========================================== -->
    <!-- 3. TWITTER CARDS                           -->
    <!-- ========================================== -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="<?php echo htmlspecialchars($host_actual); ?> | aux.1-s.es - NetBoot Tools">
    <meta name="twitter:description" content="Repository for NetBoot images, pre-extracted kernels, and Linux distros. Perfect for Debian Trixie deployments.">
    <meta name="twitter:image" content="https://aux.1-s.eu/aux-logo.png">

    <!-- ========================================== -->
    <!-- 4. ASSETS PRELOAD & FAVICON                -->
    <!-- ========================================== -->
    <link rel="preload" fetchpriority="high" href="./aux-logo.png" as="image" type="image/png">
    <link rel="icon" type="image/png" href="favicon.png">

    <!-- ========================================== -->
    <!-- 5. TERMINAL ASCII STYLES (SYS-OPS MODE)    -->
    <!-- ========================================== -->
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: monospace; padding: 20px; line-height: 1.5; max-width: 1200px; margin: auto;}
        .header-main { border-bottom: 2px solid #38bdf8; margin-bottom: 20px; padding-bottom: 10px; }
        h1 { color: #38bdf8; margin: 0; }
        
        .mirror-panel { border: 1px dashed #fbbf24; background-color: #1e293b; padding: 15px; margin-bottom: 25px; }
        .mirror-panel select, .mirror-panel input { background-color: #0f172a; color: #38bdf8; border: 1px solid #475569; padding: 4px; font-family: monospace; }
        .mirror-panel button { background-color: #fbbf24; color: #0f172a; border: none; padding: 4px 10px; font-weight: bold; cursor: pointer; font-family: monospace; }
        .mirror-panel button:hover { background-color: #f59e0b; }

        details { margin-bottom: 10px; margin-left: 10px; }
        summary { color: #38bdf8; font-weight: bold; cursor: pointer; padding: 5px 0; outline: none; }
        summary:hover { color: #7dd3fc; text-decoration: underline; }
        
        ul.tree { list-style: none; padding-left: 20px; border-left: 1px dashed #475569; margin-left: 5px; margin-top: 5px; }
        li { margin: 6px 0; }
        
        a { color: #10b981; text-decoration: none; }
        a:hover { text-decoration: underline; color: #34d399; background: rgba(16, 185, 129, 0.1); }
        a:focus { background-color: #1e293b; outline: 1px solid #10b981; }

        /* SYS-OPS Color Codes */
        .iso-link { color: #fbbf24; font-weight: bold; }   /* Yellow: ISOs/Archives */
        .dir-link { color: #a78bfa; font-weight: bold; }   /* Purple: Directories */
        .bin-link { color: #f472b6; font-weight: bold; font-size: 0.9em; } /* Pink: Kernels/Binaries */
        .badge { color: #94a3b8; font-size: 0.85em; margin-left: 10px; }
        .hash { color: #64748b; font-size: 0.8em; }
        
        .footer-main { margin-top: 40px; border-top: 1px solid #334155; padding-top: 20px; }
        .client-info { margin-top: 20px; border-top: 1px dashed #475569; padding-top: 15px; color: #64748b; font-size: 0.85em; }
        .client-info span { color: #94a3b8; font-weight: bold; }
        .sys-alert { color: #fbbf24; font-size: 0.85em; margin-bottom: 15px; display: inline-block; border: 1px solid #fbbf24; padding: 2px 8px; background: #000;}

        /* Scanner Table */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em;}
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #334155; }
        th { color: #38bdf8; }
        tr:hover { background-color: #1e293b; }
    </style>
</head>
<body>

    <!-- CABECERA SEMÁNTICA -->
    <header class="header-main">
        <h1> <?php echo htmlspecialchars($host_actual); ?> | aux.1-s.es </h1>
        <p>Massive NetBoot Ecosystem & Distro Repositories</p>
        <p class="badge"> Quick Navigation CLI Friendly (links2) </p>
        <div style="margin-top:10px;">
            <span class="sys-alert" role="alert">[!] ABSOLUTE FLAT ROOT DEPLOYMENT. NO SYMLINKS.</span>
            <span class="sys-alert" role="alert" style="border-color:#f472b6; color:#f472b6;">[!] KERNELS (vmlinuz/initrd) EXPOSED.</span>
        </div>
    </header>

    <!-- SECCIÓN DE ENRUTAMIENTO (Aislada lógicamente) -->
    <section class="mirror-panel" aria-label="Server Offload Router">
        <span style="color: #fbbf24; font-weight: bold;"> [⚙️] Server Offload Router </span><br>
        <p style="margin: 5px 0; color: #94a3b8; font-size: 0.9em;"> Local Node (Serves Binaries): <span style="color: #f8fafc;"><?php echo htmlspecialchars($host_actual); ?></span></p>
        <p style="margin: 5px 0; color: #94a3b8; font-size: 0.9em;"> Payload Offload Target (ISOs): <span style="color: #10b981;"><?php echo htmlspecialchars($dl_url); ?></span></p>
        
        <form action="" method="GET" style="margin-top: 10px;">
            <label for="mirror"> Download From:</label>
            <select name="mirror" id="mirror">
                <option value="aux.1-s.es" <?php if($mirror_arg=='aux.1-s.es') echo 'selected'; ?>>aux.1-s.es (GCloud - Small)</option>
                <option value="aux.1-s.eu" <?php if($mirror_arg=='aux.1-s.eu') echo 'selected'; ?>>aux.1-s.eu (GCloud - Small)</option>
                <option value="boot.1-s.es" <?php if($mirror_arg=='boot.1-s.es') echo 'selected'; ?>>boot.1-s.es (Corei5 - Lab)</option>
                <option value="boot.1-s.eu" <?php if($mirror_arg=='boot.1-s.eu') echo 'selected'; ?>>boot.1-s.eu (Corei5 - Lab)</option>
                <option value="b.1-s.es" <?php if($mirror_arg=='b.1-s.es') echo 'selected'; ?>>b.1-s.es (OVH Heavy Duty - Default)</option>
                <option value="b.1-s.eu" <?php if($mirror_arg=='b.1-s.eu') echo 'selected'; ?>>b.1-s.eu (OVH Heavy Duty)</option>
            </select>
            <button type="submit">Route Traffic</button>
        </form>

        <p style="margin-top: 10px; font-size: 0.85em; color: #64748b;">
            * This drop down menu lets you choose where to download large payloads from.<br>
            * NetBoot files (PXE, EFI, vmlinuz) are ALWAYS served from the assigned domain server.
        </p>
    </section>

    <!-- CONTENIDO PRINCIPAL (El Árbol de Archivos Curado) -->
    <main>
        <h2> [CURATED REPOSITORIES] </h2>
        
        <!-- SECCIÓN DEBIAN -->
        <details>
            <summary>[+] Debian Ecosystem</summary>
            <ul class="tree">
                <li>
                    <details>
                        <summary>Debian 13.3.0 Stable (amd64 / arm64)</summary>
                        <ul class="tree">
                            <li><a href="?click=deb13-amd-iso&url=<?php echo urlencode($dl_url.'/debian-13.3.0-amd64-netinst.iso'); ?>" class="iso-link">[ISO] debian-13.3.0-amd64-netinst.iso</a></li>
                            <li><a href="/debian-13.3.0-amd64-netinst/" class="dir-link">[DIR] Extracted Tree (amd64)</a></li>
                            <li><a href="?click=deb13-arm-iso&url=<?php echo urlencode($dl_url.'/debian-13.3.0-arm64-netinst.iso'); ?>" class="iso-link">[ISO] debian-13.3.0-arm64-netinst.iso</a></li>
                            <li><a href="/debian-13.3.0-arm64-netinst/" class="dir-link">[DIR] Extracted Tree (arm64)</a></li>
                        </ul>
                    </details>
                </li>
                <li>
                    <details>
                        <summary>Debian Trixie / Forky (Testing Netboot)</summary>
                        <ul class="tree">
                            <li><a href="?click=deb-test-amd-iso&url=<?php echo urlencode($dl_url.'/debian-testing-amd64-netinst.iso'); ?>" class="iso-link">[ISO] debian-testing-amd64-netinst.iso</a></li>
                            <li><a href="/debian-testing-amd64-netinst/" class="dir-link">[DIR] Extracted Tree (amd64)</a></li>
                            <li><a href="?click=deb-test-arm-iso&url=<?php echo urlencode($dl_url.'/debian-testing-arm64-netinst.iso'); ?>" class="iso-link">[ISO] debian-testing-arm64-netinst.iso</a></li>
                            <li><a href="/debian-testing-arm64-netinst/" class="dir-link">[DIR] Extracted Tree (arm64)</a></li>
                        </ul>
                    </details>
                </li>
                <li>
                    <details>
                        <summary>Debian Live (GNOME / XFCE)</summary>
                        <ul class="tree">
                            <li><a href="?click=deb-live-13gnm&url=<?php echo urlencode($dl_url.'/debian-live-13.3.0-amd64-gnome.iso'); ?>" class="iso-link">[ISO] debian-live-13.3.0-amd64-gnome.iso</a></li>
                            <li><a href="/debian-live-13.3.0-amd64-gnome/" class="dir-link">[DIR] Extracted Live GNOME 13.3</a></li>
                            <li><a href="?click=deb-live-13xfc&url=<?php echo urlencode($dl_url.'/debian-live-13.3.0-amd64-xfce.iso'); ?>" class="iso-link">[ISO] debian-live-13.3.0-amd64-xfce.iso</a></li>
                            <li><a href="/debian-live-13.3.0-amd64-xfce/" class="dir-link">[DIR] Extracted Live XFCE 13.3</a></li>
                        </ul>
                    </details>
                </li>
            </ul>
        </details>

        <!-- SECCIÓN FEDORA -->
        <details>
            <summary>[+] Fedora Ecosystem</summary>
            <ul class="tree">
                <li><a href="?click=fed-srv-x86-iso&url=<?php echo urlencode($dl_url.'/Fedora-Server-netinst-x86_64-41-1.4.iso'); ?>" class="iso-link">[ISO] Fedora-Server-netinst-x86_64-41-1.4.iso</a></li>
                <li><a href="/Fedora-Server-netinst-x86_64-41-1.4/" class="dir-link">[DIR] Extracted Server Netboot (x86_64)</a></li>
                <li><a href="?click=fed-srv-arm-iso&url=<?php echo urlencode($dl_url.'/Fedora-Server-netinst-aarch64-41-1.4.iso'); ?>" class="iso-link">[ISO] Fedora-Server-netinst-aarch64-41-1.4.iso</a></li>
                <li><a href="/Fedora-Server-netinst-aarch64-41-1.4/" class="dir-link">[DIR] Extracted Server Netboot (aarch64)</a></li>
                <li><a href="?click=fed-wrk-x86-iso&url=<?php echo urlencode($dl_url.'/Fedora-Workstation-Live-x86_64-41-1.4.iso'); ?>" class="iso-link">[ISO] Fedora-Workstation-Live-x86_64-41-1.4.iso</a></li>
                <li><a href="/Fedora-Workstation-Live-x86_64-41-1.4/" class="dir-link">[DIR] Extracted Workstation (x86_64)</a></li>
            </ul>
        </details>

        <!-- SECCIÓN UBUNTU -->
        <details>
            <summary>[+] Ubuntu Ecosystem</summary>
            <ul class="tree">
                <li>
                    <details>
                        <summary>Ubuntu 25.10 (Plucky)</summary>
                        <ul class="tree">
                            <li><a href="?click=ub2510-srv-iso&url=<?php echo urlencode($dl_url.'/ubuntu-25.10-live-server-amd64.iso'); ?>" class="iso-link">[ISO] ubuntu-25.10-live-server-amd64.iso</a></li>
                            <li><a href="/ubuntu-25.10-live-server-amd64/" class="dir-link">[DIR] Extracted Server 25.10 (amd64)</a></li>
                            <li><a href="?click=ub2510-dsk-iso&url=<?php echo urlencode($dl_url.'/ubuntu-25.10-desktop-amd64.iso'); ?>" class="iso-link">[ISO] ubuntu-25.10-desktop-amd64.iso</a></li>
                            <li><a href="/ubuntu-25.10-desktop-amd64/" class="dir-link">[DIR] Extracted Desktop 25.10 (amd64)</a></li>
                        </ul>
                    </details>
                </li>
                <li>
                    <details>
                        <summary>Ubuntu 24.04 LTS (Noble)</summary>
                        <ul class="tree">
                            <li><a href="?click=ub2404-srv-iso&url=<?php echo urlencode($dl_url.'/ubuntu-24.04.4-live-server-amd64.iso'); ?>" class="iso-link">[ISO] ubuntu-24.04.4-live-server-amd64.iso</a></li>
                            <li><a href="/ubuntu-24.04.4-live-server-amd64/" class="dir-link">[DIR] Extracted Server 24.04 (amd64)</a></li>
                            <li><a href="?click=ub2404-srvarm-iso&url=<?php echo urlencode($dl_url.'/ubuntu-24.04.4-live-server-arm64.iso'); ?>" class="iso-link">[ISO] ubuntu-24.04.4-live-server-arm64.iso</a></li>
                            <li><a href="/ubuntu-24.04.4-live-server-arm64/" class="dir-link">[DIR] Extracted Server 24.04 (arm64)</a></li>
                            <li><a href="?click=ub2404-dsk-iso&url=<?php echo urlencode($dl_url.'/ubuntu-24.04.4-desktop-amd64.iso'); ?>" class="iso-link">[ISO] ubuntu-24.04.4-desktop-amd64.iso</a></li>
                        </ul>
                    </details>
                </li>
                <li><a href="?click=ub-raspi-img&url=<?php echo urlencode($dl_url.'/ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz'); ?>" class="iso-link">[IMG] ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz</a></li>
            </ul>
        </details>

        <!-- SECCIÓN ARCH, ALPINE & GENTOO -->
        <details>
            <summary>[+] Lightweight & Rolling (Arch / Alpine / Gentoo)</summary>
            <ul class="tree">
                <li><a href="?click=arch-iso&url=<?php echo urlencode($dl_url.'/archlinux-x86_64.iso'); ?>" class="iso-link">[ISO] archlinux-x86_64.iso</a></li>
                <li><a href="/archlinux-x86_64/" class="dir-link">[DIR] Extracted Arch Filesystem</a></li>
                <li style="margin-top: 10px;"><a href="?click=alpine-x86-iso&url=<?php echo urlencode($dl_url.'/alpine-standard-3.23.3-x86_64.iso'); ?>" class="iso-link">[ISO] alpine-standard-3.23.3-x86_64.iso</a></li>
                <li><a href="/alpine-standard-3.23.3-x86_64/" class="dir-link">[DIR] Extracted Alpine x86_64</a></li>
                <li><a href="?click=alpine-arm-iso&url=<?php echo urlencode($dl_url.'/alpine-standard-3.23.3-aarch64.iso'); ?>" class="iso-link">[ISO] alpine-standard-3.23.3-aarch64.iso</a></li>
                <li><a href="/alpine-standard-3.23.3-aarch64/" class="dir-link">[DIR] Extracted Alpine aarch64</a></li>
                <li style="margin-top: 10px;"><a href="?click=gentoo-min-iso&url=<?php echo urlencode($dl_url.'/install-amd64-minimal-20260215T164556Z.iso'); ?>" class="iso-link">[ISO] install-amd64-minimal-20260215T164556Z.iso (Gentoo)</a></li>
                <li><a href="/install-amd64-minimal-20260215T164556Z/" class="dir-link">[DIR] Extracted Gentoo Minimal</a></li>
                <li><a href="?click=gentoo-gui-iso&url=<?php echo urlencode($dl_url.'/livegui-amd64-20260215T164556Z.iso'); ?>" class="iso-link">[ISO] livegui-amd64-20260215T164556Z.iso (Gentoo GUI)</a></li>
            </ul>
        </details>

        <!-- SECCIÓN KALI & PROXMOX -->
        <details>
            <summary>[+] Kali Linux & Proxmox</summary>
            <ul class="tree">
                <li><a href="?click=kali-live-iso&url=<?php echo urlencode($dl_url.'/kali-linux-2025.4-live-amd64.iso'); ?>" class="iso-link">[ISO] kali-linux-2025.4-live-amd64.iso</a></li>
                <li><a href="/kali-linux-2025.4-live-amd64/" class="dir-link">[DIR] Extracted Kali Live</a></li>
                <li><a href="?click=kali-net-amd&url=<?php echo urlencode($dl_url.'/kali-linux-2025.4-installer-netinst-amd64.iso'); ?>" class="iso-link">[ISO] kali-linux-2025.4-installer-netinst-amd64.iso</a></li>
                <li><a href="/kali-linux-2025.4-installer-netinst-amd64/" class="dir-link">[DIR] Extracted Kali Netinst amd64</a></li>
                <li><a href="?click=kali-net-arm&url=<?php echo urlencode($dl_url.'/kali-linux-2025.4-installer-netinst-arm64.iso'); ?>" class="iso-link">[ISO] kali-linux-2025.4-installer-netinst-arm64.iso</a></li>
                <li><a href="/kali-linux-2025.4-installer-netinst-arm64/" class="dir-link">[DIR] Extracted Kali Netinst arm64</a></li>
                <li><a href="?click=kali-purple&url=<?php echo urlencode($dl_url.'/kali-linux-2025.4-installer-purple-amd64.iso'); ?>" class="iso-link">[ISO] kali-linux-2025.4-installer-purple-amd64.iso</a></li>
                <li style="margin-top:10px;"><a href="?click=proxmox-iso&url=<?php echo urlencode($dl_url.'/proxmox-ve_9.1-1.iso'); ?>" class="iso-link">[ISO] proxmox-ve_9.1-1.iso</a></li>
                <li><a href="/proxmox-ve_9.1-1/" class="dir-link">[DIR] Extracted Proxmox Installer</a></li>
            </ul>
        </details>

        <!-- SECCIÓN PXE TOOLS & RESCUE -->
        <details>
            <summary>[+] PXE Rescue & Maintenance Tools</summary>
            <ul class="tree">
                <li><a href="?click=nxyz-pxe&url=<?php echo urlencode('/netboot.xyz.kpxe'); ?>" class="bin-link">[PXE] netboot.xyz.kpxe (BIOS Legacy)</a></li>
                <li><a href="?click=nxyz-efi&url=<?php echo urlencode('/netboot.xyz.efi'); ?>" class="bin-link">[EFI] netboot.xyz.efi (UEFI x64)</a></li>
                <li><a href="?click=nxyz-arm&url=<?php echo urlencode('/netboot.xyz-arm64.efi'); ?>" class="bin-link">[EFI] netboot.xyz-arm64.efi (UEFI ARM)</a></li>
                
                <li style="margin-top: 10px;"><a href="?click=clonezilla-iso&url=<?php echo urlencode($dl_url.'/clonezilla-live-3.1.2-22-amd64.iso'); ?>" class="iso-link">[ISO] clonezilla-live-3.1.2-22-amd64.iso</a></li>
                <li><a href="/clonezilla-live-3.1.2-22-amd64/" class="dir-link">[DIR] Extracted Clonezilla</a></li>
                
                <li><a href="?click=gparted-iso&url=<?php echo urlencode($dl_url.'/gparted-live-1.6.0-1-amd64.iso'); ?>" class="iso-link">[ISO] gparted-live-1.6.0-1-amd64.iso</a></li>
                <li><a href="/gparted-live-1.6.0-1-amd64/" class="dir-link">[DIR] Extracted GParted</a></li>
                
                <li><a href="?click=sysrescue-iso&url=<?php echo urlencode($dl_url.'/systemrescue-11.00-amd64.iso'); ?>" class="iso-link">[ISO] systemrescue-11.00-amd64.iso</a></li>
                <li><a href="/systemrescue-11.00-amd64/" class="dir-link">[DIR] Extracted SysRescue</a></li>
                
                <li><a href="?click=bootrepair-iso&url=<?php echo urlencode($dl_url.'/boot-repair-disk-64bit.iso'); ?>" class="iso-link">[ISO] boot-repair-disk-64bit.iso</a></li>
                <li><a href="/boot-repair-disk-64bit/" class="dir-link">[DIR] Extracted Boot Repair</a></li>

                <li style="margin-top: 10px;"><a href="?click=dban-iso&url=<?php echo urlencode($dl_url.'/dban-2.3.0_i586.iso'); ?>" class="iso-link">[ISO] dban-2.3.0_i586.iso</a></li>
                <li><a href="/dban-2.3.0_i586/" class="dir-link">[DIR] Extracted DBAN</a></li>

                <li><a href="?click=sgrub-iso&url=<?php echo urlencode($dl_url.'/super_grub2_disk_hybrid_2.06s1.iso'); ?>" class="iso-link">[ISO] super_grub2_disk_hybrid_2.06s1.iso</a></li>

                <li style="margin-top: 10px;"><span class="hash"># Memtest86+ v7.20</span></li>
                <li><a href="/mt86plus_7.20_64/memtest.efi" class="bin-link">[EFI] memtest64.efi</a></li>
                <li><a href="/mt86plus_7.20_32/memtest.efi" class="bin-link">[EFI] memtest32.efi</a></li>
                <li><a href="/mt86plus_7.20_64/memtest.bin" class="bin-link">[BIN] memtest64.bin (BIOS)</a></li>
                <li><a href="/mt86plus_7.20_32/memtest.bin" class="bin-link">[BIN] memtest32.bin (BIOS)</a></li>
            </ul>
        </details>
    </main>

    <!-- MOTOR DINÁMICO (Detecta automáticamente archivos nuevos caídos en la raíz) -->
    <section style="margin-top: 40px; border-top: 2px dashed #475569; padding-top: 20px;">
        <h2 style="color: #94a3b8;"> [RAW FILESYSTEM VIEW] </h2>
        <p style="font-size: 0.85em; color: #64748b;">Dynamic scanner (Auto-lists any new drops in root)</p>
        
        <?php
        $lis_dir = array();
        $lis_arc = array();

        if (is_dir($dir_act)) {
            $res_esc = scandir($dir_act);
            foreach ($res_esc as $nom_arc) {
                if (in_array($nom_arc, $arx_ign) || strpos($nom_arc, '.tmp') !== false) {
                    continue;
                }
                $rut_com = $dir_act . '/' . $nom_arc;
                if (is_dir($rut_com)) {
                    $lis_dir[] = $nom_arc;
                } else {
                    $lis_arc[] = $nom_arc;
                }
            }
        }
        ?>
        <table>
            <thead>
                <tr>
                    <th>Resource Name</th>
                    <th>Size</th>
                    <th>Last Modified</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($lis_dir as $nom_dir): ?>
                <tr>
                    <td><a href="<?php echo htmlspecialchars($nom_dir); ?>/" class="dir-link">[DIR] <?php echo htmlspecialchars($nom_dir); ?>/</a></td>
                    <td style="color:#64748b;">-</td>
                    <td style="color:#64748b;"><?php echo obt_fec($dir_act . '/' . $nom_dir); ?></td>
                </tr>
                <?php endforeach; ?>

                <?php foreach ($lis_arc as $nom_arc): 
                    $is_iso = preg_match('/\.(iso|zip|tar\.gz|xz|img)$/i', $nom_arc);
                    $css_cls = $is_iso ? "iso-link" : "bin-link";
                    $ico_str = $is_iso ? "[ISO]" : "[FILE]";
                    $url_fin = $is_iso ? "?click=".urlencode($nom_arc)."&url=".urlencode($dl_url."/".$nom_arc) : htmlspecialchars($nom_arc);
                ?>
                <tr>
                    <td><a href="<?php echo $url_fin; ?>" class="<?php echo $css_cls; ?>"><?php echo $ico_str . " " . htmlspecialchars($nom_arc); ?></a></td>
                    <td style="color:#94a3b8;"><?php echo obt_tam($dir_act . '/' . $nom_arc); ?></td>
                    <td style="color:#64748b;"><?php echo obt_fec($dir_act . '/' . $nom_arc); ?></td>
                </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </section>

    <!-- PIE DE PÁGINA SEMÁNTICO (Log, Admin, Información) -->
    <footer class="footer-main">
        <div style="margin-bottom: 20px;">
            <a href="/admin/" style="color: #fbbf24; margin-right: 15px; font-weight:bold;"> [⚙️] ADMIN TOOLKIT </a>
            <a href="access_log.txt" target="_blank" style="color: #10b981; margin-right: 15px; font-weight:bold;"> [📜] VIEW EVENT LOG </a>
            <a href="sitemaps.xml" target="_blank" style="color: #a78bfa; font-weight:bold;"> [🕸️] SITEMAP.XML </a>
        </div>

        <div class="client-info">
            <p>[i] System Time (Local): <span><?php echo date('Y-m-d H:i:s'); ?></span></p>
            <p>[i] Client Connection IP: <span><?php echo htmlspecialchars($ip_cliente); ?></span></p>
            <p>[i] Client Mac Address: <span style="color: #fbbf24;"><?php echo htmlspecialchars($mac_cliente); ?></span></p>
            <p>[i] Requested URI: <span><?php echo htmlspecialchars($_SERVER['REQUEST_URI']); ?></span></p>
        </div>

        <!-- LOGO FINAL -->
        <img src="aux-logo.png" alt="aux.1-s.eu / aux.1-s.es - Auxiliary NetBoot Tools and Distro Isos" loading="lazy" decoding="async" style="width:75px; height:75px; border-radius:15px; transition:0.3s; margin-top:20px; border: 1px solid #334155;">
    </footer>

</body>
</html>
