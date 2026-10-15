"""Janela principal."""
import tkinter as tk
from tkinter import ttk

from ..config import APP_TITLE, APP_VERSION, PALETTE as P
from ..settings import Settings
from .build_tab import BuildTab
from .icon_tab import IconTab
from .theme import apply_theme, load_logo


class GuyBuilderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = Settings()
        root.title(f"{APP_TITLE} • {APP_VERSION}")
        root.geometry("1120x900")
        root.minsize(980, 760)
        apply_theme(root)

        self.logo = load_logo(72)
        self._build_header()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        self.build_tab = BuildTab(self.notebook, self)
        self.icon_tab = IconTab(self.notebook, self)
        self.notebook.add(self.build_tab, text="  Build  Python → EXE  ")
        self.notebook.add(self.icon_tab, text="  Conversor PNG → ICO  ")

        if self.logo is not None:
            try:
                root.iconphoto(True, self.logo)
            except tk.TclError:
                pass
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_header(self):
        header = tk.Frame(self.root, bg=P["bg"])
        header.pack(fill="x", padx=24, pady=(18, 12))
        if self.logo is not None:
            tk.Label(header, image=self.logo, bg=P["bg"]).pack(side="left", padx=(0, 16))
        else:
            tk.Label(header, text="G", bg=P["bg"], fg=P["text"], font=("Segoe UI", 28, "bold")).pack(side="left", padx=(0, 16))
        titles = tk.Frame(header, bg=P["bg"])
        titles.pack(side="left", fill="x", expand=True)
        tk.Label(titles, text=APP_TITLE, bg=P["bg"], fg=P["text"], font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(titles, text="Transforme projetos Python em executáveis Windows independentes.",
                 bg=P["bg"], fg=P["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
        tk.Label(header, text="PYTHON  →  EXE", bg=P["primary_dark"], fg=P["text"], padx=12, pady=7,
                 font=("Segoe UI", 9, "bold")).pack(side="right", anchor="n")

    def on_close(self):
        if self.build_tab.building:
            from tkinter import messagebox
            if not messagebox.askyesno("Build em andamento", "Há um build em andamento. Cancelar e sair?"):
                return
            self.build_tab.cancel_build()
        self.settings.save()
        self.root.destroy()


def run_app():
    root = tk.Tk()
    GuyBuilderApp(root)
    root.mainloop()
