"""Localiza um interpretador Python REAL para executar o PyInstaller.

Regra central (anti-ciclo): quando o builder roda como .exe, sys.executable é o próprio
builder e NUNCA pode ser usado como interpretador.
"""
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Tuple

from .config import IS_WINDOWS, MIN_PYTHON
from .errors import STAGE_PYTHON, BuildError
from .logger import BuildLogger
from .paths import is_frozen, norm, same_path
from .process_utils import run_capture

PROBE_CODE = (
    "import sys, json, struct\n"
    "print(json.dumps({'executable': sys.executable, 'version': list(sys.version_info[:3]),"
    " 'bits': struct.calcsize('P') * 8, 'prefix': sys.prefix,"
    " 'base_prefix': getattr(sys, 'base_prefix', sys.prefix),"
    " 'frozen': bool(getattr(sys, 'frozen', False))}))\n"
)


@dataclass
class PythonInfo:
    path: Path
    version: Tuple[int, int, int]
    bits: int
    is_venv: bool
    frozen: bool
    origin: str = ""

    @property
    def version_str(self) -> str:
        return ".".join(str(v) for v in self.version)


def probe(path: Path) -> Optional[PythonInfo]:
    """Executa o candidato e confirma que ele é de fato um Python (descarta stubs da Microsoft Store)."""
    code, out = run_capture([str(path), "-c", PROBE_CODE], timeout=20)
    if code != 0:
        return None
    for line in reversed(out.strip().splitlines()):
        try:
            data = json.loads(line)
            return PythonInfo(
                path=Path(data["executable"] or path),
                version=tuple(data["version"]),
                bits=int(data["bits"]),
                is_venv=data["prefix"] != data["base_prefix"],
                frozen=bool(data["frozen"]),
            )
        except (ValueError, KeyError, TypeError):
            continue
    return None


def _venv_python(root: Path, folder: str) -> Path:
    return root / folder / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def iter_candidates(project_root: Optional[Path], override: Optional[Path]) -> Iterator[Tuple[str, Path]]:
    if override:
        # Escolha explícita do usuário: sem fallback silencioso.
        yield "interpretador informado pelo usuário", Path(override)
        return
    if project_root:
        for folder in (".venv", "venv", "env"):
            candidate = _venv_python(Path(project_root), folder)
            if candidate.is_file():
                yield f"ambiente virtual do projeto ({folder})", candidate
    if not is_frozen():
        yield "Python que está executando o builder", Path(sys.executable)
    launcher = shutil.which("py") if IS_WINDOWS else None
    if launcher:
        code, out = run_capture([launcher, "-3", "-c", "import sys; print(sys.executable)"], timeout=20)
        lines = out.strip().splitlines()
        if code == 0 and lines:
            yield "py launcher (py -3)", Path(lines[-1].strip())
    for exe in ("python", "python3"):
        found = shutil.which(exe)
        if found:
            yield f"PATH ({exe})", Path(found)
    if IS_WINDOWS:
        bases = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        ]
        for base in bases:
            if base.is_dir():
                for candidate in sorted(base.glob("Python3*/python.exe"), reverse=True):
                    yield "instalação padrão do Python", candidate


def find_python(project_root: Optional[Path], override: Optional[Path], log: BuildLogger) -> PythonInfo:
    seen = set()
    tried = []
    for origin, path in iter_candidates(project_root, override):
        key = norm(path)
        if key in seen:
            continue
        seen.add(key)
        if is_frozen() and same_path(path, sys.executable):
            log.warn(f"Ignorado ({origin}): é o próprio executável do GUY Builder.")
            tried.append(str(path))
            continue
        info = probe(path)
        if info is None:
            log.warn(f"Ignorado ({origin}): {path} não executa como Python.")
            tried.append(str(path))
            continue
        if info.frozen:
            log.warn(f"Ignorado ({origin}): {path} é um executável congelado, não um interpretador.")
            tried.append(str(path))
            continue
        if info.version[:2] < MIN_PYTHON:
            log.warn(f"Ignorado ({origin}): Python {info.version_str} < {'.'.join(map(str, MIN_PYTHON))}.")
            tried.append(str(path))
            continue
        info.origin = origin
        log.ok(f"Python encontrado: {info.path} (v{info.version_str}, {info.bits}-bit, {origin})")
        return info

    if override:
        raise BuildError(
            STAGE_PYTHON, f"O interpretador informado não é utilizável: {override}",
            hint="Aponte para um python.exe válido (3.8 ou superior) ou deixe o campo vazio para detecção automática.")
    raise BuildError(
        STAGE_PYTHON, "Nenhum Python utilizável foi encontrado nesta máquina.",
        details=tried,
        hint="Instale o Python 3.8+ (python.org), marque 'Add python.exe to PATH', "
             "ou informe o python.exe no campo 'Interpretador Python'.")
