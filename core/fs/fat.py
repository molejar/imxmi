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
# https://www.easeus.com/resource/fat32-disk-structure.htm
# https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system
# https://msdn.microsoft.com/en-us/windows/hardware/gg463080.aspx


def hexdump(data, saddr=0, compress=True, length=16, sep='.'):
    """ Return string array in hex dump.format
    :param data:     {List} The data array of {Bytes}
    :param saddr:    {Int}  Absolute Start Address
    :param compress: {Bool} Compressed output (remove duplicated content, rows)
    :param length:   {Int}  Number of Bytes for row (max 16).
    :param sep:      {Char} For the text part, {sep} will be used for non ASCII char.
    """
    msg = []

    # The max line length is 16 bytes
    if length > 16:
        length = 16

    # Create header
    header = '  ADDRESS | '
    for i in range(0, length):
        header += "{:02X} ".format(i)
    header += '| '
    for i in range(0, length):
        header += "{:X}".format(i)
    msg.append(header)
    msg.append((' ' + '-' * (13 + 4 * length)))

    # Check address align
    offset = saddr % length
    address = saddr - offset
    align = True if (offset > 0) else False

    # Print flags
    prev_line = None
    print_mark = True

    # process data
    for i in range(0, len(data) + offset, length):

        hexa = ''
        if align:
            subSrc = data[0: length - offset]
        else:
            subSrc = data[i - offset: i + length - offset]
            if compress:
                # compress output string
                if subSrc == prev_line:
                    if print_mark:
                        print_mark = False
                        msg.append(' *')
                    continue
                else:
                    prev_line = subSrc
                    print_mark = True

        if align:
            hexa += '   ' * offset

        for h in range(0, len(subSrc)):
            h = subSrc[h]
            if not isinstance(h, int):
                h = ord(h)
            hexa += "{:02X} ".format(h)

        text = ''
        if align:
            text += ' ' * offset

        for c in subSrc:
            if not isinstance(c, int):
                c = ord(c)
            if 0x20 <= c < 0x7F:
                text += chr(c)
            else:
                text += sep

        msg.append((' {:08X} | {:<' + str(length * 3) + 's}| {:s}').format(address + i, hexa, text))
        align = False

    msg.append((' ' + '-' * (13 + 4 * length)))
    return '\n'.join(msg)


def size_fmt(num, use_kibibyte=True):
    base, suffix = [(1000., 'B'), (1024., 'iB')][use_kibibyte]
    for x in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < num < base:
            break
        num /= base
    return "{0:3.1f} {1:s}".format(num, x)


def lfn_checksum(name):
    assert isinstance(name, str)

    checksum = 0
    for c in name:
        checksum = ((checksum & 1) << 7) + (checksum >> 1) + ord(c)

    return checksum


def decode_date_time(date, time):
    return (date >> 9) + 1980, (date >> 5) & 0x7, date & 0xF, (time >> 11), (time >> 5) & 0x1F, (time & 0xF) * 2


def encode_date(years, mounts, days):
    return (years - 1980) << 9 | (mounts & 0x7) << 5 | days & 0xF


