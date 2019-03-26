# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from zlib import crc32
from datetime import datetime
from io import BufferedReader, FileIO, BytesIO, SEEK_CUR, SEEK_END
from struct import pack, unpack_from, calcsize
from easy_enum import EEnum as Enum

# http://elm-chan.org/docs/fat_e.html
# https://msdn.microsoft.com/en-us/windows/hardware/gg463080.aspx


class FATError(Exception):
    pass


class BootSector(object):

    BOOTSTRAP_SIZE = 448
    BOOT_SIGNATURE = 0xAA55
    FORMAT = '<3s8sHBHBHHBHHHIIBBBI11s8s'
    SIZE = 512

    @property
    def cluster_size(self):
        return self.bytes_per_sector * self.sectors_per_cluster

    @property
    def fat_size(self):
        return (self.total_logical_sectors or self.total_sectors) / self.sectors_per_cluster

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.sectors_count

    @property
    def root_offset(self):
        return self.fat_offset + self.fat_copies * self.sectors_per_fat * self.bytes_per_sector

    @property
    def data_offset(self):
        return self.root_offset + self.max_root_entries * 32

    def __init__(self):
        self.jump_instruction = b''
        self.oem_name = ''
        self.bytes_per_sector = 512
        self.sectors_per_cluster = 0
        self.sectors_count = 1
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
        self.fs_type = "FAT16"
        # ...
        self.bootstrap_code = bytearray(self.BOOTSTRAP_SIZE)

    def __eq__(self, obj):
        if not isinstance(obj, BootSector):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        msg = str()
        msg += " OEM Name:              {}\n".format(self.oem_name)
        msg += " Bytes per Sector:      {}\n".format(self.bytes_per_sector)
        msg += " Sectors per Cluster:   {}\n".format(self.sectors_per_cluster)
        msg += " Sectors Count:         {}\n".format(self.sectors_count)
        msg += " FAT Copies:            {}\n".format(self.fat_copies)
        msg += " Max Root Entries:      {}\n".format(self.max_root_entries)
        msg += " Total Sectors:         {}\n".format(self.total_sectors)
        msg += " Media Descriptor:      0x{:02X}\n".format(self.media_descriptor)
        msg += " Sectors per FAT:       {}\n".format(self.sectors_per_fat)
        msg += " Sectors per Track:     {}\n".format(self.sectors_per_track)
        msg += " Heads:                 {}\n".format(self.heads)
        msg += " Hidden Sectors:        {}\n".format(self.hidden_sectors)
        msg += " Total Logical Sectors: {}\n".format(self.total_logical_sectors)
        msg += " Physical Drv Number:   {}\n".format(self.physical_drive_number)
        msg += " Boot Signature:        {}\n".format(self.boot_signature)
        msg += " Volume ID:             0x{:08X}\n".format(self.volume_id)
        msg += " Volume Label:          {}\n".format(self.volume_label)
        msg += " FS Type:               {}\n".format(self.fs_type)
        return msg

    def export(self):
        data = pack(self.FORMAT,
                    self.jump_instruction,
                    self.oem_name.encode(),
                    self.bytes_per_sector,
                    self.sectors_per_cluster,
                    self.sectors_count,
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
        data += pack("<H", self.BOOT_SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise FATError()

        obj = cls()
        (
            obj.jump_instruction,
            oem_name,
            obj.bytes_per_sector,
            obj.sectors_per_cluster,
            obj.sectors_count,
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


class BootSector32(object):

    BOOTSTRAP_SIZE = 420
    BOOT_SIGNATURE = 0xAA55
    FORMAT = '<3s8sHBHBHHBHHHIIIHHIHH12sBBBI11s8s'
    SIZE = 512

    @property
    def cluster_size(self):
        return self.bytes_per_sector * self.sectors_per_cluster

    @property
    def fat_size(self):
        return self.total_logical_sectors / self.sectors_per_cluster

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.sectors_count

    @property
    def data_offset(self):
        return self.fat_offset + self.fat_copies * self.sectors_per_fat * self.bytes_per_sector

    def __init__(self):
        self.jump_instruction = b''
        self.oem_name = ''
        self.bytes_per_sector = 512
        self.sectors_per_cluster = 0
        self.sectors_count = 1
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
        self.boot_signature = 0
        self.volume_id = 0
        self.volume_label = ''
        self.fs_type = "FAT32"
        # ...
        self.bootstrap_code = bytearray(self.BOOTSTRAP_SIZE)

    def __eq__(self, obj):
        if not isinstance(obj, BootSector32):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        msg = str()
        msg += " OEM Name:              {}\n".format(self.oem_name)
        msg += " Bytes per Sector:      {}\n".format(self.bytes_per_sector)
        msg += " Sectors per Cluster:   {}\n".format(self.sectors_per_cluster)
        msg += " Sectors Count:         {}\n".format(self.sectors_count)
        msg += " FAT Copies:            {}\n".format(self.fat_copies)
        msg += " Max Root Entries:      {}\n".format(self.max_root_entries)
        msg += " Total Sectors:         {}\n".format(self.total_sectors)
        msg += " Media Descriptor:      0x{:02X}\n".format(self.media_descriptor)
        msg += " Sectors per FAT:       {}\n".format(self.sectors_per_fat)
        msg += " Sectors per Track:     {}\n".format(self.sectors_per_track)
        msg += " Heads:                 {}\n".format(self.heads)
        msg += " Hidden Sectors:        {}\n".format(self.hidden_sectors)
        msg += " Total Logical Sectors: {}\n".format(self.total_logical_sectors)
        msg += " Ext. Flags:            {}\n".format(self.ext_flags)
        msg += " Version:               {}\n".format(self.version)
        msg += " Root Cluster:          {}\n".format(self.root_cluster)
        msg += " FSI Sector:            {}\n".format(self.fsi_sector)
        msg += " Boot Copy Sector:      {}\n".format(self.boot_copy_sector)
        msg += " Physical Drv Number:   {}\n".format(self.physical_drive_number)
        msg += " Boot Signature:        {}\n".format(self.boot_signature)
        msg += " Volume ID:             0x{:08X}\n".format(self.volume_id)
        msg += " Volume Label:          {}\n".format(self.volume_label)
        msg += " FS Type:               {}\n".format(self.fs_type)
        return msg

    def export(self):
        data = pack(self.FORMAT,
                    self.jump_instruction,
                    self.oem_name.encode(),
                    self.bytes_per_sector,
                    self.sectors_per_cluster,
                    self.sectors_count,
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
                    b'\0' * 12,  # Reserved, use 0
                    self.physical_drive_number,
                    0,  # Reserved1 (It should be set 0 when create the volume.)
                    self.boot_signature,
                    self.volume_id,
                    self.volume_label.ljust(11).encode(),
                    self.fs_type.ljust(8).encode())
        data += bytes(self.bootstrap_code)
        data += pack("<H", self.BOOT_SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise FATError()

        obj = cls()
        (
            obj.jump_instruction,
            oem_name,
            obj.bytes_per_sector,
            obj.sectors_per_cluster,
            obj.sectors_count,
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
            obj.boot_signature,
            obj.volume_id,
            volume_label,
            fs_type
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.oem_name = oem_name.decode().strip()
        obj.volume_label = volume_label.decode().strip()
        obj.fs_type = fs_type.decode().strip()
        offset += cls.SIZE - (cls.BOOTSTRAP_SIZE + 2)
        obj.bootstrap_code = bytearray(data[offset:offset+cls.BOOTSTRAP_SIZE])

        return obj


class FsInfo32(object):

    BOOT_SIGNATURE = 0xAA55
    FIRST_SIGNATURE = 0x41615252
    SECOND_SIGNATURE = 0x61417272
    SIZE = 512

    def __init__(self):
        self.free_clusters = 0
        self.next_free_cluster = 0

    def __eq__(self, obj):
        if not isinstance(obj, FsInfo32):
            return False
        if self.free_clusters != obj.free_clusters or self.next_free_cluster != obj.next_free_cluster:
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        msg = str()
        msg += " Free Clusters:         {}\n".format(self.free_clusters)
        msg += " Next Free Cluster:     {}\n".format(self.next_free_cluster)
        return msg

    def export(self):
        data = pack('<I', self.FIRST_SIGNATURE)
        data += b'\0' * 480
        data += pack('<IIIH', self.SECOND_SIGNATURE, self.free_clusters, self.next_free_cluster, self.BOOT_SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.BOOT_SIGNATURE:
            raise FATError()

        obj = cls()
        (
            obj.first_signature,
            _,
            obj.second_signature,
            obj.free_clusters,
            obj.next_free_cluster
        ) = unpack_from('<I480sIII', data, offset)

        return obj


class FileAttr(Enum):
    READ_ONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    VOLUME_ID = 0x08
    DIRECTORY = 0x10
    ARCHIVE = 0x20
    LONG_FILE_NAME = 0x0F


class FileShortName(object):

    FORMAT = '<8s3s3B7HI'
    SIZE = calcsize(FORMAT)

    def __init__(self):
        self.name = ''
        self.extension = ''
        self.attributes = FileAttr.READ_ONLY
        self.creation_time_ms = 0
        self.creation_time = 0
        self.creation_date = 0
        self.last_access_time = 0
        self.modified_time = 0
        self.modified_date = 0
        self.first_cluster = 0
        self.file_size = 0

    def __eq__(self, obj):
        if not isinstance(obj, FileShortName):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        msg = str()
        msg += " Name:                  {}\n".format(self.name)
        msg += " Extension:             {}\n".format(self.extension)
        msg += " Attributes:            {}\n".format(self.attributes)
        msg += " Creation Time [ms]:    {}\n".format(self.creation_time_ms)
        msg += " Creation Time:         {}\n".format(self.creation_time)
        msg += " Creation Date:         {}\n".format(self.creation_date)
        msg += " Last Access Time:      {}\n".format(self.last_access_time)
        msg += " Modified Time:         {}\n".format(self.modified_time)
        msg += " Modified Date:         {}\n".format(self.modified_date)
        msg += " First Cluster:         {}\n".format(self.first_cluster)
        msg += " File Size:             {}\n".format(self.file_size)
        return msg

    def export(self):
        data = pack(self.FORMAT,
                    self.name.encode(),
                    self.extension.encode(),
                    self.attributes,
                    0,
                    self.creation_time_ms,
                    self.creation_time,
                    self.creation_date,
                    self.last_access_time,
                    (self.first_cluster >> 16) & 0xFFFF,
                    self.modified_time,
                    self.modified_date,
                    (self.first_cluster & 0xFFFF),
                    self.file_size)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()

        obj = cls()
        (
            name,
            extension,
            obj.attributes,
            _,
            obj.creation_time_ms,
            obj.creation_time,
            obj.creation_date,
            obj.last_access_date,
            start_cluster_hi,
            obj.modified_time,
            obj.modified_date,
            start_cluster_lo,
            obj.file_size
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.name = name.decode()
        obj.extension = extension.decode()
        obj.first_cluster = (start_cluster_hi << 16) | start_cluster_lo

        return obj


class FileLongName(object):

    FORMAT = '<B10s3B12sH2s'
    SIZE = calcsize(FORMAT)

    def __init__(self):
        self.sequence_number = 0
        self.name = ''
        self.attributes = FileAttr.LONG_FILE_NAME
        self.type = 0
        self.checksum = 0
        self.first_cluster = 0  # Always 0x0000

    def __eq__(self, obj):
        if not isinstance(obj, FileLongName):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        pass

    def export(self):
        name = self.name.ljust(13)
        data = pack(self.FORMAT,
                    self.sequence_number,
                    name[0:5].encode('UTF-16-LE'),
                    self.attributes,
                    self.type,
                    self.checksum,
                    name[5:11].encode('UTF-16-LE'),
                    self.first_cluster,
                    name[11:13].encode('UTF-16-LE'))
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()


class FAT(object):
    """ FAT12, FAT16 and FAT32 Class """

    RESERVED = {12: 0x0FF7, 16: 0xFFF7, 32: 0x0FFFFFF7}
    BAD = {12: 0x0FF7, 16: 0xFFF7, 32: 0x0FFFFFF7}
    LAST = {12: 0x0FFF, 16: 0xFFFF, 32: 0x0FFFFFF8}

    def __init__(self, stream, clusters, bits=32):
        """
        :param stream: FileIO or BytesIO stream
        :param clusters: total clusters in the data area
        :param bits: cluster slot bits (12, 16 or 32)
        """
        assert isinstance(stream, (BufferedReader, FileIO, BytesIO))
        assert bits in (12, 16, 32)
        assert clusters <= (2 ** bits) - 11

        self._io = stream
        self.bits = bits
        self.clusters = clusters
        self.reserved = self.RESERVED[bits]
        self.bad = self.BAD[bits]
        self.last = self.LAST[bits]
        self.boot_sector = None
        self.fs_info = None

    def __eq__(self, obj):
        if not isinstance(obj, FAT):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def load(self):
        self.boot_sector = BootSector32.parse(self._io.read(BootSector32.SIZE))
        self.fs_info = FsInfo32.parse(self._io.read(FsInfo32.SIZE))
        print(self.boot_sector.info())
        print(self.fs_info.info())



