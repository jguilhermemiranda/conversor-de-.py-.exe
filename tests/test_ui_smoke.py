"""Smoke test da UI com Tkinter FALSO: valida ligações/fluxos (nomes, callbacks, eventos).
NÃO valida aparência nem layout real - isso exige abrir a janela no Windows."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class W:
    def __init__(self, *a, **k): self._d = {}
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        return lambda *a, **k: ()
    def __setitem__(self, k, v): self._d[k] = v
    def __getitem__(self, k): return self._d.get(k)
    def get(self, *a): return ""
    def curselection(self): return ()


class Var:
    def __init__(self, value="", **k): self.v = value
    def get(self): return self.v
    def set(self, v): self.v = v


def install_fakes():
    tk = types.ModuleType("tkinter"); ttk = types.ModuleType("tkinter.ttk")
    fd = types.ModuleType("tkinter.filedialog"); mb = types.ModuleType("tkinter.messagebox")
    for n in ("Tk", "Frame", "Label", "Listbox", "Text", "Misc", "Canvas"): setattr(tk, n, W)
    tk.StringVar, tk.BooleanVar, tk.TclError = Var, Var, type("TclError", (Exception,), {})
    for n in ("Frame", "Label", "Entry", "Button", "Combobox", "Checkbutton", "Radiobutton", "Progressbar",
              "Notebook", "LabelFrame", "Scrollbar", "Style"): setattr(ttk, n, W)
    tk.ttk, tk.filedialog, tk.messagebox = ttk, fd, mb
    for n in ("askdirectory", "askopenfilename", "askopenfilenames", "asksaveasfilename"): setattr(fd, n, lambda *a, **k: "")
    for n in ("showinfo", "showwarning", "showerror"): setattr(mb, n, mock.Mock())
    mb.askyesno = mock.Mock(return_value=False)
    imagetk = types.ModuleType("PIL.ImageTk"); imagetk.PhotoImage = lambda img: W()
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": fd,
                        "tkinter.messagebox": mb, "PIL.ImageTk": imagetk})
    import PIL; PIL.ImageTk = imagetk
    return fd, mb


class UiSmoke(unittest.TestCase):
    def test_flow(self):
        fd, mb = install_fakes()
        from guy_builder.ui.app import GuyBuilderApp
        from guy_builder.errors import BuildError
        from guy_builder.models import BuildResult
        app = GuyBuilderApp(W())
        bt, it = app.build_tab, app.icon_tab

        with tempfile.TemporaryDirectory() as t:
            proj = Path(t, "p"); proj.mkdir()
            (proj / "main.py").write_text("import tkinter\n")
            fd.askdirectory = lambda *a, **k: str(proj)
            bt.select_project()
            self.assertEqual(bt.entry_point.get(), "main.py")
            self.assertEqual(bt.app_name.get(), "main")
            self.assertFalse(bt.console.get())                       # sugestão: janela (usa tkinter)
            cfg = bt._make_config()
            self.assertEqual(cfg.output_dir, proj / "dist")
            self.assertFalse(cfg.console)

            fd.askopenfilename = lambda *a, **k: str(proj / "main.py")
            bt.select_py(); self.assertEqual(bt.entry_point.get(), "main.py")

            bt._on_done(BuildResult(False, error=BuildError("Empacotamento", "x", hint="y", fix_action="install_pyinstaller")))
            bt._on_done(BuildResult(False, cancelled=True))
            bt._on_done(BuildResult(True, artifact=proj / "dist" / "x.exe", duration=3))
            bt.events.put(("log", "info", "linha")); bt.events.put(("progress", 50, "etapa"))
            bt._poll()

            png = Path(t, "logo.png")
            from PIL import Image
            Image.new("RGBA", (300, 300), (9, 9, 9, 255)).save(png)
            fd.askopenfilename = lambda *a, **k: str(png)
            it.choose_png(); self.assertEqual(it.info_vars["Resolução"].get(), "300×300px")
            it.convert(); self.assertIsNotNone(it.result)
            out = Path(t, "logo.ico")
            fd.asksaveasfilename = lambda *a, **k: str(out)
            it.save(); self.assertTrue(out.is_file())
            it.use_in_build(); self.assertEqual(bt.icon_file.get(), str(out))


if __name__ == "__main__":
    unittest.main()
