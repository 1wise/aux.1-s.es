# Define your USB drive here (CAREFUL!)
USB_DRIVE="/dev/sdX"

# Wipe and partition
parted -s $USB_DRIVE mklabel msdos
parted -s -a optimal $USB_DRIVE mkpart primary fat32 1MiB 40mb
parted -s $USB_DRIVE set 1 boot on

# Format to VFAT
mkfs.vfat -F 32 -n "ARSENAL_PXE" ${USB_DRIVE}1

mkdir -p /mnt/usb
mount ${USB_DRIVE}1 /mnt/usb

# 1. Install Legacy BIOS GRUB (to the MBR)
grub-install --target=i386-pc --boot-directory=/mnt/usb/boot --recheck $USB_DRIVE

# 2. Install UEFI 64-bit GRUB (to the VFAT partition, removable mode)
grub-install --target=x86_64-efi --efi-directory=/mnt/usb --boot-directory=/mnt/usb/boot --removable --recheck

mkdir -p /mnt/usb/boot/ipxe
cp bin/ipxe.lkrn /mnt/usb/boot/ipxe/
cp bin-x86_64-efi/ipxe.efi /mnt/usb/boot/ipxe/

cat << 'EOF' > /mnt/usb/boot/grub/grub.cfg
set timeout=2
set default=0
set color_normal=cyan/black
set color_highlight=black/cyan

menuentry "[ 1-s.eu | ARSENAL W.A.N. Auto-Boot ]" {
    if [ "${grub_platform}" = "efi" ]; then
        echo ">> Motherboard detected: UEFI. Loading ipxe.efi..."
        chainloader /boot/ipxe/ipxe.efi
    else
        echo ">> Motherboard detected: BIOS Legacy. Loading ipxe.lkrn..."
        linux16 /boot/ipxe/ipxe.lkrn
    fi
}

# Opción útil para depuración manual
menuentry "[ Open GRUB Command Line (Shell) ]" {
    terminal_input console
    terminal_output console
}

menuentry "[ Reboot System ]" {
    reboot
}
EOF

umount /mnt/usb
sync


