# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author and Credits: https://www.alawise.es/1-s
# Interactive storage and account setup are deliberate; no disk is erased by this profile.
# Match this source and the installer ISO to the same selected Fedora development branch.
graphical
lang es_ES.UTF-8
keyboard --xlayouts=es
timezone Europe/Andorra --utc
network --bootproto=dhcp --device=link --activate
url --url=https://download.fedoraproject.org/pub/fedora/linux/releases/45/Everything/x86_64/os/
rootpw --lock
selinux --enforcing
firewall --enabled
services --enabled=NetworkManager,chronyd
xconfig --startxonboot

%packages
@core
@base-x
@xfce-desktop
kernel
kernel-modules
kernel-modules-extra
linux-firmware
NetworkManager
NetworkManager-tui
chrony
firewalld
sudo
python3
python3-pip
openssh-server
openssh-clients
tmux
ncurses
dialog
qrencode
cockpit
cockpit-storaged
cockpit-networkmanager
cockpit-packagekit
bash-completion
nano
less
file
pciutils
usbutils
lsof
strace
rsync
curl
wget
git
unzip
xorriso
squashfs-tools
util-linux
parted
gparted
gdisk
cryptsetup
lvm2
mdadm
btrfs-progs
xfsprogs
e2fsprogs
dosfstools
exfatprogs
ntfs-3g
smartmontools
nvme-cli
ddrescue
testdisk
sleuthkit
iproute
iputils
bind-utils
ethtool
tcpdump
nmap
iperf3
selinux-policy-targeted
policycoreutils-python-utils
%end

%post --erroronfail
# Work and storage are ordinary persistent directories in the installed root.
install -d -m 0700 /work /storage
%end
