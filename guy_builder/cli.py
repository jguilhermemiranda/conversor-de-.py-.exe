"""Modo CLI (sem interface): permite automatizar testes e compilar a partir do próprio .exe."""
import argparse
import os
import sys
from pathlib import Path

from .build_runner import BuildRunner
from .config import APP_TITLE, APP_VERSION
from .logger import BuildLogger
from .models import BuildConfig, ExtraData
from .project import sanitize_name


def _parse_add_data(value: str) -> ExtraData:
    src, _, dest = value.partition("|")
    source = Path(src)
    return ExtraData(source, dest or ("." if not source.is_dir() else source.name))


def main(argv) -> int:
    # Em .exe "windowed" não existem stdout/stderr: evita crash do argparse/print.
    for stream in ("stdout", "stderr"):
        if getattr(sys, stream) is None:
            setattr(sys, stream, open(os.devnull, "w"))

    p = argparse.ArgumentParser(prog=APP_TITLE, description=f"{APP_TITLE} {APP_VERSION} - modo CLI")
    p.add_argument("--entry", required=True, help="arquivo .py de entrada")
    p.add_argument("--project", help="pasta do projeto (padrão: pasta do .py)")
    p.add_argument("--name", help="nome do executável (padrão: nome do .py)")
    p.add_argument("--out", required=True, help="pasta de saída")
    p.add_argument("--icon", help="arquivo .ico")
    p.add_argument("--windowed", action="store_true", help="sem console")
    p.add_argument("--onedir", action="store_true", help="gera pasta em vez de arquivo único")
    p.add_argument("--no-clean", action="store_true", help="não passa --clean ao PyInstaller")
    p.add_argument("--hidden", default="", help="imports extras, separados por vírgula")
    p.add_argument("--add-data", action="append", default=[], metavar="ORIGEM[|DESTINO]")
    p.add_argument("--python", help="python.exe a usar")
    p.add_argument("--log-file", help="grava o log neste arquivo")
    args = p.parse_args(argv)

    entry = Path(args.entry).expanduser().resolve()
    project = Path(args.project).expanduser().resolve() if args.project else entry.parent
    cfg = BuildConfig(
        entry=entry, project_root=project,
        name=args.name or sanitize_name(entry.stem),
        output_dir=Path(args.out).expanduser().resolve(),
        icon=Path(args.icon).expanduser().resolve() if args.icon else None,
        console=not args.windowed, onefile=not args.onedir, clean_cache=not args.no_clean,
        hidden_imports=[h.strip() for h in args.hidden.split(",") if h.strip()],
        extra_data=[_parse_add_data(v) for v in args.add_data],
        python_override=Path(os.path.abspath(os.path.expanduser(args.python))) if args.python else None,  # sem resolve(): preserva o venv
    )

    log_handle = open(args.log_file, "w", encoding="utf-8") if args.log_file else None

    def emit(level, line):
        try:
            print(line, flush=True)
        except Exception:
            pass
        if log_handle:
            log_handle.write(line + "\n")
            log_handle.flush()

    try:
        result = BuildRunner(cfg, BuildLogger(emit)).run()
    finally:
        if log_handle:
            log_handle.close()
    return 0 if result.success else (2 if result.cancelled else 1)
