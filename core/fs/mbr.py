# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from struct import pack, unpack_from, calcsize
from easy_enum import EEnum as Enum


class MBRError(Exception):
    pass


class PartitionType(Enum):
    """ MBR Partition Type """

    EMPTY = (0x00, 'Empty')
    FAT12 = (0x01, 'FAT12')
    FAT16_32M = (0x04, 'FAT16 16-32MB')
    EXTENDED_CHS = (0x05, 'Extended, CHS')
    FAT16_2G = (0x06, 'FAT16 32MB-2GB')
    NTFS = (0x07, 'NTFS')
    FAT32 = (0x0B, 'FAT32')
    FAT32X = (0x0C, 'FAT32X')
    FAT16X = (0x0E, 'FAT16X')
    EXTENDED_LBA = (0x0F, 'Extended, LBA')
    HIDDEN_FAT12 = (0x11, 'Hidden FAT12')
    HIDDEN_FAT16_32M = (0x14, 'Hidden FAT16,16-32MB')
    HIDDEN_EXTENDED_CHS = (0x15, 'Hidden Extended, CHS')
    HIDDEN_FAT16_2G = (0x16, 'Hidden FAT16,32MB-2GB')
    HIDDEN_NTFS = (0x17, 'Hidden NTFS')
    HIDDEN_FAT32 = (0x1B, 'Hidden FAT32')
    HIDDEN_FAT32X = (0x1C, 'Hidden FAT32X')
    HIDDEN_FAT16X = (0x1E, 'Hidden FAT16X')
    HIDDEN_EXTENDED_LBA = (0x1F, 'Hidden Extended, LBA')
    WINDOWS_RECOVERY_ENV = (0x27,  'Windows recovery environment')
    PLAN9 = (0x39, 'Plan 9')
    MAGIC_RECOVERY = (0x3C, 'PartitionMagic recovery partition')
    WINDOWS_DYNAMIC = (0x42, 'Windows dynamic extended partition marker')
    GO_BACK = (0x44, 'GoBack partition')
    UNIX_SYSTEM_V = (0x63, 'Unix System V')
    PC_ARMOUR_PROTECTED = (0x64, 'PC-ARMOUR protected partition')
    MINIX = (0x81, 'Minix')
    LINUX_SWAP = (0x82, 'Linux Swap')
    LINUX = (0x83, 'Linux')
    HIBERNATION = (0x84, 'Hibernation')
    LINUX_EXTENDED = (0x85, 'Linux Extended')
    FT_FAT16B = (0x86, 'Fault-tolerant FAT16B volume set')
    FT_NTFS = (0x87, 'Fault-tolerant NTFS volume set')
    LINUX_PLAINTEXT = (0x88, 'Linux plaintext')
    LINUX_LVM = (0x8E, 'Linux LVM')
    HIDDEN_LINUX = (0x93, 'Hidden Linux')
    BSD_OS = (0x9F, 'BSD/OS')
    HIBERNATION1 = (0xA0, 'Hibernation')
    HIBERNATION2 = (0xA1, 'Hibernation')
    FREEBSD = (0xA5, 'FreeBSD')
    OPENBSD = (0xA6, 'OpenBSD')
    MAC_OSX = (0xA8, 'Mac OS X')
    NETBSD = (0xA9, 'NetBSD')
    MAC_OSX_BOOT = (0xAB, 'Mac OS X Boot')
    MAC_OSX_HFS = (0xAF, 'Mac OS X HFS')
    SOLARIS_BOOT = (0xBE, 'Solaris 8 boot partition')
    SOLARIS_X86 = (0xBF, 'Solaris x86')
    LINUX_UF_KEY = (0xE8, 'Linux Unified Key Setup')
    BFS = (0xEB, 'BFS')
    EFI_GPT_PROTECT_MBR = (0xEE, 'EFI GPT protective MBR')
    EFI_SYSTEM = (0xEF, 'EFI system partition')
    BOCHS_X86_EMULATOR = (0xFA, 'Bochs x86 emulator')
    VMWARE_FS = (0xFB, 'VMware File System')
    VMWARE_SWAP = (0xFC, 'VMware Swap')
    LINUX_RAID = (0xFD, 'Linux RAID')


