#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto Level Editor
# Copyright (C) 2009-2026 Pyamoto contributors
# This file is part of Pyamoto.

# See LICENSE.txt for more information.

# yaz0.py
# Multiple methods for Yaz0 (de)compression


################################################################
################################################################

import fastyz

def compressFASTYZ(inb, outf):
    """
    Compress the file using fastYZ
    """
    try:
        data = fastyz.compress(inb)

        with open(outf, "wb+") as out:
            out.write(data)

    except:
        return False

    else:
        return True


def decompressFASTYZ(inb):
    """
    Decompress the file using fastYZ
    """
    try:
        data = fastyz.decompress(inb)

    except Exception as e:
        print(f"DEBUG - Decompression failed because: {repr(e)}")
        return None

    else:
        return data
