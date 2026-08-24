#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path


EXPECTED_VERSION = "0.7.0"
CODEX_SKILL_PATH = ".agents/skills"


def option_value(arguments: list[str], option: str) -> str | None:
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(f"{option}="):
            return argument.split("=", 1)[1]
    return None


def configure_skill_name(skill_argument: str, evals_argument: str) -> None:
    from agent_skill_eval.skills import SkillInstaller

    skill_path = Path(skill_argument).resolve()
    suite = json.loads(Path(evals_argument).read_text())
    expected_name = suite.get("skill_name")
    if not isinstance(expected_name, str) or not expected_name:
        raise RuntimeError("eval suite must declare a non-empty skill_name")

    installer = SkillInstaller(skill_path)
    installer.skill_name = expected_name
    problems = installer.frontmatter_problems()
    if problems:
        raise RuntimeError("invalid Skill metadata: " + "; ".join(problems))

    original_init = SkillInstaller.__init__

    def normalized_init(self, path: Path) -> None:
        original_init(self, path)
        if Path(path).resolve() == skill_path:
            self.skill_name = expected_name

    SkillInstaller.__init__ = normalized_init


def smoke_test(skill_argument: str) -> None:
    from agent_skill_eval.models import AgentType
    from agent_skill_eval.skills import SkillInstaller

    skill_path = Path(skill_argument).resolve()
    installer = SkillInstaller(skill_path)
    user_home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", user_home / ".codex"))
    ambient_paths = {
        user_home / CODEX_SKILL_PATH / installer.skill_name,
        codex_home / "skills" / installer.skill_name,
        Path("/etc/codex/skills") / installer.skill_name,
    }
    existing_ambient_paths = sorted(path for path in ambient_paths if path.exists())
    if existing_ambient_paths:
        paths = ", ".join(str(path) for path in existing_ambient_paths)
        raise RuntimeError(
            f"ambient Skill path(s) would contaminate the without-Skill baseline: {paths}; "
            "run the benchmark from a clean user profile or container"
        )
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        installed_path = installer.install(workspace, AgentType.CODEX)
        expected_path = workspace / CODEX_SKILL_PATH / installer.skill_name
        if installed_path != expected_path or not (installed_path / "SKILL.md").is_file():
            raise RuntimeError("Codex skill discovery smoke test did not use .agents/skills")
        installed_hash = SkillInstaller(installed_path).content_hash()
        if installed_hash != installer.content_hash():
            raise RuntimeError("Codex skill discovery smoke test found a content hash mismatch")
    print(
        f"Codex skill discovery smoke test passed: "
        f"path={CODEX_SKILL_PATH}/{installer.skill_name} hash={installed_hash}",
        file=sys.stderr,
    )


def main() -> None:
    installed_version = version("agent-skill-eval")
    if installed_version != EXPECTED_VERSION:
        raise RuntimeError(
            f"expected agent-skill-eval {EXPECTED_VERSION}, found {installed_version}"
        )

    from agent_skill_eval.models import AgentType
    from agent_skill_eval.skills import SKILL_PATHS

    SKILL_PATHS[AgentType.CODEX] = [CODEX_SKILL_PATH]
    if sys.argv[1:2] == ["run"]:
        arguments = sys.argv[2:]
        skill_argument = option_value(arguments, "--skill") or option_value(arguments, "-s")
        evals_argument = option_value(arguments, "--evals") or option_value(arguments, "-e")
        if skill_argument is not None and evals_argument is not None:
            configure_skill_name(skill_argument, evals_argument)
            smoke_test(skill_argument)

    from agent_skill_eval.cli import app

    app()


if __name__ == "__main__":
    main()
