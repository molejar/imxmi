# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import uuid
import binascii
from struct import pack, unpack_from, calcsize

########################################################################################################################
# common
########################################################################################################################

PART_DESC = {

    # General
    '00000000-0000-0000-0000-000000000000': "Unused entry",
    '024dee41-33e7-11d3-9d69-0008c781f39f': "MBR Partition Scheme",
    'c12a7328-f81f-11d2-ba4b-00a0c93ec93b': "EFI System Partition",
    '21686148-6449-6e6f-744e-656564454649': "BIOS Boot Partition",
    'd3bfe2de-3daf-11df-ba40-e3a556d89593': "Intel Fast Flash (iFFS) partition",
    'f4019732-066e-4e12-8273-346c5641494f': "Sony Boot Partition",
    'bfbfafe7-a34f-448a-9a5b-6213eb736c22': "Lenovo Boot Partition",

    # Windows
    'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7': "Windows: Basic Data Partition",
    'e3c9e316-0b5c-4db8-817d-f92df00215ae': "Windows: Microsoft Reserved Partition",
    'af9b60a0-1431-4f62-bc68-3311714a69ad': "Windows: Logical Disk Manager (LDM) Data Partition",
    'de94bba4-06d1-4d40-a16a-bfd50179d6ac': "Windows: Windows Recovery Environment",
    '37affc90-ef7d-4e96-91c3-2d7ae055b174': "Windows: IBM General Parallel File System (GPFS) Partition",
    'e75caf8f-f680-4cee-afa3-b001e56efc2d': "Windows: Storage Spaces Partition",
    'db97dba9-0840-4bae-97f0-ffb9a327c7e1': "Windows: Cluster Metadata Partition",

    # HP-UX
    '75894c1e-3aeb-11d3-b7c1-7b03a0000000': "HP-UX: Data Partition",
    'e2a1e728-32e3-11d6-a682-7b03a0000000': "HP-UX: Service Partition",

    # Linux
    '0fc63daf-8483-4772-8e79-3d69d8477de4': "Linux: Filesystem Data Partition",
    'a19d880f-05fc-4d3b-a006-743f0f84911e': "Linux: RAID Partition",
    '0657fd6d-a4ab-43c4-84e5-0933c84b4f4f': "Linux: SWAO Partition",
    'e6d6d379-f507-44c2-a23c-238f2a3df928': "Linux: Logical Volume Manager (LVM) Partition",
    '8da63339-0007-60c0-c436-083ac8230908': "Linux: Reserved Partition",

    # FreeBSD
    '83bd6b9d-7f41-11dc-be0b-001560b84f0f': "FreeBSD: Boot Partition",
    '516e7cb4-6ecf-11d6-8ff8-00022d09712b': "FreeBSD: Data Partition",
    '516e7cb5-6ecf-11d6-8ff8-00022d09712b': "FreeBSD: Swap Partition",
    '516e7cb6-6ecf-11d6-8ff8-00022d09712b': "FreeBSD: Unix File System (UFS) Partition",
    '516e7cb8-6ecf-11d6-8ff8-00022d09712b': "FreeBSD: Vinum Volume Manager / RAID Partition",
    '516e7cba-6ecf-11d6-8ff8-00022d09712b': "FreeBSD: ZFS Partition",

    # NetBSD
    '49f48d32-b10e-11dc-b99b-0019d1879648': "NetBSD: Swap Partition",
    '49f48daa-b10e-11dc-b99b-0019d1879648': "NetBSD: RAID Partition",
    '49f48d5a-b10e-11dc-b99b-0019d1879648': "NetBSD: FFS Partition",
    '49f48d82-b10e-11dc-b99b-0019d1879648': "NetBSD: LFS Partition",
    '2db519c4-b10f-11dc-b99b-0019d1879648': "NetBSD: Concatenated Partition",
    '2db519ec-b10f-11dc-b99b-0019d1879648': "NetBSD: Encrypted Partition",

    # Android
    '2568845d-2332-4675-bc39-8fa5a4748d15': "Android: Bootloader",
    '114eaffe-1552-4022-b26e-9b053604cf84': "Android: Bootloader 2",
    '49a4d17f-93a3-45c1-a0de-f50b2ebe2599': "Android: Boot",
    '4177c722-9e92-4aab-8644-43502bfd5506': "Android: Recovery",
    'ef32a33b-a409-486c-9141-9ffb711f6266': "Android: Misc",
    '20ac26be-20b7-11e3-84c5-6cfdb94711e9': "Android: Metadata",
    '38f428e6-d326-425d-9140-6e0ea133647c': "Android: System",
    'a893ef21-e428-470a-9e55-0668fd91a2d9': "Android: Cache",
    'dc76dda9-5ac1-491c-af42-a82591580c0d': "Android: Data",
    'ebc597d0-2053-4b15-8b64-e0aac75f4db1': "Android: Persistent",
    'c5a0aeec-13ea-11e5-a1b1-001e67ca0c3c': "Android: Vendor",
    'bd59408b-4514-490d-bf12-9878d963f378': "Android: Config",
    '8f68cc74-c5e5-48da-be91-a0c8c15e9c80': "Android: Factory",
}


