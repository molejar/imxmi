# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
from zlib import crc32
from datetime import datetime, date, time
from io import BufferedReader, FileIO, BytesIO, SEEK_CUR, SEEK_END
from struct import pack, unpack_from, calcsize
from easy_enum import EEnum as Enum

# http://elm-chan.org/docs/fat_e.html
# https://www.easeus.com/resource/fat32-disk-structure.htm
# https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system
# https://msdn.microsoft.com/en-us/windows/hardware/gg463080.aspx


########################################################################################################################
# helper functions
########################################################################################################################

def size_fmt(num, use_kibibyte=True):
    base, suffix = [(1000., 'B'), (1024., 'iB')][use_kibibyte]
    for x in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < num < base:
            break
        num /= base
    return "{0:3.1f} {1:s}".format(num, x)


def lfn_crc(name):
    assert isinstance(name, bytes)
    assert len(name) == 11

    crc_sum = 0
    for c in name:
        crc_sum = ((crc_sum & 1) << 7) + (crc_sum >> 1) + c
        crc_sum &= 0xFF

    return crc_sum


def decode_datetime(raw_date, raw_time, raw_time_ms=0):
    return datetime((raw_date >> 9) + 1980, (raw_date >> 5) & 0x7, raw_date & 0xF,
                    (raw_time >> 11), (raw_time >> 5) & 0x1F, (raw_time & 0xF) * 2, raw_time_ms * 1000)


def decode_date(raw_date):
    return date((raw_date >> 9) + 1980, (raw_date >> 5) & 0x7, raw_date & 0xF)


def encode_date(obj_date):
    assert isinstance(obj_date, date)
    return (obj_date.years - 1980) << 9 | (obj_date.mounts & 0x7) << 5 | obj_date.days & 0xF


