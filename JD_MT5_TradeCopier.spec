# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

datas = [('Templates', 'Templates'), ('static', 'static')]
binaries = []
hiddenimports = []

# Collect numpy completely
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Add numpy core modules explicitly
hiddenimports += [
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.core.multiarray',
    'numpy.core.umath',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'numpy.random',
    'numpy.random.mtrand',
    'numpy.linalg',
    'numpy.fft',
    'numpy._typing',
    'numpy._typing._array_like',
    'numpy._typing._dtype_like',
]

# Collect MetaTrader5
try:
    mt5_ret = collect_all('MetaTrader5')
    datas += mt5_ret[0]
    binaries += mt5_ret[1]
    hiddenimports += mt5_ret[2]
except:
    pass

hiddenimports += ['MetaTrader5']

# Collect pandas
try:
    pandas_ret = collect_all('pandas')
    datas += pandas_ret[0]
    binaries += pandas_ret[1]
    hiddenimports += pandas_ret[2]
except:
    pass

hiddenimports += ['pandas', 'pandas.core', 'pandas.io']

# Additional hidden imports for the app
hiddenimports += [
    'flask',
    'jinja2',
    'werkzeug',
    'cryptography',
    'cryptography.fernet',
    'master_watcher_new',
    'child_executor_new',
    'dashboard_new',
    'license',
    'auth_license',
    'storage',
]

a = Analysis(
    ['launcher_new.py'],
    pathex=[],
    binaries=binaries,
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
