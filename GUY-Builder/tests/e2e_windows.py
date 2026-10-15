"""Teste REAL em Windows dos 4 cenários pedidos (precisa de Python 3.8+, PyInstaller e Pillow).

    python tests/e2e_windows.py

Etapas: (1) Hello World console, (2) app Tkinter, (3) projeto multi-arquivo com dados,
(4) self-build: main.py -> 'GUY Builder.exe' -> usa ESSE .exe para compilar outro .py ->
    apaga o builder e prova que o segundo .exe roda sozinho.
Tudo acontece em pastas temporárias; nada do seu projeto é alterado.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAIN = REPO / "main.py"
ICON = REPO / "assets" / "guymarck.ico"
results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("[ OK ] " if ok else "[FALHA] ") + name + (f"\n        {detail}" if detail and not ok else ""))


def cli(builder_cmd, entry, out, name, *extra, log):
    cmd = builder_cmd + ["--cli", "--entry", str(entry), "--out", str(out), "--name", name,
                         "--log-file", str(log)] + list(extra)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=1500)


def tail(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[-1200:]
    except OSError:
        return "(sem log)"


def main():
    work = Path(tempfile.mkdtemp(prefix="guy_e2e_"))
    py = [sys.executable, str(MAIN)]
    print("Pasta de teste:", work)

    # 1) Hello World (console)
    p1 = work / "t1"; p1.mkdir()
    (p1 / "hello.py").write_text('print("Hello World")\ninput()\n', encoding="utf-8")
    r = cli(py, p1 / "hello.py", work / "out1", "Hello", log=work / "log1.txt")
    exe = work / "out1" / "Hello.exe"
    check("1. build Hello World", r.returncode == 0 and exe.is_file(), tail(work / "log1.txt"))
    if exe.is_file():
        run = subprocess.run([str(exe)], input="\n", capture_output=True, text=True, timeout=60)
        check("1. Hello.exe imprime 'Hello World'", "Hello World" in run.stdout, run.stdout + run.stderr)

    # 2) GUI Tkinter (windowed: valida por arquivo marcador, pois não há console)
    p2 = work / "t2"; p2.mkdir()
    (p2 / "gui.py").write_text(
        "import tkinter as tk, sys, pathlib\n"
        "root = tk.Tk(); root.after(300, root.destroy); root.mainloop()\n"
        "pathlib.Path(sys.argv[1]).write_text('gui-ok')\n", encoding="utf-8")
    r = cli(py, p2 / "gui.py", work / "out2", "GuiApp", "--windowed", log=work / "log2.txt")
    exe = work / "out2" / "GuiApp.exe"
    check("2. build app Tkinter", r.returncode == 0 and exe.is_file(), tail(work / "log2.txt"))
    if exe.is_file():
        marker = work / "gui_marker.txt"
        subprocess.run([str(exe), str(marker)], timeout=60)
        check("2. GuiApp.exe abre e fecha a janela", marker.is_file() and marker.read_text() == "gui-ok")

    # 3) Projeto multi-arquivo + arquivo de dados
    p3 = work / "t3"; (p3 / "pkg").mkdir(parents=True)
    (p3 / "main.py").write_text(
        "import sys, pathlib\nfrom pkg.core import answer\n"
        "base = pathlib.Path(getattr(sys, '_MEIPASS', pathlib.Path(__file__).parent))\n"
        "data = (base / 'config.txt').read_text()\n"
        "pathlib.Path(sys.argv[1]).write_text(f'{answer()}:{data}')\n", encoding="utf-8")
    (p3 / "pkg" / "__init__.py").write_text("")
    (p3 / "pkg" / "core.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    (p3 / "config.txt").write_text("dados", encoding="utf-8")
    r = cli(py, p3 / "main.py", work / "out3", "Multi", "--project", str(p3),
            "--add-data", str(p3 / "config.txt"), log=work / "log3.txt")
    exe = work / "out3" / "Multi.exe"
    check("3. build projeto multi-arquivo", r.returncode == 0 and exe.is_file(), tail(work / "log3.txt"))
    if exe.is_file():
        marker = work / "multi_marker.txt"
        subprocess.run([str(exe), str(marker)], timeout=60)
        check("3. Multi.exe usa pacote local + dado embutido",
              marker.is_file() and marker.read_text() == "42:dados")

    # 4) Self-build e independência
    builder_out = work / "self_dist"
    r = cli(py, MAIN, builder_out, "GUY Builder", "--project", str(REPO), "--windowed",
            "--icon", str(ICON), log=work / "log4.txt")
    builder_exe = builder_out / "GUY Builder.exe"
    check("4. self-build gera 'GUY Builder.exe'", r.returncode == 0 and builder_exe.is_file(),
          tail(work / "log4.txt"))
    if builder_exe.is_file():
        out4 = work / "out4"
        p4 = work / "t4"; p4.mkdir()
        (p4 / "segundo.py").write_text("import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('segundo-ok')\n")
        # usa o .exe do builder (não o código-fonte) para compilar outro programa
        subprocess.run([str(builder_exe), "--cli", "--entry", str(p4 / "segundo.py"), "--out", str(out4),
                        "--name", "Segundo", "--log-file", str(work / "log5.txt")],
                       capture_output=True, text=True, timeout=1500)
        second = out4 / "Segundo.exe"
        check("4. GUY Builder.exe compila outro .py", second.is_file(), tail(work / "log5.txt"))
        if second.is_file():
            isolated = work / "isolado"; isolated.mkdir()
            moved = isolated / "Segundo.exe"
            shutil.copy2(second, moved)
            shutil.rmtree(builder_out, ignore_errors=True)   # remove o .exe do builder e seu dist
            shutil.rmtree(out4, ignore_errors=True)          # remove o dist original do segundo
            marker = work / "segundo_marker.txt"
            subprocess.run([str(moved), str(marker)], timeout=60, cwd=str(isolated))
            check("4. Segundo.exe roda sozinho (builder e dist apagados)",
                  marker.is_file() and marker.read_text() == "segundo-ok")

    leftovers = list(Path(tempfile.gettempdir()).glob("guybuilder_*"))
    check("temporários do builder removidos", not leftovers, str(leftovers))
    failed = [n for n, ok in results if not ok]
    print("\nRESULTADO:", "TUDO OK" if not failed else f"{len(failed)} falha(s)")
    print("Logs completos em:", work)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
