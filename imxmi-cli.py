#!/usr/bin/env python

# Copyright (c) 2017-2018 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import sys
import yaml
import click
# local module
import core


# Application error code
ERROR_CODE = 1

# Application version
VERSION = core.__version__

# Application description
DESCRIPTION = (
    "i.MX Image Maker, ver.: " + VERSION + "\n\n"
    "NOTE: Development version, be carefully with it usage !\n"
)


@click.group(context_settings=dict(help_option_names=['-?', '--help']), help=DESCRIPTION)
@click.version_option(VERSION, '-v', '--version')
def cli():
    click.echo()


@cli.command(short_help="List i.MX boot image info")
@click.option('-t', '--type', type=click.Choice(['auto', 'sd', 'emmc', 'imx']),
              default='auto', show_default=True, help="Image type")
@click.argument('file', nargs=1, type=click.Path(exists=True))
def info(type, file):
    pass
