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
        data = f.read()

    mbr = core.mbr.MBR.parse(data)
    assert len(mbr) == 1
    assert mbr[0].partition_type == core.mbr.PartitionType.EFI_GPT_PROTECT_MBR

    gpt = core.gpt.GPT.parse(data, 512)
    assert len(gpt) > 0

    print(gpt.info())

