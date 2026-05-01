from PyQt5 import QtCore
import globals
from verifications import SetDirty

class Command:
    """Base class for all undoable commands."""
    def __init__(self, description=""):
        self.description = description

    def undo(self):
        raise NotImplementedError

    def redo(self):
        raise NotImplementedError

    @staticmethod
    def _set_item_pos(item, x, y):
        """Helper to set item position correctly across different item types."""
        if hasattr(item, 'setNewObjPos'):
            item.setNewObjPos(x, y)
        else:
            item.objx, item.objy = x, y
            # ObjectItem/LocationItem use different scaling
            from items import ObjectItem, LocationItem
            if isinstance(item, ObjectItem):
                item.setPos(x * globals.TileWidth, y * globals.TileWidth)
            else:
                # LocationItem/SpriteItem-like (locations/paths use pixel-based objx/objy)
                item.setPos(x * (globals.TileWidth / 16), y * (globals.TileWidth / 16))


class CompoundCommand(Command):
    """Executes a sequence of commands."""
    def __init__(self, description=""):
        super().__init__(description)
        self.commands = []

    def add_command(self, command):
        self.commands.append(command)

    def undo(self):
        for cmd in reversed(self.commands):
            cmd.undo()

    def redo(self):
        for cmd in self.commands:
            cmd.redo()


class UndoManager(QtCore.QObject):
    """Manages the undo and redo stacks."""
    stackChanged = QtCore.pyqtSignal()

    def __init__(self, max_history=100):
        super().__init__()
        self.max_history = max_history
        self.undo_stack = []
        self.redo_stack = []
        self._current_compound = None

    def push(self, command):
        """Executes a command and adds it to the undo stack."""
        command.redo()
        
        if self._current_compound is not None:
            self._current_compound.add_command(command)
        else:
            self.undo_stack.append(command)
            if len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
            self._update_ui()

    def begin_compound(self, description):
        """Starts grouping commands into a CompoundCommand."""
        if self._current_compound is None:
            self._current_compound = CompoundCommand(description)

    def end_compound(self):
        """Ends grouping and pushes the CompoundCommand if it has sub-commands."""
        if self._current_compound is not None:
            cmd = self._current_compound
            self._current_compound = None
            if cmd.commands:
                self.undo_stack.append(cmd)
                if len(self.undo_stack) > self.max_history:
                    self.undo_stack.pop(0)
                self.redo_stack.clear()
                self._update_ui()

    def undo(self):
        if self.canUndo():
            cmd = self.undo_stack.pop()
            cmd.undo()
            self.redo_stack.append(cmd)
            self._update_ui()
            SetDirty()

    def redo(self):
        if self.canRedo():
            cmd = self.redo_stack.pop()
            cmd.redo()
            self.undo_stack.append(cmd)
            self._update_ui()
            SetDirty()

    def canUndo(self):
        return len(self.undo_stack) > 0

    def canRedo(self):
        return len(self.redo_stack) > 0

    def undoText(self):
        return self.undo_stack[-1].description if self.canUndo() else ""

    def redoText(self):
        return self.redo_stack[-1].description if self.canRedo() else ""

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._current_compound = None
        self._update_ui()

    def _update_ui(self):
        """Emits signal to update UI."""
        self.stackChanged.emit()


# -----------------------------------------------------------------------------
# Specific Commands
# -----------------------------------------------------------------------------

# Object Commands
class MoveObjectsCommand(Command):
    def __init__(self, moves):
        super().__init__("Move Objects")
        # moves is a list of tuples: (obj, old_pos, new_pos)
        self.moves = moves

    def undo(self):
        for obj, old_pos, _ in self.moves:
            self._set_item_pos(obj, old_pos[0], old_pos[1])
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for obj, _, new_pos in self.moves:
            self._set_item_pos(obj, new_pos[0], new_pos[1])
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class ResizeObjectCommand(Command):
    def __init__(self, obj, old_geom, new_geom):
        super().__init__("Resize Object")
        self.obj = obj
        # geom is (x, y, w, h)
        self.old_geom = old_geom
        self.new_geom = new_geom

    def undo(self):
        self._apply_geom(self.old_geom)

    def redo(self):
        self._apply_geom(self.new_geom)

    def _apply_geom(self, geom):
        x, y, w, h = geom
        self._set_item_pos(self.obj, x, y)
        self.obj.width, self.obj.height = w, h
        self.obj.UpdateRects()
        self.obj.prepareGeometryChange()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class AddObjectCommand(Command):
    def __init__(self, obj, layer_idx, z_value=None):
        super().__init__("Add Object")
        self.obj = obj
        self.layer_idx = layer_idx
        self.z_value = z_value

    def undo(self):
        self.obj.delete()
        if self.obj.scene():
            self.obj.scene().removeItem(self.obj)
            
    def redo(self):
        layer = globals.Area.layers[self.layer_idx]
        layer.append(self.obj)
        self.obj.layer = self.layer_idx
        if self.z_value is not None:
            self.obj.setZValue(self.z_value)
        else:
            self.obj.setZValue(len(layer) - 1 + (self.layer_idx * 10000))
        self.obj.AddToSearchDatabase()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            if self.obj.scene() != globals.mainWindow.scene:
                globals.mainWindow.scene.addItem(self.obj)


