#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto Level Editor — entry point
# Run this file directly: python pyamoto.py

import os
import sys

# Ensure the project root (this file's directory) is on sys.path so that the
# miyamoto package and all root-level libraries (addrlib, bc3, fastyz, etc.) resolve.
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from miyamoto.app import main

main()
