"""Área temporária e publicação do resultado - limpeza sempre restrita a artefatos do builder."""
import os
import shutil
import stat
import tempfile
import time
from pathlib import Path

from .config import EXE_SUFFIX, STALE_TEMP_HOURS, TEMP_MARKER, TEMP_PREFIX
from .errors import STAGE_PUBLISH, STAGE_WORKSPACE, BuildError
from .logger import BuildLogger
from .models import BuildConfig
from .paths import is_within


def make_workspace() -> Path:
    try:
        path = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
        (path / TEMP_MARKER).write_text("GUY Builder temporary workspace\n", encoding="utf-8")
        return path
    except OSError as error:
        raise BuildError(STAGE_WORKSPACE, f"Não foi possível criar a pasta temporária: {error}",
                         hint="Verifique espaço em disco e permissões da pasta TEMP do Windows.")


def _is_workspace(path: Path) -> bool:
    return (path.name.startswith(TEMP_PREFIX)
            and (path / TEMP_MARKER).is_file()
            and is_within(path, tempfile.gettempdir())
            and path.resolve() != Path(tempfile.gettempdir()).resolve())


def _force_remove(func, target, _exc):
    try:
        os.chmod(target, stat.S_IWRITE)
        func(target)
    except OSError:
        pass


def remove_workspace(path: Path, log: BuildLogger) -> bool:
    path = Path(path)
    if not _is_workspace(path):
        log.warn(f"Limpeza recusada (não é uma área temporária do builder): {path}")
        return False
    shutil.rmtree(path, onerror=_force_remove)
    if path.exists():
        log.warn(f"Não foi possível remover totalmente a pasta temporária: {path}")
        return False
    log.info("Arquivos temporários removidos.")
    return True


def cleanup_stale_workspaces(log: BuildLogger):
    """Remove áreas temporárias de builds anteriores que foram interrompidos (> STALE_TEMP_HOURS)."""
    limit = time.time() - STALE_TEMP_HOURS * 3600
    root = Path(tempfile.gettempdir())
    try:
        entries = list(root.glob(TEMP_PREFIX + "*"))
    except OSError:
        return
    for path in entries:
        try:
            if path.is_dir() and _is_workspace(path) and path.stat().st_mtime < limit:
                shutil.rmtree(path, onerror=_force_remove)
                log.info(f"Temporário antigo removido: {path.name}")
        except OSError:
            continue


def _looks_like_pyinstaller_onedir(folder: Path, name: str) -> bool:
    return (folder / (name + EXE_SUFFIX)).is_file() and (
        (folder / "_internal").is_dir() or (folder / "base_library.zip").is_file())


def publish_artifact(staged: Path, cfg: BuildConfig, log: BuildLogger) -> Path:
    """Copia o resultado da área temporária para a pasta de saída (substitui só o artefato do mesmo nome)."""
    out = Path(cfg.output_dir)
    try:
        out.mkdir(parents=True, exist_ok=True)
        if cfg.onefile:
            target = out / (cfg.name + EXE_SUFFIX)
            if target.exists():
                if target.is_dir():
                    raise BuildError(STAGE_PUBLISH, f"Existe uma PASTA com o nome do executável: {target}",
                                     hint="Escolha outro nome ou outra pasta de saída.")
                log.info("Substituindo executável anterior...")
                target.unlink()
            partial = target.with_name(target.name + ".partial")
            shutil.copy2(staged, partial)
            os.replace(partial, target)
            return target
        target = out / cfg.name
        if target.exists():
            if not (target.is_dir() and _looks_like_pyinstaller_onedir(target, cfg.name)):
                raise BuildError(STAGE_PUBLISH,
                                 f"'{target}' já existe e não parece ter sido gerado pelo PyInstaller.",
                                 hint="Por segurança o builder não apaga isso. Escolha outro nome ou pasta de saída.")
            log.info("Substituindo pasta anterior do mesmo aplicativo...")
            shutil.rmtree(target)
        shutil.copytree(staged, target)
        return target / (cfg.name + EXE_SUFFIX)
    except PermissionError as error:
        raise BuildError(STAGE_PUBLISH, f"Permissão negada ao gravar em {out}: {error}",
                         hint="Feche o programa se estiver em execução (um .exe em uso não pode ser "
                              "substituído) ou escolha outra pasta de saída.")
    except OSError as error:
        raise BuildError(STAGE_PUBLISH, f"Falha ao gravar o resultado: {error}",
                         hint="Verifique espaço em disco e se o caminho de saída é válido.")
