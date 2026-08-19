# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
hidden = []
for package in ("uvicorn", "webview", "faster_whisper", "kokoro", "soundfile"):
    try:
        hidden += collect_submodules(package)
    except Exception:
        pass

datas = [(str(root / "web"), "web")]
for package in ("certifi",):
    try:
        datas += collect_data_files(package)
    except Exception:
        pass

icon_path = root / "assets" / "orivox.ico"

analysis = Analysis(
    [str(root / "desktop.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ORIVOX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_path) if icon_path.exists() else None,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ORIVOX",
)
