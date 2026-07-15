import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


class AtomicJsonStore:
    def __init__(self, path: Path, default: Any) -> None:
        self.path = path
        self.default = default
        self._lock = threading.RLock()

    def ensure(self) -> None:
        with self._lock:
            if not self.path.exists():
                self.write(deepcopy(self.default))

    def read(self) -> Any:
        with self._lock:
            self.ensure()
            return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, value: Any) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(value, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

