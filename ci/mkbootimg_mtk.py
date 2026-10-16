#!/usr/bin/env python3
"""Pack an Android boot.img (header v2, MTK layout) from scratch.

Replicates the stock TB-X606F boot.img byte structure exactly:
  - page_size 2048, header_version 2, boot_header_size 1660 (MTK extends
    the AOSP v2 header by 12 bytes)
  - kernel area = Image(.gz) + DTB concatenated, no padding between
    (MTK LK splits them by scanning for the FDT magic)
  - MTK private header field @1648 = dtb_size + 64 (mirrors stock)
  - base addresses from stock: kernel 0x40080000, ramdisk 0x51b00000,
    second 0x40f00000, tags 0x47880000
  - cmdline keeps the stock bootopt prefix (LK storage hint)

Works on any host with python3 (no AOSP mkbootimg needed).
"""
import struct, sys

KERNEL_ADDR  = 0x40080000
RAMDISK_ADDR = 0x51b00000
SECOND_ADDR  = 0x40f00000
TAGS_ADDR    = 0x47880000
PAGE_SIZE    = 2048
OS_VERSION   = 0x1400015b   # stock value; meaningless for boot
HDR_SIZE     = 1660         # stock boot_header_size

def pad(data, page):
    r = len(data) % page
    return data + b'\0' * (page - r) if r else data

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--kernel', required=True, help='Image or Image.gz')
    p.add_argument('--dtb', required=True)
    p.add_argument('--ramdisk', required=True, help='initramfs cpio(.gz)')
    p.add_argument('-o', '--output', required=True)
    # Keep the stock bootopt prefix (LK storage hint) AND our console args.
    # Some MTK LK builds overwrite chosen/bootargs with the header cmdline;
    # if we only shipped bootopt there we would lose console= entirely and a
    # blind bring-up would have no log path. If LK *appends* instead, the
    # duplicated args are harmless (each is registered; the parser takes the
    # last one for /dev/console, and printk goes to all of them anyway).
    p.add_argument('--cmdline',
                   default='bootopt=64S3,32N2,64N2 buildvariant=user '
                           'earlycon console=ttyS0,921600n1 console=ttyGS0 '
                           'clk_ignore_unused regulator_ignore_unused')
    p.add_argument('--pagesize', type=int, default=PAGE_SIZE)
    a = p.parse_args()

    with open(a.kernel, 'rb') as f:
        kernel_img = f.read()
    with open(a.dtb, 'rb') as f:
        dtb = f.read()
    with open(a.ramdisk, 'rb') as f:
        ramdisk = f.read()

    # sanity: kernel magic
    if kernel_img[:2] != b'\x1f\x8b' and kernel_img[:4] != b'\x00\x00\xa0\xe1' \
       and kernel_img[0x38:0x3c] != b'ARM\x64':
        print(f"[pack] WARNING: unrecognized kernel image magic: {kernel_img[:8].hex()}",
              file=sys.stderr)
    if dtb[:4] != b'\xd0\x0d\xfe\xed':
        sys.exit(f"[pack] ERROR: {a.dtb} is not a DTB (bad FDT magic)")

    page = a.pagesize
    kernel_blob = kernel_img + dtb

    hdr = bytearray(2048)
    hdr[0:8] = b'ANDROID!'
    struct.pack_into('<9I', hdr, 8, len(kernel_blob), KERNEL_ADDR,
                     len(ramdisk), RAMDISK_ADDR, 0, SECOND_ADDR, TAGS_ADDR,
                     page, 2)
    struct.pack_into('<I', hdr, 44, OS_VERSION)
    cmdline = a.cmdline.encode()
    assert len(cmdline) < 512
    hdr[64:64+len(cmdline)] = cmdline
    hdr[576:608] = b'\0' * 32                      # id: zeroed
    struct.pack_into('<I', hdr, 1632, 0)           # recovery_dtbo_offset
    struct.pack_into('<Q', hdr, 1636, 0)           # recovery_dtbo_size
    struct.pack_into('<I', hdr, 1644, HDR_SIZE)    # boot_header_size
    struct.pack_into('<I', hdr, 1648, len(dtb) + 64)  # MTK: dtb_size + 64
    struct.pack_into('<I', hdr, 1652, TAGS_ADDR)      # MTK: tags_addr again
    struct.pack_into('<I', hdr, 1656, 0)

    # The stock image carries the DTB twice:
    #   1. bare FDT appended to the kernel image (that is what the kernel
    #      itself decompresses against), and
    #   2. after the ramdisk, a mkdtboimg-style "Android DTB" blob: a 64-byte
    #      header (magic 0xd7b7ab1e, big-endian) followed by the same DTB.
    #      LK reads *this* copy -- the size in the MTK private header field
    #      @1648 is its total size (64 + dtb_size). Shipping only the bare
    #      copy is why LK failed to find a DTB and dropped into download mode.
    adtb = bytearray(64)
    struct.pack_into('>8I', adtb, 0,
                     0xd7b7ab1e,          # magic
                     len(dtb) + 64,       # total size
                     0x20,                # header size
                     0x20,                # entry size
                     1,                   # number of entries
                     0x20,                # offset to entry table
                     page,                # page size
                     0)                   # version
    struct.pack_into('>4I', adtb, 32,
                     len(dtb),            # entry0: dtb size
                     0x40,                # entry0: dtb offset
                     0, 0)                # device id, revision (+16 reserved)

    out = bytes(hdr) + pad(kernel_blob, page) + pad(ramdisk, page) + bytes(adtb) + dtb
    with open(a.output, 'wb') as f:
        f.write(out)
    print(f"[pack] {a.output}: {len(out)} bytes "
          f"(kernel={len(kernel_blob)} [Image {len(kernel_img)} + dtb {len(dtb)}], "
          f"ramdisk={len(ramdisk)}, page={page})")
    print(f"[pack] cmdline: {cmdline.decode()}")

if __name__ == '__main__':
    main()