def encode_time(obj_time):
    assert isinstance(obj_time, time)
    return (obj_time.hours << 11) | ((obj_time.minutes & 0x1F) << 5) | ((obj_time.seconds // 2) & 0xF)


########################################################################################################################
# FAT Exceptions
########################################################################################################################

class FATError(Exception):
    pass


########################################################################################################################
# FAT Classes
########################################################################################################################

class BootSector(object):

    JUMP_INSTRUCTION = b'\xEB\x3C\x90'
    BOOT_SIGNATURE = 0xAA55
    BOOTSTRAP_SIZE = 448
    FORMAT = '<3s8sHBHBHHBHHHIIBBBI11s8s'
    SIZE = 512

    @property
    def cluster_size(self):
        return self.bytes_per_sector * self.sectors_per_cluster

    @property
    def fat_size(self):
        return self.sectors_per_fat * self.bytes_per_sector

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.reserved_sectors_count

    @property
    def root_offset(self):
        return self.fat_offset + self.fat_copies * self.fat_size

    @property
    def data_offset(self):
        return self.root_offset + (self.max_root_entries * 32)

    def __init__(self):
        self.jump_instruction = self.JUMP_INSTRUCTION
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
        msg += " OEM Name:               {}\n".format(self.oem_name)
        msg += " Bytes per Sector:       {}\n".format(self.bytes_per_sector)
        msg += " Sectors per Cluster:    {}\n".format(self.sectors_per_cluster)
        msg += " Reserved Sectors Count: {}\n".format(self.reserved_sectors_count)
        msg += " FAT Copies:             {}\n".format(self.fat_copies)
        msg += " Max Root Entries:       {}\n".format(self.max_root_entries)
        msg += " Total Sectors:          {}\n".format(self.total_sectors)
        msg += " Media Descriptor:       0x{:02X}\n".format(self.media_descriptor)
        msg += " Sectors per FAT:        {}\n".format(self.sectors_per_fat)
        msg += " Sectors per Track:      {}\n".format(self.sectors_per_track)
        msg += " Heads:                  {}\n".format(self.heads)
        msg += " Hidden Sectors:         {}\n".format(self.hidden_sectors)
        msg += " Total Logical Sectors:  {}\n".format(self.total_logical_sectors)
        msg += " Physical Drv Number:    {}\n".format(self.physical_drive_number)
        msg += " Boot Signature:         {}\n".format(self.boot_signature)
        msg += " Volume ID:              0x{:08X}\n".format(self.volume_id)
        msg += " Volume Label:           {}\n".format(self.volume_label)
        msg += " FS Type:                {}\n".format(self.fs_type)
        return msg

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
        if data[:3] != cls.JUMP_INSTRUCTION:
            raise FATError()

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
        obj.oem_name = oem_name.decode().strip()
        obj.volume_label = volume_label.decode().strip()
        obj.fs_type = fs_type.decode().strip()
        offset += cls.SIZE - (cls.BOOTSTRAP_SIZE + 2)
        obj.bootstrap_code = bytearray(data[offset:offset+cls.BOOTSTRAP_SIZE])

        return obj


class BootSector32(object):

    JUMP_INSTRUCTION = b'\xEB\x3C\x90'
    BOOTSTRAP_SIZE = 420
    BOOT_SIGNATURE = 0xAA55
    FORMAT = '<3s8sHBHBHHBHHHIIIHHIHH12sBBBI11s8s'
    SIZE = 512

    @property
    def cluster_size(self):
        return self.bytes_per_sector * self.sectors_per_cluster

    @property
    def fat_size(self):
        return self.sectors_per_fat * self.bytes_per_sector

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.reserved_sectors_count

    @property
    def data_offset(self):
        return self.fat_offset + (self.fat_copies * self.fat_size)

    def __init__(self):
        self.jump_instruction = self.JUMP_INSTRUCTION
        self.oem_name = 'imxmi'
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
        msg += " OEM Name:               {}\n".format(self.oem_name)
        msg += " Bytes per Sector:       {}\n".format(self.bytes_per_sector)
        msg += " Sectors per Cluster:    {}\n".format(self.sectors_per_cluster)
        msg += " Reserved Sectors Count: {}\n".format(self.reserved_sectors_count)
        msg += " FAT Copies:             {}\n".format(self.fat_copies)
        msg += " Max Root Entries:       {}\n".format(self.max_root_entries)
        msg += " Total Sectors:          {}\n".format(self.total_sectors)
        msg += " Media Descriptor:       0x{:02X}\n".format(self.media_descriptor)
        msg += " Sectors per FAT:        {}\n".format(self.sectors_per_fat)
        msg += " Sectors per Track:      {}\n".format(self.sectors_per_track)
        msg += " Heads:                  {}\n".format(self.heads)
        msg += " Hidden Sectors:         {}\n".format(self.hidden_sectors)
        msg += " Total Logical Sectors:  {}\n".format(self.total_logical_sectors)
        msg += " Ext. Flags:             {}\n".format(self.ext_flags)
        msg += " Version:                {}\n".format(self.version)
        msg += " Root Cluster:           {}\n".format(self.root_cluster)
        msg += " FSI Sector:             {}\n".format(self.fsi_sector)
        msg += " Boot Copy Sector:       {}\n".format(self.boot_copy_sector)
        msg += " Physical Drv Number:    {}\n".format(self.physical_drive_number)
        msg += " Boot Signature:         {}\n".format(self.boot_signature)
        msg += " Volume ID:              0x{:08X}\n".format(self.volume_id)
        msg += " Volume Label:           {}\n".format(self.volume_label)
        msg += " FS Type:                {}\n".format(self.fs_type)
        return msg

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
        if data[:3] != cls.JUMP_INSTRUCTION:
            raise FATError()

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

    LEAD_SIGNATURE = 0x41615252
    FSNFO_SIGNATURE = 0x61417272
    TRAIL_SIGNATURE = 0xAA550000
    SIZE = 512

    def __init__(self, free_clusters, next_free_cluster):
        self.free_clusters = free_clusters
        self.next_free_cluster = next_free_cluster

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
        data = pack('<I', self.LEAD_SIGNATURE)
        data += b'\0' * 480
        data += pack('<III', self.FSNFO_SIGNATURE, self.free_clusters, self.next_free_cluster)
        data += b'\0' * 12
        data += pack('<I', self.TRAIL_SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SIZE):
            raise FATError()
        if unpack_from("<I", data, offset)[0] != cls.LEAD_SIGNATURE:
            raise FATError()
        offset += 484
        if unpack_from("<I", data, offset)[0] != cls.FSNFO_SIGNATURE:
            raise FATError()
        if unpack_from("<I", data, offset + 24)[0] != cls.TRAIL_SIGNATURE:
            raise FATError()

        (free_clusters, next_free_cluster) = unpack_from('<II', data, offset + 4)

        return cls(free_clusters, next_free_cluster)


class FileAttr(Enum):
    READ_ONLY = 0x01
    HIDDEN = 0x02
    SYSTEM = 0x04
    VOLUME_ID = 0x08
    DIRECTORY = 0x10
    ARCHIVE = 0x20
    LONG_FILE_NAME = 0x0F


class FileEntry(object):

    def __init__(self, name, attr, size=0):
        self.name = name
        self.attributes = attr
        self.creation_dt = datetime.now()
        self.modified_dt = datetime.now()
        self.last_access_date = self.modified_dt.date()
        self.first_cluster = 0
        self.file_size = size

    def __eq__(self, obj):
        if not isinstance(obj, FileEntry):
            return False
        if self.name != obj.name or \
           self.attributes != obj.attributes or \
           self.creation_dt != obj.creation_dt or \
           self.modified_dt != obj.modified_dt or \
           self.last_access_date != obj.last_access_date or \
           self.first_cluster != obj.first_cluster or \
           self.file_size != obj.file_size:
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def __str__(self):
        return '<{} - {}>'.format(self.name, size_fmt(self.file_size))

    def info(self):
        msg = str()
        msg += " File Name:             {}\n".format(self.name)
        msg += " Attributes:            {}\n".format(FileAttr[self.attributes])
        msg += " Last Access Date:      {}\n".format(self.last_access_date.strftime('%d.%m.%Y'))
        msg += " Modified Date & Time:  {}\n".format(self.modified_dt.strftime('%d.%m.%Y [%X]'))
        msg += " Creation Date & Time:  {}\n".format(self.creation_dt.strftime('%d.%m.%Y [%X]'))
        msg += " First Cluster:         {}\n".format(self.first_cluster)
        msg += " File Size:             {}\n".format(size_fmt(self.file_size))
        return msg


class RootEntry(object):

    SFN_FORMAT = '<11s3B7HI'
    LFN_FORMAT = '<B10s3B12sH4s'
    SFN_SIZE = calcsize(SFN_FORMAT)
    LFN_SIZE = calcsize(LFN_FORMAT)
    LFN_BYTES = 26

    def __init__(self, name):
        self.volume_name = name
        self.creation_dt = datetime.now()
        self.modified_dt = datetime.now()
        self.last_access_date = self.modified_dt.date()
        self._files = []

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def __len__(self):
        return len(self._files)

    def __getitem__(self, key):
        return self._files[key]

    def __setitem__(self, key, value):
        self._files[key] = value

    def __iter__(self):
        return self._files.__iter__()

    def clear(self):
        self._files.clear()

    def dell(self, index):
        return self._files.pop(index)

    def append(self, value):
        self._files.append(value)

    def get_file_entry(self, file_name):
        isinstance(file_name, str)

        for file_entry in self._files:
            if file_entry.name == file_name:
                return file_entry

        return None

    @staticmethod
    def short_name(name):
        file_name = name.split('.')
        if len(file_name) > 2 or len(file_name[-1]) > 3 or (len(file_name[0]) + len(file_name[1])) > 11:
            short_name = name[:6].upper() + '~1   '
        else:
            short_name = file_name[0] + file_name[1]

        return short_name.encode()

    def info(self):
        msg = str()
        msg += " Volume Name:           {}\n".format(self.volume_name)
        msg += " Last Access Date:      {}\n".format(self.last_access_date.strftime('%d.%m.%Y'))
        msg += " Modified Date & Time:  {}\n".format(self.modified_dt.strftime('%d.%m.%Y [%X]'))
        msg += " Creation Date & Time:  {}\n".format(self.creation_dt.strftime('%d.%m.%Y [%X]'))
        msg += " Files Count:           {}\n".format(len(self._files))
        for f in self._files:
            msg += "\n"
            msg += f.info()
        return msg

    def export(self):
        data = pack(self.SFN_FORMAT, self.volume_name.encode(), FileAttr.VOLUME_ID, 0,
                    self.creation_dt.microsecond // 1000, encode_time(self.creation_dt.time()),
                    encode_date(self.creation_dt.date()), encode_date(self.last_access_date), 0,
                    encode_time(self.modified_dt.time()), encode_date(self.modified_dt.date()), 0, 0)

        for f in self._files:
            short_name = self.short_name(f.name)
            long_name = f.name.encode('UTF-16-LE')
            long_name_size = len(long_name)
            sn_crc = lfn_crc(short_name)
            # align complete long name to LN_BYTES
            if long_name_size % self.LFN_BYTES:
                long_name += b'\xFF' * (self.LFN_BYTES - long_name_size)
            # calculate key parameters
            offset = len(long_name) - self.LFN_BYTES
            snum = (len(long_name) // self.LFN_BYTES) | 0x40

            while True:
                name = long_name[offset: offset + self.LFN_BYTES]
                data += pack(self.LFN_FORMAT, snum, name[0:10], 0x0F, 0, sn_crc, name[10:22], 0, name[22:26])
                if offset == 0:
                    break
                if snum & 0x40:
                    snum &= 0x3F
                offset -= self.LFN_BYTES
                snum -= 1

            data += pack(self.SFN_FORMAT,
                         short_name,
                         f.attributes,
                         0,  # Reserved for use by Windows NT. Use: 0
                         f.creation_dt.microsecond // 1000,
                         encode_time(f.creation_dt.time()),
                         encode_date(f.creation_dt.date()),
                         encode_date(f.last_access_date),
                         (f.first_cluster >> 16) & 0xFFFF,
                         encode_time(f.modified_dt.time()),
                         encode_date(f.modified_dt.date()),
                         f.first_cluster & 0xFFFF,
                         f.file_size)

        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SFN_SIZE):
            raise FATError()
        if data[offset + 11] != FileAttr.VOLUME_ID:
            raise FATError()

        (name, _, _, ctime_ms, ctime, cdate, la_date, _, mtime, mdate, _, _) = unpack_from(cls.SFN_FORMAT, data, offset)

        obj = cls(name.decode())
        obj.creation_dt = decode_datetime(cdate, ctime, ctime_ms)
        obj.modified_dt = decode_datetime(mdate, mtime)
        obj.last_access_date = decode_date(la_date)

        offset += cls.SFN_SIZE
        while data[offset] != 0 and data[offset + 1] != 0:
            long_name = b''
            long_name_cnt = 0
            long_name_crc = 0

            while data[offset + 11] == FileAttr.LONG_FILE_NAME:
                (cnt, name0, attr, _, crc, name1, _, name2) = unpack_from(cls.LFN_FORMAT, data, offset)
                if cnt & 0x40:
                    long_name_cnt = cnt & 0x3F
                    long_name_crc = crc
                else:
                    if long_name_cnt != cnt:
                        raise FATError()
                    if long_name_crc != crc:
                        raise FATError()

                long_name_cnt -= 1
                long_name = name0 + name1 + name2 + long_name
                offset += cls.LFN_SIZE

            (short_name, attr, _, creation_time_ms, creation_time, creation_date, last_access_date, start_cluster_hi,
             modified_time, modified_date, start_cluster_lo, file_size) = unpack_from(cls.SFN_FORMAT, data, offset)
            offset += cls.SFN_SIZE

            if long_name_crc != lfn_crc(short_name):
                name = short_name.decode()
            else:
                name = long_name.rstrip(b'\xFF\xFF').decode('UTF-16-LE').strip('\0')

            obj_file = FileEntry(name, attr, file_size)
            obj_file.first_cluster = (start_cluster_hi << 16) | start_cluster_lo
            obj_file.creation_dt = decode_datetime(creation_date, creation_time, creation_time_ms)
            obj_file.modified_dt = decode_datetime(modified_date, modified_time)
            obj_file.last_access_date = decode_date(last_access_date)
            obj.append(obj_file)

        return obj


def get_fat_bits(stream, offset):

    FAT_BITS = {'FAT12': 12, 'FAT16': 16, 'FAT32': 32}

    try:
        stream.seek(offset)
        boot_sector = BootSector32.parse(stream.read(BootSector32.SIZE))
    except:
        stream.seek(offset)
        boot_sector = BootSector.parse(stream.read(BootSector.SIZE))

    if boot_sector.fs_type not in FAT_BITS:
        raise FATError()

    return FAT_BITS[boot_sector.fs_type]


class FAT(object):
    """ FAT12, FAT16 and FAT32 Class """

    RESERVED = {12: 0x0FF7, 16: 0xFFF7, 32: 0x0FFFFFF7}
    BAD_MARK = {12: 0x0FF7, 16: 0xFFF7, 32: 0x0FFFFFF7}
    EOF_MARK = {12: 0x0FF8, 16: 0xFFF8, 32: 0x0FFFFFF8}

    def __init__(self, stream, offset, sectors, bits=32):
        """
        :param stream: FileIO or BytesIO stream
        :param clusters: total clusters in the data area
        :param bits: cluster slot bits (12, 16 or 32)
        """
        assert isinstance(stream, (BufferedReader, FileIO, BytesIO))
        assert bits in (0, 12, 16, 32)
        # assert clusters <= (2 ** bits) - 11

        self._io = stream
        self._io_offset = offset
        self.bits = bits
        self.sectors = sectors
        self.reserved = self.RESERVED[bits]
        self.bad_mark = self.BAD_MARK[bits]
        self.eof_mark = self.EOF_MARK[bits]
        self.boot_sector = None
        self.fs_info = None
        self.fat_blob = None
        self.root_dir = None
        # ...
        self.load()

    def __eq__(self, obj):
        if not isinstance(obj, FAT):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def _get_data_cluster_offset(self, cluster):
        cluster = cluster - 2
        return self._io_offset + self.boot_sector.data_offset + cluster * self.boot_sector.cluster_size

    def _get_file_clusters(self, first_cluster):
        clusters = [first_cluster]
        fat_index = first_cluster

        while True:
            if self.bits == 12:
                blob_index = fat_index + fat_index // 2
                if blob_index >= len(self.fat_blob):
                    break

                if fat_index % 2:
                    value = self.fat_blob[blob_index] >> 4
                    value |= self.fat_blob[blob_index + 1] << 4
                else:
                    value = self.fat_blob[blob_index]
                    value |= (self.fat_blob[blob_index + 1] & 0x0F) << 8

            elif self.bits == 16:
                value = unpack_from('<H', self.fat_blob, fat_index * 2)

            else:
                value = unpack_from('<I', self.fat_blob, fat_index * 4)

            if value == self.eof_mark:
                break

            clusters.append(value)
            fat_index = value

        return clusters

    def info(self):
        nfo = str()
        nfo += " < FAT: Boot Sector > " + "-" * 39 + "\n"
        nfo += self.boot_sector.info()
        if self.fs_info is not None:
            nfo += self.fs_info.info()
        if self.root_dir is not None:
            nfo += "\n < FAT: Root Directory > " + "-" * 36 + "\n"
            nfo += self.root_dir.info()
        nfo += " " + "-" * 60 + "\n\n"
        return nfo

    def load(self):
        self._io.seek(self._io_offset)

        # Parse Boot Sector
        if self.bits == 32:
            self.boot_sector = BootSector32.parse(self._io.read(BootSector32.SIZE))
            self.fs_info = FsInfo32.parse(self._io.read(FsInfo32.SIZE))

            if self.boot_sector.boot_copy_sector:
                self._io.seek(self._io_offset + self.boot_sector.bytes_per_sector * self.boot_sector.boot_copy_sector)
                boot_copy_sector = BootSector32.parse(self._io.read(BootSector32.SIZE))
                if self.boot_sector != boot_copy_sector:
                    raise FATError()
        else:
            self.boot_sector = BootSector.parse(self._io.read(BootSector.SIZE))

        # Read FAT table
        self._io.seek(self._io_offset + self.boot_sector.fat_offset)
        self.fat_blob = self._io.read(self.boot_sector.fat_size)

        # Compare it with FAT copies
        for n in range(1, self.boot_sector.fat_copies):
            fat_data_copy = self._io.read(self.boot_sector.fat_size)
            if self.fat_blob != fat_data_copy:
                raise FATError()

        # parse root directory
        root_dir_len = self.boot_sector.bytes_per_sector * self.boot_sector.sectors_per_cluster
        self._io.seek(self._io_offset + self.boot_sector.root_offset)
        self.root_dir = RootEntry.parse(self._io.read(root_dir_len))

    def export_file(self, name_or_entry):
        if isinstance(name_or_entry, str):
            file_entry = self.root_dir.get_file_entry(name_or_entry)
            if file_entry is None:
                raise FATError("File \"{}\" doesnt exist !".format(name_or_entry))
        elif isinstance(name_or_entry, FileEntry):
            file_entry = name_or_entry
        else:
            raise FATError()

        file_data = b''
        file_size = file_entry.file_size
        file_clusters = self._get_file_clusters(file_entry.first_cluster)

        for cluster in file_clusters:
            if file_size == 0:
                break
            # calculate cluster offset and data size
            offset = self._get_data_cluster_offset(cluster)
            size = min(self.boot_sector.cluster_size, file_size)
            # read data from cluster
            self._io.seek(offset)
            file_data += self._io.read(size)
            file_size -= size

        return file_data

    def save_file(self, name_or_entry, dest_path=''):
        if isinstance(name_or_entry, str):
            file_entry = self.root_dir.get_file_entry(name_or_entry)
            if file_entry is None:
                raise FATError("File \"{}\" doesnt exist !".format(name_or_entry))
        elif isinstance(name_or_entry, FileEntry):
            file_entry = name_or_entry
        else:
            raise FATError()

        file_size = file_entry.file_size
        file_path = os.path.join(dest_path, file_entry.name)
        file_clusters = self._get_file_clusters(file_entry.first_cluster)

        with open(file_path, "wb") as f:
            for cluster in file_clusters:
                # break if no more date
                if file_size == 0:
                    break
                # calculate cluster offset and data size
                offset = self._get_data_cluster_offset(cluster)
                size = min(self.boot_sector.cluster_size,  file_size)
                # copy data from cluster
                self._io.seek(offset)
                f.write(self._io.read(size))
                file_size -= size

    def import_file(self, file_name, data):
        assert isinstance(file_name, str)
        assert isinstance(data, bytes)
        # TODO: write implementation
        pass

    def load_file(self, file_path):
        assert isinstance(file_path, str)
        if not os.path.exists(file_path):
            raise FATError()
        # TODO: write implementation
        pass

    def remove_file(self, name_or_entry):
        if isinstance(name_or_entry, str):
            file_entry = self.root_dir.get_file_entry(name_or_entry)
            if file_entry is None:
                raise FATError("File \"{}\" doesnt exist !".format(name_or_entry))
        elif isinstance(name_or_entry, FileEntry):
            file_entry = name_or_entry
        else:
            raise FATError()
        # TODO: write implementation
        pass

    def remove_all(self):
        # TODO: write implementation
        pass
