# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


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


########################################################################################################################
# Ext2/3/4 classes
########################################################################################################################

class ExtX(object):

    READ_SECTOR_SIZE = 1024

    def __init__(self, stream, offset, size):
        """
        :param stream:
        :param offset:
        :param size:
        """
        self._io = stream
        self._io_offset = offset
        self._size = size

    def info(self):
        nfo = str()
        nfo += " " + "-" * 60 + "\n"
        nfo += " RootFS Image: {}\n".format(size_fmt(self._size))
        nfo += " " + "-" * 60 + "\n"
        return nfo

    def save_as(self, file_path):
        assert isinstance(file_path, str)

        file_size = self._size
        self._io.seek(self._io_offset)
        with open(file_path, "wb") as f:
            while file_size > 0:
                f.write(self._io.read(self.READ_SECTOR_SIZE if file_size > self.READ_SECTOR_SIZE else file_size))
                file_size -= self.READ_SECTOR_SIZE