class DeleteObjectsCommand(Command):
    def __init__(self, obj_info_list):
        super().__init__("Delete Objects")
        # obj_info_list contains (obj, layer_idx, list_idx, z_value)
        self.obj_info_list = obj_info_list

    def undo(self):
        # Restore in reverse order to maintain indices
        for obj, layer_idx, list_idx, z_value in reversed(self.obj_info_list):
            layer = globals.Area.layers[layer_idx]
            layer.insert(list_idx, obj)
            obj.layer = layer_idx
            obj.setZValue(z_value)
            obj.AddToSearchDatabase()
            
            # Shift Z-values of items after it up
            for i in range(list_idx + 1, len(layer)):
                upd = layer[i]
                upd.setZValue(upd.zValue() + 1)
                
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                globals.mainWindow.scene.addItem(obj)

    def redo(self):
        for obj, _, _, _ in self.obj_info_list:
            obj.delete()
            if obj.scene():
                obj.scene().removeItem(obj)


# Sprite Commands
class MoveSpriteCommand(Command):
    def __init__(self, moves):
        super().__init__("Move Sprites")
        # moves: list of (spr, old_x, old_y, new_x, new_y)
        self.moves = moves

    def undo(self):
        for spr, old_x, old_y, _, _ in self.moves:
            self._set_item_pos(spr, old_x, old_y)
            spr.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for spr, _, _, new_x, new_y in self.moves:
            self._set_item_pos(spr, new_x, new_y)
            spr.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class AddSpriteCommand(Command):
    def __init__(self, spr):
        super().__init__("Add Sprite")
        self.spr = spr
        self.list_idx = -1

    def undo(self):
        if self.spr in globals.Area.sprites:
            self.list_idx = globals.Area.sprites.index(self.spr)
            globals.Area.sprites.remove(self.spr)
            
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            sprlist = globals.mainWindow.spriteList
            globals.mainWindow.UpdateFlag = True
            if self.spr.listitem is not None:
                sprlist.takeItem(sprlist.row(self.spr.listitem))
            globals.mainWindow.UpdateFlag = False
            if self.spr.ImageObj and self.spr.ImageObj.scene():
                self.spr.ImageObj.scene().removeItem(self.spr.ImageObj)
            for aux in self.spr.ImageObj.aux:
                if aux.scene():
                    aux.scene().removeItem(aux)
            if self.spr.scene():
                self.spr.scene().removeItem(self.spr)
            globals.mainWindow.scene.update()

    def redo(self):
        if self.list_idx != -1 and self.list_idx <= len(globals.Area.sprites):
            globals.Area.sprites.insert(self.list_idx, self.spr)
        else:
            globals.Area.sprites.append(self.spr)
            
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.scene.addItem(self.spr)
            mw.scene.addItem(self.spr.ImageObj)
            for aux in self.spr.ImageObj.aux:
                mw.scene.addItem(aux)
                
            mw.UpdateFlag = True
            if self.spr.listitem is not None:
                if self.list_idx != -1 and self.list_idx <= mw.spriteList.count():
                    mw.spriteList.insertItem(self.list_idx, self.spr.listitem)
                else:
                    mw.spriteList.addItem(self.spr.listitem)
            mw.UpdateFlag = False
            mw.scene.update()


class DeleteSpritesCommand(Command):
    def __init__(self, spr_info_list):
        super().__init__("Delete Sprites")
        # spr_info_list: list of (spr, list_idx)
        self.spr_info_list = spr_info_list

    def undo(self):
        for spr, list_idx in reversed(self.spr_info_list):
            globals.Area.sprites.insert(list_idx, spr)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.scene.addItem(spr)
                mw.scene.addItem(spr.ImageObj)
                for aux in spr.ImageObj.aux:
                    mw.scene.addItem(aux)
                mw.UpdateFlag = True
                if spr.listitem is not None:
                    mw.spriteList.insertItem(list_idx, spr.listitem)
                mw.UpdateFlag = False
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for spr, _ in self.spr_info_list:
            if spr in globals.Area.sprites:
                globals.Area.sprites.remove(spr)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.UpdateFlag = True
                if spr.listitem is not None:
                    mw.spriteList.takeItem(mw.spriteList.row(spr.listitem))
                mw.UpdateFlag = False
                if spr.ImageObj and spr.ImageObj.scene():
                    spr.ImageObj.scene().removeItem(spr.ImageObj)
                for aux in spr.ImageObj.aux:
                    if aux.scene():
                        aux.scene().removeItem(aux)
                if spr.scene():
                    spr.scene().removeItem(spr)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class SpriteDataChangedCommand(Command):
    def __init__(self, spr, old_data, new_data):
        super().__init__("Change Sprite Data")
        self.spr = spr
        self.old_data = old_data
        self.new_data = new_data

    def undo(self):
        self.spr.spritedata = self.old_data
        self.spr.UpdateListItem()
        self.spr.UpdateDynamicSizing()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.UpdateModeInfo()

    def redo(self):
        self.spr.spritedata = self.new_data
        self.spr.UpdateListItem()
        self.spr.UpdateDynamicSizing()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.UpdateModeInfo()

