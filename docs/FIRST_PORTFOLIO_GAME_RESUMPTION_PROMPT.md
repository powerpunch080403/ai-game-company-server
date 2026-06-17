# First Portfolio Game Resumption Guide

이 문서는 Codex CLI 사용량이 초기화된 후 즉시 첫 번째 포트폴리오 게임 **Neon Survival Prototype**의 개발에 착수할 수 있도록 돕는 실전 가이드라인 및 프롬프트 명세입니다.

---

## 1. 첫 3개 Task 상세 가이드 (15~30분 크기)

에이전트가 오작동하지 않고 한 번에 성공하도록 매우 구체적이고 논리적인 조건들로 가이드라인을 정의했습니다.

### Task 1: Project Bootstrap
* **Goal**: Initialize the project directory with `.game-company` scaffolding and baseline directories.
* **Role**: `code_worker`
* **Branch**: `worker/project-bootstrap`
* **Estimated Minutes**: 30
* **Requirements**:
  - Scaffold project structure inside the workspace directory (`C:\Users\user2\.gemini\antigravity\scratch\neon-survival-workspace`):
    * Create empty directories: `src/game/`, `tests/`, `scripts/`, `assets/`, `docs/`.
    * Ensure `__init__.py` files exist in `src/` and `src/game/` to make them python packages.
  - Create a valid `.game-company/project.json` containing:
    ```json
    {
      "project_name": "Neon Survival Prototype",
      "engine": "pygame",
      "version": "1.0.0"
    }
    ```
  - Create `.game-company/test_runner.json` configured to run pytest:
    ```json
    {
      "phases": {
        "setup": "pip install -r requirements.txt",
        "test": "python -m pytest",
        "smoke": "python scripts/smoke_check.py"
      }
    }
    ```
  - Create a minimal `requirements.txt` containing `pygame-ce>=2.5.0` or `pygame>=2.5.0`.
  - Create a baseline `.gitignore` containing:
    ```text
    __pycache__/
    *.pyc
    .venv/
    *.log
    .game-company/artifacts/
    ```
* **Success Criteria**:
  - The directories `src/game`, `tests`, and `scripts` exist.
  - `.game-company/test_runner.json` is present and valid.
  - `requirements.txt` lists Pygame.
* **Evidence Required**: Workspace worker output log showing list of directories created.
* **Memory Refs**: `project_rules`, `project_knowledge`

---

### Task 2: Basic Game Loop
* **Goal**: Create the main entry point running a standard Pygame game loop.
* **Role**: `code_worker`
* **Branch**: `worker/basic-game-loop`
* **Estimated Minutes**: 20
* **Requirements**:
  - Create `src/game/settings.py` containing:
    ```python
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    FPS = 60
    BG_COLOR = (20, 20, 25) # Neon Dark Theme
    ```
  - Create `src/game/main.py` implementing:
    * Pygame window initialization (`pygame.init()`, `pygame.display.set_mode()`, `pygame.display.set_caption()`).
    * Game clock (`pygame.time.Clock()`).
    * Capture `pygame.QUIT` to break the loop.
    * Dummy video driver support (`os.environ.get("SDL_VIDEODRIVER") == "dummy"`).
    * Screen fill with `BG_COLOR` and frame update via `pygame.display.flip()`.
* **Success Criteria**:
  - Running `python -m src.game.main` in headless dummy mode completes successfully without crashing.
* **Evidence Required**: Test runner output showing game loop start and clean exit codes.
* **Memory Refs**: `coding_rules`

---

### Task 3: Player Movement & Boundary Checks
* **Goal**: Implement WASD player keyboard control and boundary check logic.
* **Role**: `code_worker`
* **Branch**: `worker/player-movement`
* **Estimated Minutes**: 25
* **Requirements**:
  - Create `src/game/player.py` containing:
    * `Player` class with `x`, `y`, `speed` (default: 5), `radius` (default: 15).
    * `update(keys)` method adjusting coordinate positions based on WASD keys pressed.
    * Constraint checks clamping `x` inside `[radius, SCREEN_WIDTH - radius]` and `y` inside `[radius, SCREEN_HEIGHT - radius]`.
    * `render(screen)` method drawing a glowing neon cyan circle: `pygame.draw.circle(screen, (0, 255, 255), (int(self.x), int(self.y)), self.radius, 2)`.
  - Instantiate `Player` in `src/game/main.py` and invoke its `update(pygame.key.get_pressed())` and `render(screen)` inside the main game loop.
  - Create `tests/test_player.py` with unit tests checking:
    * Movement updates coordinates correctly.
    * Player cannot move beyond screen borders.
