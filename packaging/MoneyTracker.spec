# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../templates', 'templates'),
        ('../static', 'static'),
        ('../settings.json', '.'),
    ],
    hiddenimports=[
        'engineio.async_drivers.threading',
        'dns.resolver',
        'dns.reversename',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtWebEngineCore',
        'webview',
        'webview.platforms.gtk',
        'webview.guilib',
    ],
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
    name='MoneyTracker',
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
    icon=None,
)

# For macOS app bundle
app = BUNDLE(
    exe,
    name='MoneyTracker.app',
    icon=None,
    bundle_identifier='com.moneytracker.app',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'Money Tracker',
        'CFBundleDisplayName': 'Money Tracker',
        'CFBundleIdentifier': 'com.moneytracker.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'NSHighResolutionCapable': True,
    },
)