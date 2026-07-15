import shutil
import stat
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.errors import AppError
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api/skills", tags=["技能"])


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    content: str = Field(min_length=1)
    enabled: bool = True


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None


def skills_root() -> Path:
    return get_settings().workspace_dir / "skills"


def metadata_repo(skill_id: str) -> CollectionRepository:
    return CollectionRepository(skills_root() / skill_id / "metadata.json")


def list_metadata() -> list[dict]:
    results = []
    for path in skills_root().iterdir():
        metadata = path / "metadata.json"
        if path.is_dir() and metadata.is_file():
            import json

            results.append(json.loads(metadata.read_text(encoding="utf-8")))
    return sorted(results, key=lambda item: item["updated_at"], reverse=True)


def get_metadata(skill_id: str) -> dict:
    import json

    path = skills_root() / skill_id / "metadata.json"
    if not path.is_file():
        raise AppError("SKILL_NOT_FOUND", "技能不存在", 404)
    return json.loads(path.read_text(encoding="utf-8"))


def write_metadata(skill_id: str, data: dict) -> None:
    from app.storage.json_store import AtomicJsonStore

    AtomicJsonStore(skills_root() / skill_id / "metadata.json", data).write(data)


def tree_for(path: Path) -> list[dict]:
    nodes = []
    for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name == "metadata.json":
            continue
        node = {
            "name": child.name,
            "path": str(child.relative_to(path)),
            "type": "directory" if child.is_dir() else "file",
        }
        if child.is_dir():
            node["children"] = tree_for(child)
        nodes.append(node)
    return nodes


def detail(skill_id: str) -> dict:
    root = skills_root() / skill_id
    metadata = get_metadata(skill_id)
    return {
        **metadata,
        "content": (root / "SKILL.md").read_text(encoding="utf-8"),
        "tree": tree_for(root),
    }


def create_skill_files(name: str, description: str, content: str, enabled: bool, source: Path | None = None) -> dict:
    if not content.strip():
        raise AppError("SKILL_MD_REQUIRED", "SKILL.md 不能为空", 422)
    skill_id = str(uuid4())
    target = skills_root() / skill_id
    if source:
        shutil.move(str(source), target)
    else:
        target.mkdir(parents=True)
    (target / "SKILL.md").write_text(content, encoding="utf-8")
    timestamp = datetime.now(UTC).isoformat()
    metadata = {
        "id": skill_id,
        "name": name,
        "description": description,
        "enabled": enabled,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    write_metadata(skill_id, metadata)
    return metadata


@router.get("")
def list_skills() -> list[dict]:
    return list_metadata()


@router.get("/{skill_id}")
def get_skill(skill_id: str) -> dict:
    return detail(skill_id)


@router.post("", status_code=201)
def create_skill(payload: SkillCreate) -> dict:
    return create_skill_files(payload.name, payload.description, payload.content, payload.enabled)


@router.put("/{skill_id}")
@router.patch("/{skill_id}")
def update_skill(skill_id: str, payload: SkillUpdate) -> dict:
    metadata = get_metadata(skill_id)
    updates = payload.model_dump(exclude_none=True)
    content = updates.pop("content", None)
    if content is not None:
        (skills_root() / skill_id / "SKILL.md").write_text(content, encoding="utf-8")
    metadata.update(updates)
    metadata["updated_at"] = datetime.now(UTC).isoformat()
    write_metadata(skill_id, metadata)
    return metadata


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: str) -> None:
    agents = CollectionRepository(get_settings().workspace_dir / "agents.json").list()
    if any(skill_id in agent.get("skill_ids", []) for agent in agents):
        raise AppError("SKILL_IN_USE", "该技能仍被智能体使用", 409)
    get_metadata(skill_id)
    shutil.rmtree(skills_root() / skill_id)


@router.post("/import", status_code=201)
async def import_skill(file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    data = await file.read(settings.max_skill_zip_bytes + 1)
    if len(data) > settings.max_skill_zip_bytes:
        raise AppError("SKILL_ZIP_TOO_LARGE", "ZIP 包超过大小限制", 413)
    staging = Path(tempfile.mkdtemp(prefix="skill-import-", dir=skills_root()))
    archive_path = staging / "upload.zip"
    archive_path.write_bytes(data)
    extracted = staging / "content"
    extracted.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            total_size = 0
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
                    raise AppError("UNSAFE_SKILL_ZIP", "ZIP 包包含不安全路径", 422)
                total_size += info.file_size
                if total_size > settings.max_skill_expanded_bytes:
                    raise AppError("SKILL_ZIP_EXPANDED_TOO_LARGE", "ZIP 解压后超过大小限制", 413)
            archive.extractall(extracted)
        candidates = [path.parent for path in extracted.rglob("SKILL.md")]
        if len(candidates) != 1:
            raise AppError("INVALID_SKILL_ZIP", "ZIP 包必须且只能包含一个 SKILL.md", 422)
        root = candidates[0]
        content = (root / "SKILL.md").read_text(encoding="utf-8")
        heading = next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), "导入的技能")
        temp_skill = staging / "skill"
        shutil.copytree(root, temp_skill)
        return create_skill_files(heading, "通过 ZIP 导入", content, True, temp_skill)
    except zipfile.BadZipFile as exc:
        raise AppError("INVALID_SKILL_ZIP", "文件不是有效的 ZIP 包", 422) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)