# Entrance Commands
class MoveEntranceCommand(Command):
    def __init__(self, moves):
        super().__init__("Move Entrances")
        self.moves = moves

    def undo(self):
        for ent, old_x, old_y, _, _ in self.moves:
            self._set_item_pos(ent, old_x, old_y)
            ent.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for ent, _, _, new_x, new_y in self.moves:
            self._set_item_pos(ent, new_x, new_y)
            ent.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class AddEntranceCommand(Command):
    def __init__(self, ent):
        super().__init__("Add Entrance")
        self.ent = ent
        self.list_idx = -1

    def undo(self):
        if self.ent in globals.Area.entrances:
            self.list_idx = globals.Area.entrances.index(self.ent)
            globals.Area.entrances.remove(self.ent)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.UpdateFlag = True
            if self.ent.listitem is not None:
                mw.entranceList.takeItem(mw.entranceList.row(self.ent.listitem))
            mw.UpdateFlag = False
            if self.ent.scene():
                self.ent.scene().removeItem(self.ent)
            for aux in self.ent.aux:
                if aux.scene():
                    aux.scene().removeItem(aux)
            mw.scene.update()

    def redo(self):
        if self.list_idx != -1 and self.list_idx <= len(globals.Area.entrances):
            globals.Area.entrances.insert(self.list_idx, self.ent)
        else:
            globals.Area.entrances.append(self.ent)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.scene.addItem(self.ent)
            for aux in self.ent.aux:
                mw.scene.addItem(aux)
            mw.UpdateFlag = True
            if self.ent.listitem is not None:
                if self.list_idx != -1 and self.list_idx <= mw.entranceList.count():
                    mw.entranceList.insertItem(self.list_idx, self.ent.listitem)
                else:
                    mw.entranceList.addItem(self.ent.listitem)
            mw.UpdateFlag = False
            mw.scene.update()


class DeleteEntrancesCommand(Command):
    def __init__(self, ent_info_list):
        super().__init__("Delete Entrances")
        # ent_info_list: list of (ent, list_idx)
        self.ent_info_list = ent_info_list

    def undo(self):
        for ent, list_idx in reversed(self.ent_info_list):
            globals.Area.entrances.insert(list_idx, ent)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.scene.addItem(ent)
                for aux in ent.aux:
                    mw.scene.addItem(aux)
                mw.UpdateFlag = True
                if ent.listitem is not None:
                    mw.entranceList.insertItem(list_idx, ent.listitem)
                mw.UpdateFlag = False
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for ent, _ in self.ent_info_list:
            if ent in globals.Area.entrances:
                globals.Area.entrances.remove(ent)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.UpdateFlag = True
                if ent.listitem is not None:
                    mw.entranceList.takeItem(mw.entranceList.row(ent.listitem))
                mw.UpdateFlag = False
                if ent.scene():
                    ent.scene().removeItem(ent)
                for aux in ent.aux:
                    if aux.scene():
                        aux.scene().removeItem(aux)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class EntrancePropertyChangedCommand(Command):
    def __init__(self, ent, old_props, new_props):
        super().__init__("Change Entrance Properties")
        self.ent = ent
        self.old_props = old_props
        self.new_props = new_props

    def undo(self):
        self._apply_props(self.old_props)

    def redo(self):
        self._apply_props(self.new_props)

    def _apply_props(self, props):
        for k, v in props.items():
            setattr(self.ent, k, v)
        if 'enttype' in props:
            self.ent.TypeChange()
        self.ent.update()
        self.ent.UpdateTooltip()
        self.ent.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.UpdateModeInfo()


# Location Commands
class MoveLocationCommand(Command):
    def __init__(self, moves):
        super().__init__("Move Locations")
        self.moves = moves

    def undo(self):
        for loc, old_x, old_y, _, _ in self.moves:
            self._set_item_pos(loc, old_x, old_y)
            loc.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for loc, _, _, new_x, new_y in self.moves:
            self._set_item_pos(loc, new_x, new_y)
            loc.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class ResizeLocationCommand(Command):
    def __init__(self, loc, old_geom, new_geom):
        super().__init__("Resize Location")
        self.loc = loc
        self.old_geom = old_geom
        self.new_geom = new_geom

    def undo(self):
        self._apply_geom(self.old_geom)

    def redo(self):
        self._apply_geom(self.new_geom)

    def _apply_geom(self, geom):
        x, y, w, h = geom
        self._set_item_pos(self.loc, x, y)
        self.loc.width = w
        self.loc.height = h
        self.loc.UpdateRects()
        self.loc.prepareGeometryChange()
        self.loc.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.UpdateModeInfo()


