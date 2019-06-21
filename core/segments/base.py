# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
from voluptuous import Schema, ALLOW_EXTRA


def get_full_path(root, *path_list):
    """
    :param root:
    :param path:
    :return:
    """
    ret_path = []
    for path in path_list:
        file_path = ""
        for abs_path in [path, os.path.join(root, path)]:
            abs_path = os.path.normpath(abs_path)
            if os.path.exists(abs_path):
                file_path = abs_path
                break
        if not file_path:
            raise Exception("Path: \"%s\" doesnt exist" % path)
        ret_path.append(file_path)

    return ret_path


def get_data_segment(db, name):
    """ Get data segments by it's name
    :param db:
    :param name: The name of data segments
    :return: return object
    """
    assert isinstance(db, list), ""
    assert isinstance(name, str), ""

    for item in db:
        if item.full_name == name.upper():
            return item

    raise Exception("{} doesn't exist !".format(name))


class DatSegBase(object):
    """ Data segments base class """

    MARK = 'base'
    SCHEMA = {}

    @property
    def loaded(self):
        return False if self.smx_data is None else True

    @property
    def full_name(self):
        return '{}.{}'.format(self.name, self.MARK)

    def __init__(self, name, smx_data=None):
        """ Init BaseItem
        :param name: Data segments name
        :return Data segments object
        """
        assert isinstance(name, str)

        self.name = name
        self.data = None
        self.smx_data = None
        if smx_data is not None:
            self.init(smx_data)

    def __str__(self):
        """ String representation """
        return self.info()

    def __ne__(self, node):
        """ Check data segments inequality """
        return not self.__eq__(node)

    def init(self, smx_data):
        """ Initialize IMX segments
        :param smx_data: ...
        """
        assert isinstance(smx_data, dict)

        s = Schema(self.SCHEMA, extra=ALLOW_EXTRA)
        self.smx_data = s(smx_data)

    def info(self):
        return self.full_name

    def load(self, db, root_path):
        raise NotImplementedError()