def encode_time(hours, minutes, seconds):
    return (hours << 11) | ((minutes & 0x1F) << 5) | ((seconds // 2) & 0xF)


class FATError(Exception):
    pass


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
        return (self.total_logical_sectors or self.total_sectors) / self.sectors_per_cluster

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.reserved_sectors_count

    @property
    def root_offset(self):
        return self.fat_offset + self.fat_copies * self.sectors_per_fat * self.bytes_per_sector

    @property
    def data_offset(self):
        return self.root_offset + self.max_root_entries * 32

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
        return self.total_logical_sectors / self.sectors_per_cluster

    @property
    def fat_offset(self):
        return self.bytes_per_sector * self.reserved_sectors_count

    @property
    def data_offset(self):
        return self.fat_offset + self.fat_copies * self.sectors_per_fat * self.bytes_per_sector

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


class FileShortName(object):

    FORMAT = '<11s3B7HI'
    SIZE = calcsize(FORMAT)

    def __init__(self):
        self.name = ''
        self.attributes = FileAttr.READ_ONLY
        self.creation_dt = datetime.now()
        self.modified_dt = datetime.now()
        self.last_access_time = 0
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
        msg += " Attributes:            {}\n".format(FileAttr[self.attributes])
        msg += " Last Access Time:      {}\n".format(self.last_access_time)
        msg += " Modified Date & Time:  {}\n".format(self.modified_dt.strftime('%d.%m.%Y [%X]'))
        msg += " Creation Date & Time:  {}\n".format(self.creation_dt.strftime('%d.%m.%Y [%X]'))
        msg += " First Cluster:         {}\n".format(self.first_cluster)
        msg += " File Size:             {}\n".format(size_fmt(self.file_size))
        return msg

    def export(self):
        data = pack(self.FORMAT,
                    self.name.encode(),
                    self.attributes,
                    0,
                    self.creation_dt.microsecond // 1000,
                    encode_time(self.creation_dt.hour, self.creation_dt.minute, self.creation_dt.second),
                    encode_date(self.creation_dt.year, self.creation_dt.month, self.creation_dt.day),
                    self.last_access_time,
                    (self.first_cluster >> 16) & 0xFFFF,
                    encode_time(self.modified_dt.hour, self.modified_dt.minute, self.modified_dt.second),
                    encode_date(self.modified_dt.year, self.modified_dt.month, self.modified_dt.day),
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
            obj.attributes,
            _,
            creation_time_ms,
            creation_time,
            creation_date,
            obj.last_access_date,
            start_cluster_hi,
            modified_time,
            modified_date,
            start_cluster_lo,
            obj.file_size
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.name = name.decode()
        obj.first_cluster = (start_cluster_hi << 16) | start_cluster_lo
        obj.creation_dt = datetime(*decode_date_time(creation_date, creation_time), creation_time_ms * 1000)
        obj.modified_dt = datetime(*decode_date_time(modified_date, modified_time))

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
        msg = str()
        msg += " Name:                   {}\n".format(self.name)
        msg += " Sequence Number:        {}\n".format(self.sequence_number)
        msg += " Attributes:             {}\n".format(self.attributes)
        msg += " Type:                   {}\n".format(self.type)
        msg += " Checksum:               {}\n".format(self.checksum)
        msg += " First Cluster:          {}\n".format(self.first_cluster)
        return msg

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

        obj = cls()
        (
            obj.sequence_number,
            name0,
            obj.attributes,
            obj.type,
            obj.checksum,
            name1,
            obj.first_cluster,
            name2
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.name = name0.decode('UTF-16-LE')
        obj.name += name1.decode('UTF-16-LE')
        obj.name += name2.decode('UTF-16-LE')

        return obj


class FileEntry(object):

    SFN_FORMAT = '<11s3B7HI'
    LFN_FORMAT = '<B10s3B12sH4s'
    SFN_SIZE = calcsize(SFN_FORMAT)
    LFN_SIZE = calcsize(LFN_FORMAT)
    LFN_BYTES = 26

    @property
    def name(self):
        return self._file_name

    @name.setter
    def name(self, value):
        self._file_name = value

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes = value

    def __init__(self, file_name, attributes, long_name=True):
        self._long_name = long_name
        self._file_name = file_name
        self._attributes = attributes
        self.creation_time_ms = 0
        self.creation_time = 0
        self.creation_date = 0
        self.last_access_time = 0
        self.modified_time = 0
        self.modified_date = 0
        self.first_cluster = 0
        self.file_size = 0

    def __eq__(self, obj):
        if not isinstance(obj, FileEntry):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def _short_name(self):
        file_name = self._file_name.split('.', '')
        if len(file_name) > 2 or len(file_name[-1]) > 3 or (len(file_name[0]) + len(file_name[1])) > 11:
            return self._file_name[:6].upper() + '~1   '
        else:
            return file_name[0] + file_name[1]

    def info(self):
        msg = str()
        msg += " Name:                   {}\n".format(self.name)
        msg += " Attributes:             {}\n".format(self.attributes)
        msg += " Creation Time [ms]:     {}\n".format(self.creation_time_ms)
        msg += " Creation Time:          {}\n".format(self.creation_time)
        msg += " Creation Date:          {}\n".format(self.creation_date)
        msg += " Last Access Time:       {}\n".format(self.last_access_time)
        msg += " Modified Time:          {}\n".format(self.modified_time)
        msg += " Modified Date:          {}\n".format(self.modified_date)
        msg += " First Cluster:          {}\n".format(self.first_cluster)
        msg += " File Size:              {}\n".format(self.file_size)
        return msg

    def export(self):
        data = bytes()
        short_name = self._short_name()
        data += pack(self.SFN_FORMAT,
                     short_name,
                     self._attributes,
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

        if self._long_name:
            snum = 1
            offset = 0
            long_name = self.name.encode('UTF-16-LE')
            long_name_size = len(long_name)
            short_name_crc = lfn_checksum(short_name)
            # align full long name to LN_BYTES
            if long_name_size % self.LFN_BYTES:
                long_name += b'\0' * (self.LFN_BYTES - long_name_size)
            while True:
                if offset >= long_name_size:
                    break
                if (offset + self.LFN_BYTES) >= long_name_size:
                    snum |= 0x40
                name = long_name[offset:offset + self.LFN_BYTES]
                data += pack(self.LFN_FORMAT, snum, name[0:10], 0x0F, 0, short_name_crc, name[10:22], 0, name[22:26])
                offset += self.LFN_BYTES
                snum += 1

        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (offset + cls.SFN_SIZE):
            raise FATError()


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
        assert bits in (12, 16, 32)
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
        # ...
        self.load()

    def __eq__(self, obj):
        if not isinstance(obj, FAT):
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        nfo = str()
        nfo += " < FAT: Boot Sector > " + "-" * 39 + "\n"
        nfo += self.boot_sector.info()
        if self.fs_info is not None:
            nfo += self.fs_info.info()
        nfo += " " + "-" * 60 + "\n\n"
        return nfo

    def load(self):
        self._io.seek(self._io_offset)

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

        self._io.seek(self._io_offset + self.boot_sector.root_offset)
        aa = self._io.read(512 * 8)
        print(hexdump(aa, 0, False))

        print(FileShortName.parse(aa).info())
        print(FileShortName.parse(aa[0x80:]).info())

    def update(self):
        pass