class AddLocationCommand(Command):
    def __init__(self, loc):
        super().__init__("Add Location")
        self.loc = loc
        self.list_idx = -1

    def undo(self):
        if self.loc in globals.Area.locations:
            self.list_idx = globals.Area.locations.index(self.loc)
            globals.Area.locations.remove(self.loc)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.UpdateFlag = True
            if self.loc.listitem is not None:
                mw.locationList.takeItem(mw.locationList.row(self.loc.listitem))
            mw.UpdateFlag = False
            if self.loc.scene():
                self.loc.scene().removeItem(self.loc)
            mw.scene.update()

    def redo(self):
        if self.list_idx != -1 and self.list_idx <= len(globals.Area.locations):
            globals.Area.locations.insert(self.list_idx, self.loc)
        else:
            globals.Area.locations.append(self.loc)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.scene.addItem(self.loc)
            mw.UpdateFlag = True
            if self.loc.listitem is not None:
                if self.list_idx != -1 and self.list_idx <= mw.locationList.count():
                    mw.locationList.insertItem(self.list_idx, self.loc.listitem)
                else:
                    mw.locationList.addItem(self.loc.listitem)
            mw.UpdateFlag = False
            mw.scene.update()


class DeleteLocationsCommand(Command):
    def __init__(self, loc_info_list):
        super().__init__("Delete Locations")
        self.loc_info_list = loc_info_list

    def undo(self):
        for loc, list_idx in reversed(self.loc_info_list):
            globals.Area.locations.insert(list_idx, loc)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.scene.addItem(loc)
                mw.UpdateFlag = True
                if loc.listitem is not None:
                    mw.locationList.insertItem(list_idx, loc.listitem)
                mw.UpdateFlag = False
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for loc, _ in self.loc_info_list:
            if loc in globals.Area.locations:
                globals.Area.locations.remove(loc)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.UpdateFlag = True
                if loc.listitem is not None:
                    mw.locationList.takeItem(mw.locationList.row(loc.listitem))
                mw.UpdateFlag = False
                if loc.scene():
                    loc.scene().removeItem(loc)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


# Path Commands
class MovePathNodeCommand(Command):
    def __init__(self, moves, is_nabbit=False):
        super().__init__("Move Path Nodes")
        self.moves = moves
        self.is_nabbit = is_nabbit

    def undo(self):
        for node, old_x, old_y, _, _ in self.moves:
            self._set_item_pos(node, old_x, old_y)
            node.updatePos()
            if not self.is_nabbit:
                node.pathinfo['peline'].nodePosChanged()
            node.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for node, _, _, new_x, new_y in self.moves:
            self._set_item_pos(node, new_x, new_y)
            node.updatePos()
            if not self.is_nabbit:
                node.pathinfo['peline'].nodePosChanged()
            node.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class AddPathNodeCommand(Command):
    def __init__(self, pathinfo, nodeinfo, node, is_nabbit=False):
        super().__init__("Add Path Node")
        self.pathinfo = pathinfo
        self.nodeinfo = nodeinfo
        self.node = node
        self.is_nabbit = is_nabbit
        self.is_new_path = (len(pathinfo['nodes']) == 1)

    def undo(self):
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            plist = mw.nabbitPathList if self.is_nabbit else mw.pathList
            paths = globals.Area.nPaths if self.is_nabbit else globals.Area.paths
            
            mw.UpdateFlag = True
            if self.node.listitem is not None:
                plist.takeItem(plist.row(self.node.listitem))
            mw.UpdateFlag = False
            
            if self.node in paths:
                paths.remove(self.node)
            if self.nodeinfo in self.pathinfo['nodes']:
                self.pathinfo['nodes'].remove(self.nodeinfo)
                
            if len(self.pathinfo['nodes']) == 0:
                if self.is_nabbit:
                    globals.Area.nPathdata = []
                else:
                    if self.pathinfo in globals.Area.pathdata:
                        globals.Area.pathdata.remove(self.pathinfo)
                if 'peline' in self.pathinfo and self.pathinfo['peline'].scene():
                    self.pathinfo['peline'].scene().removeItem(self.pathinfo['peline'])
            else:
                for pathnode in self.pathinfo['nodes']:
                    pathnode['graphicsitem'].updateId()
                if 'peline' in self.pathinfo:
                    self.pathinfo['peline'].nodePosChanged()

            if self.node.scene():
                self.node.scene().removeItem(self.node)
            mw.scene.update()

    def redo(self):
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            plist = mw.nabbitPathList if self.is_nabbit else mw.pathList
            paths = globals.Area.nPaths if self.is_nabbit else globals.Area.paths
            
            if self.is_new_path:
                if self.is_nabbit:
                    globals.Area.nPathdata = [self.pathinfo]
                else:
                    globals.Area.pathdata.append(self.pathinfo)
                    globals.Area.pathdata.sort(key=lambda p: int(p['id']))
                if 'peline' in self.pathinfo:
                    mw.scene.addItem(self.pathinfo['peline'])
            
            if self.nodeinfo not in self.pathinfo['nodes']:
                self.pathinfo['nodes'].append(self.nodeinfo)
            if self.node not in paths:
                paths.append(self.node)
                
            mw.scene.addItem(self.node)
            
            # Rebuild list
            mw.UpdateFlag = True
            if not self.is_nabbit:
                plist.clear()
                for fpath in globals.Area.pathdata:
                    for fpnode in fpath['nodes']:
                        plist.addItem(fpnode['graphicsitem'].listitem)
                        fpnode['graphicsitem'].updateId()
            else:
                plist.addItem(self.node.listitem)
                for fpath in globals.Area.nPathdata:
                    for fpnode in fpath['nodes']:
                        fpnode['graphicsitem'].updateId()
                        
            mw.UpdateFlag = False
            
            if 'peline' in self.pathinfo:
                self.pathinfo['peline'].nodePosChanged()
            mw.scene.update()


