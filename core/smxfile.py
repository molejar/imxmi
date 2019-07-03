# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText


import os
import sys
import yaml
import jinja2
from voluptuous import Optional, Required, Range, All, Any, Schema, ALLOW_EXTRA, Invalid

# internals
from .segments import DatSegFDT, DatSegDCD, DatSegIMX2, DatSegIMX2B, DatSegIMX3, DatSegRAW, DatSegUBI, \
                      DatSegUBX, DatSegUBT, DatSegUEV, DatSegCSF
from .fs import mbr, gpt, fat, ext
from .image import LinuxImage, AndroidImage


########################################################################################################################
# helper functions
########################################################################################################################
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
        mapping['__line__'] = node.start_mark.line
        return mapping


########################################################################################################################
# SMX Exceptions
########################################################################################################################
class SMXError(Exception):
    """ Thrown when parsing a file fails """

    @property
    def line_number(self):
        return self._line

    @property
    def path_to_error(self):
        return self._path

    @property
    def error_description(self):
        return self._desc

    def __init__(self, msg, line=None, path=None):
        """ Initialize the Exception with given message. """
        self._line = line
        self._path = path
        self._desc = msg

    def __str__(self):
        """ Return the Exception message. """
        msg = ""
        if self._line:
            msg += '<L:{}> '.format(self._line)
        if self._path:
            msg += '{} => '.format(self._path)
        return msg + self._desc


########################################################################################################################
# SMX Classes
########################################################################################################################
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
            Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
        },
        Optional('uboot_env'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
        },
        Optional('partitions'): All(list, [{
            Optional('name'): str,
            Optional('type'): All(str, Any(*supported_parts)),
            Optional('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('size'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('file'): str,
            Optional('data'): All(list, [{
                Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
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

    PARTS = [item[0] for item in mbr.PartitionType]

    SCHEMA = {
        Required('mbr_type'): str,
        Required('bootloader'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
        },
        Optional('uboot_env'): {
            Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
        },
        Optional('partitions'): All(list, [{
            Optional('name'): str,
            Optional('type'): All(str, Any(*PARTS)),
            Optional('offset'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('size'): Any(int, All(str, lambda v: int(v, 0))),
            Optional('file'): str,
            Optional('data'): All(list, [{
                Required(Any('image', 'file'), msg="required key 'image' or 'file' not provided"): str,
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

    DS = {
        DatSegDCD.MARK: DatSegDCD,
        DatSegCSF.MARK: DatSegCSF,
        DatSegFDT.MARK: DatSegFDT,
        DatSegUBI.MARK: DatSegUBI,
        DatSegUBX.MARK: DatSegUBX,
        DatSegUBT.MARK: DatSegUBT,
        DatSegUEV.MARK: DatSegUEV,
        DatSegRAW.MARK: DatSegRAW,
        DatSegIMX2.MARK: DatSegIMX2,
        DatSegIMX3.MARK: DatSegIMX3,
        DatSegIMX2B.MARK: DatSegIMX2B
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

        # open smx file
        with open(file, 'r') as f:
            txt_data = f.read()

        # load smx file
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
                    # set error params
                    error_line = data.get('__line__')
                    error_path = full_name
                    try:
                        item_name, item_type = full_name.split('.')
                    except ValueError:
                        raise SMXError("not supported data-segment format: {}".format(full_name),
                                       error_line, error_path)
                    # case tolerant type
                    item_type = item_type.lower()
                    if item_type not in self.DS.keys():
                        raise SMXError("not supported data-segment type: {}".format(item_type), error_line, error_path)
                    try:
                        data_segment = self.DS[item_type](item_name, data)
                    except Invalid as e:
                        for name in e.path:
                            if isinstance(name, (str, int)):
                                error_path += "/{}".format(name)
                            elif isinstance(name, Required) and isinstance(name.schema, str):
                                error_path += "/{}".format(name.schema)
                        raise SMXError(e.error_message, error_line, error_path)
                    self.data.append(data_segment)

            elif key == 'linux_sd_image':
                try:
                    self.image = SmxLinuxImage(value)
                except Invalid as e:
                    error_path = key
                    for name in e.path:
                        if isinstance(name, (str, int)):
                            error_path += "/{}".format(name)
                        elif isinstance(name, Required) and isinstance(name.schema, str):
                            error_path += "/{}".format(name.schema)
                    raise SMXError(e.error_message, value.get('__line__'), error_path)

            elif key == 'android_sd_image':
                try:
                    self.image = SmxAndroidImage(value)
                except Invalid as e:
                    error_path = key
                    for name in e.path:
                        if isinstance(name, (str, int)):
                            error_path += "/{}".format(name)
                        elif isinstance(name, Required) and isinstance(name.schema, str):
                            error_path += "/{}".format(name.schema)
                    raise SMXError(e.error_message, value.get('__line__'), error_path)

        if self.platform is None:
            raise SMXError("Required key 'platform' not provided in {}".format(file))
        if self.image is None:
            raise SMXError("Required key 'boot_image' not provided in {}".format(file))
        if not self.data:
            raise SMXError("Required key 'data_segments' not provided in {}".format(file))

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



