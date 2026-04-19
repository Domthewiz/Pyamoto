#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Addrlib
# Copyright © 2018 AboodXD

# Addrlib
# A Python/Cython Address Library for Wii U textures.

try:
    from . import addrlib_cy as addrlib
except ImportError:
    print("Warning: Addrlib Cython extension not found. Falling back to Python.")
    from . import addrlib

# Define the functions that can be used
getDefaultGX2TileMode = addrlib.getDefaultGX2TileMode
deswizzle = addrlib.deswizzle
swizzle = addrlib.swizzle
surfaceGetBitsPerPixel = addrlib.surfaceGetBitsPerPixel
getSurfaceInfo = addrlib.getSurfaceInfo
