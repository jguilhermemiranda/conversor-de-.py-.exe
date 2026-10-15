"""Testes do núcleo (sem GUI). Rodar: python -m unittest discover -s tests -v

Os testes de pipeline usam um PyInstaller FALSO instalado em um venv descartável: validam a
orquestração do builder (Python, dependências, staging, publicação, limpeza, cancelamento), NÃO o
PyInstaller real. O teste real em Windows está em tests/e2e_windows.py.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from guy_builder import cleaner, process_utils  # noqa: E402
from guy_builder.build_runner import BuildRunner  # noqa: E402
from guy_builder.config import EXE_SUFFIX, TEMP_PREFIX  # noqa: E402
from guy_builder.dependencies import analyze  # noqa: E402
from guy_builder.errors import BuildError, classify_failure  # noqa: E402
from guy_builder.icon_tools import build_ico_bytes, is_valid_ico  # noqa: E402
from guy_builder.logger import BuildLogger  # noqa: E402
from guy_builder.models import BuildConfig  # noqa: E402
from guy_builder.preview import ico_frames, ico_strip  # noqa: E402
from guy_builder.project import sanitize_name, scan_entrypoints  # noqa: E402
from guy_builder.python_finder import find_python  # noqa: E402

STUB = '''
import json, os, sys, time
a = sys.argv[1:]
def opt(n): return a[a.index(n) + 1]
if "--version" in a:
    print("6.99.0-stub"); sys.exit(0)
if os.environ.get("STUB_FAIL"):
    print("ERROR: boom"); print("ModuleNotFoundError: No module named 'foo'"); sys.exit(1)
print("INFO: stub PyInstaller"); sys.stdout.flush()
if os.environ.get("STUB_SLEEP"):
    time.sleep(60)
name, dist = opt("--name"), opt("--distpath")
suffix = ".exe" if os.name == "nt" else ""
os.makedirs(dist, exist_ok=True)
if "--onefile" in a:
    open(os.path.join(dist, name + suffix), "wb").write(b"MZ-stub")
else:
    d = os.path.join(dist, name); os.makedirs(os.path.join(d, "_internal"))
    open(os.path.join(d, name + suffix), "wb").write(b"MZ-stub")
sys.exit(0)
'''


def write(path: Path, text: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class IconTests(unittest.TestCase):
    def test_multires_and_alpha(self):
        from PIL import Image
        img = Image.new("RGBA", (300, 500), (0, 0, 0, 0))
        img.paste((200, 30, 30, 255), (100, 100, 200, 300))
        res = build_ico_bytes(img)
        self.assertEqual(res.sizes, [16, 32, 48, 64, 128, 256])
        self.assertTrue(any("quadrada" in w for w in res.warnings))
        frames = dict(ico_frames(res.data))
        self.assertEqual(frames[256].getpixel((0, 0))[3], 0)          # transparência preservada
        self.assertGreater(frames[256].getpixel((128, 128))[3], 200)  # miolo opaco
        self.assertEqual(ico_strip(res.data).mode, "RGB")

    def test_small_source_warns_and_still_complete(self):
        from PIL import Image
        res = build_ico_bytes(Image.new("RGBA", (64, 64), (1, 2, 3, 255)))
        self.assertIn(256, res.sizes)
        self.assertTrue(any("ampliada" in w for w in res.warnings))

    def test_is_valid_ico(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            good = Path(t, "a.ico"); good.write_bytes(build_ico_bytes(Image.new("RGBA", (256, 256))).data)
            fake = Path(t, "b.ico"); fake.write_bytes(b"\x89PNG\r\n\x1a\n")
            self.assertTrue(is_valid_ico(good))
            self.assertFalse(is_valid_ico(fake))
            self.assertFalse(is_valid_ico(Path(t, "nao_existe.ico")))


class AnalysisTests(unittest.TestCase):
    def test_imports_local_relative_optional_and_third_party(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            write(root / "main.py", "import os, requests\nfrom app import core\nfrom app.util import helper\n"
                                    "try:\n    import ujson\nexcept ImportError:\n    ujson = None\n")
            write(root / "app" / "__init__.py")
            write(root / "app" / "core.py", "from . import util\nimport numpy\n")
            write(root / "app" / "util.py", "from PIL import Image\nhelper = 1\n")
            res = analyze(root / "main.py", [root])
            self.assertEqual(sorted(res.required), ["PIL", "numpy", "os", "requests"])
            self.assertEqual(sorted(res.optional), ["ujson"])
            self.assertNotIn("app", res.required)
            self.assertEqual(len(res.files), 4)   # main + app/__init__ + core + util

    def test_syntax_error_reported(self):
        with tempfile.TemporaryDirectory() as t:
            write(Path(t, "main.py"), "def x(:\n  pass\n")
            res = analyze(Path(t, "main.py"), [Path(t)])
            self.assertEqual(len(res.syntax_errors), 1)

    def test_scan_ignores_excluded_dirs_but_not_ancestors(self):
        with tempfile.TemporaryDirectory() as t:
            proj = Path(t, "env", "meu_projeto")      # ancestral chamado "env" (bug do código antigo)
            write(proj / "main.py"); write(proj / ".venv" / "x.py"); write(proj / "sub" / "z.py")
            found = [p.relative_to(proj).as_posix() for p in scan_entrypoints(proj)]
            self.assertEqual(found, ["main.py", "sub/z.py"])

    def test_sanitize(self):
        self.assertEqual(sanitize_name("GUY Builder"), "GUY Builder")
        self.assertEqual(sanitize_name("a/b:c"), "a_b_c")
        self.assertEqual(sanitize_name("  "), "MeuAplicativo")

    def test_classify(self):
        msg, hint, fix = classify_failure(["ModuleNotFoundError: No module named 'PIL.Image'"])
        self.assertIn("PIL", msg); self.assertIn("Pillow", hint)
        self.assertEqual(classify_failure(["No module named PyInstaller"])[2], "install_pyinstaller")
        self.assertIn("Permissão", classify_failure(["PermissionError: [WinError 5] Access is denied"])[0])


class SafetyTests(unittest.TestCase):
    def test_clean_env_drops_pyinstaller_vars(self):
        with mock.patch.dict(os.environ, {"_MEIPASS2": "x", "_PYI_APPLICATION_HOME_DIR": "y", "KEEP": "1"}):
            env = process_utils.clean_env()
        self.assertNotIn("_MEIPASS2", env); self.assertNotIn("_PYI_APPLICATION_HOME_DIR", env)
        self.assertEqual(env["KEEP"], "1")

    def test_workspace_removal_is_restricted(self):
        log = BuildLogger()
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(cleaner.remove_workspace(Path(t), log))       # sem marcador/prefixo
            self.assertTrue(Path(t).exists())
        ws = cleaner.make_workspace()
        self.assertTrue(cleaner.remove_workspace(ws, log)); self.assertFalse(ws.exists())

    def test_publish_refuses_foreign_dir(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t, "out"); (out / "App").mkdir(parents=True); (out / "App" / "meu_arquivo.txt").write_text("x")
            staged = Path(t, "staged"); (staged / "_internal").mkdir(parents=True); (staged / ("App" + EXE_SUFFIX)).write_text("x")
            cfg = BuildConfig(entry=Path("x.py"), project_root=Path(t), name="App", output_dir=out, onefile=False)
            with self.assertRaises(BuildError):
                cleaner.publish_artifact(staged, cfg, BuildLogger())
            self.assertTrue((out / "App" / "meu_arquivo.txt").exists())   # nada foi apagado

    def test_frozen_self_is_never_a_python_candidate(self):
        fake_exe = sys.executable
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch("guy_builder.python_finder.shutil.which", return_value=None), \
                mock.patch.dict(os.environ, {"PATH": ""}):
            # override == próprio "exe" congelado -> deve ser recusado, sem fallback
            with mock.patch.object(sys, "executable", fake_exe):
                with self.assertRaises(BuildError):
                    find_python(None, Path(fake_exe), BuildLogger())


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        venv = Path(cls.tmp.name, "venv")
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
        cls.bindir = venv / ("Scripts" if os.name == "nt" else "bin")
        cls.venv_python = cls.bindir / ("python.exe" if os.name == "nt" else "python")
        purelib = subprocess.run([str(cls.venv_python), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        write(Path(purelib, "PyInstaller", "__init__.py"))
        write(Path(purelib, "PyInstaller", "__main__.py"), STUB)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.temp_area = tempfile.TemporaryDirectory()
        self._old_tmp = tempfile.tempdir
        tempfile.tempdir = self.temp_area.name        # isola os temporários do builder
        self.addCleanup(self._restore)
        self.proj = self.root / "proj"
        write(self.proj / "main.py", "import json\nfrom helper import f\nprint(f())\n")
        write(self.proj / "helper.py", "def f(): return 1\n")
        self.out = self.root / "out"

    def _restore(self):
        tempfile.tempdir = self._old_tmp
        self.temp_area.cleanup(); self.work.cleanup()

    def cfg(self, **kw):
        base = dict(entry=self.proj / "main.py", project_root=self.proj, name="Meu App", output_dir=self.out,
                    python_override=self.venv_python)
        base.update(kw)
        return BuildConfig(**base)

    def leftovers(self):
        return [p for p in Path(self.temp_area.name).glob(TEMP_PREFIX + "*")]

    def test_onefile_success_and_cleanup(self):
        log = BuildLogger()
        res = BuildRunner(self.cfg(), log).run()
        self.assertTrue(res.success, log.text())
        self.assertEqual(res.artifact, self.out / ("Meu App" + EXE_SUFFIX))
        self.assertTrue(res.artifact.is_file())
        self.assertEqual(self.leftovers(), [])                       # temporários removidos
        self.assertFalse((self.proj / "build").exists() or (self.proj / "dist").exists())  # projeto intocado
        self.assertIn("-m PyInstaller", log.text())

    def test_onedir_and_rebuild_replaces_previous(self):
        for _ in range(2):
            res = BuildRunner(self.cfg(onefile=False), BuildLogger()).run()
            self.assertTrue(res.success)
        self.assertTrue((self.out / "Meu App" / ("Meu App" + EXE_SUFFIX)).is_file())

    def test_frozen_builder_uses_real_python_not_itself(self):
        """Regressão do ciclo: com o builder 'congelado', o Python do build NÃO pode ser sys.executable."""
        fake_builder_exe = self.root / "GUY Builder.exe"
        fake_builder_exe.write_bytes(b"not python")
        log = BuildLogger()
        env_path = str(self.bindir) + os.pathsep + os.environ.get("PATH", "")
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", str(fake_builder_exe)), \
                mock.patch.dict(os.environ, {"PATH": env_path}):
            res = BuildRunner(self.cfg(python_override=None), log).run()
        self.assertTrue(res.success, log.text())
        cmd_lines = [l for l in log.lines if "Comando:" in l]
        self.assertTrue(cmd_lines)
        self.assertNotIn("GUY Builder.exe", cmd_lines[0])
        self.assertIn(str(self.bindir), cmd_lines[0])

    def test_refuses_to_overwrite_running_builder(self):
        self.out.mkdir()
        target = self.out / ("GUY Builder" + EXE_SUFFIX)
        target.write_bytes(b"running")
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", str(target)):
            res = BuildRunner(self.cfg(name="GUY Builder"), BuildLogger()).run()
        self.assertFalse(res.success)
        self.assertEqual(res.error.stage, "Validação")
        self.assertEqual(target.read_bytes(), b"running")

    def test_missing_dependency_is_reported_before_build(self):
        write(self.proj / "main.py", "import json\nimport pacote_que_nao_existe_xyz\n")
        res = BuildRunner(self.cfg(), BuildLogger()).run()
        self.assertFalse(res.success)
        self.assertEqual(res.error.stage, "Análise de dependências")
        self.assertIn("pacote_que_nao_existe_xyz", "\n".join(res.error.details))
        self.assertEqual(self.leftovers(), [])

    def test_syntax_error_in_entry(self):
        write(self.proj / "main.py", "def x(:\n")
        res = BuildRunner(self.cfg(), BuildLogger()).run()
        self.assertIn("sintaxe", res.error.message)

    def test_pyinstaller_failure_is_classified(self):
        with mock.patch.dict(os.environ, {"STUB_FAIL": "1"}):
            res = BuildRunner(self.cfg(), BuildLogger()).run()
        self.assertFalse(res.success)
        self.assertEqual(res.error.stage, "Empacotamento")
        self.assertIn("foo", res.error.message)
        self.assertTrue(res.error.command)
        self.assertFalse(self.out.exists() and any(self.out.iterdir()))
        self.assertEqual(self.leftovers(), [])

    def test_invalid_icon_is_caught_early(self):
        bad = self.root / "x.ico"; bad.write_bytes(b"\x89PNG....")
        res = BuildRunner(self.cfg(icon=bad), BuildLogger()).run()
        self.assertEqual(res.error.stage, "Validação")
        self.assertIn("ico", res.error.message.lower())

    def test_empty_output_dir_rejected(self):
        res = BuildRunner(self.cfg(output_dir=Path("")), BuildLogger()).run()
        self.assertEqual(res.error.stage, "Validação")

    def test_cancel_kills_process_and_cleans(self):
        runner = BuildRunner(self.cfg(), BuildLogger())
        with mock.patch.dict(os.environ, {"STUB_SLEEP": "1"}):
            threading.Timer(2.0, runner.cancel).start()
            started = time.time()
            res = runner.run()
        self.assertTrue(res.cancelled)
        self.assertLess(time.time() - started, 20)
        self.assertEqual(self.leftovers(), [])


if __name__ == "__main__":
    unittest.main()
