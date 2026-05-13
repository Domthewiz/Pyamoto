#!/usr/bin/env python3
"""Build the Pyamoto DMG using dmgbuild."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT_DIR)

from globals import MiyamotoVersionFloat
VERSION = str(MiyamotoVersionFloat)

APP_PATH = os.path.join(ROOT_DIR, 'build', 'Pyamoto.app')
DMG_OUT  = os.path.join(ROOT_DIR, f'Pyamoto-v{VERSION}-macOS-universal.dmg')
BG_PATH  = os.path.join(SCRIPT_DIR, 'dmg_background.tiff')

assert os.path.isdir(APP_PATH), f'App bundle not found: {APP_PATH}'
assert os.path.isfile(BG_PATH), f'Background not found: {BG_PATH}'

import dmgbuild

settings = {
    'files':      [APP_PATH],
    'symlinks':   {'Applications': '/Applications'},
    'background': BG_PATH,
    'icon_locations': {
        'Pyamoto.app':  (156, 185),
        'Applications': (456, 185),
    },
    'window_rect': ((200, 120), (600, 350)),
    'icon_size':    100,
    'format':      'UDBZ',
    'compression_level': 9,
}

print(f'Building {DMG_OUT} ...')
dmgbuild.build_dmg(DMG_OUT, f'Pyamoto v{VERSION}', settings=settings)
print(f'Done: {DMG_OUT}')