class DeletePathNodeCommand(Command):
    def __init__(self, node_info_list, is_nabbit=False):
        super().__init__("Delete Path Nodes")
        # node_info_list: list of (node, pathinfo, nodeinfo, node_idx, path_was_removed, is_nabbit)
        self.node_info_list = node_info_list
        self.is_nabbit = is_nabbit

    def undo(self):
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            plist = mw.nabbitPathList if self.is_nabbit else mw.pathList
            paths = globals.Area.nPaths if self.is_nabbit else globals.Area.paths
            
            for node, pathinfo, nodeinfo, node_idx, path_was_removed, _ in reversed(self.node_info_list):
                if path_was_removed:
                    if self.is_nabbit:
                        globals.Area.nPathdata = [pathinfo]
                    else:
                        globals.Area.pathdata.append(pathinfo)
                        globals.Area.pathdata.sort(key=lambda p: int(p['id']))
                    if 'peline' in pathinfo:
                        mw.scene.addItem(pathinfo['peline'])
                
                pathinfo['nodes'].insert(node_idx, nodeinfo)
                paths.append(node)
                mw.scene.addItem(node)
            
            # Rebuild list to ensure correct order
            mw.UpdateFlag = True
            if not self.is_nabbit:
                plist.clear()
                for fpath in globals.Area.pathdata:
                    for fpnode in fpath['nodes']:
                        plist.addItem(fpnode['graphicsitem'].listitem)
                        fpnode['graphicsitem'].updateId()
            else:
                plist.clear()
                for fpath in globals.Area.nPathdata:
                    for fpnode in fpath['nodes']:
                        plist.addItem(fpnode['graphicsitem'].listitem)
                        fpnode['graphicsitem'].updateId()
            mw.UpdateFlag = False
            
            # Update polylines
            for _, pathinfo, _, _, _, _ in self.node_info_list:
                if 'peline' in pathinfo:
                    pathinfo['peline'].nodePosChanged()
            
            mw.scene.update()

    def redo(self):
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            plist = mw.nabbitPathList if self.is_nabbit else mw.pathList
            paths = globals.Area.nPaths if self.is_nabbit else globals.Area.paths
            
            for node, pathinfo, nodeinfo, _, path_was_removed, _ in self.node_info_list:
                if node in paths:
                    paths.remove(node)
                if nodeinfo in pathinfo['nodes']:
                    pathinfo['nodes'].remove(nodeinfo)
                
                if path_was_removed:
                    if self.is_nabbit:
                        globals.Area.nPathdata = []
                    else:
                        if pathinfo in globals.Area.pathdata:
                            globals.Area.pathdata.remove(pathinfo)
                    if 'peline' in pathinfo and pathinfo['peline'].scene():
                        pathinfo['peline'].scene().removeItem(pathinfo['peline'])
                else:
                    for pathnode in pathinfo['nodes']:
                        pathnode['graphicsitem'].updateId()
                    if 'peline' in pathinfo:
                        pathinfo['peline'].nodePosChanged()
                
                if node.scene():
                    node.scene().removeItem(node)
                
            # Rebuild list
            mw.UpdateFlag = True
            if not self.is_nabbit:
                plist.clear()
                for fpath in globals.Area.pathdata:
                    for fpnode in fpath['nodes']:
                        plist.addItem(fpnode['graphicsitem'].listitem)
            else:
                plist.clear()
                for fpath in globals.Area.nPathdata:
                    for fpnode in fpath['nodes']:
                        plist.addItem(fpnode['graphicsitem'].listitem)
            mw.UpdateFlag = False
            mw.scene.update()


# Comment Commands
class MoveCommentCommand(Command):
    def __init__(self, moves):
        super().__init__("Move Comments")
        self.moves = moves

    def undo(self):
        for com, old_x, old_y, _, _ in self.moves:
            self._set_item_pos(com, old_x, old_y)
            com.handlePosChange(old_x, old_y)
            com.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.scene.update()

    def redo(self):
        for com, _, _, new_x, new_y in self.moves:
            self._set_item_pos(com, new_x, new_y)
            com.handlePosChange(new_x, new_y)
            com.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.scene.update()


