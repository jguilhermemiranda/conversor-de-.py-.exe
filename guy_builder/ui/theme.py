"""Tema visual (paleta GUY) e logo embutido."""
import base64
import io
import tkinter as tk
from tkinter import ttk

from ..assets_data import LOGO_PNG_B64
from ..config import PALETTE as P


def apply_theme(root: tk.Misc):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=P["bg"])

    style.configure("TFrame", background=P["bg"])
    style.configure("Card.TFrame", background=P["surface"])
    style.configure("TLabel", background=P["surface"], foreground=P["text"], font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=P["surface"], foreground=P["muted"], font=("Segoe UI", 9))
    style.configure("Card.TLabelframe", background=P["surface"], bordercolor=P["border"],
                    lightcolor=P["border"], darkcolor=P["border"])
    style.configure("Card.TLabelframe.Label", background=P["surface"], foreground=P["text"],
                    font=("Segoe UI", 10, "bold"))
    style.configure("TEntry", fieldbackground=P["field"], foreground=P["text"], insertcolor=P["text"],
                    bordercolor=P["border"], lightcolor=P["border"], darkcolor=P["border"], padding=7)
    style.configure("TCombobox", fieldbackground=P["field"], foreground=P["text"], background=P["field"],
                    arrowcolor=P["text"], bordercolor=P["border"], padding=6)
    style.map("TCombobox", fieldbackground=[("readonly", P["field"])],
              foreground=[("readonly", P["text"])], selectbackground=[("readonly", P["field"])],
              selectforeground=[("readonly", P["text"])])
    style.configure("Primary.TButton", background=P["primary"], foreground="white", borderwidth=0,
                    padding=(20, 11), font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", P["primary_hover"]), ("disabled", P["border"])],
              foreground=[("disabled", "#9c869b")])
    style.configure("Secondary.TButton", background=P["field"], foreground=P["text"], borderwidth=1,
                    bordercolor=P["border"], padding=(12, 8), font=("Segoe UI", 9, "bold"))
    style.map("Secondary.TButton", background=[("active", P["primary_dark"]), ("disabled", P["surface"])],
              foreground=[("disabled", "#8e7a8d")])
    for kind in ("TCheckbutton", "TRadiobutton"):
        style.configure(kind, background=P["surface"], foreground=P["text"], font=("Segoe UI", 9))
        style.map(kind, background=[("active", P["surface"])], foreground=[("active", "white")])
    style.configure("TProgressbar", troughcolor=P["field"], background=P["primary"],
                    bordercolor=P["field"], lightcolor=P["primary"], darkcolor=P["primary"])
    style.configure("TNotebook", background=P["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=P["surface"], foreground=P["muted"],
                    padding=(18, 8), font=("Segoe UI", 10, "bold"), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", P["primary"]), ("active", P["primary_dark"])],
              foreground=[("selected", "white"), ("active", "white")])
    style.configure("Vertical.TScrollbar", background=P["primary_dark"], troughcolor=P["field"],
                    bordercolor=P["field"], arrowcolor=P["text"])


def load_logo(max_height: int = 72):
    """Logo embutido no código (não depende de arquivo externo). Retorna None se indisponível."""
    try:
        from PIL import Image, ImageTk
        image = Image.open(io.BytesIO(base64.b64decode(LOGO_PNG_B64))).convert("RGBA")
        resample = getattr(Image, "Resampling", Image).LANCZOS
        image.thumbnail((max_height * 2, max_height), resample)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None