class PartitionEntry(object):
    """ MBR Partition Entry """

    FORMAT = '<8BLL'
    SIZE = calcsize(FORMAT)

    @property
    def bootable(self):
        return True if self._status & 0x80 else False

    @bootable.setter
    def bootable(self, value):
        assert isinstance(value, bool)
        self._status = 0x80 if value else 0x00

    @property
    def partition_type(self):
        return self._partition_type

    @partition_type.setter
    def partition_type(self, value):
        assert PartitionType.is_valid(value)
        self._partition_type = value

    def __init__(self, status=0, partition_type=0):
        self._status = status
        self._partition_type = partition_type
        # CHS Start
        self.start_head = 0
        self.start_sector = 0
        self.start_cylinder = 0
        # CHS End
        self.end_head = 0
        self.end_sector = 0
        self.end_cylinder = 0
        # partition allocation
        self.lba_start = 0
        self.num_sectors = 0

    def info(self):
        """ Return Partition-Entry info """
        nfo = str()
        nfo += " Bootable:       {}\n".format('YES' if self.bootable else 'NO')
        nfo += " Partition Type: {}\n".format(PartitionType[self.partition_type])
        nfo += " CHS Start:      {} Head, {} Sector, {} Cylinder\n".format(self.start_head,
                                                                           self.start_sector,
                                                                           self.start_cylinder)
        nfo += " CHS End:        {} Head, {} Sector, {} Cylinder\n".format(self.end_head,
                                                                           self.end_sector,
                                                                           self.end_cylinder)
        nfo += " LBA Start:      {}\n".format(self.lba_start)
        nfo += " Sectors Count:  {}\n".format(self.num_sectors)
        return nfo

    def export(self):
        """ Export Partition-Entry as bytes array
        :return type: bytes
        """
        return pack(self.FORMAT,
                    self._status,
                    self.start_head,
                    (self.start_sector & 0x3F) | ((self.start_cylinder >> 2) & 0xC0),
                    self.start_cylinder & 0xFF,
                    self._partition_type,
                    self.end_head,
                    (self.end_sector & 0x3F) | ((self.end_cylinder >> 2) & 0xC0),
                    self.end_cylinder & 0xFF,
                    self.lba_start,
                    self.num_sectors)

    @classmethod
    def parse(cls, data, offset=0):
        """ Parse Partition-Entry from bytes array
        :param data: The bytes array
        :param offset: The offset in bytes array
        :return: PartitionEntry object
        """
        (
            status, start_head, start_sc, start_cs, partition_type, end_head, end_sc, end_cs, lba_start, num_sectors
        ) = unpack_from(cls.FORMAT, data, offset)
        obj = cls(status, partition_type)
        obj.start_head = start_head
        obj.start_sector = start_sc & 0x3F
        obj.start_cylinder = start_cs | ((start_sc & 0xC0) << 2)
        obj.end_head = end_head
        obj.end_sector = end_sc & 0x3F
        obj.end_cylinder = end_cs | ((end_sc & 0xC0) << 2)
        obj.lba_start = lba_start
        obj.num_sectors = num_sectors
        return obj


class MBR(object):
    """ The Master Boot Record (MBR) Class """

    BOOTSTRAP_SIZE = 446
    MAX_PARTITIONS = 4
    SIGNATURE = 0xAA55
    SIZE = 512

    @property
    def bootstrap(self):
        return self._bootstrap

    @bootstrap.setter
    def bootstrap(self, value):
        assert isinstance(value, (bytes, bytearray))
        self._bootstrap = bytearray(value)

    def __init__(self, bootstrap=None):
        self._bootstrap = bytearray(self.BOOTSTRAP_SIZE)
        self._partitions = {}
        if bootstrap is not None:
            self.bootstrap = bootstrap

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
        """ Remove all partitions entry """
        self._partitions.clear()

    def dell(self, index):
        """ Remove selected partition entry """
        return self._partitions.pop(index)

    def info(self):
        """ Return MBR info """
        nfo = str()
        for i, partition in self._partitions.items():
            nfo += " < MBR Partition {} > ".format(i)
            nfo += "-" * 40 + "\n"
            nfo += partition.info()
            nfo += " " + "-" * 60 + "\n\n"
        return nfo

    def export(self):
        """ Export MBR as bytes array
        :return type: bytes
        """
        data = bytes(self.bootstrap)
        for i in range(self.MAX_PARTITIONS):
            data += bytes([0]*PartitionEntry.SIZE) if self._partitions.get(i) is None else self._partitions[i].export()
        data += pack("<H", self.SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        """ Parse MBR from bytes array
        :param data: The bytes array
        :param offset: The offset in bytes array
        :return: MBR object
        """
        if len(data) < (cls.SIZE + offset):
            raise MBRError()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.SIGNATURE:
            raise MBRError()

        mbr = cls(data[offset:offset+cls.BOOTSTRAP_SIZE])
        offset += cls.BOOTSTRAP_SIZE
        for i in range(cls.MAX_PARTITIONS):
            partition = PartitionEntry.parse(data, offset)
            offset += PartitionEntry.SIZE
            if partition.partition_type != PartitionType.EMPTY:
                mbr[i] = partition
        return mbr
