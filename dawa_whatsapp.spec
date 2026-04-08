# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: one-file GUI app with bundled logo.png (see BUNDLE_DIR in config).
# Windows: python -m PyInstaller --noconfirm --clean dawa_whatsapp.spec (requires logo.ico in project root)
# macOS:   bash scripts/make_logo_icns.sh && python3 -m PyInstaller --noconfirm --clean dawa_whatsapp.spec

import os
import sys

from PyInstaller.utils.hooks import collect_all

# SPEC is set by PyInstaller when loading this file (__file__ is not available).
_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
_IS_DARWIN = sys.platform == "darwin"


def _exe_icon_path():
    """Windows: existing logo.ico. macOS: logo.icns (make_logo_icns.sh)."""
    if _IS_DARWIN:
        p = os.path.join(_SPEC_DIR, "logo.icns")
        return p if os.path.isfile(p) else None
    p = os.path.join(_SPEC_DIR, "logo.ico")
    return p if os.path.isfile(p) else None


_EXE_ICON = _exe_icon_path()

block_cipher = None

datas = [("logo.png", ".")]
binaries = []
hiddenimports = []

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
datas += ctk_datas
binaries += ctk_binaries
hiddenimports += ctk_hiddenimports

hiddenimports += [
    "firebase_admin",
    "firebase_admin.credentials",
    "firebase_admin.firestore",
    "google.cloud.firestore",
    "google.cloud.firestore_v1",
    "grpc",
    "PIL._tkinter_finder",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DawaWhatsApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not _IS_DARWIN,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_EXE_ICON if os.path.isfile(_EXE_ICON) else None,
)

