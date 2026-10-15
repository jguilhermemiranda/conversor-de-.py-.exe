"""Utilitários de caminho que funcionam tanto no código-fonte quanto no .exe."""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    return (Path(base) if base else Path.home() / ".config") / "GUY Builder"


def norm(path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def same_path(a, b) -> bool:
    return norm(a) == norm(b)


def is_within(child, parent) -> bool:
    c = norm(Path(child).resolve())
    p = norm(Path(parent).resolve()).rstrip("\\/")
    return c == p or c.startswith(p + os.sep)
