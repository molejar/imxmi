# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import uuid
import binascii
from struct import pack, unpack_from, calcsize
from easy_enum import EEnum as Enum


class GPTError(Exception):
    pass


class PartitionType(Enum):
    """ GPT Partition Type """

    # General
    UNUSED_ENTRY = (0x00000000000000000000000000000000, 'Unused entry')
    MBR_PART_SCHEME = (0x024DEE4133E711D39D690008C781F39F, 'MBR Partition Scheme')
    EFI_SYSTEM = (0xC12A7328F81F11D2BA4B00A0C93EC93B, 'EFI System Partition')
    BIOS_BOOT = (0x2168614864496E6F744E656564454649, 'BIOS Boot Partition')
    INTEL_FAST_FLASH = (0xD3BFE2DE3DAF11DFBA40E3A556D89593, 'Intel Fast Flash (iFFS) partition')
    SONY_BOOT = (0xF4019732066E4E128273346C5641494F, 'Sony Boot Partition')
    LENOVO_BOOT = (0xBFBFAFE7A34F448A9A5B6213EB736C22, 'Lenovo Boot Partition')

    # Windows
    WIN_BASIC_DATA = (0xEBD0A0A2B9E5443387C068B6B72699C7, 'Windows: Basic Data Partition')
    WIN_MS_RESERVED = (0xE3C9E3160B5C4DB8817DF92DF00215AE, 'Windows: Microsoft Reserved Partition')
    WIN_LDM_METADATA = (0xEBD0A0A2B9E5443387C068B6B72699C7, 'Windows: Logical Disk Manager (LDM) Metadata Partition')
    WIN_LDM_DATA = (0xAF9B60A014314F62BC683311714A69AD, 'Windows: Logical Disk Manager (LDM) Data Partition')
    WIN_RECOVERY_ENV = (0xDE94BBA406D14D40A16ABFD50179D6AC, 'Windows: Windows Recovery Environment')
    WIN_IBM_GPFS = (0x37AFFC90EF7D4E9691C32D7AE055B174, 'Windows: IBM General Parallel File System (GPFS) Partition')
    WIN_STORAGE_SPACES = (0xE75CAF8FF6804CEEAFA3B001E56EFC2D, 'Windows: Storage Spaces Partition')
    WIN_CLUSTER_METADATA = (0xDB97DBA908404BAE97F0FFB9A327C7E1, 'Windows: Cluster Metadata Partition')

    # HP-UX
    HPUX_DATA = (0x75894C1E3AEB11D3B7C17B03A0000000, 'HP-UX: Data Partition')
    HPUX_SERVICE = (0xE2A1E72832E311D6A6827B03A0000000, 'HP-UX: Service Partition')

    # Linux
    LINUX_FS_DATA = (0x0FC63DAF848347728E793D69D8477DE4, 'Linux: Filesystem Data Partition')
    LINUX_RAID = (0xA19D880F05FC4D3BA006743F0F84911E, 'Linux: RAID Partition')
    LINUX_SWAO = (0x0657FD6DA4AB43C484E50933C84B4F4F, 'Linux: SWAO Partition')
    LINUX_LVM = (0xE6D6D379F50744C2A23C238F2A3DF928, 'Linux: Logical Volume Manager (LVM) Partition')
    LINUX_RESERVED = (0x8DA63339000760C0C436083AC8230908, 'Linux: Reserved Partition')

    # FreeBSD
    FBSD_BOOT = (0x83BD6B9D7F4111DCBE0B001560B84F0F, 'FreeBSD: Boot Partition')
    FBSD_DATA = (0x516E7CB46ECF11D68FF800022D09712B, 'FreeBSD: Data Partition')
    FBSD_SWAP = (0x516E7CB56ECF11D68FF800022D09712B, 'FreeBSD: Swap Partition')
    FBSD_UFS = (0x516E7CB66ECF11D68FF800022D09712B, 'FreeBSD: Unix File System (UFS) Partition')
    FBSD_VVM = (0x516E7CB86ECF11D68FF800022D09712B, 'FreeBSD: Vinum Volume Manager / RAID Partition')
    FBSD_ZFS = (0x516E7CBA6ECF11D68FF800022D09712B, 'FreeBSD: ZFS Partition')

    # NetBSD
    NBSD_SWAP = (0x49F48D32B10E11DCB99B0019D1879648, 'NetBSD: Swap Partition')
    NBSD_RAID = (0x49F48DAAB10E11DCB99B0019D1879648, 'NetBSD: RAID Partition')
    NBSD_FFS = (0x49F48D5AB10E11DCB99B0019D1879648, 'NetBSD: FFS Partition')
    NBSD_LFS = (0x49F48D82B10E11DCB99B0019D1879648, 'NetBSD: LFS Partition')
    NBSD_CONCATENATED = (0x2DB519C4B10F11DCB99B0019D1879648, 'NetBSD: Concatenated Partition')
    NBSD_ENCRIPTED = (0x2DB519ECB10F11DCB99B0019D1879648, 'NetBSD: Encrypted Partition')

    # QNX
    # TODO: ...

    # Mac OSX
    # TODO: ...

    # Solaris
    # TODO: ...

    # Chrome OS
    # TODO: ...

    # Android
    # TODO: ...


