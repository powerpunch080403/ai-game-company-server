from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_PROJECT_TYPES = (
    "game-basic",
    "web-basic",
    "app-basic",
    "backend-basic",
    "tool-basic",
    "automation-basic",
    "plugin-basic",
)


class ProjectTemplateError(ValueError):
    pass


@dataclass(frozen=True)
class TemplateResult:
    target: Path
    project_type: str
    files: list[str]


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def normalize_project_name(name: str) -> str:
    value = " ".join(name.strip().split())
    if not value:
        raise ProjectTemplateError("Project name is required.")
    return value


def project_kind(project_type: str) -> str:
    return project_type.removesuffix("-basic")


def project_metadata(name: str, project_type: str, engine: str) -> dict[str, Any]:
    kind = project_kind(project_type)
    metadata: dict[str, Any] = {
        "version": 1,
        "name": name,
        "project_type": kind,
        "base_branch": "main",
        "server": {
            "project_id": None,
        },
        "paths": {
            "docs": "docs",
            "source": "src",
            "tests": "tests",
            "artifacts": ".game-company/artifacts",
        },
    }
    if kind == "game":
        metadata["engine"] = engine
    else:
        metadata["framework"] = "undecided"
    return metadata


def test_runner_config(engine: str) -> dict[str, Any]:
    return {
        "version": 1,
        "engine": engine,
        "commands": {
            "setup": [],
            "build": ["python --version"],
            "test": [],
            "run": [],
        },
        "artifacts": {
            "root": ".game-company/artifacts",
            "logs": ["test-runner.log"],
            "reports": ["test-runner-report.json"],
        },
        "timeouts": {
            "setup_seconds": 300,
            "build_seconds": 900,
            "test_seconds": 900,
            "run_seconds": 300,
        },
    }


def ai_company_test_runner_config(engine: str) -> dict[str, Any]:
    config = test_runner_config(engine)
    config["artifacts"] = {
        "root": ".ai-company/artifacts",
        "logs": ["test-runner.log"],
        "reports": ["test-runner-report.json"],
    }
    return config


def type_notes(project_type: str) -> str:
    notes = {
        "game-basic": "Focus on game concept, play loop, controls, visual direction, and engine choice.",
        "web-basic": "Focus on user flows, screens, API boundaries, and deployment constraints.",
        "app-basic": "Focus on core screens, platform constraints, sync, release, and analytics.",
        "backend-basic": "Focus on API contracts, data model, migrations, reliability, and operations.",
        "tool-basic": "Focus on commands, inputs, outputs, packaging, and documentation.",
        "automation-basic": "Focus on triggers, safety limits, rollback, logs, and operator controls.",
        "plugin-basic": "Focus on host app version, manifest, extension points, packaging, and tests.",
    }
    return notes[project_type]


def readme_text(name: str, project_type: str, engine: str) -> str:
    kind = project_kind(project_type)
    engine_line = f"- Engine: {engine}\n" if kind == "game" else "- Framework: undecided\n"
    return (
        f"# {name}\n\n"
        "This repository was created from the AI Game Company v1 minimal project template.\n\n"
        "## Project\n\n"
        f"- Type: {kind}\n"
        f"{engine_line}"
        "- Automation config: `.game-company/`\n"
        "- Forward-looking automation config: `.ai-company/`\n\n"
        "## Start Here\n\n"
        "- `docs/DESIGN.md` keeps durable design context.\n"
        "- `docs/TASKS.md` tracks human-readable work.\n"
        "- `docs/TESTING.md` explains local validation and artifacts.\n"
    )


def design_text(name: str, project_type: str) -> str:
    return (
        f"# {name} Design\n\n"
        "## Current Direction\n\n"
        f"{type_notes(project_type)}\n\n"
        "## Constraints\n\n"
        "- Keep the first version small and verifiable.\n"
        "- Record durable decisions in `docs/DECISIONS.md`.\n"
        "- Keep generated artifacts out of git unless explicitly requested.\n\n"
        "## Open Questions\n\n"
        "- What is the smallest playable or usable slice?\n"
        "- Which tools, engine, or framework should be selected later?\n"
    )


def tasks_text() -> str:
    return (
        "# Tasks\n\n"
        "## Project Bootstrap\n\n"
        "- Confirm project goal.\n"
        "- Choose the first build/test command after the stack is selected.\n"
        "- Replace placeholder source and test notes with real files.\n"
    )