* **Success Criteria**:
  - Running `python -m pytest tests/test_player.py` passes all assertions.
* **Evidence Required**: Pytest test run log (`test.log`).
* **Memory Refs**: `coding_rules`, `project_knowledge`

---

## 2. Codex CLI 재개 후 실행할 첫 프롬프트 (Execution Prompt)

Codex CLI가 활성화되었을 때 즉시 새 터미널이나 에이전트 인스턴스에 입력하여 실행을 개시할 프롬프트입니다.

```text
현재 로컬 개발 서버(FastAPI 포트 8080)와 Discord Gateway가 로컬에서 구동 중입니다.
첫 포트폴리오 게임 개발 착수를 위해 아래 단계를 정밀하게 자동 수행하고, 절대로 다른 추가적인 작업을 진행하지 마십시오.

[주의 사항]
- 본 작업은 오직 "Task 1: Project Bootstrap" 개발 단계만 다룹니다.
- Basic Game Loop(Task 2) 또는 Player Movement(Task 3) 등 다음 작업들을 미리 작성하거나 동시에 구현하지 마십시오.
- 어느 단계에서든 오류나 실패가 발생할 경우, 작업을 즉시 중단(Stop/Pause)하고 현재 상태를 사용자에게 보고한 뒤 피드백을 기다려야 합니다.
- 이 작업을 마친 후에는 다음 Task(Task 2 등)로 임대(Lease)를 시도하거나 넘어가지 말고 정지하십시오.

[수행할 단계]
1. `docs/FIRST_PORTFOLIO_GAME_SEED_DRAFT.md`에 기술된 "Neon Survival Prototype" 프로젝트 기획 명세를 바탕으로, `data/game_company.sqlite3` 데이터베이스에 신규 Project, Epic, SubEpic, 그리고 9개의 Task를 생성하는 시드 파이썬 스크립트(`scripts/seed_portfolio_game.py`)를 작성하고 실행해 주십시오. (주의: DB 외래 키 제약 조건 만족을 위해 project가 먼저 들어간 뒤 epic과 task가 순서대로 insert되어야 합니다.)
2. 시드 스크립트 실행이 성공하면, 첫 번째 작업인 "Task 1: Project Bootstrap" (branch: `worker/project-bootstrap`) 작업만 Lease(임대) 받아 주십시오.
3. 임대받은 `worker/project-bootstrap` 브랜치를 기준으로 새 워크스페이스 디렉토리(`C:\Users\user2\.gemini\antigravity\scratch\neon-survival-workspace`)에 git repository를 생성(git init)하고 다음 파일들만 정확히 작성해 주십시오:
   - 생성 및 구성해야 할 파일 목록:
     * `.game-company/project.json` (프로젝트 정보 및 pygame 엔진 타입 설정)
     * `.game-company/test_runner.json` (setup, test, smoke 단계 실행 정의)
     * `requirements.txt` (pygame-ce>=2.5.0 또는 pygame>=2.5.0 라이브러리 목록 지정)
     * `.gitignore` (__pycache__/, .venv/, *.log, .game-company/artifacts/ 타겟 지정)
4. 파일 작성이 완료되면 다음 테스트 명령어를 실행해 설정을 로컬 검증하십시오:
   - 검증 테스트 명령어:
     * Test Runner의 설정 로컬 정형 검증 (또는 API `/projects/{id}/tasks/{id}/test` Dry-Run 호출)
5. 테스트 검증이 성공적으로 통과하면 아래 메시지로 git commit을 작성하고 push해 주십시오:
   - 커밋 메시지: `feat: scaffold neon-survival-prototype workspace structure`
6. 푸시 후, 해당 브랜치에 대해 Owner Approval (자연어 "승인" 또는 API `/approvals/{id}/decision` 호출)을 획득하여 main 브랜치에 최종 병합(Merge)해 주십시오.
7. 병합이 성공적으로 끝난 후, 절대로 다음 태스크로 이행하지 말고 실행을 멈추십시오.
```

