# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from cx_Freeze import setup, Executable
import sys
import UM
import UM.Qt #@UnusedImport
import cura  #@UnusedImport
import os
import shutil
import site
import os
import scipy

os.environ['TCL_LIBRARY'] = r'C:\Python35-32\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Python35-32\tcl\tk8.6'

# work around the limitation that shutil.copytree does not allow the target directory to exist
def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

includes = ["sip", "PyQt5.QtNetwork", "PyQt5._QOpenGLFunctions_2_0", "Arcus", "Savitar", "google.protobuf.descriptor", "xml.etree.ElementTree", "cura.OneAtATimeIterator", "numpy.core._methods", 
            "numpy.lib.format", "numpy.matlib", "zeroconf"]
# Include all the UM modules in the includes. As py2exe fails to properly find all the dependencies due to the plugin architecture.
for dirpath, dirnames, filenames in os.walk(os.path.dirname(UM.__file__)):
    if "__" in dirpath:
        continue
    module_path = dirpath.replace(os.path.dirname(UM.__file__), "UM")
    module_path = module_path.split(os.path.sep)
    module_name = ".".join(module_path)
    if os.path.isfile(dirpath + "/__init__.py"):
        includes += [module_name]
        for filename in filenames:
            if "__" in filename or not filename.endswith(".py"):
                continue
            includes += [module_name + "." + os.path.splitext(filename)[0]]

packages = ["ctypes", "UM", "serial", "google", "google.protobuf", "cura", "xml.etree", "stl"]
includefiles_list=[]
scipy_path = os.path.dirname(scipy.__file__)
includefiles_list.append(scipy_path)

print("Removing previous distribution package")
shutil.rmtree("dist", True)

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

build_exe_options = {
    "build_exe": "dist",
    "includes": includes,
    "packages": packages,
    "include_files": includefiles_list
}

setup(  
    name="Cura",
    version="2.6.0",
    author="Ultimaker",
    author_email="a.hiemstra@ultimaker.com",
    url="http://software.ultimaker.com/",
    license="GNU AFFERO GENERAL PUBLIC LICENSE (AGPL)",
    options = {
        "build_exe": build_exe_options
    },
    executables = [Executable(script="cura_app.py", base=base, icon="icons/cura.ico", targetName="Cura.exe")]
)

print("Coping Cura plugins.")
shutil.copytree("../Resources/uranium/plugins", "dist/plugins", ignore = shutil.ignore_patterns("ConsoleLogger", "OBJWriter", "MLPWriter", "MLPReader"))
for path in os.listdir("plugins"):
    copytree("plugins/" + path, "dist/plugins/" + path)
print("Coping resources.")
copytree("../share/uranium/resources", "dist/resources")
copytree("resources", "dist/resources")
print("Coping Uranium QML.")
shutil.copytree(os.path.dirname(UM.__file__) + "/Qt/qml/UM", "dist/qml/UM")
for site_package in site.getsitepackages():
    qt_origin_path = os.path.join(site_package, "PyQt5/Qt")
    if os.path.isdir(qt_origin_path):
        print("Coping PyQt5 plugins from: %s" % qt_origin_path)
        shutil.copytree(os.path.join(qt_origin_path, "plugins"), "dist/PyQt5/plugins")
        print("Coping PyQt5 QtQuick from: %s" % qt_origin_path)
        shutil.copytree(os.path.join(qt_origin_path, "qml/QtQuick"), "dist/qml/QtQuick")
        shutil.copytree(os.path.join(qt_origin_path, "qml/QtQuick.2"), "dist/qml/QtQuick.2")
        print("Coping PyQt5 svg library from: %s" % qt_origin_path)
        shutil.copy(os.path.join(qt_origin_path + "/bin", "Qt5Svg.dll"), "dist/Qt5Svg.dll")
        print("Copying Angle libraries from %s" % qt_origin_path)
        shutil.copy(os.path.join(qt_origin_path + "/bin", "libEGL.dll"), "dist/libEGL.dll")
        shutil.copy(os.path.join(qt_origin_path + "/bin", "libGLESv2.dll"), "dist/libGLESv2.dll")