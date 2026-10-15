"""Aba PNG -> ICO: selecionar, pré-visualizar, converter, pré-visualizar o .ico e salvar."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional

from ..config import ICO_SIZES, PALETTE as P
from ..icon_tools import IcoResult, ImageInfo, build_ico_bytes, load_rgba, read_image_info
from ..preview import fit_on_checker, ico_strip

PREVIEW_BOX = (300, 300)


def _fmt_size(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 1_048_576 else f"{n / 1_048_576:.2f} MB"


class IconTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self.png_path = tk.StringVar()
        self.size_vars: Dict[int, tk.BooleanVar] = {s: tk.BooleanVar(value=True) for s in ICO_SIZES}
        self.info_vars = {k: tk.StringVar(value="—") for k in ("Resolução", "Formato", "Modo de cor", "Tamanho do arquivo")}
        self.ico_info = tk.StringVar(value="—")
        self.warning_text = tk.StringVar(value="")

        self.image = None                       # PIL RGBA original
        self.result: Optional[IcoResult] = None
        self.saved_path: Optional[Path] = None
        self._photos = {}                       # evita que o Tk descarte as imagens

        self._build_ui()

    def _build_ui(self):
        top = ttk.LabelFrame(self, text="  01  •  Imagem PNG  ", style="Card.TLabelframe", padding=14)
        top.pack(fill="x", pady=(10, 10))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Arquivo PNG").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(top, textvariable=self.png_path, state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Button(top, text="Selecionar PNG", style="Secondary.TButton", command=self.choose_png).grid(
            row=0, column=2, padx=(8, 0))
        info = ttk.Frame(top, style="Card.TFrame")
        info.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))
        for i, (label, var) in enumerate(self.info_vars.items()):
            ttk.Label(info, text=f"{label}:", style="Muted.TLabel").grid(row=0, column=i * 2, sticky="w", padx=(0, 4))
            ttk.Label(info, textvariable=var).grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 22))

        sizes = ttk.LabelFrame(self, text="  02  •  Resoluções do ícone  ", style="Card.TLabelframe", padding=14)
        sizes.pack(fill="x", pady=(0, 10))
        for size in ICO_SIZES:
            ttk.Checkbutton(sizes, text=f"{size}×{size}", variable=self.size_vars[size]).pack(side="left", padx=(0, 16))

        previews = tk.Frame(self, bg=P["bg"])
        previews.pack(fill="both", expand=True)
        previews.columnconfigure(1, weight=1)
        left = ttk.LabelFrame(previews, text="  Original (PNG)  ", style="Card.TLabelframe", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.png_view = tk.Label(left, bg=P["surface"], fg=P["muted"], text="Nenhuma imagem selecionada",
                                 width=42, height=16)
        self.png_view.pack()
        right = ttk.LabelFrame(previews, text="  Resultado (ICO)  ", style="Card.TLabelframe", padding=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.ico_view = tk.Label(right, bg=P["surface"], fg=P["muted"], text="Converta para ver as resoluções",
                                 height=16)
        self.ico_view.pack(fill="both", expand=True)
        ttk.Label(right, textvariable=self.ico_info, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        tk.Label(right, textvariable=self.warning_text, bg=P["surface"], fg=P["warning"], wraplength=520,
                 justify="left", font=("Segoe UI", 9)).pack(anchor="w")

        actions = tk.Frame(self, bg=P["bg"])
        actions.pack(fill="x", pady=(10, 4))
        self.convert_button = ttk.Button(actions, text="Converter para ICO", style="Primary.TButton",
                                         command=self.convert, state="disabled")
        self.convert_button.pack(side="left")
        self.save_button = ttk.Button(actions, text="Salvar ICO...", style="Secondary.TButton",
                                      command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=8)
        self.use_button = ttk.Button(actions, text="Usar como ícone do build", style="Secondary.TButton",
                                     command=self.use_in_build, state="disabled")
        self.use_button.pack(side="left")

    # ------------------------------------------------------------------
    def _show(self, label: tk.Label, pil_image, key: str):
        from PIL import ImageTk
        photo = ImageTk.PhotoImage(pil_image)
        self._photos[key] = photo
        label.configure(image=photo, text="", width=0, height=0)

    def choose_png(self):
        file = filedialog.askopenfilename(title="Selecione a imagem PNG",
                                          filetypes=[("PNG", "*.png"), ("Imagens", "*.png *.jpg *.jpeg *.bmp *.webp"),
                                                     ("Todos os arquivos", "*.*")])
        if not file:
            return
        try:
            info: ImageInfo = read_image_info(file)
            self.image = load_rgba(file)
        except Exception as error:
            messagebox.showerror("Imagem inválida", f"Não foi possível abrir a imagem:\n\n{error}")
            return
        self.png_path.set(file)
        self.info_vars["Resolução"].set(f"{info.width}×{info.height}px")
        self.info_vars["Formato"].set(info.format)
        self.info_vars["Modo de cor"].set(info.mode + (" (com transparência)" if info.has_alpha else ""))
        self.info_vars["Tamanho do arquivo"].set(_fmt_size(info.file_size))
        self._show(self.png_view, fit_on_checker(self.image, PREVIEW_BOX), "png")
        self.result = None
        self.saved_path = None
        self.ico_view.configure(image="", text="Converta para ver as resoluções")
        self.ico_info.set("—")
        self.warning_text.set("")
        self.convert_button.configure(state="normal")
        self.save_button.configure(state="disabled")
        self.use_button.configure(state="disabled")

    def convert(self):
        if self.image is None:
            return
        sizes = [s for s, var in self.size_vars.items() if var.get()]
        if not sizes:
            messagebox.showwarning("Resoluções", "Marque ao menos uma resolução.")
            return
        try:
            self.result = build_ico_bytes(self.image, sizes)
            self._show(self.ico_view, ico_strip(self.result.data), "ico")
        except Exception as error:
            messagebox.showerror("Falha na conversão", str(error))
            return
        self.saved_path = None
        self.ico_info.set(f"Resoluções: {', '.join(f'{s}×{s}' for s in self.result.sizes)}  •  "
                          f"{_fmt_size(len(self.result.data))}  •  ainda não salvo")
        self.warning_text.set("\n".join("⚠ " + w for w in self.result.warnings))
        self.save_button.configure(state="normal")
        self.use_button.configure(state="disabled")

    def save(self):
        if not self.result:
            return
        default = Path(self.png_path.get()).with_suffix(".ico")
        file = filedialog.asksaveasfilename(title="Salvar ícone", defaultextension=".ico",
                                            initialdir=str(default.parent), initialfile=default.name,
                                            filetypes=[("Ícone Windows", "*.ico")])
        if not file:
            return
        try:
            Path(file).write_bytes(self.result.data)
        except OSError as error:
            messagebox.showerror("Não foi possível salvar", f"{error}\n\nVerifique permissões e o caminho escolhido.")
            return
        self.saved_path = Path(file)
        self.ico_info.set(f"Salvo em {file}  •  {_fmt_size(len(self.result.data))}")
        self.use_button.configure(state="normal")

    def use_in_build(self):
        if self.saved_path:
            self.app.build_tab.icon_file.set(str(self.saved_path))
            self.app.notebook.select(self.app.build_tab)
