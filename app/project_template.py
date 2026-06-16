from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_PROJECT_TYPES = (
    "game-basic",
    "game-pygame-mini",
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
    if project_type == "game-pygame-mini":
        return "game"
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


def test_runner_config(engine: str, project_type: str = "game-basic") -> dict[str, Any]:
    if project_type == "game-pygame-mini":
        commands = {
            "setup": [],
            "build": ["python -m compileall src tests scripts"],
            "test": ["python -m unittest discover -s tests"],
            "run": ["python scripts/smoke_check.py"],
        }
    else:
        commands = {
            "setup": [],
            "build": ["python --version"],
            "test": [],
            "run": [],
        }
    return {
        "version": 1,
        "engine": engine,
        "commands": commands,
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


def ai_company_test_runner_config(engine: str, project_type: str = "game-basic") -> dict[str, Any]:
    config = test_runner_config(engine, project_type)
    config["artifacts"] = {
        "root": ".ai-company/artifacts",
        "logs": ["test-runner.log"],
        "reports": ["test-runner-report.json"],
    }
    return config


def type_notes(project_type: str) -> str:
    notes = {
        "game-basic": "Focus on game concept, play loop, controls, visual direction, and engine choice.",
        "game-pygame-mini": "Focus on a tiny Pygame survival loop that validates the AI development pipeline.",
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
    extra = ""
    if project_type == "game-pygame-mini":
        extra = (
            "\n## Golden Path Smoke Commands\n\n"
            "```bash\n"
            "python -m compileall src tests scripts\n"
            "python -m unittest discover -s tests\n"
            "python scripts/smoke_check.py\n"
            "```\n\n"
            "Install `pygame` only when you want to open the interactive window:\n\n"
            "```bash\n"
            "python -m pip install -r requirements.txt\n"
            "python -m ai_survival_mini.main\n"
            "```\n"
        )
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
        f"{extra}"
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


def testing_text(project_type: str = "game-basic") -> str:
    if project_type == "game-pygame-mini":
        return (
            "# Testing\n\n"
            "The v1 test runner reads `.game-company/test_runner.json` and writes logs under "
            "`.game-company/artifacts/`.\n\n"
            "Golden Path validation commands:\n\n"
            "```bash\n"
            "python -m compileall src tests scripts\n"
            "python -m unittest discover -s tests\n"
            "python scripts/smoke_check.py\n"
            "```\n\n"
            "The smoke command does not require Pygame. It validates that the task runner can "
            "execute the project and collect logs before the interactive runtime is installed.\n"
        )
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


def pygame_game_state_py() -> str:
    return (
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n"
        "from math import hypot\n\n\n"
        "@dataclass\n"
        "class Player:\n"
        "    x: float = 400.0\n"
        "    y: float = 300.0\n"
        "    health: int = 100\n"
        "    speed: float = 220.0\n\n\n"
        "@dataclass\n"
        "class Enemy:\n"
        "    x: float\n"
        "    y: float\n"
        "    speed: float = 90.0\n\n\n"
        "def clamp(value: float, low: float, high: float) -> float:\n"
        "    return max(low, min(high, value))\n\n\n"
        "def move_player(player: Player, dx: float, dy: float, dt: float, width: int = 800, height: int = 600) -> Player:\n"
        "    length = hypot(dx, dy)\n"
        "    if length:\n"
        "        dx /= length\n"
        "        dy /= length\n"
        "    player.x = clamp(player.x + dx * player.speed * dt, 0, width)\n"
        "    player.y = clamp(player.y + dy * player.speed * dt, 0, height)\n"
        "    return player\n\n\n"
        "def enemy_step(enemy: Enemy, player: Player, dt: float) -> Enemy:\n"
        "    dx = player.x - enemy.x\n"
        "    dy = player.y - enemy.y\n"
        "    length = hypot(dx, dy)\n"
        "    if length:\n"
        "        enemy.x += dx / length * enemy.speed * dt\n"
        "        enemy.y += dy / length * enemy.speed * dt\n"
        "    return enemy\n\n\n"
        "def is_collision(player: Player, enemy: Enemy, radius: float = 28.0) -> bool:\n"
        "    return hypot(player.x - enemy.x, player.y - enemy.y) <= radius\n\n\n"
        "def enemy_count_for_time(elapsed_seconds: float) -> int:\n"
        "    return 1 + max(0, int(elapsed_seconds // 15))\n"
    )


def pygame_main_py() -> str:
    return (
        "from __future__ import annotations\n\n"
        "import argparse\n"
        "import json\n"
        "from pathlib import Path\n\n"
        "from ai_survival_mini.game_state import Enemy, Player, enemy_count_for_time, enemy_step, is_collision, move_player\n\n\n"
        "def smoke_payload() -> dict[str, object]:\n"
        "    player = Player()\n"
        "    enemy = Enemy(100.0, 100.0)\n"
        "    move_player(player, 1, 0, 0.1)\n"
        "    enemy_step(enemy, player, 0.1)\n"
        "    return {\n"
        "        \"status\": \"ok\",\n"
        "        \"player\": {\"x\": round(player.x, 2), \"y\": round(player.y, 2), \"health\": player.health},\n"
        "        \"enemy_count_at_60s\": enemy_count_for_time(60),\n"
        "        \"collision_now\": is_collision(player, enemy),\n"
        "    }\n\n\n"
        "def run_game() -> int:\n"
        "    try:\n"
        "        import pygame\n"
        "    except ImportError:\n"
        "        print(\"Pygame is not installed. Run: python -m pip install -r requirements.txt\")\n"
        "        return 2\n\n"
        "    pygame.init()\n"
        "    screen = pygame.display.set_mode((800, 600))\n"
        "    pygame.display.set_caption(\"AI Survival Mini\")\n"
        "    clock = pygame.time.Clock()\n"
        "    font = pygame.font.Font(None, 32)\n"
        "    player = Player()\n"
        "    enemies = [Enemy(80.0, 80.0)]\n"
        "    elapsed = 0.0\n"
        "    running = True\n"
        "    game_over = False\n"
        "    while running:\n"
        "        dt = clock.tick(60) / 1000.0\n"
        "        elapsed += dt\n"
        "        for event in pygame.event.get():\n"
        "            if event.type == pygame.QUIT:\n"
        "                running = False\n"
        "            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and game_over:\n"
        "                player = Player()\n"
        "                enemies = [Enemy(80.0, 80.0)]\n"
        "                elapsed = 0.0\n"
        "                game_over = False\n"
        "        keys = pygame.key.get_pressed()\n"
        "        if not game_over:\n"
        "            move_player(player, keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w], dt)\n"
        "            while len(enemies) < enemy_count_for_time(elapsed):\n"
        "                enemies.append(Enemy(40.0, 560.0))\n"
        "            for enemy in enemies:\n"
        "                enemy_step(enemy, player, dt)\n"
        "                if is_collision(player, enemy):\n"
        "                    player.health -= 20\n"
        "                    enemy.x, enemy.y = 40.0, 40.0\n"
        "            game_over = player.health <= 0 or elapsed >= 60\n"
        "        screen.fill((18, 22, 28))\n"
        "        pygame.draw.circle(screen, (80, 180, 255), (int(player.x), int(player.y)), 14)\n"
        "        for enemy in enemies:\n"
        "            pygame.draw.circle(screen, (240, 80, 70), (int(enemy.x), int(enemy.y)), 12)\n"
        "        hud = font.render(f\"HP {player.health}  Time {int(elapsed)}  Enemies {len(enemies)}\", True, (240, 240, 240))\n"
        "        screen.blit(hud, (16, 16))\n"
        "        if game_over:\n"
        "            label = font.render(\"Game Over - press R to restart\", True, (255, 220, 120))\n"
        "            screen.blit(label, (240, 280))\n"
        "        pygame.display.flip()\n"
        "    pygame.quit()\n"
        "    return 0\n\n\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        "    parser = argparse.ArgumentParser(description=\"AI Survival Mini\")\n"
        "    parser.add_argument(\"--smoke\", action=\"store_true\", help=\"Run a dependency-light smoke check.\")\n"
        "    parser.add_argument(\"--smoke-output\", default=\"\", help=\"Optional JSON output path.\")\n"
        "    args = parser.parse_args(argv)\n"
        "    if args.smoke:\n"
        "        payload = smoke_payload()\n"
        "        output = json.dumps(payload, indent=2)\n"
        "        if args.smoke_output:\n"
        "            Path(args.smoke_output).write_text(output + \"\\n\", encoding=\"utf-8\")\n"
        "        print(output)\n"
        "        return 0\n"
        "    return run_game()\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(main())\n"
    )


def pygame_smoke_check_py() -> str:
    return (
        "from __future__ import annotations\n\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "sys.path.insert(0, str(ROOT / \"src\"))\n\n"
        "from ai_survival_mini.main import main\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(main([\"--smoke\"]))\n"
    )


def pygame_test_game_state_py() -> str:
    return (
        "from __future__ import annotations\n\n"
        "import sys\n"
        "import unittest\n"
        "from pathlib import Path\n\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "sys.path.insert(0, str(ROOT / \"src\"))\n\n"
        "from ai_survival_mini.game_state import Enemy, Player, enemy_count_for_time, enemy_step, is_collision, move_player\n\n\n"
        "class GameStateTests(unittest.TestCase):\n"
        "    def test_player_movement_is_clamped(self) -> None:\n"
        "        player = Player(x=795, y=300)\n"
        "        move_player(player, 1, 0, 1.0)\n"
        "        self.assertEqual(player.x, 800)\n\n"
        "    def test_enemy_moves_toward_player(self) -> None:\n"
        "        player = Player(x=100, y=0)\n"
        "        enemy = Enemy(x=0, y=0, speed=10)\n"
        "        enemy_step(enemy, player, 1.0)\n"
        "        self.assertGreater(enemy.x, 0)\n"
        "        self.assertEqual(enemy.y, 0)\n\n"
        "    def test_collision_and_spawn_curve(self) -> None:\n"
        "        self.assertTrue(is_collision(Player(x=0, y=0), Enemy(x=10, y=0)))\n"
        "        self.assertEqual(enemy_count_for_time(0), 1)\n"
        "        self.assertEqual(enemy_count_for_time(60), 5)\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    unittest.main()\n"
    )


def pygame_requirements_text() -> str:
    return "pygame>=2.6\n"


def template_files(name: str, project_type: str, engine: str) -> dict[str, str]:
    if project_type == "game-pygame-mini" and engine in {"", "undecided"}:
        engine = "pygame"
    metadata = project_metadata(name, project_type, engine)
    ai_metadata = dict(metadata)
    ai_metadata["paths"] = dict(metadata["paths"])
    ai_metadata["paths"]["artifacts"] = ".ai-company/artifacts"
    files = {
        "README.md": readme_text(name, project_type, engine),
        ".gitignore": gitignore_text(),
        ".game-company/project.json": json_text(metadata),
        ".game-company/test_runner.json": json_text(test_runner_config(engine, project_type)),
        ".game-company/artifacts/.gitkeep": "",
        ".ai-company/project.json": json_text(ai_metadata),
        ".ai-company/test_runner.json": json_text(ai_company_test_runner_config(engine, project_type)),
        ".ai-company/artifacts/.gitkeep": "",
        "docs/DESIGN.md": design_text(name, project_type),
        "docs/TASKS.md": tasks_text(),
        "docs/TESTING.md": testing_text(project_type),
        "docs/DECISIONS.md": decisions_text(),
        "src/README.md": placeholder_text("Source"),
        "tests/README.md": placeholder_text("Tests"),
    }
    if project_type == "game-pygame-mini":
        files.update(
            {
                "requirements.txt": pygame_requirements_text(),
                "scripts/smoke_check.py": pygame_smoke_check_py(),
                "src/ai_survival_mini/__init__.py": "",
                "src/ai_survival_mini/game_state.py": pygame_game_state_py(),
                "src/ai_survival_mini/main.py": pygame_main_py(),
                "tests/test_game_state.py": pygame_test_game_state_py(),
            }
        )
    return files


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
