# -*- mode: python ; coding: utf-8 -*-
# SGK E-Kesinti Otomasyon - Profesyonel GUI EXE (PyInstaller spec)
# Arda Yazılım

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

a = Analysis(
    ['sgk_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)

# sgk_bot ve api_client dinamik import edilir (BotThread insil/run içinde)
a.datas += collect_data_files('selenium')
a.hiddenimports += collect_submodules('webdriver_manager')
a.hiddenimports += ['sgk_bot', 'api_client']

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