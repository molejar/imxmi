# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import uboot
from .base import DatSegBase, get_full_path
from voluptuous import Optional, Required, All, Any, Length


supported_images = [item[0] for item in uboot.EnumImageType]
supported_archs = [item[0] for item in uboot.EnumArchType]
supported_oss = [item[0] for item in uboot.EnumOsType]
supported_compressions = [item[0] for item in uboot.EnumCompressionType]


class ErrorUBI(Exception):
    """ Thrown when parsing a file fails """
    pass


class ErrorUBX(Exception):
    """ Thrown when parsing a file fails """
    pass


class ErrorUBT(Exception):
    """ Thrown when parsing a file fails """
    pass


class ErrorUEV(Exception):
    """ Thrown when parsing a file fails """
    pass


class DatSegUBI(DatSegBase):
    """ Data segments class for old U-Boot main image

        <NAME>.ubi:
            description: str
            address: int
            file: str (required)
            mark: str (default: 'bootcmd=')
            mode: <'disabled', 'merge' or 'replace'> (default: 'disabled')
            eval: str (required if 'mode' is not disabled)
    """

    MARK = 'ubi'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required('file'): str,
        Optional('mark', default='bootcmd='): str,
        Optional('mode', default='disabled'): All(str, Any('disabled', 'merge', 'replace')),
        Optional('eval'): str
    }

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if self.smx_data['mode'] == 'disabled':
            with open(get_full_path(root_path, self.smx_data['file'])[0], 'rb') as f:
                self.data = f.read()
        else:
            img_obj = uboot.EnvImgOld(self.smx_data['mark'])
            img_obj.open_img(get_full_path(root_path, self.smx_data['file'])[0])
            if self.smx_data['mode'] == 'replace':
                img_obj.clear()
            img_obj.load(self.smx_data['eval'])

            self.data = img_obj.export_img()


class DatSegUBX(DatSegBase):
    """ Data segments class for old U-Boot executable image

        <NAME>.uexe:
            description: srt
            address: int
            header:
                name: str(32)
                entry_address: int (default: 0)
                load_address: int (default: 0)
                image_type:  "standalone", "firmware", "script", "multi" (default: "firmware")
                target_arch: "alpha", "arm", "x86", ... (default: "arm")
                os: "openbsd", "netbsd", "freebsd", "bsd4", "linux", ... (default: "linux")
                compression: "none", "gzip", "bzip2", "lzma", "lzo", "lz4" (default: "none")
            <data or file>: str, list (required)
    """

    MARK = 'ubx'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required(Any('data', 'file'), msg="required key 'data' or 'file' not provided"): Any(str, list),
        Optional('header'): {
            Optional('name', default=''): All(str, Length(min=0, max=32)),
            Optional('entry_address', default=0): Any(int, All(str, lambda v: int(v, 0))),
            Optional('load_address', default=0): Any(int, All(str, lambda v: int(v, 0))),
            Optional('image_type', default='firmware'): All(str, Any(*supported_images)),
            Optional('target_arch', default='arm'): All(str, Any(*supported_archs)),
            Optional('running_os', default='linux'): All(str, Any(*supported_oss)),
            Optional('compression', default='none'): All(str, Any(*supported_compressions))
        }
    }

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'header' in self.smx_data:
            img_obj = uboot.new_img(
                name=self.smx_data['header']['name'],
                eaddr=self.smx_data['header']['entry_address'],
                laddr=self.smx_data['header']['load_address'],
                image=self.smx_data['header']['image_type'],
                arch=self.smx_data['header']['target_arch'],
                os=self.smx_data['header']['running_os'],
                compress=self.smx_data['header']['compression']
            )
        else:
            img_obj = uboot.new_img(
                name='',
                eaddr=0,
                laddr=0,
                image='firmware',
                arch='arm',
                os='linux',
                compress='none'
            )

        if img_obj.header.image_type == uboot.EnumImageType.FIRMWARE:
            with open(get_full_path(root_path, self.smx_data['file'])[0], 'rb') as f:
                img_obj.data = f.read()
        elif img_obj.header.image_type == uboot.EnumImageType.SCRIPT:
            if 'data' is self.smx_data:
                img_obj.load(self.smx_data['data'])
            else:
                with open(get_full_path(root_path, self.smx_data['file'])[0], 'r') as f:
                    img_obj.load(f.read())
        elif img_obj.header.image_type == uboot.EnumImageType.MULTI:
            for img_path in get_full_path(root_path, self.smx_data['file']):
                with open(img_path, 'rb') as f:
                    img_obj.append(uboot.parse_img(f.read()))
        else:
            with open(get_full_path(root_path, self.smx_data['file'])[0], 'rb') as f:
                img_obj.data = f.read()

        self.data = img_obj.export()


class DatSegUBT(DatSegBase):
    """ Data segments class for new FDT U-Boot image

        <NAME>.ubt:
            description: str
            address: int
            <data or file>: str (required)
    """

    MARK = 'ubt'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Required(Any('data', 'file'), msg="required key 'data' or 'file' not provided"): str,
    }

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        :return:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'file' in self.smx_data:
            its_path = get_full_path(root_path, self.smx_data['file'])[0]
            its_dir = os.path.dirname(its_path)
            with open(its_path, 'r') as f:
                data = f.read()
        else:
            its_dir = root_path
            data = self.smx_data['data']

        ftd_obj = uboot.parse_its(data, its_dir)
        self.data = ftd_obj.to_itb()


class DatSegUEV(DatSegBase):
    """ Data segments class for U-Boot ENV image

        <NAME>.uev:
            description: str
            address: int
            file: str
            mark: str (default: 'bootcmd=')
            eval: str
    """

    MARK = 'uev'
    SCHEMA = {
        Optional('description'): str,
        Optional('address'): Any(int, All(str, lambda v: int(v, 0))),
        Optional('file'): str,
        Optional('mark', default='bootcmd='): str,
        Required('eval'): str
    }

    def load(self, db, root_path):
        """ Load content
        :param db:
        :param root_path:
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)

        if 'data' in self.smx_data:
            env_obj = uboot.EnvBlob()
            env_obj.load(self.smx_data['data'])
        else:
            file_path = get_full_path(root_path, self.smx_data['file'])[0]
            if file_path.endswith(".txt"):
                with open(file_path, 'r') as f:
                    env_obj = uboot.EnvBlob()
                    env_obj.load(f.read())
            else:
                with open(file_path, 'rb') as f:
                    env_obj = uboot.EnvBlob.parse(f.read())

        self.data = env_obj.export()
