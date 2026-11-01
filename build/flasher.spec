# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for HexDrop.

Produces one folder containing two executables that share every dependency:

    HexDrop.exe   windowed - what the operator double-clicks
    hexdrop-cli.exe        console  - diagnostics and support

Both run the same code; ``hexdrop/__main__.py`` opens the window when given
no arguments and runs the command line otherwise.

One folder, not one file. A --onefile build unpacks itself to a temp directory
on every launch, which is slow and is what makes antivirus flag it - and this
tool gets emailed to field staff, so that matters more than tidiness.

    pyinstaller build/flasher.spec --noconfirm
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
PKG = SRC / "hexdrop"
ASSETS = PKG / "ui" / "assets"

sys.path.insert(0, str(SRC))
from hexdrop import __version__  # noqa: E402

# Data is placed at the same relative path the source tree uses, so the
# ordinary Path(__file__).parent lookups keep working in a frozen build with no
# special-casing scattered through the code.
datas = [
    (str(PKG / "backends/avr/tools/avrdude.exe"), "hexdrop/backends/avr/tools"),
    (str(PKG / "backends/avr/tools/avrdude.conf"), "hexdrop/backends/avr/tools"),
    (str(PKG / "backends/avr/tools/LICENSE.txt"), "hexdrop/backends/avr/tools"),
    (str(PKG / "config/boards"), "hexdrop/config/boards"),
    (str(ASSETS / "logo.png"), "hexdrop/ui/assets"),
    (str(ASSETS / "app.ico"), "hexdrop/ui/assets"),
    (str(ASSETS / "fonts"), "hexdrop/ui/assets/fonts"),
]

# Qt ships a great deal this tool never opens. Dropping it roughly halves the
# download an operator has to wait for.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtQuick",
    "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.QtQuickWidgets", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSensors",
    "PySide6.QtSerialBus", "PySide6.QtNfc", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSpatialAudio", "PySide6.QtTextToSpeech",
    "PySide6.QtNetwork", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "tkinter", "unittest", "pydoc_data", "pytest", "PIL", "numpy",
    # No network anywhere in this tool, so no TLS stack is needed.
    "ssl", "_ssl", "http", "urllib.request", "email", "xml",
]

# Whole DLLs Qt or Python drag in that this tool never calls. Removing them
# takes roughly 35 MB off what an operator has to download:
#   opengl32sw   a 20 MB software OpenGL renderer, for 3D that is never drawn
#   libcrypto/libssl   OpenSSL, and this tool makes no network connection
#   Qt6Network   likewise
UNWANTED = ("opengl32sw", "libcrypto-3", "libssl-3", "Qt6Network", "Qt6Svg")


def prune(binaries):
    kept = [b for b in binaries if not any(name in b[0] for name in UNWANTED)]
    dropped = len(binaries) - len(kept)
    print(f"spec: dropped {dropped} unused binaries")
    return kept


a = Analysis(
    [str(PKG / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    # pyserial finds its Windows backend at runtime, so PyInstaller cannot see
    # the import by static analysis.
    hiddenimports=["serial.tools.list_ports", "serial.serialwin32"],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
a.binaries = prune(a.binaries)
pyz = PYZ(a.pure)

ICON = str(ASSETS / "app.ico")
VERSION_FILE = str(ROOT / "build" / "version_info.txt")

gui = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="HexDrop",
    icon=ICON,
    version=VERSION_FILE,
    console=False,          # double-clicked; no console window should appear
    disable_windowed_traceback=False,
    upx=False,              # UPX-packed binaries trip antivirus heuristics
)

cli = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="hexdrop-cli",
    icon=ICON,
    version=VERSION_FILE,
    console=True,           # diagnostics need somewhere to print
    upx=False,
)

coll = COLLECT(
    gui, cli,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HexDrop",
)
