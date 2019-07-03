# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


from .base import DatSegBase, get_full_path
from voluptuous import Optional, Required, All, Any


class ErrorRAW(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegRAW(DatSegBase):
    """ Data segments class for raw binary image

        <NAME>.raw:
            description: srt
            address: int
            file: str (required)
    """

    MARK = 'raw'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required('file'): str
    }

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        with open(get_full_path(root_path, self.smx_data['file'])[0], 'rb') as f:
            self.data = f.read()
