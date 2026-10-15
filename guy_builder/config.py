"""Constantes centrais do GUY Builder (configuração separada da lógica)."""
import os

APP_TITLE = "GUY Builder"
APP_VERSION = "3.0"

IS_WINDOWS = os.name == "nt"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""

# Versão mínima do Python usada para EMPACOTAR (o PyInstaller 6.x exige no mínimo isto).
MIN_PYTHON = (3, 8)
PYINSTALLER_REQUIREMENT = "pyinstaller>=6.0"

# Paleta do projeto GUY (+ tons derivados para texto/estado).
PALETTE = {
    "bg": "#1b0c1a",
    "surface": "#351834",
    "field": "#1b0c1a",
    "border": "#50234e",
    "primary": "#6a2f68",
    "primary_hover": "#7e3a7c",
    "primary_dark": "#50234e",
    "log_bg": "#000000",
    "text": "#f4edf4",
    "muted": "#c3adc2",
    "success": "#72e6b2",
    "warning": "#ffd479",
    "danger": "#ff7d9a",
}

# Pastas que nunca fazem parte do código-fonte da aplicação.
EXCLUDED_DIRS = frozenset({
    ".venv", "venv", "env", "__pycache__", "build", "dist", ".git", "node_modules",
    ".idea", ".vscode", "site-packages", ".mypy_cache", ".pytest_cache", "_guy_builder",
})

ENTRY_PRIORITY = ("main.py", "app.py", "run.py", "start.py", "__main__.py", "gui.py")

# Bibliotecas que indicam aplicação gráfica (usado só como SUGESTÃO de --windowed).
GUI_LIBS = frozenset({
    "tkinter", "customtkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
    "wx", "kivy", "pygame", "dearpygui",
})

# Nome de import -> nome no PyPI (apenas DICA de instalação; nunca é instalado automaticamente).
IMPORT_TO_PIP = {
    "PIL": "Pillow", "cv2": "opencv-python", "yaml": "PyYAML", "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4", "serial": "pyserial", "dotenv": "python-dotenv",
    "win32api": "pywin32", "win32con": "pywin32", "win32gui": "pywin32", "pythoncom": "pywin32",
    "Crypto": "pycryptodome", "dateutil": "python-dateutil", "docx": "python-docx",
    "fitz": "PyMuPDF", "skimage": "scikit-image", "usb": "pyusb", "magic": "python-magic",
}

ICO_SIZES = (16, 32, 48, 64, 128, 256)

TEMP_PREFIX = "guybuilder_"
TEMP_MARKER = ".guy_builder_workspace"
STALE_TEMP_HOURS = 24
