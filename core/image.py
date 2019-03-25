# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from io import FileIO, BytesIO, SEEK_CUR, SEEK_END
from .fs import mbr, gpt, fat


class ImageBase(object):

    def __init__(self, stream):
        assert isinstance(stream, (FileIO, BytesIO))
        self._io = stream
        self._pos = 0

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
        self._io.seek(0, SEEK_END)
        full_size = self._io.tell()
        self._io.seek(cur_pos)
        return full_size

    @classmethod
    def from_file(cls, filename):
        f = open(filename, 'rb')
        try:
            return cls(f)
        except Exception:
            f.close()
            raise

    @classmethod
    def from_bytes(cls, buf):
        return cls(BytesIO(buf))


class LinuxImage(ImageBase):

    def __init__(self, stream, parse=False):
        super().__init__(stream)
        self.mbr = None
        self.gpt = None
        if parse:
            self.parse()

    def parse(self):
        self.mbr = mbr.MBR.parse(self._io.read(mbr.MBR.SIZE))
        if self.mbr[0].partition_type == mbr.PartitionType.EFI_GPT_PROTECT_MBR:
            self.gpt = gpt.GPT.parse(self._io.read(gpt.GPT.SIZE))

    def update(self):
        pass

    def info(self):
        pass


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
