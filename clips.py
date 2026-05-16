#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt

import globals

CLIPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clips.json')
PREVIEW_MAX = 64


class Clip:
    """A saved MiyamotoClip with a name and rendered thumbnail preview."""

    def __init__(self, name='', miyamoto_clip=''):
        self.name = name
        self.miyamoto_clip = miyamoto_clip
        self.preview = None  # QPixmap — rendered lazily on first paint

    # ── Preview rendering ─────────────────────────────────────────────────────

    def ensure_preview(self):
        """Renders and caches the preview if not yet done. Safe to call any time."""
        if self.preview is not None:
            return
        mw = getattr(globals, 'mainWindow', None)
        if mw is None:
            return
        try:
            self.preview = self._render_preview(mw)
        except Exception:
            self.preview = QtGui.QPixmap()  # empty — give up gracefully

    def invalidate_preview(self):
        """Forces a re-render on the next paint."""
        self.preview = None

    def _render_preview(self, mw):
        layers, sprites = mw.getEncodedObjects(self.miyamoto_clip, False)

        minX = minY = float('inf')
        maxX = maxY = float('-inf')

        for spr in sprites:
            br = spr.getFullRect()
            x1, y1 = br.topLeft().x(), br.topLeft().y()
            x2, y2 = x1 + br.width(), y1 + br.height()
            minX = min(minX, x1); maxX = max(maxX, x2)
            minY = min(minY, y1); maxY = max(maxY, y2)

        for layer in layers:
            for obj in layer:
                x1 = obj.objx * globals.TileWidth
                y1 = obj.objy * globals.TileWidth
                x2 = x1 + obj.width * globals.TileWidth
                y2 = y1 + obj.height * globals.TileWidth
                minX = min(minX, x1); maxX = max(maxX, x2)
                minY = min(minY, y1); maxY = max(maxY, y2)

        if not (minX < maxX and minY < maxY):
            return QtGui.QPixmap()

        offsetX = int(minX // globals.TileWidth) * globals.TileWidth
        offsetY = int(minY // globals.TileWidth) * globals.TileWidth
        drawOffX = offsetX - minX
        drawOffY = offsetY - minY

        for spr in sprites:
            spr.objx -= offsetX / (globals.TileWidth / 16)
            spr.objy -= offsetY / (globals.TileWidth / 16)
        for layer in layers:
            for obj in layer:
                obj.objx -= offsetX // globals.TileWidth
                obj.objy -= offsetY // globals.TileWidth

        pw = max(1, int(maxX - minX))
        ph = max(1, int(maxY - minY))
        pix = QtGui.QPixmap(pw, ph)
        pix.fill(Qt.transparent)
        painter = QtGui.QPainter(pix)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        objw = int(pw // globals.TileWidth) + 1
        objh = int(ph // globals.TileWidth) + 1

        for layer in reversed(layers):
            tmap = [[-1] * objw for _ in range(objh)]
            for obj in layer:
                sx, sy = int(obj.objx), int(obj.objy)
                dy = sy
                for row in obj.objdata:
                    if 0 <= dy < objh:
                        for i, tile in enumerate(row):
                            dx = sx + i
                            if tile > 0 and 0 <= dx < objw:
                                tmap[dy][dx] = tile
                    dy += 1
            for ry, row in enumerate(tmap):
                for rx, tile in enumerate(row):
                    if tile > 0 and globals.Tiles[tile] is not None:
                        r = globals.Tiles[tile].main
                        if r is not None:
                            painter.drawPixmap(
                                rx * globals.TileWidth + int(drawOffX),
                                ry * globals.TileWidth + int(drawOffY),
                                r,
                            )

        for spr in sprites:
            offx = (spr.objx + spr.ImageObj.xOffset) * globals.TileWidth / 16 + drawOffX
            offy = (spr.objy + spr.ImageObj.yOffset) * globals.TileWidth / 16 + drawOffY
            painter.save()
            painter.translate(offx, offy)
            spr.paint(painter, None, None, True)
            painter.restore()
            for aux in spr.ImageObj.aux:
                painter.save()
                painter.translate(offx + aux.x(), offy + aux.y())
                aux.paint(painter, None, None)
                painter.restore()

        painter.end()

        if pix.width() > PREVIEW_MAX or pix.height() > PREVIEW_MAX:
            pix = pix.scaled(PREVIEW_MAX, PREVIEW_MAX, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return pix

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self):
        return {'name': self.name, 'data': self.miyamoto_clip}

    @staticmethod
    def from_dict(d):
        return Clip(name=d.get('name', 'Unnamed'), miyamoto_clip=d.get('data', ''))

    # ── Validation helpers ────────────────────────────────────────────────────

    @staticmethod
    def is_valid_string(s):
        return isinstance(s, str) and s.startswith('MiyamotoClip|') and s.endswith('|%')

    @staticmethod
    def sanitize_string(s):
        return s.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')


# ── Persistence ───────────────────────────────────────────────────────────────

def load_clips():
    """Return a list of Clip objects loaded from disk (previews not yet rendered)."""
    if not os.path.exists(CLIPS_FILE):
        return []
    try:
        with open(CLIPS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [Clip.from_dict(d) for d in data if isinstance(d, dict)]
    except Exception:
        return []


def save_clips(clips):
    """Persist a list of Clip objects to disk."""
    try:
        with open(CLIPS_FILE, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in clips], f, indent=2, ensure_ascii=False)
    except Exception:
        pass
