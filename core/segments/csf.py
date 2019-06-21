# Copyright (c) 2017-2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from .base import DatSegBase, get_full_path
from voluptuous import Optional, Required, Range, All, Any


class InitErrorCSF(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegCSF(DatSegBase):
    """ Data segments class for Code Signing File

        <NAME>.csf:
            header:
                version: '4.1'
                hash_algorithm: 'sha256'
                engine_configuration: 0
                certificate_format: 'X509'
                signature_format: 'CMS'
                engine: 'CAAM'

            install_srk:
                source_index: int
                file: str

            install_csfk:
                file: str

            unlock_commands:
                - engine: str
                  features: str

            install_key:
                source_index: int
                target_index: int
                file: str

            authenticate_data:
                verification_index: int
                blocks:
                    - address: int or str
                      offset: int or str
                      size: int or str

            install_secret_key:
                verification_index: int
                target_index: int
                key_path: str
                key_length: int
                blob_address: int, str

            decrypt_data:
                verification_index: int
                mac_bytes: int
                blocks:
                    - address: int or str
                      offset: int or str
                      size: int or str
    """

    MARK = 'csf'
    SCHEMA = {
        Optional('description'): str,
        Required('header'): {
            Required('version'): All(str, Any('4.0', '4.1')),
            Required('hash_algorithm'): All(str, Any('sha256', 'sha384', 'sha512')),
            Required('engine_configuration'): int,
            Required('certificate_format'): All(str, Any('X509')),
            Required('signature_format'): All(str, Any('CMS')),
            Required('engine'): All(str, Any('CAAM'))
        },
        Required('install_srk'): {
            Required('source_index'): All(int, Range(0, 3)),
            Required('file'): str
        },
        Required('install_csfk'): {
            Required('file'): str
        },
        Optional('unlock_commands'):  All(list, [{
            Required('engine'): str,
            Required('features'): str
        }]),
        Required('install_key'): {
            Required('verification_index'): All(int, Range(0, 3)),
            Required('target_index'): All(int, Range(0, 3)),
            Required('file'): str
        },
        Optional('authenticate_data'): {
            Required('verification_index'): All(int, Range(0, 3)),
            Required('blocks'): All(list, [{
                Required('address'): Any(int, All(str, lambda v: int(v, 0))),
                Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
                Required('size'): Any(int, All(str, lambda v: int(v, 0)))
            }]),
        },
        Optional('install_secret_key'): {
            Required('verification_index'): All(int, Range(0, 3)),
            Required('target_index'): All(int, Range(0, 3)),
            Required('key_path'): str,
            Required('key_length'): int,
            Required('blob_address'): Any(int, All(str, lambda v: int(v, 0)))
        },
        Optional('decrypt_data'): {
            Required('verification_index'): All(int, Range(0, 3)),
            Required('mac_bytes'): int,
            Required('blocks'): All(list, [{
                Required('address'): Any(int, All(str, lambda v: int(v, 0))),
                Required('offset'): Any(int, All(str, lambda v: int(v, 0))),
                Required('size'): Any(int, All(str, lambda v: int(v, 0)))
            }])
        }
    }

    def load(self, db, root_path):
        """ load DCD segments
        :param db: ...
        :param root_path: ...
        """
        assert isinstance(db, list)
        assert isinstance(root_path, str)
