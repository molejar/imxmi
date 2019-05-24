# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import os
import imx
import yaml
import jinja2

# internals
from .segments import DatSegFDT, DatSegDCD, DatSegIMX2, DatSegIMX2B, DatSegIMX3, DatSegRAW, DatSegUBI, \
                      DatSegUBX, DatSegUBT
from .fs import mbr, gpt, fat, ext


def fmt_size(num, kibibyte=True):
    base, suffix = [(1000., 'B'), (1024., 'iB')][kibibyte]
    for x in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < num < base:
            break
        num /= base
    return "{0:3.1f} {1:s}".format(num, x)


class ParseError(Exception):
    """Thrown when parsing a file fails"""
    pass


class SmxImage(object):

    def __init__(self, smx_data):
        """ Init SmxImage
        :param smx_data:
        :return object
        """
        assert isinstance(smx_data, dict)

        self.uboot_offset = 0
        self.uboot_image = None
        self.ubenv_offset = 0
        self.ubenv_image = None
        self.fat_offset = 0
        self.fat_type = mbr.PartitionType.FAT32
        self.fat_size = 0
        self.fat_files = []
        self.ext_part = None

    def save(self, path):
        pass


class SmxFile(object):

    data_segments = {
        DatSegDCD.MARK: DatSegDCD,
        DatSegFDT.MARK: DatSegFDT,
        DatSegIMX2.MARK: DatSegIMX2,
        DatSegIMX2B.MARK: DatSegIMX2B,
        DatSegIMX3.MARK: DatSegIMX3,
        DatSegUBI.MARK: DatSegUBI,
        DatSegUBX.MARK: DatSegUBX,
        DatSegUBT.MARK: DatSegUBT,
        DatSegRAW.MARK: DatSegRAW
    }

    @property
    def name(self):
        return self._name

    @property
    def platform(self):
        return self._platform

    @property
    def description(self):
        return self._description

    @property
    def scripts(self):
        return self._body

    @property
    def path(self):
        return self._path

    def __init__(self, file=None, auto_load=False):
        # private
        self._name = ""
        self._description = ""
        self._platform = None
        self._path = None
        self._data = []
        self._body = None
        # init
        if file is not None:
            self.open(file, auto_load)

    def info(self):
        pass

    def open(self, file, auto_load=False):
        """ Open core file
        :param file:
        :param auto_load:
        :return
        """
        assert isinstance(file, str)

        # open core file
        with open(file, 'r') as f:
            txt_data = f.read()

        # load core file
        smx_data = yaml.load(txt_data)
        if 'VARS' in smx_data:
            var_data = smx_data['VARS']
            txt_data = jinja2.Template(txt_data).render(var_data)
            smx_data = yaml.load(txt_data)

        # check if all variables have been defined
        # if re.search("\{\{.*x.*\}\}", text_data) is not None:
        #   raise Exception("Some variables are not defined !")

        # set absolute path to core file
        self._path = os.path.abspath(os.path.dirname(file))

        # validate segments in core file
        if 'HEAD' not in smx_data:
            raise Exception("HEAD segments doesn't exist inside file: %s" % file)
        if 'DATA' not in smx_data:
            raise Exception("DATA segments doesn't exist inside file: %s" % file)
        if 'BODY' not in smx_data:
            raise Exception("BODY segments doesn't exist inside file: %s" % file)

        # parse header segments
        if "CHIP" not in smx_data['HEAD']:
            raise Exception("CHIP not defined in HEAD segments")
        if smx_data['HEAD']['CHIP'] not in imx.sdp.supported_devices():
            raise Exception("Device type not supported !")
        self._name = smx_data['HEAD']['NAME'] if 'NAME' in smx_data['HEAD'] else ""
        self._description = smx_data['HEAD']['DESC'] if 'DESC' in smx_data['HEAD'] else ""
        self._platform = smx_data['HEAD']['CHIP']

        # clear all data
        self._data = []
        self._body = None

        # parse data segments
        for full_name, data in smx_data['DATA'].items():
            try:
                item_name, item_type = full_name.split('.')
            except ValueError:
                raise Exception("Not supported data segments format: {}".format(full_name))
            # case tolerant type
            item_type = item_type.lower()
            if item_type not in self.data_segments.keys():
                raise Exception("Not supported data segments type: {}".format(item_type))

            self._data.append(self.data_segments[item_type](item_name, data))

        # parse scripts
        self._body = SmxImage(smx_data['BODY'])

        if auto_load:
            self.load()

    def load(self):
        # load simple data segments
        for item in self._data:
            if item.MARK not in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self._data, self._path)

        # load complex data segments which can include simple data segments
        for item in self._data:
            if item.MARK in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self._data, self._path)