class Header(object):

    SIGNATURE = b'EFI PART'
    FORMAT = '<8s4s3I4Q16sQ3I'
    SIZE = calcsize(FORMAT)

    @property
    def header_crc(self):
        crc32_input =  pack(self.FORMAT,
                            self.SIGNATURE,
                            self.revision,
                            self.SIZE,
                            0,  # set to 0 for crc32 calculation
                            0,  # reserved
                            self.current_lba,
                            self.backup_lba,
                            self.first_usable_lba,
                            self.last_usable_lba,
                            self.disk_guid.to_bytes(16, 'little'),
                            self.partition_entry_lba,
                            self.number_of_partition_entries,
                            self.size_of_partition_entry,
                            self.partition_entry_array_crc32)
        return binascii.crc32(crc32_input)

    def __init__(self):
        self.revision = bytes([0x00, 0x00, 0x01, 0x00])
        self.current_lba = 0
        self.backup_lba = 0
        self.first_usable_lba = 0
        self.last_usable_lba = 0
        self.disk_guid = 0
        self.partition_entry_lba = 0
        self.number_of_partition_entries = 0
        self.size_of_partition_entry = 0
        self.partition_entry_array_crc32 = 0

    def info(self):
        nfo = str()
        nfo += " Revision:         {}.{}\n".format(self.revision[2], self.revision[3])
        nfo += " Current LBA:      {}\n".format(self.current_lba)
        nfo += " Backup LBA:       {}\n".format(self.backup_lba)
        nfo += " First Usable LBA: {}\n".format(self.first_usable_lba)
        nfo += " Last Usable LBA:  {}\n".format(self.last_usable_lba)
        nfo += " Disk GUID:        {}\n".format(uuid.UUID(int=self.disk_guid))
        nfo += " Entries Count:    {}\n".format(self.number_of_partition_entries)
        nfo += " Part. Entry LBA:  {}\n".format(self.last_usable_lba)
        nfo += " Part. Entry Size: {}\n".format(self.size_of_partition_entry)
        nfo += " Part. Entry CRC:  0x{:X}\n".format(self.partition_entry_array_crc32)
        return nfo

    def export(self):
        return pack(self.FORMAT,
                    self.SIGNATURE,
                    self.revision,
                    self.SIZE,
                    self.header_crc,
                    0,  # reserved
                    self.current_lba,
                    self.backup_lba,
                    self.first_usable_lba,
                    self.last_usable_lba,
                    self.disk_guid.to_bytes(16, 'little'),
                    self.partition_entry_lba,
                    self.number_of_partition_entries,
                    self.size_of_partition_entry,
                    self.partition_entry_array_crc32)

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) <= offset + cls.SIZE:
            raise Exception()
        obj = cls()
        (
            signature,
            obj.revision,
            header_size,
            header_crc,
            _,
            obj.current_lba,
            obj.backup_lba,
            obj.first_usable_lba,
            obj.last_usable_lba,
            disk_guid,
            obj.partition_entry_lba,
            obj.number_of_partition_entries,
            obj.size_of_partition_entry,
            obj.partition_entry_array_crc32
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.disk_guid = int.from_bytes(disk_guid, 'little')
        if signature != cls.SIGNATURE:
            raise GPTError('Bad signature: %r' % signature)
        if header_size != cls.SIZE:
            raise GPTError('Bad header size: %r' % header_size)
        if header_crc != obj.header_crc:
            raise GPTError('Bad header crc: %r' % header_crc)
        return obj


class PartitionEntry(object):

    FORMAT = '<16s16sQQQ72s'
    SIZE = calcsize(FORMAT)

    def __init__(self):
        self.partition_name = ''
        self.partition_type = 0
        self.partition_guid = 0
        self.first_lba = 0
        self.last_lba = 0
        self.attribute_flags = 0

    def info(self):
        nfo = str()
        nfo += " Part. Name:   {}\n".format(self.partition_name)
        nfo += " Part. Type:   {}\n".format(PartitionType[self.partition_type] if
                                            PartitionType.is_valid(self.partition_type) else
                                            uuid.UUID(int=self.partition_type))
        nfo += " Part. GUID:   {}\n".format(uuid.UUID(int=self.partition_guid))
        nfo += " First LBA:    {}\n".format(self.first_lba)
        nfo += " Last  LBA:    {}\n".format(self.last_lba)
        nfo += " Attr. Flags:  0x{:X}\n".format(self.attribute_flags)
        return nfo

    def export(self):
        return pack(self.FORMAT,
                    self.partition_type.to_bytes(16, 'little'),
                    self.partition_guid.to_bytes(16, 'little'),
                    self.first_lba,
                    self.last_lba,
                    self.attribute_flags,
                    self.partition_name.encode('utf-16'))

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) <= offset + cls.SIZE:
            raise Exception()
        obj = cls()
        (
            partition_type,
            partition_guid,
            obj.first_lba,
            obj.last_lba,
            obj.attribute_flags,
            partition_name
        ) = unpack_from(cls.FORMAT, data, offset)
        obj.partition_type = int.from_bytes(partition_type, 'little')
        obj.partition_guid = int.from_bytes(partition_guid, 'little')
        obj.partition_name = partition_name.decode('utf-16').strip('\0')
        return obj


