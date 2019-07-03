# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import imx
import uboot
from .base import DatSegBase, get_data_segment, get_full_path
from voluptuous import Optional, Required, All, Any, Schema, ALLOW_EXTRA

img_types = {
    "SCD": imx.img.EnumAppType.SCD,
    "SCFW": imx.img.EnumAppType.SCFW,
    "CM4-0": imx.img.EnumAppType.M4_0,
    "CM4-1": imx.img.EnumAppType.M4_1,
    "APP-A35": imx.img.EnumAppType.A53,
    "APP-A53": imx.img.EnumAppType.A53,
    "APP-A72": imx.img.EnumAppType.A72
}


class ErrorIMX(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegIMX2(DatSegBase):
    """ Data segments class for i.MX6 and i.MX7 boot image

        <NAME>.imx2:
            description: str
            csf: str
            file: str (required)
            mode: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            mark: str (default: 'bootcmd=')
            eval: str (required if MODE is not disabled)

        <NAME>.imx2:
            description: str
            address: int (required)
            offset: int (default: 0x400)
            plugin: <'yes' or 'no'> (default: 'no')
            version: int (default: 0x41)
            dcd_seg: <NAME>.dcd
            app_seg: <NAME>.ubin (required)
            csf_seg: <NAME>.csf
    """

    SCHEMA1 = {
        Optional('description'): str,
        Optional('csf'): str,
        Required('file'): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge', 'replace')),
        Optional('mark', default='bootcmd='): str,
        Optional('eval'): str
    }

    SCHEMA2 = {
        Optional('description'): str,
        Required('address'): Any(int, All(str, lambda v: int(v, 0))),
        Optional('offset', default=0x400): Any(int, All(str, lambda v: int(v, 0))),
        Optional('plugin', default='no'): All(str, Any('yes', 'no')),
        Optional('version', default=0x41): Any(int, All(str, lambda v: int(v, 0))),
        Optional('dcd_seg'): str,
        Required('app_seg'): str,
        Optional('csf_seg'): str
    }

    MARK = 'imx2'
    SCHEMA = Any(Schema(SCHEMA1, extra=ALLOW_EXTRA), Schema(SCHEMA2, extra=ALLOW_EXTRA))

    def __init__(self, name, smx_data=None):
        super().__init__(name, smx_data)
        self.address = None
        self.dcd = None

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'file' not in self.smx_data:
            imx_obj = imx.img.BootImg2(self.smx_data['address'], self.smx_data['offset'], self.smx_data['version'],
                                       True if self.smx_data['plugin'] == 'yes' else False)
            if 'dcdseg' in self.smx_data:
                self.dcd = get_data_segment(db, self.smx_data['dcdseg']).data
                imx_obj.dcd = imx.img.SegDCD.parse(self.dcd)

            imx_obj.add_image(get_data_segment(db, self.smx_data['appseg']))
            self.address = imx_obj.address + imx_obj.offset
            self.data = imx_obj.export()

        else:
            img_path = get_full_path(root_path, self.smx_data['file'])[0]
            if self.smx_data['mode'] == 'disabled':
                with open(img_path, 'rb') as f:
                    self.data = f.read()
            else:
                env_img = uboot.EnvImgOld(self.smx_data['mark'])
                env_img.open_img(img_path)
                if self.smx_data['mode'] == 'replace':
                    env_img.clear()
                env_img.load(self.smx_data['eval'])
                self.data = env_img.export_img()

            imx_obj = imx.img.BootImg2.parse(self.data)
            self.address = imx_obj.address + imx_obj.offset
            self.dcd = imx_obj.dcd.export()


class DatSegIMX2B(DatSegBase):
    """ Data segments class for i.MX8M and i.MX8Mm boot image

        <NAME>.imx2b:
            description: srt
            mode: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            mark: str (default: 'bootcmd=')
            eval: str

            file: srt (required)
    """

    MARK = 'imx2b'
    SCHEMA = {
        Optional('description'): str,
        Required('file'): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge', 'replace')),
        Optional('mark', default='bootcmd='): str,
        Optional('eval'): str
    }

    def __init__(self, name, smx_data=None):
        super().__init__(name, smx_data)
        self.address = None
        self.dcd = None

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)


class DatSegIMX3(DatSegBase):
    """ Data segments class for i.MX8QM, i.MX8DM and i.MX8QXP boot image

        <NAME>.imx3:
            description: srt
            mode: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            mark: str (default: 'bootcmd=')
            eval: str

            file: srt (required)

        <NAME>.imx3:
            description: srt
            mode: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            mark: str (default: 'bootcmd=')
            eval: str (required if 'mode' is not disabled)

            address: int (required)
            offset: int (default: 0x400)
            version: int (default: 0x41)
            dcdseg: <NAME>.dcd
            images: list
                - type: <'SCD', 'SCFW', 'CM4-0', 'CM4-1', 'APP-A35', 'APP-A53' or 'APP-A72'>
                  address: int (default: 0)
                  file: str (required)
    """

    SCHEMA1 = {
        Optional('description'): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge', 'replace')),
        Optional('mark', default='bootcmd='): str,
        Optional('eval'): str,

        Required('file'): str
    }

    SCHEMA2 = {
        Optional('description'): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge', 'replace')),
        Optional('mark', default='bootcmd='): str,
        Optional('eval'): str,

        Required('address'): Any(int, All(str, lambda v: int(v, 0))),
        Optional('offset', default=0x400): Any(int, All(str, lambda v: int(v, 0))),
        Optional('plugin', default='no'): All(str, Any('yes', 'no')),
        Optional('version', default=0x41): Any(int, All(str, lambda v: int(v, 0))),
        Optional('dcdseg'): str,
        Required('images'): All(list, [{
            Optional('address', default=0): Any(int, All(str, lambda v: int(v, 0))),
            Required('type'): All(str, Any(*img_types.keys())),
            Required('file'): str
        }]),
    }

    MARK = 'imx3'
    SCHEMA = Any(Schema(SCHEMA1, extra=ALLOW_EXTRA), Schema(SCHEMA2, extra=ALLOW_EXTRA))

    def __init__(self, name, smx_data=None):
        super().__init__(name, smx_data)
        self.address = None
        self.dcd = None

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'file' not in self.smx_data:
            imx_obj = imx.img.BootImg3b(self.smx_data['address'], self.smx_data['offset'], self.smx_data['version'])
            if 'dcdseg' in self.smx_data:
                self.dcd = get_data_segment(db, self.smx_data['dcdseg']).data
                imx_obj.dcd = imx.img.SegDCD.parse(self.dcd)

            for image in self.smx_data['images']:
                with open(get_full_path(root_path, image['file'])[0], 'rb') as f:
                    imx_obj.add_image(f.read(), img_types[image['type']], image['address'])

            self.address = imx_obj.address + imx_obj.offset
            self.data = imx_obj.export()

        else:
            img_path = get_full_path(root_path, self.smx_data['file'])[0]
            if self.smx_data['mode'] == 'disabled':
                with open(img_path, 'rb') as f:
                    self.data = f.read()
            else:
                env_img = uboot.EnvImgOld(self.smx_data['mark'])
                env_img.open_img(img_path)
                if self.smx_data['mode'] == 'replace':
                    env_img.clear()
                env_img.load(self.smx_data['eval'])
                self.data = env_img.export_img()

            imx_obj = imx.img.BootImg3b.parse(self.data)
            self.address = imx_obj.address + imx_obj.offset
            self.dcd = imx_obj.dcd.export()
