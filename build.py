#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Miyamoto! Level Editor - New Super Mario Bros. U Level Editor
# Copyright (C) 2009-2021 Treeki, Tempus, angelsl, JasonP27, Kinnay,
# MalStar1000, RoadrunnerWMC, MrRean, Grop, AboodXD, Gota7, John10v10,
# mrbengtsson

# This file is part of Miyamoto!.

# Miyamoto! is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Miyamoto! is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Miyamoto!.  If not, see <http://www.gnu.org/licenses/>.

# build.py
# Builds Miyamoto! to a binary
# Use the values below to configure the release:

from globals import MiyamotoVersionFloat
import os, os.path, platform, shutil, sys

# Set architectures for universal build on macOS.
# CI overrides ARCHFLAGS per-runner (arm64 or x86_64) then lipo-merges.
# Local builds without ARCHFLAGS set default to universal.
if sys.platform == 'darwin':
    if 'ARCHFLAGS' not in os.environ:
        os.environ["ARCHFLAGS"] = "-arch x86_64 -arch arm64"

Version = str(MiyamotoVersionFloat)
PackageName = 'miyamoto_v%s' % Version


################################################################
################################################################

# Imports
import os, os.path, platform, shutil, sys
from cx_Freeze import setup, Executable

from setuptools import Extension
from Cython.Build import cythonize
from setuptools.command.build_ext import build_ext

cmdclass_dict = {}

if sys.platform == 'win32':
    os.environ["CC"] = "clang-cl"
    os.environ["CXX"] = "clang-cl"

    class ClangBuildExt(build_ext):
        def build_extensions(self):
            original_spawn = self.compiler.spawn
            def hijacked_spawn(cmd, **kwargs):
                if 'cl.exe' in cmd[0].lower():
                    cmd[0] = 'clang-cl'
                elif 'link.exe' in cmd[0].lower():
                    cmd[0] = 'lld-link'
                original_spawn(cmd, **kwargs)

            self.compiler.spawn = hijacked_spawn
            super().build_extensions()
            
    cmdclass_dict = {'build_ext': ClangBuildExt}

# Pick a build directory
dir_ = 'distrib/' + PackageName

# Print some stuff
print('[[ Freezing Miyamoto! ]]')
print('>> Destination directory: %s' % dir_)

# Add the "build" parameter to the system argument list
if len(sys.argv) == 1:
    sys.argv.extend(['build_ext', '--inplace', 'build_exe'])

# Clear the directory
if os.path.isdir(dir_): shutil.rmtree(dir_)
os.makedirs(dir_)

# exclude QtWebChannel, QtWebSockets and QtNetwork to save space, plus Python stuff we don't use
excludes = ['doctest', 'pdb', 'unittest', 'difflib',
    'multiprocessing', 'ssl',
    'PyQt5.QtWebChannel', 'PyQt5.QtWebSockets', 'PyQt5.QtNetwork']

# Extension flags — derived from ARCHFLAGS (already set above for macOS)
extra_args = []
if sys.platform == 'darwin':
    extra_args = os.environ.get("ARCHFLAGS", "").split()

fastyz_ext = Extension(
    name="fastyz",
    sources=["fastyz.pyx", "FastYZ/fastyz.c"],
    include_dirs=["."],
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)

addrlib_ext = Extension(
    name="addrlib.addrlib_cy",
    sources=["addrlib/addrlib_cy.pyx"],
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)

bc3_compress_ext = Extension(
    name="bc3.compress_cy",
    sources=["bc3/compress_cy.pyx"],
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)
        
bc3_decompress_ext = Extension(
    name="bc3.decompress_cy",
    sources=["bc3/decompress_cy.pyx"],
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)

# Platform-specific include_files
include_files = [
    'miyamotodata',
    'miyamotoextras',
    'license.txt',
    'README.md',
    'Objects',
    'data',
]
if sys.platform == 'darwin':
    include_files.append('macTools')
elif sys.platform == 'win32':
    include_files.append('Tools')
else:
    include_files.append('linuxTools')

# Set it up
base = 'gui' if sys.platform == 'win32' else None
setup(
    name = 'Pyamoto',
    version = Version,
    description = 'New Super Mario Bros. U Level Editor',
    options={
        'build_exe': {
            'excludes': excludes,
            'packages': ['encodings', 'encodings.hex_codec', 'encodings.utf_8', 'addrlib', 'bc3'],
            'includes': ['fastyz', 'addrlib', 'bc3'], 
            'build_exe': dir_,
            'optimize': 2,
            'silent': True,
            'include_files': include_files
            },
        'bdist_mac': {
            'bundle_name': 'Pyamoto',
            'iconfile': 'miyamotodata/pyamoto.icns',
        }
        },
    cmdclass = cmdclass_dict,
    ext_modules = cythonize([fastyz_ext, addrlib_ext, bc3_compress_ext, bc3_decompress_ext], language_level=3),
    executables = [
        Executable(
            'miyamoto.py',
            target_name = 'Pyamoto',
            icon = 'miyamotodata/win_icon.ico',
            base = base,
            ),
        ],
    )
print('>> Built frozen executable!')



# Post-build finalization
if 'bdist_mac' in sys.argv:
    print('>> Performing macOS specific finalization...')
    app_path = 'build/Pyamoto.app'
    if os.path.isdir(app_path):
        settings_path = os.path.join(app_path, 'Contents/MacOS/settings.ini')
        if os.path.isfile(settings_path):
            os.remove(settings_path)
            print('>> Removed local settings.ini from bundle.')
elif platform.system() == 'Windows':
    try: os.unlink(dir_ + '/w9xpopen.exe')
    except: pass

print('>> Miyamoto! has been frozen !')