class AddCommentCommand(Command):
    def __init__(self, com):
        super().__init__("Add Comment")
        self.com = com
        self.list_idx = -1

    def undo(self):
        if self.com in globals.Area.comments:
            self.list_idx = globals.Area.comments.index(self.com)
            globals.Area.comments.remove(self.com)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.UpdateFlag = True
            if self.com.listitem is not None:
                mw.commentList.takeItem(mw.commentList.row(self.com.listitem))
            mw.UpdateFlag = False
            
            p = self.com.TextEditProxy
            if p and p.scene():
                p.scene().removeItem(p)
            if self.com.scene():
                self.com.scene().removeItem(self.com)
            mw.SaveComments()
            mw.scene.update()

    def redo(self):
        if self.list_idx != -1 and self.list_idx <= len(globals.Area.comments):
            globals.Area.comments.insert(self.list_idx, self.com)
        else:
            globals.Area.comments.append(self.com)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            mw = globals.mainWindow
            mw.scene.addItem(self.com)
            mw.scene.addItem(self.com.TextEditProxy)
            mw.UpdateFlag = True
            if self.com.listitem is not None:
                if self.list_idx != -1 and self.list_idx <= mw.commentList.count():
                    mw.commentList.insertItem(self.list_idx, self.com.listitem)
                else:
                    mw.commentList.addItem(self.com.listitem)
            mw.UpdateFlag = False
            mw.SaveComments()
            mw.scene.update()


class DeleteCommentsCommand(Command):
    def __init__(self, com_info_list):
        super().__init__("Delete Comments")
        self.com_info_list = com_info_list

    def undo(self):
        for com, list_idx in reversed(self.com_info_list):
            globals.Area.comments.insert(list_idx, com)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.scene.addItem(com)
                mw.scene.addItem(com.TextEditProxy)
                mw.UpdateFlag = True
                if com.listitem is not None:
                    mw.commentList.insertItem(list_idx, com.listitem)
                mw.UpdateFlag = False
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.scene.update()

    def redo(self):
        for com, _ in self.com_info_list:
            if com in globals.Area.comments:
                globals.Area.comments.remove(com)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                mw = globals.mainWindow
                mw.UpdateFlag = True
                if com.listitem is not None:
                    mw.commentList.takeItem(mw.commentList.row(com.listitem))
                mw.UpdateFlag = False
                
                p = com.TextEditProxy
                if p and p.scene():
                    p.scene().removeItem(p)
                if com.scene():
                    com.scene().removeItem(com)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.scene.update()


# Other Commands
class ZonePropertyChangedCommand(Command):
    def __init__(self, zone, old_props, new_props):
        super().__init__("Change Zone Properties")
        self.zone = zone
        self.old_props = old_props
        self.new_props = new_props

    def undo(self):
        self._apply_props(self.old_props)

    def redo(self):
        self._apply_props(self.new_props)

    def _apply_props(self, props):
        self.zone.objx = props['x']
        self.zone.objy = props['y']
        self.zone.width = props['w']
        self.zone.height = props['h']
        self.zone.cammode = props.get('cammode', 0)
        self.zone.zoom = props.get('zoom', 0)
        self.zone.colorbg = props.get('colorbg', 0)
        
        self.zone.prepareGeometryChange()
        self.zone.UpdateRects()
        self.zone.setPos(self.zone.objx * (globals.TileWidth / 16), self.zone.objy * (globals.TileWidth / 16))
        
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class RaiseLowerObjectsCommand(Command):
    def __init__(self, desc, obj_info_list):
        super().__init__(desc)
        # list of (obj, old_z, new_z)
        self.obj_info_list = obj_info_list

    def undo(self):
        for obj, old_z, _ in self.obj_info_list:
            obj.setZValue(old_z)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            self._sort_layers(globals.mainWindow)

    def redo(self):
        for obj, _, new_z in self.obj_info_list:
            obj.setZValue(new_z)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            self._sort_layers(globals.mainWindow)
            
    def _sort_layers(self, mw):
        for layer in globals.Area.layers:
            layer.sort(key=lambda obj: obj.zValue())
        mw.scene.update()


class ShiftItemsCommand(Command):
    def __init__(self, item_moves):
        super().__init__("Shift Items")
        # item_moves: list of (item, old_x, old_y, new_x, new_y)
        self.item_moves = item_moves

    def undo(self):
        for item, old_x, old_y, _, _ in self.item_moves:
            self._set_item_pos(item, old_x, old_y)
            if hasattr(item, 'updatePos'):
                item.updatePos()
            if hasattr(item, 'handlePosChange'):
                item.handlePosChange(old_x, old_y)
            if hasattr(item, 'UpdateListItem'):
                item.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for item, _, _, new_x, new_y in self.item_moves:
            self._set_item_pos(item, new_x, new_y)
            if hasattr(item, 'updatePos'):
                item.updatePos()
            if hasattr(item, 'handlePosChange'):
                item.handlePosChange(new_x, new_y)
            if hasattr(item, 'UpdateListItem'):
                item.UpdateListItem()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class ObjectTypeChangedCommand(Command):
    def __init__(self, changes):
        super().__init__("Change Object Type")
        # changes: list of (obj, old_ts, old_type, old_data, new_ts, new_type, new_data)
        self.changes = changes

    def undo(self):
        for obj, old_ts, old_type, old_data, _, _, _ in self.changes:
            obj.SetType(old_ts, old_type)
            obj.data = old_data
            obj.update()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()

    def redo(self):
        for obj, _, _, _, new_ts, new_type, new_data in self.changes:
            obj.SetType(new_ts, new_type)
            obj.data = new_data
            obj.update()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()


