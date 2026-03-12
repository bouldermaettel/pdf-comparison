# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

spec_root = Path(globals().get("SPECPATH", ".")).resolve()
project_root = spec_root
frontend_dist = project_root / "frontend" / "dist"

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "frontend/dist"))

datas += collect_data_files("pdfplumber")
datas += collect_data_files("fitz")

hiddenimports = []
hiddenimports += collect_submodules("pdfplumber")
hiddenimports += collect_submodules("fitz")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("starlette")


a = Analysis(
    ["app.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdf_matcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pdf_matcher",
)
