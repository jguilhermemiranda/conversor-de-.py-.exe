"""Preferências simples do usuário (últimas pastas usadas)."""
import json
from typing import Any, Dict

from .paths import user_data_dir


class Settings:
    def __init__(self):
        self.path = user_data_dir() / "settings.json"
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError:
            pass  # preferências são opcionais; nunca devem quebrar o builder
