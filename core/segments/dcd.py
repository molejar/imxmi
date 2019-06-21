# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from imx.img import SegDCD
from .base import DatSegBase, get_full_path
from voluptuous import Optional, Required, All, Any


class InitErrorDCD(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegDCD(DatSegBase):
    """ Data segments class for Device Configuration Data

        <NAME>.dcd:
            description: srt
            address: int
            <data or file>: str (required)
    """

    MARK = 'dcd'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required(Any('data', 'file')): str
    }

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'data' not in self.smx_data:
            dcd_obj = SegDCD.parse_txt(self.smx_data['data'])
        else:
            file_path = get_full_path(root_path, self.smx_data['file'])[0]
            if file_path.endswith(".txt"):
                with open(file_path, 'r') as f:
                    dcd_obj = SegDCD.parse_txt(f.read())
            else:
                with open(file_path, 'rb') as f:
                    dcd_obj = SegDCD.parse(f.read())

        self.data = dcd_obj.export()
