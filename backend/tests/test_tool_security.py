from pathlib import Path

import pytest

from app.errors import AppError
from app.tools.executors import read_file, resolve_in_workspace, write_file


def test_rejects_parent_and_absolute_path_escape(tmp_path: Path):
    with pytest.raises(AppError, match="路径超出"):
        resolve_in_workspace(tmp_path, "../secret.txt")
    with pytest.raises(AppError, match="路径超出"):
        resolve_in_workspace(tmp_path, "/tmp/secret.txt")


async def test_read_and_write_stay_in_workspace(tmp_path: Path):
    await write_file(tmp_path, {"path": "notes/today.md", "content": "完成"})
    result = await read_file(tmp_path, {"path": "notes/today.md"})

    assert result == {"path": "notes/today.md", "content": "完成"}

