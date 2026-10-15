"""Descoberta de projeto e entrypoint."""
import os
from pathlib import Path
from typing import List, Optional

from .config import ENTRY_PRIORITY, EXCLUDED_DIRS
from .dependencies import analyze, looks_like_gui


def sanitize_name(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " _-" else "_" for c in value).strip()
    return cleaned or "MeuAplicativo"


def scan_entrypoints(project_dir: Path) -> List[Path]:
    """Lista .py do projeto ordenados por probabilidade de serem o entrypoint.

    A exclusão de pastas considera apenas caminhos DENTRO do projeto (não os ancestrais).
    """
    project_dir = Path(project_dir)
    files: List[Path] = []
    for current, dirs, names in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        files.extend(Path(current) / n for n in names if n.lower().endswith(".py"))

    def score(path: Path):
        name = path.name.lower()
        rel = path.relative_to(project_dir)
        prio = ENTRY_PRIORITY.index(name) if name in ENTRY_PRIORITY else 999
        return (prio, len(rel.parts), str(rel).lower())

    return sorted(files, key=score)


def pick_default_entry(files: List[Path]) -> Optional[Path]:
    if not files:
        return None
    preferred = next((p for p in files if p.name.lower() in ENTRY_PRIORITY), None)
    return preferred or files[0]


def suggest_windowed(entry: Path, project_root: Path) -> bool:
    """True se o código importa bibliotecas gráficas (sugestão; o usuário decide)."""
    roots = [Path(project_root)]
    if Path(entry).parent != Path(project_root):
        roots.append(Path(entry).parent)
    return looks_like_gui(analyze(Path(entry), roots))
