#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto Level Editor
# Copyright (C) 2009-2026 Pyamoto contributors
# This file is part of Pyamoto.

# See LICENSE.txt for more information.


################################################################
################################################################

############ Imports ############

import json
import os

from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt

if not hasattr(QtWidgets.QGraphicsItem, 'ItemSendsGeometryChanges'):
    # enables itemChange being called on QGraphicsItem
    QtWidgets.QGraphicsItem.ItemSendsGeometryChanges = QtWidgets.QGraphicsItem.GraphicsItemFlag(0x800)

from . import globals

#################################


class LevelScene(QtWidgets.QGraphicsScene):
    """
    GraphicsScene subclass for the level scene
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.setBackgroundBrush(QtGui.QBrush(globals.theme.color('bg')))

    def drawForeground(self, painter, rect):
        """
        Draw a foreground grid (only called when taking a screenshot)
        """
        drawForegroundGrid(painter, rect)

    def drawBackground(self, painter, rect):
        """
        Draws the background (does nothing since tiles are now rendered by ObjectItems)
        """
        super().drawBackground(painter, rect)


class HexSpinBox(QtWidgets.QSpinBox):
    class HexValidator(QtGui.QValidator):
        def __init__(self, min, max):
            super().__init__()
            self.valid = set('0123456789abcdef')
            self.min = min
            self.max = max

        def validate(self, input, pos):
            try:
                input = str(input).lower()
            except Exception:
                return (self.Invalid, input, pos)
            valid = self.valid

            for char in input:
                if char not in valid:
                    return (self.Invalid, input, pos)

            try:
                value = int(input, 16)
            except ValueError:
                # If value == '' it raises ValueError
                return (self.Invalid, input, pos)

            if value < self.min or value > self.max:
                return (self.Intermediate, input, pos)

            return (self.Acceptable, input, pos)

    def __init__(self, format='%04X', *args):
        self.format = format
        super().__init__(*args)
        self.validator = self.HexValidator(self.minimum(), self.maximum())

    def setMinimum(self, value):
        self.validator.min = value
        QtWidgets.QSpinBox.setMinimum(self, value)

    def setMaximum(self, value):
        self.validator.max = value
        QtWidgets.QSpinBox.setMaximum(self, value)

    def setRange(self, min, max):
        self.validator.min = min
        self.validator.max = max
        QtWidgets.QSpinBox.setMinimum(self, min)
        QtWidgets.QSpinBox.setMaximum(self, max)

    def validate(self, text, pos):
        return self.validator.validate(text, pos)

    def textFromValue(self, value):
        return self.format % value

    def valueFromText(self, value):
        return int(str(value), 16)


class SpriteDefinition:
    """
    Stores and manages the data info for a specific sprite
    """

    def __init__(self):
        self.id = -1
        self.string_id = None
        self.name = ""
        self.fields = []
        self.notes = None
        self.relatedObjFiles = None

    class ListPropertyModel(QtCore.QAbstractListModel):
        """
        Contains all the possible values for a list property on a sprite
        """

        def __init__(self, entries, existingLookup, max):
            """
            Constructor
            """
            super().__init__()
            self.entries = entries
            self.existingLookup = existingLookup
            self.max = max

        def rowCount(self, parent=None):
            """
            Required by Qt
            """
            return len(self.entries)

        def data(self, index, role=Qt.DisplayRole):
            """
            Get what we have for a specific row
            """
            if not index.isValid():
                return None

            n = index.row()
            if n < 0 or n >= len(self.entries):
                return None

            if role == Qt.DisplayRole:
                return '%d: %s' % self.entries[n]

            return None

    def loadFrom(self, elem):
        """
        Loads in all the field data from an XML node
        """
        self.fields = []
        fields = self.fields

        for field in elem:
            if field.tag not in ['checkbox', 'list', 'value', 'bitfield']: continue

            attribs = field.attrib

            if 'comment' in attribs:
                comment = '<b>[name]</b>: [note]'.replace('[name]', str(attribs['title'])).replace('[note]', str(attribs['comment']))
            else:
                comment = None

            if field.tag == 'checkbox':
                # parameters: title, bit, mask, comment, id_type, category
                if 'nybble' in attribs:
                    sbit = attribs['nybble']
                    sft = 2

                else:
                    sbit = attribs['bit']
                    sft = 0

                if not '-' in sbit:
                    if not sft:
                        # just 1 bit
                        bit = int(sbit)

                    else:
                        # just 4 bits
                        bit = (((int(sbit) - 1) << 2) + 1, (int(sbit) << 2) + 1)

                else:
                    # different number of bits
                    getit = sbit.split('-')
                    bit = (((int(getit[0]) - 1) << sft) + 1, (int(getit[1]) << sft) + 1)

                if 'mask' in attribs:
                    mask = int(attribs['mask'])

                else:
                    mask = 1

                fields.append((0, attribs['title'], bit, mask, comment, None, attribs.get('category', None)))

            elif field.tag == 'list':
                # parameters: title, bit, model, comment
                if 'nybble' in attribs:
                    sbit = attribs['nybble']
                    sft = 2

                else:
                    sbit = attribs['bit']
                    sft = 0

                if not '-' in sbit:
                    if not sft:
                        # just 1 bit
                        bit = int(sbit)
                        max = 2

                    else:
                        # just 4 bits
                        bit = (((int(sbit) - 1) << 2) + 1, (int(sbit) << 2) + 1)
                        max = 16

                else:
                    # different number of bits
                    getit = sbit.split('-')
                    bit = (((int(getit[0]) - 1) << sft) + 1, (int(getit[1]) << sft) + 1)
                    max = 1 << (bit[1] - bit[0])

                entries = []
                existing = [None for i in range(max)]
                for e in field:
                    if e.tag != 'entry': continue

                    i = int(e.attrib['value'])
                    entries.append((i, e.text))
                    existing[i] = True

                fields.append(
                    (1, attribs['title'], bit, SpriteDefinition.ListPropertyModel(entries, existing, max), comment, None, attribs.get('category', None)))

            elif field.tag == 'value':
                # parameters: title, bit, max, comment
                if 'nybble' in attribs:
                    sbit = attribs['nybble']
                    sft = 2

                else:
                    sbit = attribs['bit']
                    sft = 0

                if not '-' in sbit:
                    if not sft:
                        # just 1 bit
                        bit = int(sbit)
                        max = 2

                    else:
                        # just 4 bits
                        bit = (((int(sbit) - 1) << 2) + 1, (int(sbit) << 2) + 1)
                        max = 16

                else:
                    # different number of bits
                    getit = sbit.split('-')
                    bit = (((int(getit[0]) - 1) << sft) + 1, (int(getit[1]) << sft) + 1)
                    max = 1 << (bit[1] - bit[0])

                id_type = attribs.get('id_type', None)
                fields.append((2, attribs['title'], bit, max, comment, id_type, attribs.get('category', None)))

            elif field.tag == 'bitfield':
                # parameters: title, startbit, bitnum, comment, id_type, category
                startbit = int(attribs['startbit'])
                bitnum = int(attribs['bitnum'])

                fields.append((3, attribs['title'], startbit, bitnum, comment, None, attribs.get('category', None)))


def extract_field_value(data, bit):
    """
    Extract a value from sprite data bytes given the bit specification used in
    field tuples (int for single bit, tuple (start, end) for a range, 1-indexed LTR BE).
    Shared between PropertyDecoder and IDValuePropertyDecoder.collect_used_ids().
    """
    if isinstance(bit, tuple):
        if bit[1] == bit[0] + 7 and bit[0] & 1 == 1:
            return data[(bit[0] - 1) >> 3]
        value = 0
        for n in range(bit[0], bit[1]):
            n -= 1
            value = (value << 1) | ((data[n >> 3] >> (7 - (n & 7))) & 1)
        return value
    else:
        b = bit - 1
        if (b >> 3) >= len(data):
            return 0
        return (data[b >> 3] >> (7 - (b & 7))) & 1



class Metadata:
    """
    Class for the new level metadata system
    """

    # This new system is much more useful and flexible than the old
    # system, but is incompatible with older versions of Miyamoto.
    # They will fail to understand the data, and skip it like it
    # doesn't exist. The new system is written with forward-compatibility
    # in mind. Thus, when newer versions of Miyamoto are created
    # with new metadata values, they will be easily able to add to
    # the existing ones. In addition, the metadata system is lossless,
    # so unrecognized values will be preserved when you open and save.

    # Type values:
    # 0 = binary
    # 1 = string
    # 2+ = undefined as of now - future Miyamotos can use them
    # Theoretical limit to type values is 4,294,967,296

    def __init__(self, data=None):
        """
        Creates a metadata object with the data given
        """
        self.DataDict = {}
        if not data or data[0:4] != b'MD2_': return

        # Iterate through the data
        idx = 4
        while idx < len(data) - 4:

            # Read the next (first) four bytes - the key length
            rawKeyLen = data[idx:idx + 4]
            idx += 4

            keyLen = (rawKeyLen[0] << 24) | (rawKeyLen[1] << 16) | (rawKeyLen[2] << 8) | rawKeyLen[3]

            # Read the next (key length) bytes - the key (as a str)
            rawKey = data[idx:idx + keyLen]
            idx += keyLen

            key = ''
            for b in rawKey: key += chr(b)

            # Read the next four bytes - the number of type entries
            rawTypeEntries = data[idx:idx + 4]
            idx += 4

            typeEntries = (rawTypeEntries[0] << 24) | (rawTypeEntries[1] << 16) | (rawTypeEntries[2] << 8) | \
                          rawTypeEntries[3]

            # Iterate through each type entry
            for entry in range(typeEntries):
                # Read the next four bytes - the type
                rawType = data[idx:idx + 4]
                idx += 4

                type = (rawType[0] << 24) | (rawType[1] << 16) | (rawType[2] << 8) | rawType[3]

                # Read the next four bytes - the data length
                rawDataLen = data[idx:idx + 4]
                idx += 4

                dataLen = (rawDataLen[0] << 24) | (rawDataLen[1] << 16) | (rawDataLen[2] << 8) | rawDataLen[3]

                # Read the next (data length) bytes - the data (as bytes)
                entryData = data[idx:idx + dataLen]
                idx += dataLen

                # Add it to typeData
                self.setOtherData(key, type, entryData)

    def binData(self, key):
        """
        Returns the binary data associated with key
        """
        return self.otherData(key, 0)

    def strData(self, key):
        """
        Returns the string data associated with key
        """
        data = self.otherData(key, 1)
        if data is None: return
        s = ''
        for d in data: s += chr(d)
        return s

    def otherData(self, key, type):
        """
        Returns unknown data, with the given type value, associated with key (as binary data)
        """
        if key not in self.DataDict: return
        if type not in self.DataDict[key]: return
        return self.DataDict[key][type]

    def setBinData(self, key, value):
        """
        Sets binary data, overwriting any existing binary data with that key
        """
        self.setOtherData(key, 0, value)

    def setStrData(self, key, value):
        """
        Sets string data, overwriting any existing string data with that key
        """
        data = []
        for char in value: data.append(ord(char))
        self.setOtherData(key, 1, data)

    def setOtherData(self, key, type, value):
        """
        Sets other (binary) data, overwriting any existing data with that key and type
        """
        if key not in self.DataDict: self.DataDict[key] = {}
        self.DataDict[key][type] = value

    def save(self):
        """
        Returns a bytes object that can later be loaded from
        """

        # Sort self.DataDict
        dataDictSorted = []
        for dataKey in self.DataDict: dataDictSorted.append((dataKey, self.DataDict[dataKey]))
        dataDictSorted.sort(key=lambda entry: entry[0])

        data = []

        # Add 'MD2_'
        data.append(ord('M'))
        data.append(ord('D'))
        data.append(ord('2'))
        data.append(ord('_'))

        # Iterate through self.DataDict
        for dataKey, types in dataDictSorted:

            # Add the key length (4 bytes)
            keyLen = len(dataKey)
            data.append(keyLen >> 24)
            data.append((keyLen >> 16) & 0xFF)
            data.append((keyLen >> 8) & 0xFF)
            data.append(keyLen & 0xFF)

            # Add the key (key length bytes)
            for char in dataKey: data.append(ord(char))

            # Sort the types
            typesSorted = []
            for type in types: typesSorted.append((type, types[type]))
            typesSorted.sort(key=lambda entry: entry[0])

            # Add the number of types (4 bytes)
            typeNum = len(typesSorted)
            data.append(typeNum >> 24)
            data.append((typeNum >> 16) & 0xFF)
            data.append((typeNum >> 8) & 0xFF)
            data.append(typeNum & 0xFF)

            # Iterate through typesSorted
            for type, typeData in typesSorted:

                # Add the type (4 bytes)
                data.append(type >> 24)
                data.append((type >> 16) & 0xFF)
                data.append((type >> 8) & 0xFF)
                data.append(type & 0xFF)

                # Add the data length (4 bytes)
                dataLen = len(typeData)
                data.append(dataLen >> 24)
                data.append((dataLen >> 16) & 0xFF)
                data.append((dataLen >> 8) & 0xFF)
                data.append(dataLen & 0xFF)

                # Add the data (data length bytes)
                for d in typeData: data.append(d)

        if bytes(data) == b'MD2_':
            return[]

        return data


class BGName:
    def __init__(self, name, trans):
        self.name = name
        self.trans = trans

    def __eq__(self, other):
        return other in (self.name, self.trans)

    @staticmethod
    def index(name):
        try:
            return globals.names_bg.index(name)

        except ValueError:
            return len(globals.names_bg) - 1

    @staticmethod
    def getNameForTrans(trans):
        return globals.names_bg[BGName.index(trans)].name

    @staticmethod
    def getTransAll():
        return [bg.trans for bg in globals.names_bg]

    class Custom:
        def __init__(self):
            self.name = ''
            self.trans = 'Custom filename...'

        def __eq__(self, other):
            return False


def clipStr(text, idealWidth, font=None):
    """
    Returns a shortened string, or None if it need not be shortened
    """
    if font is None: font = QtGui.QFont()
    width = QtGui.QFontMetrics(font).width(text)
    if width <= idealWidth: return None

    while width > idealWidth:
        text = text[:-1]
        width = QtGui.QFontMetrics(font).width(text)

    return text


class JsonSettings:
    """JSON-backed settings store. Replaces QSettings; stores data in the
    platform user-data directory so settings.json never lands in the repo."""

    _QBYTEARRAY_KEY = '__qba__'

    def __init__(self, path):
        self._path = path
        self._data = {}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._load()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                # Strip legacy typeof() metadata keys written by the old QSettings approach
                self._data = {k: v for k, v in self._data.items()
                              if not (k.startswith('typeof(') and k.endswith(')'))}
            except Exception:
                self._data = {}

    def sync(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── QSettings-compatible interface ────────────────────────────────────────

    def contains(self, key):
        return key in self._data

    def value(self, key, default=None, type_=None):
        if key not in self._data:
            return default
        val = self._data[key]
        if isinstance(val, dict) and self._QBYTEARRAY_KEY in val:
            return QtCore.QByteArray(bytes.fromhex(val[self._QBYTEARRAY_KEY]))
        return val

    def setValue(self, key, value):
        if isinstance(value, QtCore.QByteArray):
            self._data[key] = {self._QBYTEARRAY_KEY: bytes(value).hex()}
        else:
            self._data[key] = value

    def remove(self, key):
        self._data.pop(key, None)


def setting(name, default=None):
    return globals.settings.value(name, default)


def setSetting(name, value):
    globals.settings.setValue(name, value)
    globals.settings.sync()


def hasLevelNameSources():
    """Returns True if at least one game path or mod-with-path exists for Open Level by Name."""
    if setting('GamePath', ''):
        return True
    for key, val in list(globals.settings._data.items()):
        if key.startswith('GamePath_') and not key.startswith('GamePath_mod_') and val:
            return True
    mods = setting('LastMods') or []
    if isinstance(mods, str):
        mods = [mods]
    for folder in mods:
        if setting('GamePath_mod_' + folder, ''):
            return True
    return False


def SetGamePath(newpath):
    """
    Sets the NSMBU game path
    """
    # you know what's fun?
    # isValidGamePath crashes in os.path.join if QString is used..
    # so we must change it to a Python string manually
    globals.gamedef.SetGamePath(str(newpath))


_checkerboard_cache = {}  # size -> QPixmap


def drawForegroundGrid(painter, rect):
    """
    Draws a foreground grid
    """
    if globals.GridType is None:
        return

    Zoom = globals.mainWindow.ZoomLevel
    drawLine = lambda x1, y1, x2, y2: painter.drawLine(round(x1), round(y1), round(x2), round(y2))
    GridColor = globals.theme.color('grid')

    if globals.GridType == 'grid':  # draw a classic grid
        startx = rect.x()
        startx -= (startx % globals.TileWidth)
        endx = startx + rect.width() + globals.TileWidth

        starty = rect.y()
        starty -= (starty % globals.TileWidth)
        endy = starty + rect.height() + globals.TileWidth

        x = startx - globals.TileWidth
        while x <= endx:
            x += globals.TileWidth
            if x % (globals.TileWidth * 8) == 0:
                painter.setPen(QtGui.QPen(GridColor, 2 * globals.TileWidth / 24, Qt.DashLine))
                drawLine(x, starty, x, endy)
            elif x % (globals.TileWidth * 4) == 0:
                if Zoom < 25: continue
                painter.setPen(QtGui.QPen(GridColor, 1 * globals.TileWidth / 24, Qt.DashLine))
                drawLine(x, starty, x, endy)
            else:
                if Zoom < 50: continue
                painter.setPen(QtGui.QPen(GridColor, 1 * globals.TileWidth / 24, Qt.DotLine))
                drawLine(x, starty, x, endy)

        y = starty - globals.TileWidth
        while y <= endy:
            y += globals.TileWidth
            if y % (globals.TileWidth * 8) == 0:
                painter.setPen(QtGui.QPen(GridColor, 2 * globals.TileWidth / 24, Qt.DashLine))
                drawLine(startx, y, endx, y)
            elif y % (globals.TileWidth * 4) == 0 and Zoom >= 25:
                painter.setPen(QtGui.QPen(GridColor, 1 * globals.TileWidth / 24, Qt.DashLine))
                drawLine(startx, y, endx, y)
            elif Zoom >= 50:
                painter.setPen(QtGui.QPen(GridColor, 1 * globals.TileWidth / 24, Qt.DotLine))
                drawLine(startx, y, endx, y)

    else:  # draw a checkerboard
        L = 0.2
        D = 0.1  # Change these values to change the checkerboard opacity

        Light = QtGui.QColor(GridColor)
        Dark = QtGui.QColor(GridColor)
        Light.setAlpha(min(round(Light.alpha() * L), 255))
        Dark.setAlpha(min(round(Dark.alpha() * D), 255))

        size = globals.TileWidth if Zoom >= 50 else globals.TileWidth * 8

        if size not in _checkerboard_cache:
            _checkerboard_cache.clear()
            board = QtGui.QPixmap(8 * size, 8 * size)
            board.fill(QtGui.QColor(0, 0, 0, 0))
            p = QtGui.QPainter(board)
            p.setPen(Qt.NoPen)

            p.setBrush(QtGui.QBrush(Light))
            for x, y in ((0, size), (size, 0)):
                p.drawRect(x + (4 * size), y, size, size)
                p.drawRect(x + (4 * size), y + (2 * size), size, size)
                p.drawRect(x + (6 * size), y, size, size)
                p.drawRect(x + (6 * size), y + (2 * size), size, size)

                p.drawRect(x, y + (4 * size), size, size)
                p.drawRect(x, y + (6 * size), size, size)
                p.drawRect(x + (2 * size), y + (4 * size), size, size)
                p.drawRect(x + (2 * size), y + (6 * size), size, size)
            p.setBrush(QtGui.QBrush(Dark))
            for x, y in ((0, 0), (size, size)):
                p.drawRect(x, y, size, size)
                p.drawRect(x, y + (2 * size), size, size)
                p.drawRect(x + (2 * size), y, size, size)
                p.drawRect(x + (2 * size), y + (2 * size), size, size)

                p.drawRect(x, y + (4 * size), size, size)
                p.drawRect(x, y + (6 * size), size, size)
                p.drawRect(x + (2 * size), y + (4 * size), size, size)
                p.drawRect(x + (2 * size), y + (6 * size), size, size)

                p.drawRect(x + (4 * size), y, size, size)
                p.drawRect(x + (4 * size), y + (2 * size), size, size)
                p.drawRect(x + (6 * size), y, size, size)
                p.drawRect(x + (6 * size), y + (2 * size), size, size)

                p.drawRect(x + (4 * size), y + (4 * size), size, size)
                p.drawRect(x + (4 * size), y + (6 * size), size, size)
                p.drawRect(x + (6 * size), y + (4 * size), size, size)
                p.drawRect(x + (6 * size), y + (6 * size), size, size)

            del p
            _checkerboard_cache[size] = board

        painter.drawTiledPixmap(rect, _checkerboard_cache[size], QtCore.QPointF(rect.x(), rect.y()))
