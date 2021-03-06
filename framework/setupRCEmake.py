#!/usr/bin/env python
# -*- coding: utf-8 -*-
#     
#     setupRCEmake.py
#     
#     This file is part of the RoboEarth Cloud Engine framework.
#     
#     This file was originally created for RoboEearth
#     http://www.roboearth.org/
#     
#     The research leading to these results has received funding from
#     the European Union Seventh Framework Programme FP7/2007-2013 under
#     grant agreement no248942 RoboEarth.
#     
#     Copyright 2012 RoboEarth
#     
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#     
#     http://www.apache.org/licenses/LICENSE-2.0
#     
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#     
#     \author/s: Dominique Hunziker 
#     
#     

# Before we start to import everything check if the script can be executed
import os

if os.getuid() != 0:
    print('setupRCEmake has to be run as super user.')
    exit(1)

# Python specific imports
import sys
import subprocess

# Custom imports
import settings
from rce.util.path import processPkgPath


_STD_DIR = ['/proc', '/dev', '/dev/pts', '/sys']


def up():
    mounts = [(pkg[0], os.path.join(settings.ROOTFS, pkg[1]))
              for pkg in processPkgPath(settings.ROOT_PKG_DIR)]
    
    # Create all the necessary mount points
    for mount in mounts:
        os.makedirs(mount[1])
    
    # Add the system relevant directories which have to be mounted as well and
    # mount all directories
    for source, target in [(path, os.path.join(settings.ROOTFS, path[1:]))
                           for path in _STD_DIR] + mounts:
        try:
            subprocess.check_output(['mount', '--bind', source, target])
        except subprocess.CalledProcessError as e:
            sys.stderr.write("Could not mount '{0}'.\n\tExitcode: "
                             '{1}'.format(source, e.returncode))
            
            if e.output:
                sys.stderr.write('\tOutput: {0}'.format(e.output))
    
    # Return the directory to the root of the container filesystem
    sys.stdout.write(settings.ROOTFS)


def down():
    mounts = [os.path.join(settings.ROOTFS, pkg[1])
              for pkg in processPkgPath(settings.ROOT_PKG_DIR)]
    
    stdDir = _STD_DIR[:]
    stdDir.reverse()
    
    # Add the system relevant directories which have to be unmounted as well in
    # reversed order and unmount all directories
    for target in mounts + [os.path.join(settings.ROOTFS, path[1:])
                            for path in stdDir]:
        try:
            subprocess.check_output(['umount', target])
        except subprocess.CalledProcessError as e:
            sys.stderr.write("Could not unmount '{0}'.\n\tExitcode: "
                             '{1}'.format(target, e.returncode))
            
            if e.output:
                sys.stderr.write('\tOutput: {0}'.format(e.output))
    
    # Delete all the extra created mount points
    for mount in mounts:
        os.rmdir(mount)


def _get_argparse():
    from argparse import ArgumentParser

    parser = ArgumentParser(prog='recmake-setup',
                            description='Setup the machine for the usage of '
                                        'chroot.')

    parser.add_argument('action', choices=['up', 'down'],
                        help='Flag to select set up instead of tear down.', )

    return parser


if __name__ == '__main__':
    args = _get_argparse().parse_args()
    
    if args.action == 'up':
        up()
    elif args.action == 'down':
        down()
    else:
        raise ValueError('Action can only be up or down.')
