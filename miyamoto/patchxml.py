#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import xml.etree.ElementTree as ET


class PatchXmlEditor:
    """
    Helper for reading and writing XML files inside a userdata patch directory.
    Designed to be expanded with additional patch-XML manipulation methods.
    """

    def __init__(self, user_patch_dir):
        """user_patch_dir: absolute path to userdata/patches/<mod_folder>/"""
        self.patch_dir = user_patch_dir

    # ── Public paths ──────────────────────────────────────────────────────────

    def levelnames_path(self):
        return os.path.join(self.patch_dir, 'levelnames.xml')

    # ── Levelnames ────────────────────────────────────────────────────────────

    def set_level_name(self, level_code, level_name):
        """
        Set the display name for a level in this patch's levelnames.xml.
        Creates the file if it doesn't exist.  Updates the entry in-place if
        the level_code already appears, otherwise appends it to a
        'Custom Names' category.
        """
        ln_path = self.levelnames_path()

        if os.path.isfile(ln_path):
            tree = ET.parse(ln_path)
            root = tree.getroot()
        else:
            root = ET.Element('levels')

        # Update an existing <level file="..." /> entry
        for level_el in root.iter('level'):
            if level_el.get('file') == level_code:
                level_el.set('name', level_name)
                self._save(root, ln_path)
                return

        # No existing entry — append to the 'Custom Names' category
        custom_cat = next(
            (c for c in root
             if c.tag == 'category' and c.get('name') == 'Custom Names'),
            None,
        )
        if custom_cat is None:
            custom_cat = ET.SubElement(root, 'category')
            custom_cat.set('name', 'Custom Names')

        level_el = ET.SubElement(custom_cat, 'level')
        level_el.set('file', level_code)
        level_el.set('name', level_name)

        self._save(root, ln_path)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _save(self, root, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._indent(root)
        ET.ElementTree(root).write(path, xml_declaration=True, encoding='unicode')

    @staticmethod
    def _indent(elem, level=0):
        """Pretty-print indentation (in-place)."""
        pad = '\n' + '    ' * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = pad + '    '
            if not elem.tail or not elem.tail.strip():
                elem.tail = pad
            last = None
            for child in elem:
                PatchXmlEditor._indent(child, level + 1)
                last = child
            if last is not None and (not last.tail or not last.tail.strip()):
                last.tail = pad
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = pad
