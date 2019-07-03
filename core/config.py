# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import configparser


class Config(object):

    def __init__(self):
        self._file = os.environ.get('IMXMI_CONF', 'config.ini')
        self._conf = configparser.ConfigParser()

    def load(self):
        if os.path.exists(self._file):
            self._conf.read_file(self._file)
        else:
            self._conf.add_section('CSF')
            self._conf.set('CSF', 'cst_path', 'bin/cst.exe')

            with open(self._file, 'w') as f:
                self._conf.write(f)
