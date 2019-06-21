# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import fdt
from .base import DatSegBase, get_full_path
from voluptuous import Optional, Required, All, Any


class InitErrorFDT(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegFDT(DatSegBase):
    """ Data segments class for Device Configuration Data

        <NAME>.fdt:
            description: srt
            address: int
            file: str (required)
            mode: <'disabled' or 'merge'> default ('disabled')
            data: str
    """

    MARK = 'fdt'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required('file'): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge')),
        Optional('data'): str
    }

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        file_path = get_full_path(root_path, self.smx_data['file'])[0]
        if file_path.endswith(".dtb"):
            with open(file_path, 'rb') as f:
                fdt_obj = fdt.parse_dtb(f.read())
        else:
            with open(file_path, 'r') as f:
                fdt_obj = fdt.parse_dts(f.read())

        if 'data' in self.smx_data and self.smx_data['mode'] == 'merge':
            if 'data' not in self.smx_data:
                raise Exception()
            fdt_obj.merge(fdt.parse_dts(self.smx_data['data']))

        if fdt_obj.header.version is None:
            fdt_obj.header.version = 17

        self.data = fdt_obj.to_dtb()
