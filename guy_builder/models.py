"""Estruturas de dados compartilhadas entre interface, CLI e motor de build."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .errors import BuildError


@dataclass
class ExtraData:
    source: Path
    dest: str = "."          # pasta DENTRO do pacote onde o arquivo/pasta será colocado


@dataclass
class BuildConfig:
    entry: Path
    project_root: Path
    name: str
    output_dir: Path
    icon: Optional[Path] = None
    console: bool = True
    onefile: bool = True
    clean_cache: bool = True
    hidden_imports: List[str] = field(default_factory=list)
    extra_data: List[ExtraData] = field(default_factory=list)
    python_override: Optional[Path] = None


@dataclass
class BuildResult:
    success: bool
    artifact: Optional[Path] = None
    cancelled: bool = False
    error: Optional[BuildError] = None
    python: Optional[str] = None
    duration: float = 0.0
