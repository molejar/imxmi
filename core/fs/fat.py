# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from zlib import crc32
from datetime import datetime


# https://github.com/maxpat78/FATtools/blob/master/FAT.py

class FAT(object):

    def __init__(self, clusters, bitsize=32, exfat=False):
        pass
