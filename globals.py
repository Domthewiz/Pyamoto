#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto Level Editor
# Copyright (C) 2009-2026 Pyamoto contributors
# This file is part of Pyamoto.

# See LICENSE.txt for more information.


################################################################
################################################################

import os, sys

MiyamotoID = 'Pyamoto level editor'
MiyamotoVersion = '1.0'
MiyamotoVersionFloat = 1.0

generateStringsXML = False
app = None
mainWindow = None
trans = None
settingsArea = None
LevelScene = None
LevelOverview = None
UndoManager = None
settings = None
gamedef = None
theme = None
compressed = False
LevelNames = None
TilesetNames = None
ObjDesc = None
SpriteCategories = None
SpriteListData = None
EntranceTypeNames = None
Tiles = None  # 0x200 tiles per tileset, plus 64 for each type of override
TilesetAnimTimer = None
Overrides = None  # 320 tiles, this is put into Tiles usually
TileBehaviours = None
ObjectDefinitions = None  # 4 tilesets
ObjectAllDefinitions = None
ObjectAllCollisions = None
ObjectAllImages = None
ObjectAddedtoEmbedded = None
TilesetsAnimating = False
Area = None
Dirty = False
DirtyOverride = 0
AutoSaveDirty = False
OverrideSnapping = False
PlaceObjectFullSize = False
CurrentPaintType = -1
CurrentObject = -1
CurrentSprite = -1
CurrentLayer = 1
CurrentArea = 1
Layer0Shown = True
Layer1Shown = True
Layer2Shown = True
SpritesShown = True
SpriteImagesShown = True
RealViewEnabled = False
LocationsShown = True
CommentsShown = True
PathsShown = True
ObjectsFrozen = False
SpritesFrozen = False
EntrancesFrozen = False
LocationsFrozen = False
PathsFrozen = False
CommentsFrozen = False
OverwriteSprite = False
PaintingEntrance = None
PaintingEntranceListIndex = None
NumberFont = None
GridType = None
RestoredFromAutoSave = False
AutoSavePath = ''
AutoSaveData = b''
AutoOpenScriptEnabled = False
ExceptionRaised = False
CurrentLevelNameForAutoOpenScript = 'AAAAAAAAAAAAAAAAAAAAAAAAAA'
TileWidth = 60
szsData = {}
UseRGBA8 = False
NumSprites = 0
TilesetEdited = False
IsNSMBUDX = False
miyamoto_path = os.path.dirname(os.path.realpath(sys.argv[0])).replace("\\", "/")
cython_available = False
err_msg = ''
names_bg = []

# Game enums
FileExtentions = ('.szs', '.sarc')
FileExtensions_NSMBUDX = ('.sarc',)
Pa0Tilesets = ('Pa0_jyotyu', 'Pa0_jyotyu_chika',
               'Pa0_jyotyu_yougan', 'Pa0_jyotyu_yougan2')
