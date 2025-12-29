# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for JD MT5 Trade Copier
Professional distribution build with license protection
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

# Get the directory where this spec file is located
SPEC_DIR = r'C:\\Users\\MI\\MT5-Copier-new'

# Collect ALL numpy components
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
mt5_datas, mt5_binaries, mt5_hiddenimports = collect_all('MetaTrader5')
crypto_datas, crypto_binaries, crypto_hiddenimports = collect_all('cryptography')

# Main analysis
a = Analysis(
    [os.path.join(SPEC_DIR, 'launcher_new.py')],
    pathex=[SPEC_DIR],
    binaries=numpy_binaries + mt5_binaries + crypto_binaries,
    datas=[
        (os.path.join(SPEC_DIR, 'Templates'), 'Templates'), 
        (os.path.join(SPEC_DIR, 'static'), 'static'), 
        (os.path.join(SPEC_DIR, 'data'), 'data'),
        # Include license module
        (os.path.join(SPEC_DIR, 'license.py'), '.'),
        (os.path.join(SPEC_DIR, 'auth_license.py'), '.'),
        # Include master and child modules (needed for subprocess mode)
        (os.path.join(SPEC_DIR, 'master_watcher_new.py'), '.'),
        (os.path.join(SPEC_DIR, 'child_executor_new.py'), '.'),
        (os.path.join(SPEC_DIR, 'dashboard_new.py'), '.'),
        (os.path.join(SPEC_DIR, 'storage.py'), '.'),
    ] + numpy_datas + mt5_datas + crypto_datas,
    hiddenimports=[
        'flask', 
        'werkzeug', 
        'jinja2', 
        'multiprocessing', 
        'json', 
        'hashlib', 
        'secrets',
        'cryptography',
        'cryptography.fernet',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'base64',
        # Include the modules that are imported dynamically
        'master_watcher_new',
        'child_executor_new',
        'dashboard_new',
        'storage',
        'license',
        'auth_license',
    ] + numpy_hiddenimports + mt5_hiddenimports + crypto_hiddenimports + collect_submodules('numpy'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude development/testing modules not needed in production
        'pytest',
        'unittest',
        'test',
        'tests',
    ],
    noarchive=False,
    optimize=0,  # No optimization - numpy requires docstrings
)

# Create PYZ archive
pyz = PYZ(a.pure)

# Create executable
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
    console=True,  # Keep console for debugging - can change to False for cleaner look
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
    version=None,  # Can add version info file
)


