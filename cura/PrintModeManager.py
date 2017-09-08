from UM.Application import Application
from UM.Preferences import Preferences
from UM.Signal import Signal
from UM.Scene.SceneNode import SceneNode
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation

from cura.Settings.ExtruderManager import ExtruderManager

class PrintModeManager:

    def __init__(self):
        super().__init__()
        if PrintModeManager._instance is not None:
            raise ValueError("Duplicate singleton creation")

        PrintModeManager._instance = self

        self._duplicated_nodes = []

        old_material_id = Preferences.getInstance().getValue("cura/old_material")
        if Application.getInstance().getContainerRegistry().findContainers(id=old_material_id):
            self._old_material = Application.getInstance().getContainerRegistry().findContainers(id=old_material_id)[0]
        else:
            self._old_material = ""

        self._global_stack = None
        Application.getInstance().globalContainerStackChanged.connect(self._onGlobalStackChanged)
        self._onGlobalStackChanged()

        Application.getInstance().getMachineManager().activeMaterialChanged.connect(self._materialChanged)

        self.printModeChanged.connect(self._onPrintModeChanged)
        self._scene = Application.getInstance().getController().getScene()
        self._onPrintModeChanged()

    def addDuplicatedNode(self, node):
        self._duplicated_nodes.append(node)

    def deleteDuplicatedNodes(self):
        del self._duplicated_nodes[:]

    def deleteDuplicatedNode(self, node):
        self._duplicated_nodes.remove(node)

    def getDuplicatedNode(self, node):
        for node_dup in self._duplicated_nodes:
            if node_dup.node == node:
                return node_dup

    def getDuplicatedNodes(self):
        return self._duplicated_nodes

    def renderDuplicatedNode(self, node):
        if node.node.getParent() != self._scene.getRoot():
            parent = self.getDuplicatedNode(node.node.getParent())
        else:
            parent = self._scene.getRoot()
        op = AddSceneNodeOperation(node, parent)
        op.redo()
        node.update()

    def renderDuplicatedNodes(self):
        for node in self._duplicated_nodes:
            self.renderDuplicatedNode(node)

    def removeDuplicatedNodes(self):
        for node in self._duplicated_nodes:
            op = RemoveSceneNodeOperation(node)
            op.redo()

    def _onGlobalStackChanged(self):
        if self._global_stack:
            self._global_stack.propertyChanged.disconnect(self._onPropertyChanged)

        self._global_stack = Application.getInstance().getGlobalContainerStack()

        if self._global_stack:
            self._global_stack.propertyChanged.connect(self._onPropertyChanged)
            if not self._global_stack.getProperty("print_mode", "enabled"):
                self.deleteDuplicatedNodes()

    printModeChanged = Signal()

    def _onPropertyChanged(self, key, property_name):
        if key == "print_mode" and property_name == "value":
            self.printModeChanged.emit()

    def _onPrintModeChanged(self):
        if self._global_stack:
            print_mode = self._global_stack.getProperty("print_mode", "value")
            nodes = self._scene.getRoot().getChildren()
            if print_mode != "regular":
                for node in nodes:
                    if type(node) == SceneNode:
                        self._setActiveExtruder(node)
                if self._old_material == "":
                    self._old_material = ExtruderManager.getInstance().getExtruderStack(1).material
                    material = ExtruderManager.getInstance().getExtruderStack(0).material
                    ExtruderManager.getInstance().getExtruderStack(1).setMaterial(material)
                    Preferences.getInstance().setValue("cura/old_material", self._old_material.getId())
                self.renderDuplicatedNodes()
            else:
                self.removeDuplicatedNodes()
                if self._old_material != "":
                    ExtruderManager.getInstance().getExtruderStack(1).setMaterial(self._old_material)
                    self._old_material = ""
                    Preferences.getInstance().setValue("cura/old_material", "")

    def _materialChanged(self):
        if self._global_stack:
            print_mode = self._global_stack.getProperty("print_mode", "value")
            if print_mode != "regular":
                material = ExtruderManager.getInstance().getExtruderStack(0).material
                ExtruderManager.getInstance().getExtruderStack(1).setMaterial(material)

    def _setActiveExtruder(self, node):
        node.callDecoration("setActiveExtruder", ExtruderManager.getInstance().getExtruderStack(0).getId())

    @classmethod
    def getInstance(cls) -> "PrintModeManager":
        # Note: Explicit use of class name to prevent issues with inheritance.
        if not PrintModeManager._instance:
            PrintModeManager._instance = cls()

        return PrintModeManager._instance

    _instance = None