"""Erros de build estruturados: etapa, mensagem, comando e possível solução."""
import re
import subprocess
from typing import List, Optional, Sequence, Tuple

from .config import IMPORT_TO_PIP

STAGE_VALIDATE = "Validação"
STAGE_WORKSPACE = "Preparação do ambiente"
STAGE_PYTHON = "Localização do Python"
STAGE_PYINSTALLER = "Verificação do PyInstaller"
STAGE_DEPS = "Análise de dependências"
STAGE_PACKAGE = "Empacotamento"
STAGE_PUBLISH = "Publicação do executável"
STAGE_INTERNAL = "Erro interno"


class BuildCancelled(Exception):
    """Build cancelado pelo usuário."""


class BuildError(Exception):
    def __init__(self, stage: str, message: str, *, command: Optional[str] = None,
                 hint: Optional[str] = None, details: Optional[Sequence[str]] = None,
                 fix_action: Optional[str] = None):
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.command = command
        self.hint = hint
        self.details: List[str] = list(details or [])
        self.fix_action = fix_action      # ex.: "install_pyinstaller" (a UI pode oferecer a correção)

    def report_lines(self) -> List[str]:
        lines = [f"ERRO na etapa: {self.stage}", f"  Mensagem : {self.message}"]
        if self.command:
            lines.append(f"  Comando  : {self.command}")
        if self.hint:
            lines.append(f"  Solução  : {self.hint}")
        if self.details:
            lines.append("  Últimas linhas da saída:")
            lines.extend(f"    | {line}" for line in self.details)
        return lines


def format_command(cmd: Sequence) -> str:
    return subprocess.list2cmdline([str(c) for c in cmd])


def pip_hint(module: str) -> str:
    top = module.split(".")[0]
    return IMPORT_TO_PIP.get(top, top)


def classify_failure(lines: Sequence[str]) -> Tuple[str, str, Optional[str]]:
    """Heurística sobre a saída do PyInstaller. Retorna (mensagem, solução, fix_action).

    São padrões de texto: podem não reconhecer toda falha; nesse caso o resultado é genérico.
    """
    text = "\n".join(lines)

    if re.search(r"No module named '?PyInstaller'?", text):
        return ("O PyInstaller não está instalado no Python selecionado.",
                "Instale com: python -m pip install pyinstaller", "install_pyinstaller")

    m = re.search(r"ModuleNotFoundError: No module named '([\w\.]+)'", text)
    if m:
        mod = m.group(1)
        return (f"Módulo não encontrado: {mod}",
                f"Instale no MESMO Python usado no build: python -m pip install {pip_hint(mod)}", None)

    m = re.search(r"SyntaxError: .*", text)
    if m:
        return (f"Erro de sintaxe no código: {m.group(0)}",
                "Corrija o erro de sintaxe indicado acima e tente novamente.", None)

    if re.search(r"PermissionError|Access is denied|WinError 5\b|WinError 32\b", text):
        return ("Permissão negada ao acessar um arquivo durante o empacotamento.",
                "Feche o programa se ele estiver em execução, verifique se o antivírus não está "
                "bloqueando a pasta temporária e evite pastas protegidas (ex.: Program Files).", None)

    if re.search(r"(?i)(error|exception)[^\n]*icon|icon[^\n]*(error|exception|invalid|unsupported)", text):
        return ("Problema ao aplicar o ícone.",
                "Use um .ico válido (gere um na aba PNG → ICO) ou remova o ícone e tente novamente.", None)

    if re.search(r"No space left|Errno 28|not enough space", text, re.I):
        return ("Sem espaço em disco.", "Libere espaço na unidade temporária/de saída.", None)

    m = re.search(r"Unable to find ['\"]?(.+?)['\"]? when adding binary and data files", text)
    if m:
        return (f"Arquivo adicional não encontrado: {m.group(1)}",
                "Confira a lista de arquivos adicionais: algum caminho não existe mais.", None)

    if re.search(r"(?i)script file .+ does not exist|can't open file", text):
        return ("O arquivo de entrada não foi encontrado pelo PyInstaller.",
                "Confirme que o .py selecionado ainda existe.", None)

    return ("O PyInstaller terminou com erro (causa não reconhecida automaticamente).",
            "Leia as últimas linhas do log acima; a causa costuma estar nas linhas ERROR/Traceback.", None)