class SpriteTypeChangedCommand(Command):
    def __init__(self, changes):
        super().__init__("Change Sprite Type")
        # changes: list of (spr, old_type, old_data, new_type, new_data)
        self.changes = changes

    def undo(self):
        for spr, old_type, old_data, _, _ in self.changes:
            spr.spritedata = old_data
            spr.SetType(old_type)
            spr.update()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.ChangeSelectionHandler()
            globals.mainWindow.scene.update()

    def redo(self):
        for spr, _, _, new_type, new_data in self.changes:
            spr.spritedata = new_data
            spr.SetType(new_type)
            spr.update()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.ChangeSelectionHandler()
            globals.mainWindow.scene.update()


class SpritePropertyChangedCommand(Command):
    def __init__(self, spr, property_name, old_value, new_value):
        super().__init__("Change Sprite %s" % property_name)
        self.spr = spr
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        setattr(self.spr, self.property_name, self.old_value)
        self._sync()

    def redo(self):
        setattr(self.spr, self.property_name, self.new_value)
        self._sync()

    def _sync(self):
        self.spr.UpdateListItem()
        self.spr.UpdateDynamicSizing()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.SetDirty()


class CommentTextChangedCommand(Command):
    def __init__(self, com, old_text, new_text):
        super().__init__("Change Comment Text")
        self.com = com
        self.old_text = old_text
        self.new_text = new_text

    def undo(self):
        self.com.text = self.old_text
        self._sync()

    def redo(self):
        self.com.text = self.new_text
        self._sync()

    def _sync(self):
        self.com.UpdateListItem()
        self.com.UpdateTooltip()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.scene.update()
            globals.mainWindow.SetDirty()


class PropertyChangedCommand(Command):
    def __init__(self, obj, property_name, old_value, new_value, description=None, sync_func=None):
        if description is None:
            description = "Change %s" % property_name
        super().__init__(description)
        self.obj = obj
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        self.sync_func = sync_func

    def undo(self):
        setattr(self.obj, self.property_name, self.old_value)
        if self.sync_func: self.sync_func()
        else: self._default_sync()

    def redo(self):
        setattr(self.obj, self.property_name, self.new_value)
        if self.sync_func: self.sync_func()
        else: self._default_sync()

    def _default_sync(self):
        if hasattr(self.obj, 'update'): self.obj.update()
        if hasattr(self.obj, 'UpdateListItem'): self.obj.UpdateListItem()
        if hasattr(self.obj, 'UpdateTooltip'): self.obj.UpdateTooltip()
        if hasattr(self.obj, 'UpdateRects'): self.obj.UpdateRects()
        if hasattr(self.obj, 'prepareGeometryChange'): self.obj.prepareGeometryChange()
        if hasattr(self.obj, 'setPos') and hasattr(self.obj, 'objx') and hasattr(self.obj, 'objy'):
            self.obj.setPos(self.obj.objx * (globals.TileWidth / 16), self.obj.objy * (globals.TileWidth / 16))
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.SetDirty()


class DictPropertyChangedCommand(Command):
    def __init__(self, dct, key, old_value, new_value, description=None, sync_func=None):
        if description is None:
            description = "Change %s" % key
        super().__init__(description)
        self.dct = dct
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.sync_func = sync_func

    def undo(self):
        self.dct[self.key] = self.old_value
        if self.sync_func: self.sync_func()
        elif hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SetDirty()

    def redo(self):
        self.dct[self.key] = self.new_value
        if self.sync_func: self.sync_func()
        elif hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SetDirty()


class ChangeZonesCommand(Command):
    def __init__(self, old_zones, new_zones):
        super().__init__("Change Zones")
        self.old_zones = list(old_zones)
        self.new_zones = list(new_zones)
        # Store state snapshots for each zone to handle property changes correctly
        self.old_states = [self._get_state(z) for z in self.old_zones]
        self.new_states = [self._get_state(z) for z in self.new_zones]

    def _get_state(self, zone):
        return {
            'objx': zone.objx,
            'objy': zone.objy,
            'width': zone.width,
            'height': zone.height,
            'cammode': zone.cammode,
            'camzoom': zone.camzoom,
            'unk1': zone.unk1,
            'visibility': zone.visibility,
            'unk2': zone.unk2,
            'camtrack': zone.camtrack,
            'unk3': zone.unk3,
            'yupperbound': zone.yupperbound,
            'ylowerbound': zone.ylowerbound,
            'yupperbound2': zone.yupperbound2,
            'ylowerbound2': zone.ylowerbound2,
            'yupperbound3': zone.yupperbound3,
            'ylowerbound3': zone.ylowerbound3,
            'mpcamzoomadjust': zone.mpcamzoomadjust,
            'music': zone.music,
            'sfxmod': zone.sfxmod,
            'type': zone.type,
            'background': zone.background,
            'id': zone.id
        }

    def _apply_state(self, zone, state):
        for k, v in state.items():
            setattr(zone, k, v)
        zone.UpdateTitle()
        zone.UpdateRects()
        zone.prepareGeometryChange()
        zone.setPos(zone.objx * (globals.TileWidth / 16), zone.objy * (globals.TileWidth / 16))

    def undo(self):
        self._apply(self.old_zones, self.old_states)

    def redo(self):
        self._apply(self.new_zones, self.new_states)

    def _apply(self, zones, states):
        mw = globals.mainWindow
        # Remove current zones from scene
        for item in mw.scene.items():
            if isinstance(item, ZoneItem):
                mw.scene.removeItem(item)
        
        globals.Area.zones = list(zones)
        for zone, state in zip(zones, states):
            self._apply_state(zone, state)
            mw.scene.addItem(zone)
        
        mw.scene.update()
        mw.levelOverview.update()
        mw.SetDirty()


