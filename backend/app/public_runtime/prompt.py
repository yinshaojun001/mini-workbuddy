from pathlib import Path

from app.skills.router import get_metadata


def build_system_prompt(workspace: Path, agent: dict, prompt_blocks: list[str]) -> str:
    prompt = (workspace / "agents" / agent["id"] / "agent.md").read_text(encoding="utf-8")
    skills = []
    for skill_id in agent.get("skill_ids", []):
        metadata = get_metadata(skill_id)
        if metadata["enabled"]:
            skills.append((workspace / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8"))
    return "\n\n".join([prompt, *skills, *prompt_blocks])
