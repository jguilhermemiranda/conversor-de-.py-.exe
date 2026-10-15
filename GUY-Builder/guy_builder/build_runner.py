"""Motor de build Python -> EXE. Sem dependência de interface gráfica (testável e usado pela CLI)."""
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Callable, Deque, List, Optional, Tuple

from .cleaner import cleanup_stale_workspaces, make_workspace, publish_artifact, remove_workspace
from .config import EXE_SUFFIX, PYINSTALLER_REQUIREMENT
from .dependencies import analyze, check_installed, pyinstaller_version
from .errors import (STAGE_DEPS, STAGE_INTERNAL, STAGE_PACKAGE, STAGE_PYINSTALLER, STAGE_VALIDATE,
                     BuildCancelled, BuildError, classify_failure, format_command, pip_hint)
from .icon_tools import is_valid_ico
from .logger import BuildLogger
from .models import BuildConfig, BuildResult
from .paths import is_frozen, is_within, same_path
from .process_utils import kill_process_tree, popen_kwargs
from .project import sanitize_name
from .python_finder import PythonInfo, find_python

ProgressFn = Callable[[int, str], None]

# Módulos que o PyInstaller costuma listar como "ausentes" no Windows por serem de outras plataformas.
_PLATFORM_NOISE = {"pwd", "grp", "fcntl", "termios", "resource", "posix", "readline", "_curses",
                   "_posixsubprocess", "_posixshmem", "org", "java", "vms_lib", "nt", "os2", "ce"}


