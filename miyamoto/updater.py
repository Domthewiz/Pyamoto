#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Pyamoto update checker — checks GitHub releases for available updates.

import json
import threading
import urllib.request
import webbrowser

from PyQt5 import QtCore, QtWidgets

from . import globals
from .misc import setting

GITHUB_REPO = 'Zenith-Team/Pyamoto'
_API_BASE = f'https://api.github.com/repos/{GITHUB_REPO}/releases'
_API_RECENT = f'{_API_BASE}?per_page=10'
DOWNLOADS_URL = f'https://github.com/{GITHUB_REPO}/releases'

_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'Pyamoto-updater',
}


class _UpdateChecker(QtCore.QObject):
    update_found = QtCore.pyqtSignal(str, str)  # current_version, latest_version

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            if globals.MiyamotoReleaseType == 'nightly':
                self._check_nightly()
            else:
                self._check_release()
        except Exception:
            pass

    def _fetch(self, url):
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _check_nightly(self):
        releases = self._fetch(_API_RECENT)
        nightlies = [r for r in releases
                     if r.get('prerelease') and r['tag_name'].startswith('nightly-')]
        if not nightlies:
            return
        # Tag format: nightly-YYYY-MM-DD-<sha>
        latest_sha = nightlies[0]['tag_name'].rsplit('-', 1)[-1]
        current_sha = globals.MiyamotoVersion
        if latest_sha != current_sha:
            self.update_found.emit(current_sha, latest_sha)

    def _check_release(self):
        latest = self._fetch(f'{_API_BASE}/latest')
        latest_ver = latest['tag_name'].lstrip('v')
        current_ver = globals.MiyamotoVersion.lstrip('v')
        if latest_ver != current_ver:
            self.update_found.emit(current_ver, latest_ver)


# Kept alive for the duration of the process
_checker: _UpdateChecker | None = None


def check_for_updates():
    """Start a background update check if the user has it enabled."""
    if not setting('CheckForUpdates', True):
        return
    global _checker
    _checker = _UpdateChecker()
    _checker.update_found.connect(_show_dialog)
    _checker.start()


class _UpdateDialog(QtWidgets.QDialog):
    def __init__(self, current: str, latest: str, is_nightly: bool, parent=None):
        super().__init__(parent)
        kind = 'Nightly ' if is_nightly else ''
        article = 'A' if is_nightly else 'An'
        self.setWindowTitle(f'Pyamoto {kind}Update Available')
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.setFixedWidth(380)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Minimum,
        )

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 22, 24, 20)

        # ── Headline ────────────────────────────────────────────────────────
        headline = QtWidgets.QLabel(f'{article} {kind.lower()}update is available')
        headline_font = headline.font()
        headline_font.setPointSize(headline_font.pointSize() + 3)
        headline_font.setBold(True)
        headline.setFont(headline_font)
        root.addWidget(headline)

        # ── Version pill ─────────────────────────────────────────────────────
        pill = QtWidgets.QFrame()
        pill.setObjectName('updatePill')
        pill.setFrameShape(QtWidgets.QFrame.StyledPanel)
        # Object-name selector ensures the border only hits the pill frame,
        # not any child labels that would otherwise inherit it.
        pill.setStyleSheet(
            '#updatePill {'
            '  background: palette(base);'
            '  border: 1px solid palette(mid);'
            '  border-radius: 8px;'
            '}'
        )

        bold_font = self.font()
        bold_font.setBold(True)

        cur_lbl = QtWidgets.QLabel(current)
        cur_lbl.setFont(bold_font)
        cur_lbl.setAlignment(QtCore.Qt.AlignCenter)

        arrow_lbl = QtWidgets.QLabel('→')
        arrow_lbl.setAlignment(QtCore.Qt.AlignCenter)

        new_lbl = QtWidgets.QLabel(latest)
        new_lbl.setFont(bold_font)
        new_lbl.setAlignment(QtCore.Qt.AlignCenter)

        pill_layout = QtWidgets.QHBoxLayout(pill)
        pill_layout.setContentsMargins(16, 10, 16, 10)
        pill_layout.setSpacing(6)
        pill_layout.addStretch()
        pill_layout.addWidget(cur_lbl)
        pill_layout.addWidget(arrow_lbl)
        pill_layout.addWidget(new_lbl)
        pill_layout.addStretch()
        root.addWidget(pill)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_box = QtWidgets.QDialogButtonBox()
        cancel = btn_box.addButton('Cancel', QtWidgets.QDialogButtonBox.RejectRole)
        cancel.setAutoDefault(False)
        download = btn_box.addButton('Go to downloads', QtWidgets.QDialogButtonBox.AcceptRole)
        download.setDefault(True)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)


def _show_dialog(current: str, latest: str):
    is_nightly = globals.MiyamotoReleaseType == 'nightly'
    dlg = _UpdateDialog(current, latest, is_nightly, globals.mainWindow)
    if dlg.exec_() == QtWidgets.QDialog.Accepted:
        webbrowser.open(DOWNLOADS_URL)
