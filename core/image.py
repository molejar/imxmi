# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
from io import FileIO, BytesIO, BufferedReader, SEEK_CUR, SEEK_END
from imx import img
from uboot import env_blob
from .fs import mbr, gpt, fat, ext


########################################################################################################################
# Base class
########################################################################################################################

class ImageBase(object):

    def __init__(self, stream):
        assert isinstance(stream, (FileIO, BytesIO, BufferedReader))
        self._io = stream

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def close(self):
        self._io.close()

    def update(self):
        raise NotImplementedError()

    def info(self):
        raise NotImplementedError()

    def size(self):
        cur_pos = self._io.tell()
        end_pos = self._io.seek(0, SEEK_END)
        self._io.seek(cur_pos)
        return end_pos

    @classmethod
    def open(cls, filename):
        f = open(filename, 'rb')
        try:
            return cls(f)
        except Exception:
            f.close()
            raise

    @classmethod
    def load(cls, buffer):
        return cls(BytesIO(buffer))


########################################################################################################################
# Linux Image Class
########################################################################################################################

class LinuxImage(ImageBase):

    ENV_MAX_SIZE = 512
    FAT_PARTITIONS = {
        mbr.PartitionType.FAT12:     12,
        mbr.PartitionType.FAT16_32M: 16,
        mbr.PartitionType.FAT16_2G:  16,
        mbr.PartitionType.FAT32:     32,
        mbr.PartitionType.FAT32X:    32
    }

    def __init__(self, stream, parse=False):
        super().__init__(stream)
        self.mbr = None
        self.spl = None
        self.env = None
        self.fat = None
        self.ext = None
        self.spl_offset = None
        self.env_offset = None
        if parse:
            self.parse()

    def info(self):
        """ Linux image info """
        nfo = str()
        if self.mbr:
            nfo += self.mbr.info()
        if self.spl:
            nfo += self.spl.info()
        if self.env:
            nfo += self.env.info()
        if self.fat:
            nfo += self.fat.info()
        if self.ext:
            nfo += self.ext.info()
        return nfo

    def parse(self, spl_offset=None, env_offset=None):
        """ Parse boot image
        :param spl_offset: Secondary program loader offset
        :param env_offset: U-Boot environment variables offset
        """
        self.mbr = mbr.MBR.parse(self._io.read(mbr.MBR.SIZE))
        if self.mbr is None or len(self.mbr) == 0:
            raise Exception()

        # Get actual partition offset
        part_offset = 0x800000
        for p in self.mbr:
            part_offset = min(p.lba_start * 512, part_offset)

        # Validate and use SPL offset
        if spl_offset is not None:
            if spl_offset < part_offset:
                self._io.seek(spl_offset)
            else:
                raise Exception()

        # Parse SPL (U-Boot, Barebox, ....)
        self.spl = img.parse(self._io)

        # Store spl_offset
        if self.spl is not None:
            self.spl_offset = None

        # Parse U-Boot ENV
        if env_offset is None:
            env_offset = self._io.tell()
            while env_offset < (part_offset - self.ENV_MAX_SIZE):
                try:
                    self.env = env_blob.EnvBlob.parse(self._io.read(self.ENV_MAX_SIZE))
                    break
                except:
                    env_offset += self.ENV_MAX_SIZE
                    self._io.seek(env_offset)
        else:
            self._io.seek(env_offset)
            self.env = env_blob.EnvBlob.parse(self._io.read(self.ENV_MAX_SIZE))

        # Store env_offset
        if self.env is not None:
            self.env_offset = env_offset

        # Parse FAT and EXT2/3/4 partitions
        if self.mbr[0].partition_type in self.FAT_PARTITIONS:
            try:
                self.fat = fat.FAT(self._io, self.mbr[0].lba_start * 512, self.mbr[0].num_sectors,
                                   self.FAT_PARTITIONS[self.mbr[0].partition_type])
            except:
                fat_bits = fat.get_fat_bits(self._io, self.mbr[0].lba_start * 512)
                self.fat = fat.FAT(self._io, self.mbr[0].lba_start * 512, self.mbr[0].num_sectors, fat_bits)

        elif self.mbr[0].partition_type == mbr.PartitionType.LINUX:
            self.ext = ext.ExtX(self._io, self.mbr[0].lba_start * 512, self.mbr[0].num_sectors * 512)
        else:
            pass

        if len(self.mbr) > 1 and self.ext is None:
            if self.mbr[1].partition_type == mbr.PartitionType.LINUX:
                self.ext = ext.ExtX(self._io, self.mbr[1].lba_start * 512, self.mbr[1].num_sectors * 512)

    def extract(self, dest_path):
        """ Extract image content
        :param dest_path: Destination directory path
        """
        assert isinstance(dest_path, str)

        os.makedirs(dest_path, exist_ok=True)

        if self.spl:
            with open(os.path.join(dest_path, 'spl.imx'), 'wb') as f:
                f.write(self.spl.export())

        if self.env:
            with open(os.path.join(dest_path, 'env.txt'), 'w') as f:
                f.write(self.env.store())

        if self.fat:
            fat_dir = os.path.join(dest_path, 'fat')
            os.makedirs(fat_dir, exist_ok=True)

            for file in self.fat.root_dir:
                self.fat.save_file(file, fat_dir)

        if self.ext:
            self.ext.save_as(os.path.join(dest_path, 'rootfs.img'))

    def update(self):
        pass


########################################################################################################################
# Android Image Class
########################################################################################################################

class AndroidImage(ImageBase):

    def __init__(self, stream, parse=False):
        super().__init__(stream)
        self.mbr = None
        self.gpt = None
        if parse:
            self.parse()

    def parse(self):
        self.mbr = mbr.MBR.parse(self._io.read(mbr.MBR.SIZE))
        if self.mbr[0].partition_type != mbr.PartitionType.EFI_GPT_PROTECT_MBR:
            raise Exception()
        self.gpt = gpt.GPT.parse(self._io.read(gpt.GPT.SIZE))

    def update(self):
        pass

    def info(self):
        pass
