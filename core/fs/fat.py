# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from zlib import crc32
from datetime import datetime
from struct import pack, unpack_from, calcsize
from easy_enum import EEnum as Enum

# http://elm-chan.org/docs/fat_e.html
# https://github.com/maxpat78/FATtools/blob/master/FAT.py


class BootSectorFat16(object):

    BOOTSTRAP_SIZE = 448
    BOOT_SIGNATURE = 0xAA55
    FORMAT = '<3s8sHBHBHHBHHHIIBBBI11s8s'
    SIZE = 512

    def __init__(self):
        self.jump_instruction = b''
        self.oem_name = ''
        self.bytes_per_sector = 512
        self.sectors_per_cluster = 0
        self.reserved_sectors_count = 1
        self.fat_copies = 2
        self.max_root_entries = 0
        self.total_sectors = 0
        self.media_descriptor = 0xF8
        self.sectors_per_fat = 0
        self.sectors_per_track = 0
        self.heads = 0
        self.hidden_sectors = 0
        self.total_logical_sectors = 0
        self.physical_drive_number = 0
        self.boot_signature = 0
        self.volume_id = 0
        self.volume_label = ''
        self.fs_type = "FAT16   "
        self.bootstrap_code = bytearray(self.BOOTSTRAP_SIZE)
        self.boot_signature = self.BOOT_SIGNATURE

    def __eq__(self, obj):
        if not isinstance(obj, BootSectorFat16):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        pass

    def export(self):
        data = pack(self.FORMAT,
                    self.jump_instruction,
                    self.oem_name.encode(),
                    self.bytes_per_sector,
                    self.sectors_per_cluster,
                    self.reserved_sectors_count,
                    self.fat_copies,
                    self.max_root_entries,
                    self.total_sectors,
                    self.media_descriptor,
                    self.sectors_per_fat,
                    self.sectors_per_track,
                    self.heads,
                    self.hidden_sectors,
                    self.total_logical_sectors,
                    self.physical_drive_number,
                    0,  # Reserved1 (It should be set 0 when create the volume.)
                    self.boot_signature,
                    self.volume_id,
                    self.volume_label.encode(),
                    self.fs_type.encode())
        data += bytes(self.bootstrap_code)
        data += pack("<H", self.boot_signature)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise Exception()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise Exception()

        obj = cls()
        (
            obj.jump_instruction,
            oem_name,
            obj.bytes_per_sector,
            obj.sectors_per_cluster,
            obj.reserved_sectors_count,
            obj.fat_copies,
            obj.max_root_entries,
            obj.total_sectors,
            obj.media_descriptor,
            obj.sectors_per_fat,
            obj.sectors_per_track,
            obj.heads,
            obj.hidden_sectors,
            obj.total_logical_sectors,
            obj.physical_drive_number,
            _,
            obj.boot_signature,
            obj.volume_id,
            volume_label,
            fs_type
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.oem_name = oem_name.decode()
        obj.volume_label = volume_label.decode()
        obj.fs_type = fs_type.decode()
        offset += cls.SIZE - (cls.BOOTSTRAP_SIZE + 2)
        obj.bootstrap_code = bytearray(data[offset:offset+cls.BOOTSTRAP_SIZE])

        return obj


class BootSectorFat32(object):

    BOOTSTRAP_SIZE = 420
    BOOT_SIGNATURE = 0xAA55
    FORMAT = '<3s8sHBHBHHBHHHIIIHHIHH12sBBBI11s8s'
    SIZE = 512

    def __init__(self):
        self.jump_instruction = b''
        self.oem_name = ''
        self.bytes_per_sector = 512
        self.sectors_per_cluster = 0
        self.reserved_sectors_count = 1
        self.fat_copies = 2
        self.max_root_entries = 0
        self.total_sectors = 0
        self.media_descriptor = 0xF8
        self.sectors_per_fat = 0
        self.sectors_per_track = 0
        self.heads = 0
        self.hidden_sectors = 0
        self.total_logical_sectors = 0
        self.ext_flags = 0
        self.version = 0
        self.root_cluster = 2
        self.fsi_sector = 1
        self.boot_copy_sector = 0
        self.physical_drive_number = 0
        self.flags = 0
        self.boot_signature = 0
        self.volume_id = 0
        self.volume_label = ''
        self.fs_type = "FAT32   "
        self.bootstrap_code = bytearray(self.BOOTSTRAP_SIZE)
        self.boot_signature = self.BOOT_SIGNATURE

    def __eq__(self, obj):
        if not isinstance(obj, BootSectorFat32):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        pass

    def export(self):
        data = pack(self.FORMAT,
                    self.jump_instruction,
                    self.oem_name.encode(),
                    self.bytes_per_sector,
                    self.sectors_per_cluster,
                    self.reserved_sectors_count,
                    self.fat_copies,
                    self.max_root_entries,
                    self.total_sectors,
                    self.media_descriptor,
                    0,  # Sectors per FAT used in FAT12/16
                    self.sectors_per_track,
                    self.heads,
                    self.hidden_sectors,
                    self.total_logical_sectors,
                    self.sectors_per_fat,
                    self.ext_flags,
                    self.version,
                    self.root_cluster,
                    self.fsi_sector,
                    self.boot_copy_sector,
                    b'\0' * 12,  # Reserved, use {0, 0, ...} 12x
                    self.physical_drive_number,
                    0,  # Reserved1 (It should be set 0 when create the volume.)
                    self.flags,
                    self.boot_signature,
                    self.volume_id,
                    self.volume_label.encode(),
                    self.fs_type.encode())
        data += bytes(self.bootstrap_code)
        data += pack("<H", self.boot_signature)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise Exception()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise Exception()

        obj = cls()
        (
            obj.jump_instruction,
            oem_name,
            obj.bytes_per_sector,
            obj.sectors_per_cluster,
            obj.reserved_sectors_count,
            obj.fat_copies,
            obj.max_root_entries,
            obj.total_sectors,
            obj.media_descriptor,
            _,
            obj.sectors_per_track,
            obj.heads,
            obj.hidden_sectors,
            obj.total_logical_sectors,
            obj.sectors_per_fat,
            obj.ext_flags,
            obj.version,
            obj.root_cluster,
            obj.fsi_sector,
            obj.boot_copy_sector,
            _,
            obj.physical_drive_number,
            _,
            obj.flags,
            obj.boot_signature,
            obj.volume_id,
            volume_label,
            fs_type
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.oem_name = oem_name.decode()
        obj.volume_label = volume_label.decode()
        obj.fs_type = fs_type.decode()
        offset += cls.SIZE - (cls.BOOTSTRAP_SIZE + 2)
        obj.bootstrap_code = bytearray(data[offset:offset+cls.BOOTSTRAP_SIZE])

        return obj


class FsInfoFat32(object):

    BOOT_SIGNATURE = 0xAA55
    SIZE = 512

    def __init__(self):
        self.lead_signature = 0x41615252
        self.sector_signature = 0x61417272
        self.free_clusters = 0
        self.next_free_clusters = 0
        self.boot_signature = self.BOOT_SIGNATURE

    def __eq__(self, obj):
        if not isinstance(obj, FsInfoFat32):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        pass

    def export(self):
        data = pack('<I', self.lead_signature)
        data += b'\0' * 480
        data += pack('<III', self.sector_signature, self.free_clusters, self.next_free_clusters)
        data += pack("<H", self.boot_signature)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise Exception()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise Exception()

        obj = cls()
        (
            obj.lead_signature,
            _,
            obj.sector_signature,
            obj.free_clusters,
            obj.next_free_clusters
        ) = unpack_from('<I480sIII', data, offset)

        return obj


class FileAttribute(Enum):
    ATTR_READ_ONLY = 0x01
    ATTR_HIDDEN = 0x02
    ATTR_SYSTEM = 0x04
    ATTR_VOLUME_ID = 0x08
    ATTR_DIRECTORY = 0x10
    ATTR_ARCHIVE = 0x20
    ATTR_LONG_FILE_NAME = 0x0F


class RootDirectory(object):

    FORMAT = '<11s3B7HI'
    SIZE = calcsize(FORMAT)

    def __init__(self):
        self.file_name = ''
        self.attribute = FileAttribute.ATTR_READ_ONLY
        self.ntres = 0
        self.creation_time = 0
        self.creation_date = 0
        self.last_access_date = 0
        self.write_time = 0
        self.write_date = 0
        self.start_cluster = 0
        self.file_size = 0

    def __eq__(self, obj):
        if not isinstance(obj, RootDirectory):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def export(self):
        data = pack(self.FORMAT,
                    self.file_name.encode(),
                    self.attribute,
                    self.ntres,
                    self.creation_time,
                    self.creation_date,
                    self.last_access_date,
                    self.start_cluster >> 16,
                    self.write_time,
                    self.write_date,
                    self.start_cluster & 0xFFFF,
                    self.file_size)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        obj = cls()
        (
            file_name,
            obj.attribute,
            obj.ntres,
            obj.creation_time,
            obj.creation_date,
            obj.last_access_date,
            start_cluster_hi,
            obj.write_time,
            obj.write_date,
            start_cluster_lo,
            obj.file_size
        ) = unpack_from('<I480sIII', data, offset)
        obj.file_name = file_name.decode()
        obj.start_cluster = (start_cluster_hi << 16) | start_cluster_lo

        return obj


class FAT(object):
    """ FAT (12, 16, 32 o EX) table on disk """

    def __init__(self, clusters, bitsize=32, exfat=False):
        pass

    def __eq__(self, obj):
        if not isinstance(obj, FAT):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

