"""Aba de build Python -> EXE."""
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from ..build_runner import BuildRunner
from ..config import APP_TITLE, PALETTE as P
from ..errors import BuildError
from ..logger import BuildLogger
from ..models import BuildConfig, BuildResult, ExtraData
from ..project import pick_default_entry, sanitize_name, scan_entrypoints, suggest_windowed

LOG_COLORS = {"info": P["text"], "ok": P["success"], "warn": P["warning"], "error": P["danger"],
              "cmd": "#d9a8d6", "raw": P["muted"]}


def _card(parent, title: str) -> ttk.LabelFrame:
    return ttk.LabelFrame(parent, text=f"  {title}  ", style="Card.TLabelframe", padding=14)


class BuildTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self.settings = app.settings

        self.project_dir = tk.StringVar()
        self.entry_point = tk.StringVar()
        self.app_name = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.icon_file = tk.StringVar()
        self.hidden_imports = tk.StringVar()
        self.python_path = tk.StringVar(value=self.settings.get("python_path", ""))
        self.console = tk.BooleanVar(value=False)       # False = janela (sem console)
        self.onefile = tk.BooleanVar(value=True)
        self.clean_cache = tk.BooleanVar(value=True)

        self.extra_items: List[ExtraData] = []
        self.entry_candidates: List[Path] = []
        self.events: "queue.Queue" = queue.Queue()
        self.runner: Optional[BuildRunner] = None
        self.building = False
        self.last_artifact: Optional[Path] = None

        self._build_ui()
        self.after(60, self._poll)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        body = ttk.Frame(self, style="TFrame")
        body.pack(fill="both", expand=True, pady=(10, 0))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        # --- 01 Projeto
        project = _card(body, "01  •  Arquivo / Projeto")
        project.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        project.columnconfigure(1, weight=1)
        ttk.Label(project, text="Pasta do projeto").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(project, textvariable=self.project_dir).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Button(project, text="Selecionar pasta", style="Secondary.TButton",
                   command=self.select_project).grid(row=0, column=2, padx=(8, 0), pady=5)
        ttk.Label(project, text="Arquivo de entrada").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.entry_combo = ttk.Combobox(project, textvariable=self.entry_point, state="readonly")
        self.entry_combo.grid(row=1, column=1, sticky="ew", pady=5)
        self.entry_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_entry_changed())
        ttk.Button(project, text="Selecionar .PY", style="Secondary.TButton",
                   command=self.select_py).grid(row=1, column=2, padx=(8, 0), pady=5)
        ttk.Label(project, style="Muted.TLabel", wraplength=420, justify="left",
                  text="Escolha um .py avulso ou a pasta de um projeto (o builder sugere main.py, app.py, "
                       "run.py...). Imports locais são seguidos automaticamente.").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # --- 02 Configuração
        config = _card(body, "02  •  Aplicativo")
        config.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        config.columnconfigure(1, weight=1)
        ttk.Label(config, text="Nome do EXE").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(config, textvariable=self.app_name).grid(row=0, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Label(config, text="Ícone (.ico)").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(config, textvariable=self.icon_file).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Button(config, text="Selecionar Ícone", style="Secondary.TButton",
                   command=self.select_icon).grid(row=1, column=2, padx=(8, 0), pady=5)
        ttk.Label(config, text="Tipo").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        kind = ttk.Frame(config, style="Card.TFrame")
        kind.grid(row=2, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Radiobutton(kind, text="Console", variable=self.console, value=True).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(kind, text="Janela / sem console", variable=self.console, value=False).pack(side="left")
        ttk.Label(config, text="Imports extras").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(config, textvariable=self.hidden_imports).grid(row=3, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Label(config, text="Interpretador Python").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(config, textvariable=self.python_path).grid(row=4, column=1, sticky="ew", pady=5)
        ttk.Button(config, text="Escolher", style="Secondary.TButton",
                   command=self.select_python).grid(row=4, column=2, padx=(8, 0), pady=5)
        ttk.Label(config, style="Muted.TLabel", wraplength=420, justify="left",
                  text="Imports extras: separados por vírgula (imports dinâmicos). Interpretador: opcional; "
                       "vazio = detecção automática (venv do projeto, py launcher, PATH).").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # --- 03 Saída e arquivos adicionais
        out = _card(body, "03  •  Saída e arquivos adicionais")
        out.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        out.columnconfigure(1, weight=1)
        ttk.Label(out, text="Pasta de saída").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(out, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Button(out, text="Selecionar saída", style="Secondary.TButton",
                   command=self.select_output).grid(row=0, column=2, padx=(8, 0), pady=5)
        opts = ttk.Frame(out, style="Card.TFrame")
        opts.grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 4))
        ttk.Checkbutton(opts, text="Executável único (--onefile)", variable=self.onefile).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(opts, text="Limpar cache do PyInstaller (--clean)", variable=self.clean_cache).pack(side="left")
        ttk.Label(out, text="Arquivos adicionais").grid(row=2, column=0, sticky="nw", padx=(0, 10), pady=5)
        self.extra_box = tk.Listbox(out, height=3, bg=P["field"], fg=P["text"], relief="flat",
                                    selectbackground=P["primary"], highlightthickness=1,
                                    highlightbackground=P["border"], font=("Segoe UI", 9))
        self.extra_box.grid(row=2, column=1, sticky="ew", pady=5)
        btns = ttk.Frame(out, style="Card.TFrame")
        btns.grid(row=2, column=2, sticky="n", padx=(8, 0), pady=5)
        ttk.Button(btns, text="+ Arquivo", style="Secondary.TButton", command=self.add_extra_file).pack(fill="x")
        ttk.Button(btns, text="+ Pasta", style="Secondary.TButton", command=self.add_extra_dir).pack(fill="x", pady=3)
        ttk.Button(btns, text="Remover", style="Secondary.TButton", command=self.remove_extra).pack(fill="x")

        # --- Ações + log
        actions = tk.Frame(body, bg=P["bg"])
        actions.grid(row=2, column=0, columnspan=2, sticky="nsew")
        actions.columnconfigure(0, weight=1)
        actions.rowconfigure(2, weight=1)

        row = tk.Frame(actions, bg=P["bg"])
        row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.build_button = ttk.Button(row, text="  ⚡  GERAR EXECUTÁVEL  ", style="Primary.TButton",
                                       command=self.start_build)
        self.build_button.pack(side="left")
        self.cancel_button = ttk.Button(row, text="Cancelar", style="Secondary.TButton",
                                        command=self.cancel_build, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(row, text="Abrir saída", style="Secondary.TButton",
                                      command=self.open_output, state="disabled")
        self.open_button.pack(side="left")
        ttk.Button(row, text="Copiar log", style="Secondary.TButton", command=self.copy_log).pack(side="left", padx=8)
        self.status_label = tk.Label(row, text="Pronto.", bg=P["bg"], fg=P["muted"], font=("Segoe UI", 9))
        self.status_label.pack(side="right")

        prog = tk.Frame(actions, bg=P["bg"])
        prog.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        prog.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(prog, maximum=100, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew")
        self.stage_label = tk.Label(prog, text="", bg=P["bg"], fg=P["text"], font=("Segoe UI", 9), width=28, anchor="e")
        self.stage_label.grid(row=0, column=1, padx=(10, 0))

        card = tk.Frame(actions, bg=P["surface"], highlightbackground=P["border"], highlightthickness=1)
        card.grid(row=2, column=0, sticky="nsew")
        tk.Label(card, text="LOG DO BUILD", bg=P["surface"], fg=P["text"], font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=12, pady=(8, 4))
        frame = tk.Frame(card, bg=P["surface"])
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log = tk.Text(frame, wrap="word", bg=P["log_bg"], fg=P["text"], insertbackground="white",
                           selectbackground=P["primary_dark"], font=("Cascadia Mono", 9), relief="flat",
                           borderwidth=0, padx=10, pady=8, height=10)
        self.log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log.yview)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)
        for level, color in LOG_COLORS.items():
            self.log.tag_configure(level, foreground=color)

    # ------------------------------------------------------------------ seleção
    def _initial(self, key: str) -> Optional[str]:
        value = self.settings.get(key)
        return value if value and os.path.isdir(value) else None

    def select_project(self):
        directory = filedialog.askdirectory(title="Selecione a pasta do projeto Python",
                                            initialdir=self._initial("last_project"))
        if directory:
            self.project_dir.set(directory)
            self.output_dir.set(str(Path(directory) / "dist"))
            self.scan_project()

    def select_py(self):
        file = filedialog.askopenfilename(title="Selecione o arquivo .py",
                                          initialdir=self._initial("last_project"),
                                          filetypes=[("Python", "*.py"), ("Todos os arquivos", "*.*")])
        if not file:
            return
        path = Path(file)
        self.project_dir.set(str(path.parent))
        self.entry_candidates = [path]
        self.entry_combo["values"] = [path.name]
        self.entry_point.set(path.name)
        self.output_dir.set(str(path.parent / "dist"))
        self._on_entry_changed(rename=True)

    def scan_project(self):
        directory = Path(self.project_dir.get()).expanduser()
        if not directory.is_dir():
            messagebox.showwarning("Pasta inválida", "Selecione uma pasta de projeto válida.")
            return
        files = scan_entrypoints(directory)
        self.entry_candidates = files
        self.entry_combo["values"] = [str(p.relative_to(directory)) for p in files]
        if not files:
            self.entry_point.set("")
            messagebox.showerror("Nenhum Python encontrado", "Não encontrei arquivos .py neste projeto.")
            return
        self.entry_point.set(str(pick_default_entry(files).relative_to(directory)))
        self.status_label.configure(text=f"{len(files)} arquivo(s) Python encontrado(s).")
        self._on_entry_changed(rename=True)

    def _on_entry_changed(self, rename: bool = False):
        entry = self.entry_point.get()
        if not entry:
            return
        if rename and not self.app_name.get().strip():
            self.app_name.set(sanitize_name(Path(entry).stem))
        try:
            project = Path(self.project_dir.get())
            windowed = suggest_windowed(project / entry, project)
            self.console.set(not windowed)
            self._ui_log("info", f"Entrada: {entry} — sugestão: "
                                 f"{'janela (usa biblioteca gráfica)' if windowed else 'console'}. Ajuste se necessário.")
        except Exception:
            pass

    def select_icon(self):
        file = filedialog.askopenfilename(title="Selecione o ícone", filetypes=[("Ícone Windows", "*.ico"),
                                                                              ("Todos os arquivos", "*.*")])
        if file:
            self.icon_file.set(file)

    def select_output(self):
        directory = filedialog.askdirectory(title="Selecione a pasta de saída", initialdir=self._initial("last_output"))
        if directory:
            self.output_dir.set(directory)

    def select_python(self):
        file = filedialog.askopenfilename(title="Selecione o python.exe",
                                          filetypes=[("Python", "python*.exe"), ("Executáveis", "*.exe"),
                                                     ("Todos os arquivos", "*.*")])
        if file:
            self.python_path.set(file)

    def _refresh_extra(self):
        self.extra_box.delete(0, "end")
        for item in self.extra_items:
            self.extra_box.insert("end", f"{item.source}   →   {item.dest}")

    def add_extra_file(self):
        for file in filedialog.askopenfilenames(title="Arquivos adicionais"):
            self.extra_items.append(ExtraData(Path(file), "."))
        self._refresh_extra()

    def add_extra_dir(self):
        directory = filedialog.askdirectory(title="Pasta adicional")
        if directory:
            self.extra_items.append(ExtraData(Path(directory), Path(directory).name))
            self._refresh_extra()

    def remove_extra(self):
        for index in reversed(self.extra_box.curselection()):
            del self.extra_items[index]
        self._refresh_extra()

    # ------------------------------------------------------------------ log / eventos
    def _ui_log(self, level: str, text: str):
        self.events.put(("log", level, f"[{time.strftime('%H:%M:%S')}] {text}"))

    def _poll(self):
        try:
            while True:
                kind, *payload = self.events.get_nowait()
                if kind == "log":
                    level, text = payload
                    self.log.insert("end", text + "\n", level)
                    self.log.see("end")
                elif kind == "progress":
                    pct, label = payload
                    self.progress["value"] = pct
                    self.stage_label.configure(text=label)
                elif kind == "done":
                    self._on_done(payload[0])
                elif kind == "installed":
                    self._set_busy(False)
                    self.status_label.configure(text="PyInstaller instalado." if payload[0] else "Falha na instalação.")
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log.get("1.0", "end"))
        self.status_label.configure(text="Log copiado.")

    # ------------------------------------------------------------------ build
    def _make_config(self) -> Optional[BuildConfig]:
        project_text = self.project_dir.get().strip()
        if not project_text or not self.entry_point.get().strip():
            messagebox.showwarning("Projeto ausente", "Selecione um .py ou a pasta do projeto.")
            return None
        if not self.output_dir.get().strip():
            messagebox.showwarning("Saída ausente", "Escolha a pasta de saída.")
            return None
        project = Path(project_text).expanduser()
        python = self.python_path.get().strip()
        icon = self.icon_file.get().strip()
        return BuildConfig(
            entry=(project / self.entry_point.get()),
            project_root=project,
            name=sanitize_name(self.app_name.get()),
            output_dir=Path(self.output_dir.get()).expanduser(),
            icon=Path(icon) if icon else None,
            console=self.console.get(),
            onefile=self.onefile.get(),
            clean_cache=self.clean_cache.get(),
            hidden_imports=[h.strip() for h in self.hidden_imports.get().split(",") if h.strip()],
            extra_data=list(self.extra_items),
            python_override=Path(python) if python else None,
        )

    def _set_busy(self, busy: bool):
        self.building = busy
        self.build_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")

    def _new_runner(self, cfg: BuildConfig) -> BuildRunner:
        logger = BuildLogger(lambda level, line: self.events.put(("log", level, line)))
        return BuildRunner(cfg, logger, lambda pct, label: self.events.put(("progress", pct, label)))

    def start_build(self):
        if self.building:
            return
        cfg = self._make_config()
        if cfg is None:
            return
        self.settings.set("last_project", str(cfg.project_root))
        self.settings.set("last_output", str(cfg.output_dir))
        self.settings.set("python_path", self.python_path.get().strip())
        self.settings.save()

        self.log.delete("1.0", "end")
        self.progress["value"] = 0
        self.open_button.configure(state="disabled")
        self.status_label.configure(text="Gerando executável...")
        self._set_busy(True)
        self.runner = self._new_runner(cfg)
        threading.Thread(target=self._worker, args=(self.runner,), daemon=True).start()

    def _worker(self, runner: BuildRunner):
        self.events.put(("done", runner.run()))

    def cancel_build(self):
        if self.runner and self.building:
            self.status_label.configure(text="Cancelando...")
            self.runner.cancel()

    def _on_done(self, result: BuildResult):
        self._set_busy(False)
        if result.success:
            self.last_artifact = result.artifact
            self.open_button.configure(state="normal")
            self.status_label.configure(text=f"Concluído em {result.duration:.0f}s.")
            messagebox.showinfo(APP_TITLE, f"Executável criado com sucesso!\n\n{result.artifact}")
        elif result.cancelled:
            self.progress["value"] = 0
            self.status_label.configure(text="Build cancelado.")
        else:
            err: BuildError = result.error  # type: ignore[assignment]
            self.status_label.configure(text=f"Falhou: {err.stage}")
            text = f"Etapa: {err.stage}\n\n{err.message}"
            if err.hint:
                text += f"\n\nSolução: {err.hint}"
            if err.fix_action == "install_pyinstaller":
                if messagebox.askyesno("PyInstaller ausente", text + "\n\nInstalar o PyInstaller agora?"):
                    self._start_install()
                return
            messagebox.showerror("Falha no build", text)

    def _start_install(self):
        if self.runner is None:
            return
        self._set_busy(True)
        self.status_label.configure(text="Instalando PyInstaller...")
        runner = self.runner

        def work():
            self.events.put(("installed", runner.install_pyinstaller()))

        threading.Thread(target=work, daemon=True).start()

    def open_output(self):
        directory = Path(self.output_dir.get()).expanduser()
        if not directory.is_dir():
            messagebox.showwarning("Pasta não encontrada", "A pasta de saída não existe.")
            return
        os.startfile(str(directory))  # type: ignore[attr-defined]  # Windows

