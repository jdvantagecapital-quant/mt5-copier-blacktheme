# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['launcher_new.py'],
    pathex=[],
    binaries=[],
    datas=[('Templates', 'Templates'), ('static', 'static')],
    hiddenimports=[
        'flask',
        'jinja2',
        'MetaTrader5',
        'werkzeug',
        'master_watcher_new',
        'child_executor_new',
        'dashboard_new',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='JD_MT5_TradeCopier',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