class BuildRunner:
    def __init__(self, config: BuildConfig, logger: BuildLogger, on_progress: Optional[ProgressFn] = None):
        self.cfg = config
        self.log = logger
        self._progress = on_progress or (lambda pct, label: None)
        self._cancel = threading.Event()
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._python: Optional[PythonInfo] = None

    # ------------------------------------------------------------------ controle
    def cancel(self):
        self._cancel.set()
        with self._lock:
            proc = self._proc
        if proc is not None:
            kill_process_tree(proc)

    def _check_cancel(self):
        if self._cancel.is_set():
            raise BuildCancelled()

    def _stage(self, pct: int, label: str):
        self._check_cancel()
        self.log.info(label + "...")
        self._progress(pct, label)

    # ------------------------------------------------------------------ pipeline
    def run(self) -> BuildResult:
        started = time.time()
        workspace: Optional[Path] = None
        self.log.info("Inicializando build...")
        try:
            self._stage(3, "Validando entradas")
            self._validate()
            self._stage(8, "Preparando ambiente")
            cleanup_stale_workspaces(self.log)
            workspace = make_workspace()
            self.log.info(f"Área temporária: {workspace}")
            self._stage(15, "Localizando Python")
            self._python = find_python(self.cfg.project_root, self.cfg.python_override, self.log)
            self._stage(22, "Verificando PyInstaller")
            self._ensure_pyinstaller()
            self._stage(30, "Analisando dependências")
            self._analyze_dependencies(workspace)
            self._stage(40, "Empacotando aplicação")
            staged = self._package(workspace)
            self._stage(94, "Publicando executável")
            artifact = publish_artifact(staged, self.cfg, self.log)
            self._progress(100, "Concluído")
            self.log.ok("Build concluído!")
            self.log.ok(f"Executável: {artifact}")
            return BuildResult(True, artifact=artifact, python=str(self._python.path),
                               duration=time.time() - started)
        except BuildCancelled:
            self.log.warn("Build cancelado pelo usuário.")
            return BuildResult(False, cancelled=True, duration=time.time() - started)
        except BuildError as error:
            for line in error.report_lines():
                self.log.error(line)
            return BuildResult(False, error=error, duration=time.time() - started)
        except Exception as error:  # falha inesperada do próprio builder
            self.log.error(traceback.format_exc())
            wrapped = BuildError(STAGE_INTERNAL, f"{type(error).__name__}: {error}",
                                 hint="Erro inesperado do GUY Builder. Copie o log acima ao reportar.")
            return BuildResult(False, error=wrapped, duration=time.time() - started)
        finally:
            if workspace is not None:
                remove_workspace(workspace, self.log)

    # ------------------------------------------------------------------ etapas
    def _validate(self):
        cfg = self.cfg
        fail = lambda msg, hint: BuildError(STAGE_VALIDATE, msg, hint=hint)  # noqa: E731

        if not cfg.entry.is_file() or cfg.entry.suffix.lower() != ".py":
            raise fail(f"Arquivo de entrada inválido ou inexistente: {cfg.entry}",
                       "Selecione um arquivo .py que exista.")
        if not cfg.project_root.is_dir():
            raise fail(f"Pasta do projeto inexistente: {cfg.project_root}", "Selecione a pasta do projeto.")
        if not is_within(cfg.entry, cfg.project_root):
            raise fail("O arquivo de entrada está fora da pasta do projeto.",
                       "Escolha um .py dentro do projeto ou ajuste a pasta do projeto.")
        if not cfg.name or cfg.name != sanitize_name(cfg.name):
            raise fail(f"Nome do executável inválido: '{cfg.name}'",
                       "Use apenas letras, números, espaço, '_' e '-'.")
        if not str(cfg.output_dir).strip() or str(cfg.output_dir) == ".":
            raise fail("Pasta de saída não definida.", "Escolha explicitamente onde o .exe será criado.")
        if cfg.icon is not None:
            if not Path(cfg.icon).is_file() or Path(cfg.icon).suffix.lower() != ".ico":
                raise fail(f"Ícone inválido ou inexistente: {cfg.icon}",
                           "Selecione um arquivo .ico (a aba PNG → ICO gera um).")
            if not is_valid_ico(cfg.icon):
                raise fail(f"O arquivo não é um .ico válido: {cfg.icon}",
                           "Renomear um PNG para .ico não funciona; converta-o na aba PNG → ICO.")
        for item in cfg.extra_data:
            if not Path(item.source).exists():
                raise fail(f"Arquivo adicional não encontrado: {item.source}",
                           "Remova-o da lista ou corrija o caminho.")
        for module in cfg.hidden_imports:
            if not re.fullmatch(r"[A-Za-z_][\w\.]*", module):
                raise fail(f"Nome de import extra inválido: '{module}'", "Use nomes como 'pacote.modulo'.")

        target = Path(cfg.output_dir) / (cfg.name + EXE_SUFFIX)
        if is_frozen() and same_path(target, sys.executable):
            raise fail("O destino é o próprio executável do GUY Builder em execução.",
                       "Um .exe em uso não pode ser substituído. Escolha outro nome ou outra pasta de saída "
                       "(depois você pode renomear/trocar o arquivo).")

    def _ensure_pyinstaller(self):
        assert self._python is not None
        version = pyinstaller_version(self._python.path)
        if version is None:
            raise BuildError(
                STAGE_PYINSTALLER, "O PyInstaller não está instalado no Python selecionado.",
                command=f'"{self._python.path}" -m pip install "{PYINSTALLER_REQUIREMENT}"',
                hint="Instale o PyInstaller nesse Python (a interface oferece instalar para você).",
                fix_action="install_pyinstaller")
        self.log.ok(f"PyInstaller encontrado: {version}")
        try:
            if int(version.split(".")[0]) < 6:
                self.log.warn("PyInstaller < 6.0: o projeto foi pensado para 6.x; atualize se houver problemas.")
        except ValueError:
            pass

    def _analyze_dependencies(self, workspace: Path):
        assert self._python is not None
        cfg = self.cfg
        roots = [cfg.project_root] + ([cfg.entry.parent] if cfg.entry.parent != cfg.project_root else [])
        result = analyze(cfg.entry, roots)
        self.log.info(f"{len(result.files)} arquivo(s) Python do projeto analisado(s).")

        for path, message in result.syntax_errors:
            rel = os.path.relpath(path, cfg.project_root)
            if same_path(path, cfg.entry):
                raise BuildError(STAGE_DEPS, f"Erro de sintaxe em {rel}: {message}",
                                 hint="Corrija o erro de sintaxe e gere novamente.")
            self.log.warn(f"Erro de sintaxe em {rel}: {message}")

        names = result.third_party
        if not names:
            self.log.info("Nenhum import externo detectado (apenas biblioteca padrão e módulos do projeto).")
            return
        self.log.info("Imports externos/padrão detectados: " + ", ".join(names))
        missing = check_installed(self._python.path, names, workspace)
        if missing is None:
            self.log.warn("Não foi possível verificar as dependências; o PyInstaller fará a análise final.")
            return
        required_missing = [m for m in missing if m in result.required]
        for m in missing:
            if m not in result.required:
                self.log.warn(f"Import opcional ausente (dentro de try/except): {m}")
        if required_missing:
            details = []
            for m in required_missing:
                used = sorted(os.path.relpath(p, cfg.project_root) for p in result.required[m])[:3]
                details.append(f"{m}  ->  python -m pip install {pip_hint(m)}   (usado em: {', '.join(used)})")
            raise BuildError(
                STAGE_DEPS, f"{len(required_missing)} dependência(s) ausente(s) no Python do build.",
                command=f'"{self._python.path}" -m pip install <pacote>',
                hint="Instale os pacotes abaixo no Python indicado e gere novamente. "
                     "Os nomes de pacote são sugestões: confirme no PyPI. "
                     "Se for um módulo seu fora da pasta do projeto, mova-o para dentro dela.",
                details=details)
        self.log.ok("Todas as dependências detectadas estão instaladas.")

    def _build_command(self, workspace: Path) -> List[str]:
        assert self._python is not None
        cfg = self.cfg
        cmd = [str(self._python.path), "-m", "PyInstaller", "--noconfirm"]
        if cfg.clean_cache:
            cmd.append("--clean")
        cmd.append("--onefile" if cfg.onefile else "--onedir")
        cmd.append("--console" if cfg.console else "--windowed")
        cmd += ["--name", cfg.name,
                "--distpath", str(workspace / "dist"),
                "--workpath", str(workspace / "build"),
                "--specpath", str(workspace / "spec"),
                "--paths", str(cfg.project_root)]
        if cfg.icon:
            cmd += ["--icon", str(Path(cfg.icon).resolve())]
        for module in cfg.hidden_imports:
            cmd += ["--hidden-import", module]
        for item in cfg.extra_data:
            cmd += ["--add-data", f"{Path(item.source).resolve()}{os.pathsep}{item.dest}"]
        cmd.append(str(cfg.entry))
        return cmd

    def _package(self, workspace: Path) -> Path:
        cfg = self.cfg
        cmd = self._build_command(workspace)
        cmdline = format_command(cmd)
        self.log.info(f"Projeto : {cfg.project_root}")
        self.log.info(f"Entrada : {cfg.entry.relative_to(cfg.project_root) if is_within(cfg.entry, cfg.project_root) else cfg.entry}")
        self.log.info(f"Saída   : {cfg.output_dir}")
        self.log.info(f"Modo    : {'um arquivo' if cfg.onefile else 'pasta'} / "
                      f"{'console' if cfg.console else 'janela (sem console)'}")
        self.log.cmd("Comando: " + cmdline)

        counter = {"n": 0}

        def on_line(line: str):
            counter["n"] += 1
            self.log.raw(line)
            pct = 40 + int(50 * counter["n"] / (counter["n"] + 300))
            self._progress(pct, "Empacotando aplicação")

        code, tail = self._run_streaming(cmd, workspace, on_line, STAGE_PACKAGE, cmdline)
        if code != 0:
            message, hint, fix = classify_failure(list(tail)[-60:])
            raise BuildError(STAGE_PACKAGE, message, command=cmdline, hint=hint,
                             details=list(tail)[-12:], fix_action=fix)

        dist = workspace / "dist"
        staged = dist / (cfg.name + EXE_SUFFIX) if cfg.onefile else dist / cfg.name
        main_exe = staged if cfg.onefile else staged / (cfg.name + EXE_SUFFIX)
        if not main_exe.is_file():
            raise BuildError(STAGE_PACKAGE, "O PyInstaller terminou sem erro, mas o executável não foi gerado.",
                             command=cmdline, details=list(tail)[-12:],
                             hint="Verifique o log acima; avisos do PyInstaller podem indicar a causa.")
        self.log.ok(f"Executável gerado ({main_exe.stat().st_size / 1_048_576:.1f} MB).")
        self._report_missing_modules(workspace)
        return staged

    def _report_missing_modules(self, workspace: Path):
        """Heurística: lê o warn-<nome>.txt do PyInstaller e destaca imports de topo não resolvidos."""
        warn_file = workspace / "build" / self.cfg.name / f"warn-{self.cfg.name}.txt"
        try:
            text = warn_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        suspects = []
        for m in re.finditer(r"missing module named (\S+) - imported by (.*)", text):
            name, importers = m.group(1).strip("'\""), m.group(2)
            if name.split(".")[0] in _PLATFORM_NOISE or "top-level" not in importers:
                continue
            suspects.append(name)
        if suspects:
            shown = ", ".join(sorted(set(suspects))[:15])
            self.log.warn("Possíveis módulos não empacotados (heurística, pode haver falsos positivos): " + shown)
            self.log.warn("Se o programa falhar com ImportError, adicione-os em 'Imports extras'.")

    # ------------------------------------------------------------------ subprocesso
    def _run_streaming(self, cmd: List[str], cwd: Path, on_line: Callable[[str], None],
                       stage: str, cmdline: str) -> Tuple[int, Deque[str]]:
        tail: Deque[str] = deque(maxlen=200)
        try:
            proc = subprocess.Popen(cmd, cwd=str(cwd), **popen_kwargs())
        except OSError as error:
            raise BuildError(stage, f"Não foi possível iniciar o processo: {error}", command=cmdline,
                             hint="O Python selecionado pode ter sido movido/removido. Escolha-o novamente.")
        with self._lock:
            self._proc = proc
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip("\r\n")
                tail.append(line)
                on_line(line)
                if self._cancel.is_set():
                    kill_process_tree(proc)
                    break
            code = proc.wait()
        finally:
            with self._lock:
                self._proc = None
            if proc.stdout:
                proc.stdout.close()
        self._check_cancel()
        return code, tail

    def install_pyinstaller(self) -> bool:
        """Instala o PyInstaller no Python selecionado (ação oferecida pela UI mediante confirmação)."""
        try:
            python = self._python or find_python(self.cfg.project_root, self.cfg.python_override, self.log)
            cmd = [str(python.path), "-m", "pip", "install", PYINSTALLER_REQUIREMENT]
            cmdline = format_command(cmd)
            self.log.info("Instalando PyInstaller...")
            self.log.cmd("Comando: " + cmdline)
            code, tail = self._run_streaming(cmd, Path(tempfile.gettempdir()), self.log.raw,
                                             STAGE_PYINSTALLER, cmdline)
            if code != 0:
                self.log.error("Falha ao instalar o PyInstaller. Verifique a conexão com a internet e permissões.")
                return False
            self.log.ok("PyInstaller instalado. Clique em GERAR EXECUTÁVEL novamente.")
            return True
        except BuildCancelled:
            self.log.warn("Instalação cancelada.")
            return False
        except BuildError as error:
            for line in error.report_lines():
                self.log.error(line)
            return False
