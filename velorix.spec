# -*- mode: python ; coding: utf-8 -*-
# ============================================================
#  VELORIX — PyInstaller Spec v2
#  Genereaza: dist\Velorix\Velorix.exe (one-folder)
#  Rulare: pyinstaller velorix.spec --noconfirm
# ============================================================

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

ROOT = os.path.dirname(os.path.abspath(SPEC))

added_files = [
    (os.path.join(ROOT, 'assets', 'fonts', 'DejaVuSans.ttf'),      'assets/fonts'),
    (os.path.join(ROOT, 'assets', 'fonts', 'DejaVuSans-Bold.ttf'), 'assets/fonts'),
    (os.path.join(ROOT, 'assets', 'velorix.ico'),                  'assets'),
    (os.path.join(ROOT, 'assets', 'logo_velorix.png'),             'assets'),
    (os.path.join(ROOT, 'assets', 'logo_velorix.svg'),             'assets'),
    (os.path.join(ROOT, 'assets', 'logo_velorix_dark.svg'),        'assets'),
    (os.path.join(ROOT, 'assets', 'icons'),                        'assets/icons'),
    (os.path.join(ROOT, 'assets', 'translations.py'),              'assets'),
    (os.path.join(ROOT, 'styles', 'style.qss'),                    'styles'),
]

added_files += collect_data_files('reportlab')
added_files += collect_data_files('fpdf')

hidden_imports = [
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtOpenGL',
    'PyQt5.QtPrintSupport',
    'PyQt5.sip',
    # DB
    'psycopg2',
    'psycopg2.extensions',
    'psycopg2._psycopg',
    # Securitate
    'bcrypt',
    # PDF
    'fpdf',
    'fpdf.fpdf',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'reportlab.lib.units',
    'reportlab.lib.colors',
    'reportlab.platypus',
    'reportlab.platypus.tables',
    'reportlab.platypus.flowables',
    # Excel
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    # XML (e-Factura)
    'lxml',
    'lxml.etree',
    # Imagine
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    # Env
    'dotenv',
    # Stdlib
    'ssl',
    'webbrowser',
    'sqlite3',
    'email',
    'smtplib',
    'json',
    'csv',
    'decimal',
    # Module interne Velorix
    'database',
    'migrations',
    'migrations_cloud',
    'migrations_facturare',
    'sync_manager',
    'backup_manager',
    'notification_manager',
    'efactura_service',
    'ui',
    'ui.login_window',
    'ui.main_window',
    'ui.session_manager',
    'ui.utils_toast',
    'ui.vin_decoder',
    'ui.export_contabil',
    'ui.data_marci_modele',
    'ui.data_specificatii',
    'ui.pages.page_dashboard',
    'ui.pages.page_clienti',
    'ui.pages.page_vehicule',
    'ui.pages.page_devize',
    'ui.pages.page_lucrari',
    'ui.pages.page_facturare',
    'ui.pages.page_stocuri',
    'ui.pages.page_rapoarte',
    'ui.pages.page_setari',
    'ui.pages.page_fisa_service',
    'ui.pages.page_biblioteca',
    'ui.pages.page_istoric_lucrari',
    'ui.dialogs.dialog_client',
    'ui.dialogs.dialog_vehicul',
    'ui.dialogs.dialog_lucrare',
    'ui.dialogs.dialog_factura',
    'ui.dialogs.dialog_incasare',
    'ui.dialogs.dialog_piesa',
    'ui.dialogs.dialog_programare',
    'ui.dialogs.dialog_verificari',
    'ui.dialogs.dialog_miscare_stoc',
    'ui.dialogs.dialog_selectare_deviz',
    'ui.pdf.pdf_factura',
    'ui.pdf.deviz_pdf',
    'ui.pdf.fisa_service_pdf',
    'ui.pdf.rar_pdf',
    'ui.pdf.chitanta_pdf',
    'ui.widgets.chart_widgets',
    'ui.widgets.sync_indicator',
    'ui.widgets.notification_bell',
    'ui.widgets.checkbox_header',
    'ui.widgets.selectable_table_controller',
    'ui.widgets.raport_mecanic_widget',
    'ui.widgets.tab_export_contabil',
    'ui.services.notification_service',
    'update_checker',
]

a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pyqtgraph',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
        'tkinter',
        'unittest',
        'test',
        'distutils',
        'setuptools',
        'pkg_resources',
        'pydoc',
        'doctest',
        'IPython',
        'jupyter',
        'notebook',
        'colorama',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Velorix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'assets', 'velorix.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Velorix',
)