#!/bin/bash
# Build the TB-X606F initramfs: Alpine minirootfs + our /init.
# Runs on GitHub runners (and locally on Linux). Pure shell + cpio.
#
# Usage: build_initramfs.sh [output.cpio.gz]
set -euo pipefail

OUT="${1:-initramfs.cpio.gz}"
WS="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/../.." && pwd)}"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

ALPINE_URL="${ALPINE_URL:-https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/alpine-minirootfs-3.24.0-aarch64.tar.gz}"

cd "$WORK"
echo "[initramfs] downloading Alpine minirootfs..."
curl -fsSL -o alpine.tar.gz "$ALPINE_URL"

mkdir rootfs
tar xzf alpine.tar.gz -C rootfs

# our init: mounts SD Debian, falls back to emergency shell on ttyS0/ttyGS0
install -m 0755 "$WS/ci/initramfs/init" rootfs/init

# a usable emergency shell environment
cat > rootfs/etc/fstab <<'FSTAB'
proc /proc proc defaults 0 0
sysfs /sys sysfs defaults 0 0
devtmpfs /dev devtmpfs defaults 0 0
FSTAB
echo "tbx606" > rootfs/etc/hostname
cat > rootfs/etc/inittab <<'INITTAB'
::sysinit:/etc/init.d/rcS 2>/dev/null
::respawn:-/bin/sh
::ctrlaltdel:/sbin/reboot
::shutdown:/bin/umount -a -r 2>/dev/null
INITTAB

echo "[initramfs] packing cpio.gz..."
cd rootfs
find . -print0 | cpio -o -H newc -0 2>/dev/null | gzip -9 > "$WS/$OUT"
echo "[initramfs] $WS/$OUT: $(wc -c < "$WS/$OUT") bytes"
