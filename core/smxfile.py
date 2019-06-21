# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import os
import imx
import yaml
import jinja2

from voluptuous import Optional, Required, Range, All, Any, Schema, ALLOW_EXTRA

# internals
from .segments import DatSegFDT, DatSegDCD, DatSegIMX2, DatSegIMX2B, DatSegIMX3, DatSegRAW, DatSegUBI, \
                      DatSegUBX, DatSegUBT, DatSegUEV, DatSegCSF
from .fs import mbr, gpt, fat, ext


def fmt_size(num, kibibyte=True):
    base, suffix = [(1000., 'B'), (1024., 'iB')][kibibyte]
    for x in ['B'] + [x + suffix for x in list('kMGTP')]:
        if -base < num < base:
            break
        num /= base
    return "{0:3.1f} {1:s}".format(num, x)


class SafeCustomLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = super(SafeCustomLoader, self).construct_mapping(node, deep=deep)

        # Convert all KEYS to lowercase
        keys = mapping.keys()
        for key in keys:
            if key.startswith('_') or key.endswith('_'):
                continue
            value = mapping.pop(key)
            mapping[key.lower()] = value

        # Add line number in YAML file for parsed KEY
        mapping['__line__'] = node.start_mark.line + 1
        return mapping


class ParseError(Exception):
    """Thrown when parsing a file fails"""
    pass


class SmxLinuxImage(object):
    """ Boot Image class

        linux_sd_image:
            bootloader:
                offset: int or str (required)
                <file or image>: str (required)
            uboot_env:
                offset: int or str (required)
                <file or image>: str (required)
            partitions:
                - name: str
                  type: str (required)
                  offset: int or str
                  size: int or str
                  data:
                    - <file or image>: str (required)
                      name: str

                - name: str
                  type: LINUX
                  offset: int or str
                  size: int or str
                  file: str (required)
    """

    supported_parts = [item[0] for item in mbr.PartitionType]

    SCHEMA = {
        Required('bootloader'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file')): str
        },
        Optional('uboot_env'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file')): str
        },
        Optional('partitions'): All(list, [{
            Optional('name'): str,
            Optional('type'): All(str, Any(*supported_parts)),
            Optional('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('size'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('file'): str,
            Optional('data'): All(list, [{
                Required(Any('image', 'file')): str,
                Optional('name'): str
            }])
        }])
    }

    def __init__(self, smx_data):
        """ Init SmxImage
        :param smx_data:
        :return object
        """
        assert isinstance(smx_data, dict)

        schema = Schema(self.SCHEMA, extra=ALLOW_EXTRA)
        self.smx_data = schema(smx_data)

    def save(self, path):
        pass


class SmxAndroidImage(object):
    """ Boot Image class

        android_sd_image:
            mbr_type: srt
            bootloader:
                offset: int or str (required)
                <file or image>: str (required)
            uboot_env:
                offset: int or str (required)
                <file or image>: str (required)
            partitions:
                - name: str
                  type: str (required)
                  offset: int or str
                  size: int or str
                  data:
                    - <file or image>: str (required)
                      name: str

                - name: str
                  type: LINUX
                  offset: int or str
                  size: int or str
                  file: str (required)
    """

    supported_parts = [item[0] for item in mbr.PartitionType]

    SCHEMA = {
        Required('mbr_type'): str,
        Required('bootloader'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file')): str
        },
        Optional('uboot_env'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file')): str
        },
        Optional('partitions'): All(list, [{
            Optional('name'): str,
            Optional('type'): All(str, Any(*supported_parts)),
            Optional('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('size'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('file'): str,
            Optional('data'): All(list, [{
                Required(Any('image', 'file')): str,
                Optional('name'): str
            }])
        }])
    }

    def __init__(self, smx_data):
        """ Init SmxImage
        :param smx_data:
        :return object
        """
        assert isinstance(smx_data, dict)

        schema = Schema(self.SCHEMA, extra=ALLOW_EXTRA)
        self.smx_data = schema(smx_data)

    def save(self, path):
        pass


class SmxFile(object):

    data_segments = {
        DatSegDCD.MARK: DatSegDCD,
        DatSegCSF.MARK: DatSegCSF,
        DatSegFDT.MARK: DatSegFDT,
        DatSegIMX2.MARK: DatSegIMX2,
        DatSegIMX2B.MARK: DatSegIMX2B,
        DatSegIMX3.MARK: DatSegIMX3,
        DatSegUBI.MARK: DatSegUBI,
        DatSegUBX.MARK: DatSegUBX,
        DatSegUBT.MARK: DatSegUBT,
        DatSegUEV.MARK: DatSegUEV,
        DatSegRAW.MARK: DatSegRAW
    }

    def __init__(self, file=None, auto_load=False):
        # private
        self.name = ""
        self.description = ""
        self.platform = None
        self.path = None
        self.image = None
        self.data = []
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
        smx_data = yaml.load(txt_data, Loader=yaml.SafeLoader)
        if 'variables' in smx_data:
            var_data = smx_data['variables']
            txt_data = jinja2.Template(txt_data).render(var_data)
            smx_data = yaml.load(txt_data, Loader=SafeCustomLoader)
        else:
            smx_data = yaml.load(txt_data, Loader=SafeCustomLoader)

        # check if all variables have been defined
        # if re.search("\{\{.*x.*\}\}", text_data) is not None:
        #   raise Exception("Some variables are not defined !")

        # set absolute path to core file
        self.path = os.path.abspath(os.path.dirname(file))

        # clear all data
        self.name = ""
        self.description = ""
        self.platform = None
        self.image = None
        self.data = []

        for key, value in smx_data.items():
            if key == 'name':
                self.name = value

            elif key == 'description':
                self.description = value

            elif key == 'platform':
                self.platform = value

            elif key == 'data_segments':
                for full_name, data in value.items():
                    if full_name.startswith('_') or full_name.endswith('_'):
                        continue
                    try:
                        item_name, item_type = full_name.split('.')
                    except ValueError:
                        raise Exception("Not supported data segment format: {}".format(full_name))
                    # case tolerant type
                    item_type = item_type.lower()
                    if item_type not in self.data_segments.keys():
                        raise Exception("Not supported data segments type: {}".format(item_type))
                    self.data.append(self.data_segments[item_type](item_name, data))

            elif key == 'linux_sd_image':
                self.image = SmxLinuxImage(value)

            elif key == 'android_sd_image':
                self.image = SmxAndroidImage(value)

        if self.platform is None:
            raise Exception("Platform not specified inside: %s" % file)
        if self.image is None:
            raise Exception("Key 'boot_image' doesn't exist inside: %s" % file)
        if not self.data:
            raise Exception("Key 'data_segments' doesn't exist inside: %s" % file)

        if auto_load:
            self.load()

    def load(self):
        # load simple data segments
        for item in self.data:
            if item.MARK not in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self.data, self.path)

        # load complex data segments which can include simple data segments
        for item in self.data:
            if item.MARK in (DatSegIMX2.MARK, DatSegIMX2B.MARK, DatSegIMX3.MARK):
                item.load(self.data, self.path)