class GPT(object):
    """ GUID Partition Table (GPT) """

    MAX_PARTITIONS = 128
    SIZE = 0

    def __init__(self, header):
        self.header = header
        self.sector_size = 512
        self._partitions = {}

    def __len__(self):
        return len(self._partitions)

    def __getitem__(self, key):
        if key >= self.MAX_PARTITIONS:
            raise IndexError()
        return self._partitions.get(key)

    def __setitem__(self, key, value):
        assert isinstance(value, PartitionEntry)
        if key >= self.MAX_PARTITIONS:
            raise IndexError()
        self._partitions[key] = value

    def __iter__(self):
        return self._partitions.__iter__()

    def clear(self):
        self._partitions.clear()

    def dell(self, index):
        return self._partitions.pop(index)

    def info(self):
        nfo = str()
        nfo += " < GPT Header > " + "-" * 45 + "\n"
        nfo += self.header.info()
        nfo += " " + "-" * 60 + "\n\n"
        for i, partition in self._partitions.items():
            if partition.first_lba != 0 and partition.last_lba != 0:
                nfo += " < GPT Partition {:3d} > ".format(i)
                nfo += "-" * 38 + "\n"
                nfo += partition.info()
                nfo += " " + "-" * 60 + "\n\n"
        return nfo

    def export(self):
        # TODO: Update header
        data = self.header.export()
        data += bytes([0] * (self.sector_size - self.header.SIZE))
        for i in range(self.MAX_PARTITIONS):
            data += bytes([0] * PartitionEntry.SIZE) if self._partitions[i] is None else self._partitions[i].export()
        return data

    @classmethod
    def parse(cls, data, offset=0, sector_size=512):
        gpt = cls(Header.parse(data, offset))
        for i in range(gpt.header.number_of_partition_entries):
            pentry = PartitionEntry.parse(data, offset + sector_size)
            offset += PartitionEntry.SIZE
            if pentry.first_lba != 0 and pentry.last_lba != 0:
                gpt[i] = pentry
        return gpt
