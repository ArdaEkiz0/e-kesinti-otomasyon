# -*- mode: python ; coding: utf-8 -*-
# SGK E-Kesinti Otomasyon - Profesyonel GUI EXE (PyInstaller spec)
# Arda Yazılım

a = Analysis(
    ['sgk_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['sgk_bot', 'api_client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SGK_E_Kesinti_Otomasyon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Windows GUI modu (konsole penceresi yok)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['docs/app_icon.ico'],
)