########################################################################################################################
# GPT Exceptions
########################################################################################################################

class GPTError(Exception):
    pass


########################################################################################################################
# GPT Classes
########################################################################################################################

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
                            self.disk_guid.bytes_le,
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
        self.disk_guid = uuid.uuid4()
        self.partition_entry_lba = 0
        self.number_of_partition_entries = 0
        self.size_of_partition_entry = 0
        self.partition_entry_array_crc32 = 0

    def __eq__(self, obj):
        if not isinstance(obj, Header):
            return False
        if self.revision != obj.revision or \
           self.current_lba != obj.current_lba or \
           self.backup_lba != obj.backup_lba or \
           self.first_usable_lba != obj.first_usable_lba or \
           self.last_usable_lba != obj.last_usable_lba or \
           self.disk_guid != obj.disk_guid or \
           self.partition_entry_lba != obj.partition_entry_lba or \
           self.number_of_partition_entries != obj.number_of_partition_entries or \
           self.size_of_partition_entry != obj.size_of_partition_entry or \
           self.partition_entry_array_crc32 != obj.partition_entry_array_crc32:
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        nfo = str()
        nfo += " Revision:         {}.{}\n".format(self.revision[2], self.revision[3])
        nfo += " Current LBA:      {}\n".format(self.current_lba)
        nfo += " Backup LBA:       {}\n".format(self.backup_lba)
        nfo += " First Usable LBA: {}\n".format(self.first_usable_lba)
        nfo += " Last Usable LBA:  {}\n".format(self.last_usable_lba)
        nfo += " Disk GUID:        {}\n".format(self.disk_guid)
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
                    self.disk_guid.bytes_le,
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
        obj.disk_guid = uuid.UUID(bytes_le=disk_guid)
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
        self.partition_type = uuid.UUID('00000000-0000-0000-0000-000000000000')
        self.partition_guid = uuid.uuid4()
        self.first_lba = 0
        self.last_lba = 0
        self.attribute_flags = 0

    def __eq__(self, obj):
        if not isinstance(obj, PartitionEntry):
            return False
        if self.partition_name != obj.partition_name or \
           self.partition_type != obj.partition_type or \
           self.partition_guid != obj.partition_guid or \
           self.first_lba != obj.first_lba or \
           self.last_lba != obj.last_lba or \
           self.attribute_flags != obj.attribute_flags:
            return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

    def info(self):
        nfo = str()
        nfo += " Part. Name:   {}\n".format(self.partition_name)
        nfo += " Part. Type:   {}\n".format(PART_DESC.get(str(self.partition_type), str(self.partition_type)))
        nfo += " Part. GUID:   {}\n".format(self.partition_guid)
        nfo += " First LBA:    {}\n".format(self.first_lba)
        nfo += " Last  LBA:    {}\n".format(self.last_lba)
        nfo += " Attr. Flags:  0x{:X}\n".format(self.attribute_flags)
        return nfo

    def export(self):
        return pack(self.FORMAT,
                    self.partition_type.bytes_le,
                    self.partition_guid.bytes_le,
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
        obj.partition_type = uuid.UUID(bytes_le=partition_type)
        obj.partition_guid = uuid.UUID(bytes_le=partition_guid)
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

    def __eq__(self, obj):
        if not isinstance(obj, GPT):
            return False
        if self.header != obj.header or self.sector_size != obj.sector_size:
            return False
        if len(self._partitions) != len(obj):
            return False
        for index, part in self._partitions.items():
            if part != obj[index]:
                return False
        return True

    def __ne__(self, obj):
        return not self.__eq__(obj)

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
        return iter(self._partitions.values())

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
