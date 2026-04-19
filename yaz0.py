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
