# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

src = Path(SPECPATH).resolve()

a = Analysis(
    [str(src / 'gui.py')],
    pathex=[str(src)],  # ensures local .py files are found as imports
    binaries=[],
    datas=[
        # Bundle the entire Tesseract-OCR folder
        (str(src / 'Tesseract-OCR'), 'Tesseract-OCR'),
        # Bundle the assets (category icon templates)
        (str(src / 'assets'), 'assets'),
        # Companion Python source files imported by gui.py / relic_processor.py
        (str(src / 'relic_processor.py'), '.'),
        (str(src / 'ocr_to_json.py'), '.'),
        (str(src / 'ocr_total_artifacts_tesseract.py'), '.'),
        (str(src / 'relic_data.py'), '.'),
        (str(src / 'resolution_bounds.py'), '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'pydirectinput',
        'pygetwindow',
        'pytesseract',
        'cv2',
        'PIL',
        'numpy',
        'pyautogui',
        'keyboard',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Large ML/data stacks not used by this app.
        'torch',
        'torchvision',
        'torchaudio',
        'tensorflow',
        'pandas',
        'scipy',
        'matplotlib',
        'sklearn',
        'IPython',
        'jupyter',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GrowthDataScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # Keep console=True for the first test run so errors are visible.
    # Switch to console=False once confirmed working.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['./assets/appicon.ico']
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GrowthDataScanner',
)
