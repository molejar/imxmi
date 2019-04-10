#!/usr/bin/env python

# Copyright (c) 2019 Martin Olejar
#
# SPDX-License-Identifier: BSD-3-Clause
# The BSD-3-Clause license for this file can be found in the LICENSE file included with this distribution
# or at https://spdx.org/licenses/BSD-3-Clause.html#licenseText

import os
import sys
import yaml
import click
# local module
from core import __version__, LinuxImage


# Application error code
ERROR_CODE = 1

# Application version
VERSION = __version__

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
@click.option('-s', '--system', type=click.Choice(['linux', 'android']),
              default='linux', show_default=True, help="Image OS type")
@click.argument('file', nargs=1, type=click.Path(exists=True))
def info(system, file):

    if system is 'linux':
        with LinuxImage.open(file) as img:
            img.parse()
            click.echo(img.info())
    else:
        pass


@cli.command(short_help="Extract i.MX boot image content")
@click.option('-o', '--outdir', default=None, help="Output directory")
@click.option('-s', '--system', type=click.Choice(['linux', 'android']),
              default='linux', show_default=True, help="Image OS type")
@click.argument('file', nargs=1, type=click.Path(exists=True))
def extract(system, outdir, file):
    if system is 'linux':
        with LinuxImage.open(file) as img:
            img.parse()
            click.echo(img.info())
    else:
        pass