class AddLocationCommand(Command):
    def __init__(self, loc):
        super().__init__("Add Location")
        self.loc = loc

    def undo(self):
        if self.loc in globals.Area.locations:
            globals.Area.locations.remove(self.loc)
        if self.loc.scene():
            self.loc.scene().removeItem(self.loc)

    def redo(self):
        if self.loc not in globals.Area.locations:
            globals.Area.locations.append(self.loc)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.addItem(self.loc)
            globals.mainWindow.SetDirty()


class DeleteLocationsCommand(Command):
    def __init__(self, locs):
        super().__init__("Delete Locations")
        self.locs = list(locs)

    def undo(self):
        for loc in self.locs:
            if loc not in globals.Area.locations:
                globals.Area.locations.append(loc)
            if hasattr(globals, 'mainWindow') and globals.mainWindow:
                globals.mainWindow.scene.addItem(loc)

    def redo(self):
        for loc in self.locs:
            if loc in globals.Area.locations:
                globals.Area.locations.remove(loc)
            if loc.scene():
                loc.scene().removeItem(loc)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SetDirty()


class SetObjectTypeCommand(Command):
    def __init__(self, obj, old_tileset, old_type, new_tileset, new_type):
        super().__init__("Change Object Type")
        self.obj = obj
        self.old_tileset = old_tileset
        self.old_type = old_type
        self.new_tileset = new_tileset
        self.new_type = new_type

    def undo(self):
        self.obj.SetType(self.old_tileset, self.old_type)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.SetDirty()

    def redo(self):
        self.obj.SetType(self.new_tileset, self.new_type)
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.scene.update()
            globals.mainWindow.SetDirty()


class AddCommentsCommand(Command):
    def __init__(self, coms):
        super().__init__("Add Comment")
        self.coms = list(coms)

    def undo(self):
        for com in self.coms:
            if com in globals.Area.comments:
                globals.Area.comments.remove(com)
            if com.scene():
                com.scene().removeItem(com)
            if com.listitem:
                globals.mainWindow.commentList.takeItem(globals.mainWindow.commentList.row(com.listitem))
        globals.mainWindow.SaveComments()
        globals.mainWindow.SetDirty()

    def redo(self):
        for com in self.coms:
            if com not in globals.Area.comments:
                globals.Area.comments.append(com)
            globals.mainWindow.scene.addItem(com)
            if com.listitem:
                globals.mainWindow.commentList.addItem(com.listitem)
        globals.mainWindow.SaveComments()
        globals.mainWindow.SetDirty()


class CommentTextChangedCommand(Command):
    def __init__(self, com, old_text, new_text):
        super().__init__("Change Comment Text")
        self.com = com
        self.old_text = old_text
        self.new_text = new_text

    def undo(self):
        self.com.text = self.old_text
        self.com.TextEdit.setPlainText(self.old_text)
        self.com.UpdateListItem()
        self.com.UpdateTooltip()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.SetDirty()

    def redo(self):
        self.com.text = self.new_text
        self.com.TextEdit.setPlainText(self.new_text)
        self.com.UpdateListItem()
        self.com.UpdateTooltip()
        if hasattr(globals, 'mainWindow') and globals.mainWindow:
            globals.mainWindow.SaveComments()
            globals.mainWindow.SetDirty()


class AddEntranceCommand(Command):
    def __init__(self, ent, index):
        super().__init__("Add Entrance")
        self.ent = ent
        self.index = index

    def undo(self):
        if self.ent in globals.Area.entrances:
            globals.Area.entrances.remove(self.ent)
        if self.ent.scene():
            self.ent.scene().removeItem(self.ent)
        if self.ent.listitem:
            globals.mainWindow.entranceList.takeItem(globals.mainWindow.entranceList.row(self.ent.listitem))
        globals.mainWindow.SetDirty()

    def redo(self):
        globals.Area.entrances.insert(self.index, self.ent)
        globals.mainWindow.scene.addItem(self.ent)
        if self.ent.listitem:
            globals.mainWindow.entranceList.insertItem(self.index, self.ent.listitem)
        globals.mainWindow.SetDirty()

