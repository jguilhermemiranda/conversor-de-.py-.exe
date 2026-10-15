"""Log com timestamp. Independente de interface: a UI/CLI apenas fornecem o 'emit'."""
import time
from typing import Callable, List, Optional

INFO, OK, WARN, ERROR, CMD, RAW = "info", "ok", "warn", "error", "cmd", "raw"


class BuildLogger:
    def __init__(self, emit: Optional[Callable[[str, str], None]] = None):
        self._emit = emit
        self.lines: List[str] = []

    def _write(self, level: str, text: str, stamp: bool = True):
        for part in (str(text).splitlines() or [""]):
            line = f"[{time.strftime('%H:%M:%S')}] {part}" if stamp else part
            self.lines.append(line)
            if self._emit:
                self._emit(level, line)

    def info(self, text): self._write(INFO, text)
    def ok(self, text): self._write(OK, text)
    def warn(self, text): self._write(WARN, text)
    def error(self, text): self._write(ERROR, text)
    def cmd(self, text): self._write(CMD, text)
    def raw(self, text): self._write(RAW, "    " + str(text), stamp=False)

    def text(self) -> str:
        return "\n".join(self.lines)
