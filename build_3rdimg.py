#!/usr/bin/env python

import binascii
import struct

def round_up_to_eb(size, eb_size):
    if size % eb_size == 0:
        return int(size//eb_size)*eb_size
    else:
        return int(size//eb_size + 1)*eb_size

def round_to_next_eb(size, eb_size):
    return int(size//eb_size + 1)*eb_size

def round_down_to_eb(size, eb_size):
    return int(size//eb_size)*eb_size

def realign_rootfs_marker(rootfs, eb_size):
    jffs2_marker = 0xdeadc0de
    if int.from_bytes(rootfs[-4:], byteorder='big') != jffs2_marker:
        raise ValueError('no JFFS2 marker found')
    else:
        offset = len(rootfs)-4
        while rootfs[offset-1] == 0xff and offset > 1:
            offset -= 1;
        if offset == 0:
            raise ValueError('empty partition')
        # need to backtrack one byte
        squashfs = rootfs[:offset]
        padded_len = round_up_to_eb(len(squashfs), eb_size)
        padding = bytearray(b'\xff')*(padded_len-len(squashfs))
        padded_squashfs = bytes(squashfs+padding)
        assert (len(padded_squashfs) % eb_size) == 0
        return padded_squashfs + jffs2_marker.to_bytes(4, byteorder='big')

def extract_sysupgrade_parts(sysupgrade_path, eb_size):
    ## Extract partition data from sysupgrade image
    # The kernel partition data _must_ be smaller than the kernel partition size.
    # This means that we can't split up the sysupgrade along an arbitrary erase block
    # and return two parts of a firmware partition. We actually have to realign to an EB.
    sysupgrade = None
    with open(sysupgrade_path, 'rb') as sysupgrade_file:
        data = sysupgrade_file.read()
        # Assume sysupgrade is padded to an erase block, followed by 0xdeadc0de
        sysupgrade = data[0:round_down_to_eb(len(data), eb_size)+4]
    
    assert int.from_bytes(sysupgrade[-4:], byteorder='big') == 0xdeadc0de
    
    sqsh_offset = sysupgrade.find(struct.pack('<I', int.from_bytes(b'sqsh', byteorder='big')))
    kernel = sysupgrade[:sqsh_offset]
    rootfs = realign_rootfs_marker(sysupgrade[sqsh_offset:], eb_size)
    return (kernel, rootfs)


# Device specific info
product_name = 'EAP245'
product_version = '3.0'
kernel_partition_offset = 0xc0000
eb_size = 0x10000

sysupgrade_path = 'openwrt-ath79-generic-tplink_eap245-v3-squashfs-sysupgrade.bin'


# Image header:
# * u32 image size
# * u32 CRC32 all data starting from 0x8
# * u32 magic (0xdeadbeef)
product_info = f'product_name={product_name}\nproduct_version={product_version}\n'.encode()
factory_header = struct.pack('>I64s', 0xdeadbeef, product_info)


# Extract the partition payloads
sysupgrade_kernel, sysupgrade_rootfs = extract_sysupgrade_parts(sysupgrade_path, eb_size)
assert sysupgrade_rootfs[:4] == b'hsqs'
assert sysupgrade_rootfs[-4:] == bytes([0xde, 0xad, 0xc0, 0xde])

# Kernel partition:
# * must be named 'os-linux'
# * must start at the correct offset
# * partition size must be larger than partition payload
#   (this is the reason the squashfs needs to be re-aligned)
# * parition payload must start at 0x14c
kernel_name = b'os-linux'
kernel_part_base = kernel_partition_offset
kernel_part_size = round_to_next_eb(len(sysupgrade_kernel), eb_size)
kernel_data_offset = 0x14c
kernel_data_size = len(sysupgrade_kernel)

# RootFS partition
# * must be named 'rootfs'
# * must follow kernel partition in flash layout
# * payload must start at 0x14d + kernel_payload_size (yes, that's an off-by-one bug)
rootfs_name = b'rootfs'
rootfs_part_base = kernel_part_base + kernel_part_size
rootfs_part_size = round_up_to_eb(len(sysupgrade_rootfs), eb_size)
rootfs_data_offset = kernel_data_offset + kernel_data_size + 1
rootfs_data_size = len(sysupgrade_rootfs)

# Print some info for the user
info_template = '\t{:8s} @{:08x}+{:08x}, payload={:08x} @ {:08x}'
print('Generated partitions:')
print(info_template.format(kernel_name.decode(), kernel_part_base, kernel_part_size, kernel_data_size, kernel_data_offset))
print(info_template.format(rootfs_name.decode(), rootfs_part_base, rootfs_part_size, rootfs_data_size, rootfs_data_offset))

# The image header is followed by info structs
#    { char name[8], u32 part_base, u32 part_size, u32 payload_base, u32 payload_size }
# The code has a(nother) bug however, the number of skipped bytes in the rootfs-entry
# isn't 8 (the field size), but 6 (the actual name length). The strncmp call however,
# still requires the termination null-byte because the max compare length is still 8.
# This means we can only have rootfs partition offsets < 16M, where the highest byte is 0x00.
info_parts = [
    struct.pack('>8s4I', kernel_name, kernel_part_base, kernel_part_size,
            kernel_data_offset, kernel_data_size),
    struct.pack('>6s4I', rootfs_name, rootfs_part_base, rootfs_part_size,
            rootfs_data_offset, rootfs_data_size),
]

# Due to the payload offset bug mentioned earlier, we need to insert one byte of
# padding after the kernel partition
parts = [
    sysupgrade_kernel,
    bytes(1),
    sysupgrade_rootfs
]

# 0x100 bytes of resevered space for partition entries
info = bytearray(0x100)
info_offset = 0
for ip in info_parts:
    info[info_offset:info_offset+len(ip)] = ip
    info_offset += len(ip)

# Compose all the data required to calculate the CRC32 checksum
img_data = factory_header + info
for p in parts:
    img_data += p

crc = binascii.crc32(img_data).to_bytes(4, byteorder='big')
img_len = 4 + len(crc) + len(img_data)

with open('3rdimg.bin', 'wb') as factory_file:
    factory_file.write(img_len.to_bytes(4, byteorder='big'))
    factory_file.write(crc)
    factory_file.write(img_data)
    # Append fake 1024 bit RSA signature to get the image accepted
    factory_file.write(bytes(0x100))
