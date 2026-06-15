from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.project_template import ProjectTemplateError, scaffold_project


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_scaffold_game_project_writes_required_files(tmp_path: Path) -> None:
    target = tmp_path / "demo-game"

    result = scaffold_project(target, "Demo Game")

    assert result.project_type == "game-basic"
    assert "README.md" in result.files
    assert ".game-company/test_runner.json" in result.files
    assert ".ai-company/test_runner.json" in result.files
    assert (target / "docs" / "DESIGN.md").is_file()
    assert (target / "src" / "README.md").is_file()
    assert (target / "tests" / "README.md").is_file()

    project = read_json(target / ".game-company" / "project.json")
    assert project["name"] == "Demo Game"
    assert project["project_type"] == "game"
    assert project["engine"] == "undecided"
    assert project["paths"]["artifacts"] == ".game-company/artifacts"

    runner = read_json(target / ".game-company" / "test_runner.json")
    assert runner["commands"]["build"] == ["python --version"]
    assert runner["artifacts"]["root"] == ".game-company/artifacts"


def test_scaffold_web_project_uses_framework_instead_of_engine(tmp_path: Path) -> None:
    target = tmp_path / "dashboard"

    scaffold_project(target, "Dashboard", project_type="web-basic")

    project = read_json(target / ".game-company" / "project.json")
    assert project["project_type"] == "web"
    assert "engine" not in project
    assert project["framework"] == "undecided"
    assert "Focus on user flows" in (target / "docs" / "DESIGN.md").read_text(encoding="utf-8")


def test_scaffold_refuses_to_overwrite_existing_file_without_force(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    target.joinpath("README.md").write_text("keep me\n", encoding="utf-8")

    with pytest.raises(ProjectTemplateError, match="Refusing to overwrite existing file"):
        scaffold_project(target, "Existing")

    assert target.joinpath("README.md").read_text(encoding="utf-8") == "keep me\n"


def test_scaffold_force_overwrites_existing_template_files(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    target.joinpath("README.md").write_text("old\n", encoding="utf-8")

    scaffold_project(target, "Existing", force=True)

    assert target.joinpath("README.md").read_text(encoding="utf-8").startswith("# Existing")


def test_project_template_cli_prints_json(tmp_path: Path) -> None:
    target = tmp_path / "cli-game"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.project_template",
            str(target),
            "--name",
            "CLI Game",
            "--json",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["project_type"] == "game-basic"
    assert ".game-company/test_runner.json" in payload["files"]
    assert target.joinpath(".game-company", "test_runner.json").is_file()
