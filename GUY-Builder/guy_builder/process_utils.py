"""Execução segura de subprocessos (ambiente limpo, sem janela, cancelável)."""
import os
import signal
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from .config import IS_WINDOWS
from .paths import norm


def clean_env() -> Dict[str, str]:
    """Ambiente para o Python filho.

    Quando o builder roda como .exe (PyInstaller), o bootloader deixa variáveis internas
    (_MEIPASS2 / _PYI_*) que NÃO devem vazar para o Python que fará o build.
    """
    env = dict(os.environ)
    for key in list(env):
        if key.upper().startswith("_PYI") or key.upper() == "_MEIPASS2":
            env.pop(key, None)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = norm(meipass)
        for key in ("PYTHONHOME", "PYTHONPATH"):
            if key in env and base in norm(env[key]):
                env.pop(key, None)
        env["PATH"] = os.pathsep.join(
            p for p in env.get("PATH", "").split(os.pathsep) if p and not norm(p).startswith(base)
        )
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def popen_kwargs() -> dict:
    kw = dict(
        # stdin=DEVNULL é obrigatório: em app "windowed" não existe stdin e o Popen falha (WinError 6).
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=clean_env(),
    )
    if IS_WINDOWS:
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    return kw


def run_capture(cmd: List[str], timeout: float = 30, cwd: Optional[str] = None) -> Tuple[int, str]:
    kw = popen_kwargs()
    kw.pop("bufsize", None)
    kw.pop("stdout", None)
    kw.pop("stderr", None)
    kw.pop("start_new_session", None)
    try:
        done = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, cwd=cwd, **kw)
        return done.returncode, done.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, "tempo esgotado"
    except OSError as error:
        return -1, str(error)


def kill_process_tree(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass
