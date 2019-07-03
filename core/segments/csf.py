# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

from os import path
from jinja2 import Template
from subprocess import run, PIPE
from tempfile import gettempdir
from voluptuous import Optional, Required, Range, All, Any

from .base import DatSegBase, get_full_path

CSF_TEMPLATE = '''
[Header]
    Version = {{ header.version }}
    Hash Algorithm = {{ header.hash_algorithm }}
    Engine Configuration = {{ header.engine_configuration }}
    Certificate Format = {{ header.certificate_format }}
    Signature Format = {{ header.signature_format }}
    Engine = {{ header.engine }}

[Install SRK]
    Source index = {{ install_srk.source_index }}
    File = "{{ install_srk.file }}"

[Install CSFK]
    File = "{{ install_csfk.file }}"

[Authenticate CSF]

{% for item in unlock_commands %}
[Unlock]
    Engine = {{ item.engine }}
    Features = {{ item.features }}
{% endfor %}

[Install Key]
    Verification index = {{ install_key.verification_index }}
    Target index = {{ install_key.target_index }}
    File = "{{ install_key.file }}"

[Authenticate Data]
    Verification index = {{ authenticate_data.verification_index }}
    Blocks = \\
    {% for item in authenticate_data.blocks -%}
    {{ '0x%X' % item.address }} {{ '0x%X' % item.offset }} {{ '0x%X' % item.size }} "{{ item.file }}", \\
    {% endfor %}

{% if install_secret_key -%}             
[Install Secret Key]
    Verification index = {{ install_secret_key.verification_index }}
    Target Index = {{ install_secret_key.target_index }}
    Key = {{ install_secret_key.key_path }}
    Key Length = {{ install_secret_key.key_length }}
    Blob Address = {{ install_secret_key.blob_address }}
{%- endif %}

{% if decrypt_data -%}   
[Decrypt Data]
    Verification index = {{ decrypt_data.verification_index }}
    Mac Bytes = {{ decrypt_data.mac_bytes }}
    Blocks = \\
    {% for item in decrypt_data.blocks -%}
    {{ '0x%X' % item.address }} {{ '0x%X' % item.offset }} {{ '0x%X' % item.size }} "{{ item.file }}", \\
    {% endfor %}
{%- endif %}
'''


class CST(object):

    @property
    def version(self):
        ret = self._run('-v')
        return ret.split()[-1]

    def __init__(self, cst_exe, temp_dir=None):
        self._cst_exe = cst_exe
        self._tmp_dir = gettempdir() if temp_dir is None else path.realpath(temp_dir)
        self._dek_bin = path.join(self._tmp_dir, "dek.bin")
        self._csf_txt = path.join(self._tmp_dir, "csf.txt")
        self._boot_bin = path.join(self._tmp_dir, "boot.bin")

    def _run(self, *args):
        ret = run([self._cst_exe] + list(args), stdout=PIPE, stderr=PIPE, text=True)

        if ret.returncode != 0:
            raise Exception(ret.stderr)

        if 'error:' in ret.stdout:
            raise Exception(ret.stdout)

        return ret.stdout

    def gen_cst(self, smx_data):
        assert isinstance(smx_data, dict)

        csf_txt = Template(CSF_TEMPLATE).render(smx_data)
        with open(self._csf_txt, 'w') as f:
            f.write(csf_txt)

    def process(self, out_path, cert_path=None):

        if not path.exists(self._csf_txt):
            raise Exception(f"File doesnt exist: {self._csf_txt}")

        if cert_path is not None:
            if not path.exists(cert_path):
                raise Exception()
            ret = self._run('-i', self._csf_txt, '-o', out_path, '-c', cert_path)

        else:
            ret = self._run('-i', self._csf_txt, '-o', out_path)

        return ret


class ErrorCSF(Exception):
    """Thrown when parsing a file fails"""
    pass


class DatSegCSF(DatSegBase):
    """ Data segments class for Code Signing File

        <NAME>.csf:
            description: srt
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
