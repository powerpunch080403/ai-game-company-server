# V1 Portfolio Game - Task Templates

이 문서는 첫 번째 포트폴리오 게임(예: 2D Top-Down survival game)을 개발하기 위해 Owner 모델이 참고하여 자동 생성할 수 있는 **표준 작업 템플릿 목록**입니다. 모든 템플릿은 15~30분 크기로 적절히 쪼개진 모범 사례를 따릅니다.

---

### 1. Project Bootstrap Task
* **Goal**: Initialize the project directory with `.game-company` scaffolding and baseline directories.
* **Role**: `code_worker`
* **Branch**: `worker/project-bootstrap`
* **Estimated Minutes**: 30
* **Requirements**:
  - Scaffold project structures for src, tests, and docs using the project template script.
  - Create a valid `.game-company/project.json` and `.game-company/test_runner.json` using the Pygame mini or basic preset.
  - Initialize baseline `.gitignore`.
* **Success Criteria**:
  - `.game-company/test_runner.json` exists and validates with exit code 0.
  - Baseline directories are present on disk.
* **Evidence Required**:
  - Setup logs from workspace execution.
* **Memory Refs**: `project_rules`, `project_knowledge`

---

### 2. Basic Game Loop Task
* **Goal**: Create the main entry point running a standard Pygame game loop.
* **Role**: `code_worker`
* **Branch**: `worker/basic-game-loop`
* **Estimated Minutes**: 15
* **Requirements**:
  - Create `src/main.py` implementing a standard `pygame` loop with initialization, event processing (Quit event), rendering loop, and clock tick.
  - Render a solid black or dark grey background.
* **Success Criteria**:
  - Running `python src/main.py` in dummy mode executes without crashing.
* **Evidence Required**:
  - Test runner execution log.
* **Memory Refs**: `coding_rules`

---

### 3. Player Movement Task
* **Goal**: Implement WASD player keyboard control and boundary check logic.
* **Role**: `code_worker`
* **Branch**: `worker/player-movement`
* **Estimated Minutes**: 15
* **Requirements**:
  - Implement a `Player` class in `src/player.py` with variables for position (`x`, `y`) and movement speed.
  - Capture WASD keyboard events in the main loop to move the player shape on the screen.
  - Prevent the player from leaving the screen boundaries.
* **Success Criteria**:
  - Unittests in `tests/test_player.py` verify boundaries and movement calculation.
* **Evidence Required**:
  - Unittest pass report (`test.log`).
* **Memory Refs**: `coding_rules`, `project_knowledge`

---

### 4. Enemy Spawn Task
* **Goal**: Implement an enemy manager that spawns enemies periodically at random positions off-screen.
* **Role**: `code_worker`
* **Branch**: `worker/enemy-spawn`
* **Estimated Minutes**: 15
* **Requirements**:
  - Implement an `Enemy` class in `src/enemy.py` and an `EnemyManager` in `src/enemy_manager.py`.
  - Spawn an enemy off-screen every N frames/seconds and move them towards the player.
* **Success Criteria**:
  - Spawn intervals are verified via unit tests.
* **Evidence Required**:
  - Test log containing enemy spawn tests.
* **Memory Refs**: `project_knowledge`

---

### 5. Collision & Health Task
* **Goal**: Detect player-enemy collisions and subtract player health points.
* **Role**: `code_worker`
* **Branch**: `worker/collision-health`
* **Estimated Minutes**: 15
* **Requirements**:
  - Implement collision detection using bounding box rects (`pygame.Rect.colliderect`).
  - Upon collision, subtract points from player health.
  - Trigger player destruction if health <= 0.
* **Success Criteria**:
  - Collision unit tests pass under `tests/test_collision.py`.
* **Evidence Required**:
  - Unit test evidence reports.
* **Memory Refs**: `coding_rules`

---

### 6. Score & Time UI Task
* **Goal**: Render the current elapsed time and player score on the screen using Pygame fonts.
* **Role**: `code_worker`
* **Branch**: `worker/score-time-ui`
* **Estimated Minutes**: 30
* **Requirements**:
  - Initialize Pygame Font rendering in the main loop.
  - Render "Time: Xs" and "Score: Y" text overlays in the top corner of the screen.
* **Success Criteria**:
  - Render commands operate without errors in headless mode.
* **Evidence Required**:
  - Runtime execution log showing font initialization success.
* **Memory Refs**: `coding_rules`

---

### 7. Game Over & Restart Task
* **Goal**: Show a game over overlay when health hits 0, and support restarting via pressing space.
* **Role**: `code_worker`
* **Branch**: `worker/game-over-restart`
* **Estimated Minutes**: 15
* **Requirements**:
  - Introduce game states: `PLAYING` and `GAME_OVER`.
  - Draw "GAME OVER" text and "Press SPACE to Restart" text during `GAME_OVER` state.
  - Reset game timer, health, and scores when the Space key is pressed.
* **Success Criteria**:
  - State transitions are covered by unit tests.
* **Evidence Required**:
  - Test results and state verify logs.
* **Memory Refs**: `project_knowledge`

---

### 8. Smoke Test Artifact Task
* **Goal**: Implement a script that starts the game loop, takes a screen capture, and gracefully closes.
* **Role**: `code_worker`
* **Branch**: `worker/smoke-test-artifact`
* **Estimated Minutes**: 30
* **Requirements**:
  - Write `scripts/smoke_check.py` to launch the game using the dummy video driver.
  - Take a screenshot of the main screen after 100 frames and save it to `.game-company/artifacts/task-X/run-Y/screenshot.png`.
* **Success Criteria**:
  - Screenshot file is successfully written to disk.
* **Evidence Required**:
  - `screenshot.png` file on disk.
* **Memory Refs**: `project_rules`, `project_knowledge`

---

### 9. README & Update Task
* **Goal**: Update the project README with instructions on how to build, run, and test the game.
* **Role**: `code_worker`
* **Branch**: `worker/readme-update`
* **Estimated Minutes**: 15
* **Requirements**:
  - Document prerequisites (Python version, pygame library).
  - List execution commands: `python src/main.py`.
  - List test commands: `python -m unittest discover`.
* **Success Criteria**:
  - README.md contains verified execution command text blocks.
* **Evidence Required**:
  - Changed files validation list in report.
* **Memory Refs**: `project_rules`
