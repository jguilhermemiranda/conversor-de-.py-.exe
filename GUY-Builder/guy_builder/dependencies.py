"""Análise estática de imports + verificação no Python que fará o build."""
import ast
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import GUI_LIBS
from .process_utils import run_capture

_OPTIONAL_EXC = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


@dataclass
class _ImportRef:
    module: str
    level: int
    names: List[str]
    optional: bool


class _ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.refs: List[_ImportRef] = []
        self._optional = 0

    def visit_Import(self, node):
        for alias in node.names:
            self.refs.append(_ImportRef(alias.name, 0, [], self._optional > 0))

    def visit_ImportFrom(self, node):
        self.refs.append(_ImportRef(node.module or "", node.level, [a.name for a in node.names],
                                    self._optional > 0))

    @staticmethod
    def _catches_import_error(handler: ast.ExceptHandler) -> bool:
        if handler.type is None:
            return True
        nodes = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        for n in nodes:
            name = n.id if isinstance(n, ast.Name) else getattr(n, "attr", "")
            if name in _OPTIONAL_EXC:
                return True
        return False

    def visit_Try(self, node):
        guarded = any(self._catches_import_error(h) for h in node.handlers)
        self._optional += 1 if guarded else 0
        for child in node.body:
            self.visit(child)
        self._optional -= 1 if guarded else 0
        for part in (node.handlers, node.orelse, node.finalbody):
            for child in part:
                self.visit(child)

    visit_TryStar = visit_Try


@dataclass
class AnalysisResult:
    files: List[Path] = field(default_factory=list)
    required: Dict[str, Set[Path]] = field(default_factory=dict)   # módulos de terceiros (nome de import)
    optional: Dict[str, Set[Path]] = field(default_factory=dict)   # só dentro de try/except ImportError
    syntax_errors: List[Tuple[Path, str]] = field(default_factory=list)
    top_level_imports: Set[str] = field(default_factory=set)

    @property
    def third_party(self) -> List[str]:
        return sorted(set(self.required) | set(self.optional))


def _has_py(directory: Path) -> bool:
    try:
        return (directory / "__init__.py").is_file() or any(directory.glob("*.py"))
    except OSError:
        return False


def _module_files(base: Path, parts: List[str]) -> Tuple[List[Path], bool]:
    """Resolve 'a.b.c' a partir de 'base'. Retorna (arquivos .py encontrados, topo_é_local)."""
    if not parts:
        init = base / "__init__.py"
        return ([init] if init.is_file() else []), True
    top_pkg, top_mod = base / parts[0], base / (parts[0] + ".py")
    local = top_mod.is_file() or (top_pkg.is_dir() and _has_py(top_pkg))
    files: List[Path] = []
    cur: Optional[Path] = base
    for part in parts:
        if cur is None:
            break
        pkg, mod = cur / part, cur / (part + ".py")
        if pkg.is_dir():
            init = pkg / "__init__.py"
            if init.is_file():
                files.append(init)
            cur = pkg
        elif mod.is_file():
            files.append(mod)
            cur = None
        else:
            break
    return files, local


def analyze(entry: Path, roots: List[Path]) -> AnalysisResult:
    """Segue os imports locais a partir do entrypoint e lista as bibliotecas de terceiros/stdlib.

    Limitação: imports dinâmicos (importlib/__import__/strings) não são detectados.
    """
    result = AnalysisResult()
    visited: Set[Path] = set()
    queue: List[Path] = [Path(entry).resolve()]
    roots = [Path(r).resolve() for r in roots]

    while queue:
        path = queue.pop()
        if path in visited or not path.is_file():
            continue
        visited.add(path)
        try:
            tree = ast.parse(path.read_bytes(), filename=str(path))
        except SyntaxError as error:
            result.syntax_errors.append((path, f"{error.msg} (linha {error.lineno})"))
            continue
        except (OSError, ValueError) as error:
            result.syntax_errors.append((path, f"não foi possível ler o arquivo: {error}"))
            continue
        result.files.append(path)
        collector = _ImportCollector()
        collector.visit(tree)

        for ref in collector.refs:
            parts = [p for p in ref.module.split(".") if p]
            if ref.level > 0:
                base = path.parent
                for _ in range(ref.level - 1):
                    base = base.parent
                found, _local = _module_files(base, parts)
                queue.extend(found)
                pkg_dir = base.joinpath(*parts) if parts else base   # from . import x / from .pkg import x
                for name in ref.names:
                    sub, _ = _module_files(pkg_dir, [name])
                    queue.extend(sub)
                continue
            if not parts:
                continue
            top = parts[0]
            result.top_level_imports.add(top)
            local = False
            for root in roots + [path.parent]:
                found, is_local = _module_files(root, parts)
                if is_local:
                    local = True
                    queue.extend(found)
                    pkg_dir = root.joinpath(*parts)
                    for name in ref.names:
                        sub, _ = _module_files(pkg_dir, [name])
                        queue.extend(sub)
                    break
            if not local and top != "__future__":
                bucket = result.optional if ref.optional else result.required
                bucket.setdefault(top, set()).add(path)

    # Se um módulo é obrigatório em algum arquivo, deixa de ser "opcional".
    for name in list(result.optional):
        if name in result.required:
            result.optional.pop(name)
    return result


def looks_like_gui(result: AnalysisResult) -> bool:
    return bool(result.top_level_imports & GUI_LIBS)


_CHECK_SCRIPT = (
    "import sys, json, importlib.util\n"
    "missing = []\n"
    "for n in [x for x in sys.argv[1].split(',') if x]:\n"
    "    try:\n"
    "        if importlib.util.find_spec(n) is None:\n"
    "            missing.append(n)\n"
    "    except Exception:\n"
    "        missing.append(n)\n"
    "print(json.dumps(missing))\n"
)


def check_installed(python: Path, names: List[str], cwd: Optional[Path] = None) -> Optional[List[str]]:
    """Pergunta ao PRÓPRIO Python do build quais módulos não existem. None = não foi possível verificar."""
    if not names:
        return []
    import json
    code, out = run_capture([str(python), "-c", _CHECK_SCRIPT, ",".join(names)], timeout=60,
                            cwd=str(cwd or tempfile.gettempdir()))
    if code != 0:
        return None
    for line in reversed(out.strip().splitlines()):
        try:
            return list(json.loads(line))
        except ValueError:
            continue
    return None


def pyinstaller_version(python: Path) -> Optional[str]:
    code, out = run_capture([str(python), "-m", "PyInstaller", "--version"], timeout=60)
    if code != 0:
        return None
    match = re.search(r"\d+(\.\d+)+\S*", out)
    return match.group(0) if match else out.strip() or None
