# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import pytest
import core

DIRECTORY = "data/"


def test_parser():
    with open(DIRECTORY + "mbr_gpt.img", 'rb') as f:
        mbr = core.mbr.MBR.parse(f.read())

        assert len(mbr) == 1
        assert not mbr[0].bootable
        assert mbr[0].partition_type == core.mbr.PartitionType.EFI_GPT_PROTECT_MBR
        assert mbr[0].start_head == 0
        assert mbr[0].start_sector == 1
        assert mbr[0].start_cylinder == 0
        assert mbr[0].end_head == 255
        assert mbr[0].end_sector == 63
        assert mbr[0].end_cylinder == 1023
        assert mbr[0].lba_start == 1
        assert mbr[0].num_sectors == 27262975

