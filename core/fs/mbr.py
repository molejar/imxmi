# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from struct import pack, unpack_from
from easy_enum import Enum


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


class CHS(object):
    """ MBR ... """

    SIZE = 3

    def __init__(self):
        self.head = 0
        self.sector = 0
        self.cylinder = 0

    def info(self):
        return "Head: {}, Sector: {}, Cylinder: {}".format(self.head, self.sector, self.cylinder)

    def export(self):
        return bytes([self.head, (self.sector & 0x3F) | ((self.cylinder >> 2) & 0xC0), self.cylinder & 0xFF])

    @classmethod
    def parse(cls, data, offset=0):
        assert len(data) >= offset + cls.SIZE
        chs = cls()
        chs.head = data[offset]
        chs.sector = data[offset+1] & 0x3F
        chs.cylinder = data[offset+2] | ((data[offset+1] & 0xC0) << 2)
        return chs


class PartitionEntry(object):
    """ MBR Partition Entry """

    SIZE = 16

    def __init__(self, **kwargs):
        self.status = 0
        self.chs_start = CHS()
        self.partition_type = 0
        self.chs_end = CHS()
        self.lba_start = 0
        self.num_sectors = 0
        for key, value in kwargs.items():
            setattr(self, key, value)

    def info(self):
        nfo = str()
        nfo += " Status:         0x{:X}\n".format(self.status)
        nfo += " Partition Type: {}\n".format(PartitionType[self.partition_type])
        nfo += " CHS Start:      {}\n".format(self.chs_start.info())
        nfo += " CHS End:        {}\n".format(self.chs_end.info())
        nfo += " LBA Start:      0x{:X}\n".format(self.lba_start)
        nfo += " Sectors Count:  {}\n".format(self.num_sectors)
        return nfo

    def export(self):
        data = bytes([self.status])
        data += self.chs_start.export()
        data += bytes([self.partition_type])
        data += self.chs_end.export()
        data += pack('<LL', self.lba_start, self.num_sectors)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        obj = cls()
        obj.status = int(data[offset])
        offset += 1
        obj.chs_start = CHS.parse(data, offset)
        offset += CHS.SIZE
        obj.partition_type = int(data[offset])
        offset += 1
        obj.chs_end = CHS.parse(data, offset)
        offset += CHS.SIZE
        obj.lba_start, obj.num_sectors = unpack_from('<LL', data, offset)
        return obj


class MBR(object):
    """ Generic Master Boot Record (MBR) """

    BOOTSTRAP_SIZE = 446
    MAX_PARTITIONS = 4
    SIGNATURE = 0xAA55
    SIZE = 512

    def __init__(self, bootstrap=None):
        assert bootstrap is not None and isinstance(bootstrap, bytearray)
        self.bootstrap = bytearray(self.BOOTSTRAP_SIZE) if bootstrap is None else bootstrap
        self._partitions = []

    def __len__(self):
        return len(self._partitions)

    def __getitem__(self, key):
        return self._partitions[key]

    def __setitem__(self, key, value):
        assert isinstance(value, PartitionEntry)
        if key >= self.MAX_PARTITIONS:
            raise IndexError()
        self._partitions[key] = value

    def __iter__(self):
        return self._partitions.__iter__()

    def clear(self):
        self._partitions.clear()

    def append(self, item):
        assert isinstance(item, PartitionEntry)
        self._partitions.append(item)

    def dell(self, index):
        return self._partitions.pop(index)

    def info(self):
        nfo = str()
        for i, partition in enumerate(self._partitions):
            if partition.partition_type == PartitionType.EMPTY:
                nfo += " Partition {}: Empty\n".format(i)
            else:
                nfo += " Partition {}\n".format(i)
                nfo += " " + "-" * 50
                nfo += partition.info()
                nfo += " " + "-" * 50
        return nfo

    def export(self):
        data = bytes(self.bootstrap)
        for partition in self._partitions:
            data += partition.export()
        data += pack("<H", self.SIGNATURE)
        return data

    @classmethod
    def parse(cls, data, offset=0):
        if len(data) < (cls.SIZE + offset):
            raise Exception()
        if unpack_from("<H", data, offset + (cls.SIZE - 2))[0] != cls.SIGNATURE:
            raise Exception()
        mbr = cls(bytearray(data[offset:offset+cls.BOOTSTRAP_SIZE]))
        offset += cls.BOOTSTRAP_SIZE
        for i in range(cls.MAX_PARTITIONS):
            mbr[i] = PartitionEntry.parse(data, offset)
            offset += PartitionEntry.SIZE
        return mbr
