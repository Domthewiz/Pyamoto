#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto Level Editor
# Copyright (C) 2009-2026 Pyamoto contributors
# This file is part of Pyamoto.

# See LICENSE.txt for more information.


################################################################
################################################################

import json, os, platform, sys

def _load_project_info():
    if getattr(sys, 'frozen', False):
        # cx_Freeze: include_files land next to the executable
        base = os.path.dirname(sys.executable)
    else:
        # Development: project root is two levels up from miyamoto/globals.py
        base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    _proj = os.path.join(base, 'project.json')
    with open(_proj, 'r', encoding='utf-8') as _f:
        return json.load(_f)

_project = _load_project_info()
MiyamotoID = _project['id']
MiyamotoVersion = _project['version']
MiyamotoVersionFloat = float(_project['version_float'])

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
CategorizedSpriteData = False

SPRITE_PREVIEW_DISABLED = 0
SPRITE_PREVIEW_SMALL = 24
SPRITE_PREVIEW_MEDIUM = 40
SPRITE_PREVIEW_LARGE = 56
SpriteListPreviewSize = SPRITE_PREVIEW_DISABLED
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
if getattr(sys, 'frozen', False):
    miyamoto_path = os.path.dirname(sys.executable).replace("\\", "/")
else:
    miyamoto_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))).replace("\\", "/")

def _user_data_path():
    if platform.system() == 'Darwin':
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Pyamoto')
    elif platform.system() == 'Windows':
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Pyamoto')
    else:
        xdg = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
        return os.path.join(xdg, 'Pyamoto')

user_data_path = _user_data_path()

cython_available = False
err_msg = ''
names_bg = []

# Game enums
FileExtentions = ('.szs', '.sarc')
FileExtensions_NSMBUDX = ('.sarc',)
Pa0Tilesets = ('Pa0_jyotyu', 'Pa0_jyotyu_chika',
               'Pa0_jyotyu_yougan', 'Pa0_jyotyu_yougan2')
