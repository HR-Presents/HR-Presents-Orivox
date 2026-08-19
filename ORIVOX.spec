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

datas = [(str(root / "web"), "web"), (str(root / "assets"), "assets")]
for package in ("certifi",):
    try:
        datas += collect_data_files(package)
    except Exception:
        pass

icon_path = root / "assets" / "orivox.ico"

launcher_analysis = Analysis(
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
launcher_pyz = PYZ(launcher_analysis.pure)
launcher_exe = EXE(
    launcher_pyz,
    launcher_analysis.scripts,
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

server_analysis = Analysis(
    [str(root / "server.py")],
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
server_pyz = PYZ(server_analysis.pure)
server_exe = EXE(
    server_pyz,
    server_analysis.scripts,
    [],
    exclude_binaries=True,
    name="ORIVOX-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    launcher_exe,
    server_exe,
    launcher_analysis.binaries,
    launcher_analysis.datas,
    server_analysis.binaries,
    server_analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ORIVOX",
)
