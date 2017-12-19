# Copyright (c) 2017 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from UM.Signal import Signal, signalemitter
from . import USBPrinterOutputDevice
from UM.Application import Application
from UM.Resources import Resources
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from cura.PrinterOutputDevice import ConnectionState
from UM.Qt.ListModel import ListModel
from UM.Message import Message

from cura.CuraApplication import CuraApplication

import threading
import platform
import glob
import time
import os.path
import serial.tools.list_ports
from UM.Extension import Extension

from PyQt5.QtQml import QQmlComponent, QQmlContext
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtProperty, pyqtSignal, Qt
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")


##  Manager class that ensures that a usbPrinteroutput device is created for every connected USB printer.
@signalemitter
class USBPrinterOutputDeviceManager(QObject, OutputDevicePlugin, Extension):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        self._serial_port_list = []
        self._usb_output_devices = {}
        self._usb_output_devices_model = None
        self._update_thread = threading.Thread(target = self._updateThread)
        self._update_thread.setDaemon(True)

        self._check_updates = True
        self._firmware_view = None

        Application.getInstance().applicationShuttingDown.connect(self.stop)
        self.addUSBOutputDeviceSignal.connect(self.addOutputDevice) #Because the model needs to be created in the same thread as the QMLEngine, we use a signal.

    addUSBOutputDeviceSignal = Signal()
    connectionStateChanged = pyqtSignal()

    progressChanged = pyqtSignal()
    firmwareUpdateChange = pyqtSignal()

    @pyqtProperty(float, notify = progressChanged)
    def progress(self):
        progress = 0
        for printer_name, device in self._usb_output_devices.items(): # TODO: @UnusedVariable "printer_name"
            progress += device.progress
        return progress / len(self._usb_output_devices)

    @pyqtProperty(int, notify = progressChanged)
    def errorCode(self):
        for printer_name, device in self._usb_output_devices.items(): # TODO: @UnusedVariable "printer_name"
            if device._error_code:
                return device._error_code
        return 0

    ##  Return True if all printers finished firmware update
    @pyqtProperty(float, notify = firmwareUpdateChange)
    def firmwareUpdateCompleteStatus(self):
        complete = True
        for printer_name, device in self._usb_output_devices.items(): # TODO: @UnusedVariable "printer_name"
            if not device.firmwareUpdateFinished:
                complete = False
        return complete

    def start(self):
        self._check_updates = True
        self._update_thread.start()

    def stop(self):
        self._check_updates = False

    def _updateThread(self):
        while self._check_updates:
            result = self.getSerialPortList(only_list_usb = True)
            self._addRemovePorts(result)
            time.sleep(5)

    ##  Show firmware interface.
    #   This will create the view if its not already created.
    def spawnFirmwareInterface(self, serial_port):
        if self._firmware_view is None:
            path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath("USBPrinting"), "FirmwareUpdateWindow.qml"))
            component = QQmlComponent(Application.getInstance()._engine, path)

            self._firmware_context = QQmlContext(Application.getInstance()._engine.rootContext())
            self._firmware_context.setContextProperty("manager", self)
            self._firmware_view = component.create(self._firmware_context)

        self._firmware_view.show()

    @pyqtSlot(str)
    def updateAllFirmware(self, file_name):
        if not self._usb_output_devices:
            Message(i18n_catalog.i18nc("@info", "Unable to update firmware because there are no printers connected.")).show()
            return
        if file_name.startswith("file://"):
            file_name = QUrl(file_name).toLocalFile() # File dialogs prepend the path with file://, which we don't need / want

        for printer_connection in self._usb_output_devices:
            if self._usb_output_devices[printer_connection].connectionState != ConnectionState.connected:
                Message(i18n_catalog.i18nc("@info", "Unable to update firmware because printer connection isn't established yet.")).show()
                return
            self._usb_output_devices[printer_connection].resetFirmwareUpdate()
        self.spawnFirmwareInterface("")
        for printer_connection in self._usb_output_devices:
            try:
                self._usb_output_devices[printer_connection].updateFirmware(file_name)
            except FileNotFoundError:
                # Should only happen in dev environments where the resources/firmware folder is absent.
                self._usb_output_devices[printer_connection].setProgress(100, 100)
                Logger.log("w", "No firmware found for printer %s called '%s'", printer_connection, file_name)
                Message(i18n_catalog.i18nc("@info",
                                           "Could not find firmware required for the printer at %s.") % printer_connection).show()
                self._firmware_view.close()

                continue

    @pyqtSlot(str, str, result = bool)
    def updateFirmwareBySerial(self, serial_port, file_name):
        if serial_port in self._usb_output_devices:
            self.spawnFirmwareInterface(self._usb_output_devices[serial_port].getSerialPort())
            try:
                self._usb_output_devices[serial_port].updateFirmware(file_name)
            except FileNotFoundError:
                self._firmware_view.close()
                Logger.log("e", "Could not find firmware required for this machine called '%s'", file_name)
                return False
            return True
        return False

    ##  Return the singleton instance of the USBPrinterManager
    @classmethod
    def getInstance(cls, engine = None, script_engine = None):
        # Note: Explicit use of class name to prevent issues with inheritance.
        if USBPrinterOutputDeviceManager._instance is None:
            USBPrinterOutputDeviceManager._instance = cls()

        return USBPrinterOutputDeviceManager._instance

    ##  Helper to identify serial ports (and scan for them)
    def _addRemovePorts(self, serial_ports):
        # First, find and add all new or changed keys
        for serial_port in list(serial_ports):
            if serial_port not in self._serial_port_list:
                self.addUSBOutputDeviceSignal.emit(serial_port)  # Hack to ensure its created in main thread
                continue
        self._serial_port_list = list(serial_ports)

        devices_to_remove = []
        for port, device in self._usb_output_devices.items():
            if port not in self._serial_port_list:
                device.close()
                devices_to_remove.append(port)

        for port in devices_to_remove:
            del self._usb_output_devices[port]

    ##  Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
    def addOutputDevice(self, serial_port):
        device = USBPrinterOutputDevice.USBPrinterOutputDevice(serial_port)
        device.connectionStateChanged.connect(self._onConnectionStateChanged)
        device.connect()
        device.progressChanged.connect(self.progressChanged)
        device.firmwareUpdateChange.connect(self.firmwareUpdateChange)
        self._usb_output_devices[serial_port] = device

    ##  If one of the states of the connected devices change, we might need to add / remove them from the global list.
    def _onConnectionStateChanged(self, serial_port):
        try:
            if self._usb_output_devices[serial_port].connectionState in [ConnectionState.connected, ConnectionState.connecting]:
                self.getOutputDeviceManager().addOutputDevice(self._usb_output_devices[serial_port])
            else:
                self.getOutputDeviceManager().removeOutputDevice(serial_port)
            self.connectionStateChanged.emit()
        except KeyError:
            Logger.log("w", "Connection state of %s changed, but it was not found in the list", serial_port)

    @pyqtProperty(QObject , notify = connectionStateChanged)
    def connectedPrinterList(self):
        self._usb_output_devices_model = ListModel()
        self._usb_output_devices_model.addRoleName(Qt.UserRole + 1, "name")
        self._usb_output_devices_model.addRoleName(Qt.UserRole + 2, "printer")
        for connection in self._usb_output_devices:
            if self._usb_output_devices[connection].connectionState == ConnectionState.connected:
                self._usb_output_devices_model.appendItem({"name": connection, "printer": self._usb_output_devices[connection]})
        return self._usb_output_devices_model

    ##  Create a list of serial ports on the system.
    #   \param only_list_usb If true, only usb ports are listed
    def getSerialPortList(self, only_list_usb = False):
        base_list = []
        for port in serial.tools.list_ports.comports():
            if not isinstance(port, tuple):
                port = (port.device, port.description, port.hwid)
            if only_list_usb and not port[2].startswith("USB"):
                continue
            base_list += [port[0]]

        return list(base_list)

    _instance = None    # type: "USBPrinterOutputDeviceManager"