def testing_text() -> str:
    return (
        "# Testing\n\n"
        "The v1 test runner reads `.game-company/test_runner.json` and writes logs under "
        "`.game-company/artifacts/`.\n\n"
        "The default build command is intentionally tiny:\n\n"
        "```bash\n"
        "python --version\n"
        "```\n\n"
        "Update the command list after the project engine or framework is selected.\n"
    )


def decisions_text() -> str:
    return (
        "# Decisions\n\n"
        "| Date | Decision | Reason |\n"
        "| --- | --- | --- |\n"
        "| TBD | Engine/framework undecided | Keep the template portable until real project needs are known. |\n"
    )


def placeholder_text(kind: str) -> str:
    return (
        f"# {kind}\n\n"
        "This directory is intentionally minimal. Add real files after the project stack is selected.\n"
    )


def gitignore_text() -> str:
    return (
        ".game-company/artifacts/**\n"
        "!.game-company/artifacts/.gitkeep\n"
        ".ai-company/artifacts/**\n"
        "!.ai-company/artifacts/.gitkeep\n"
        "\n"
        ".env\n"
        ".venv/\n"
        "venv/\n"
        "__pycache__/\n"
        "\n"
        "build/\n"
        "dist/\n"
        "tmp/\n"
        "temp/\n"
        "logs/\n"
        "*.log\n"
        "\n"
        ".DS_Store\n"
        "Thumbs.db\n"
    )


def json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def template_files(name: str, project_type: str, engine: str) -> dict[str, str]:
    metadata = project_metadata(name, project_type, engine)
    ai_metadata = dict(metadata)
    ai_metadata["paths"] = dict(metadata["paths"])
    ai_metadata["paths"]["artifacts"] = ".ai-company/artifacts"
    return {
        "README.md": readme_text(name, project_type, engine),
        ".gitignore": gitignore_text(),
        ".game-company/project.json": json_text(metadata),
        ".game-company/test_runner.json": json_text(test_runner_config(engine)),
        ".game-company/artifacts/.gitkeep": "",
        ".ai-company/project.json": json_text(ai_metadata),
        ".ai-company/test_runner.json": json_text(ai_company_test_runner_config(engine)),
        ".ai-company/artifacts/.gitkeep": "",
        "docs/DESIGN.md": design_text(name, project_type),
        "docs/TASKS.md": tasks_text(),
        "docs/TESTING.md": testing_text(),
        "docs/DECISIONS.md": decisions_text(),
        "src/README.md": placeholder_text("Source"),
        "tests/README.md": placeholder_text("Tests"),
    }


def ensure_supported_type(project_type: str) -> None:
    if project_type not in SUPPORTED_PROJECT_TYPES:
        allowed = ", ".join(SUPPORTED_PROJECT_TYPES)
        raise ProjectTemplateError(f"Unsupported project type: {project_type}. Allowed: {allowed}.")


def write_template_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold_project(
    target: Path,
    name: str,
    project_type: str = "game-basic",
    engine: str = "undecided",
    force: bool = False,
) -> TemplateResult:
    ensure_supported_type(project_type)
    project_name = normalize_project_name(name)
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    files = template_files(project_name, project_type, engine)
    if not force:
        existing_files = [target / relative_path for relative_path in files if (target / relative_path).exists()]
        if existing_files:
            existing = ", ".join(str(path) for path in existing_files[:5])
            suffix = "" if len(existing_files) <= 5 else f", and {len(existing_files) - 5} more"
            raise ProjectTemplateError(f"Refusing to overwrite existing file(s): {existing}{suffix}")

    written: list[str] = []
    for relative_path, content in files.items():
        destination = target / relative_path
        write_template_file(destination, content)
        written.append(relative_posix(destination, target))

    return TemplateResult(target=target, project_type=project_type, files=written)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a minimal AI Game Company project template.")
    parser.add_argument("target", help="Directory where the project template should be created.")
    parser.add_argument("--name", default="", help="Project display name. Defaults to target directory name.")
    parser.add_argument("--type", default="game-basic", choices=SUPPORTED_PROJECT_TYPES, help="Template type.")
    parser.add_argument("--engine", default="undecided", help="Game engine name for game templates.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target)
    name = args.name or target.name
    try:
        result = scaffold_project(
            target=target,
            name=name,
            project_type=args.type,
            engine=args.engine,
            force=args.force,
        )
    except ProjectTemplateError as exc:
        print(f"Template error: {exc}")
        return 2

    payload = {
        "target": str(result.target),
        "project_type": result.project_type,
        "files": result.files,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Created {len(result.files)} template files in {result.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
