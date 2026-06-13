# AI 게임 개발 회사 v1 서버

Owner가 설계하고 Worker가 실행하는 게임 개발 조직을 위한 최소 서버입니다.

현재 v1 구현 범위:

- Project > Epic > Sub Epic > Task 계층
- Project별 engine/repo/workspace/base branch 설정
- Task 필수 필드: Goal, Requirements, Success Criteria, Estimated Time, Memory Refs, Branch
- SQLite 기반 Memory DB
- Worker 작업 임대 API
- Worker 결과 보고 저장
- Worker 실행용 Task Package 생성
- Worker Runner CLI
- Owner Run API와 Owner Command Adapter
- Owner 대시보드와 재호출 판단 플래그

## 빠른 실행

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.seed
./scripts/run_dev.sh
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.seed
.\scripts\run_dev.ps1
```

API 문서:

```text
http://localhost:8080/docs
```

외부 접속을 열 때는 `.env`에 `GAME_COMPANY_API_TOKEN`을 반드시 설정하세요. 토큰이 설정된 서버에는 API 요청 시 아래 헤더가 필요합니다.

```text
Authorization: Bearer your-token
```

## Worker Runner

Worker는 서버에서 자기 역할의 Task를 1개 임대하고, 관련 Memory를 포함한 작업 패키지를 `runs/task-{id}`에 저장합니다.

패키지만 만들기:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --dry-run
```

명령까지 실행하고 결과 보고하기:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --command "python --version"
```

Windows PowerShell:

```powershell
.\scripts\run_worker.ps1 --worker-id code-1 --role code_worker --dry-run
```

생성되는 파일:

- `runs/task-{id}/task_package.json`
- `runs/task-{id}/instructions.md`
- `runs/task-{id}/command.log`

## API Worker

API Worker는 Task Package를 OpenAI-compatible Chat Completions API로 보내고, 응답을 저장한 뒤 Task 결과를 report합니다.

필요한 `.env` 설정:

```env
GAME_COMPANY_WORKER_API_BASE_URL=https://api.openai.com/v1
GAME_COMPANY_WORKER_API_KEY=your-api-key
GAME_COMPANY_WORKER_MODEL=your-worker-model
```

프롬프트만 생성해서 확인:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker --dry-run
```

특정 Task package만 확인하고 상태를 바꾸지 않기:

```bash
./scripts/run_api_worker.sh --task-id 1 --dry-run
```

API 호출 후 report:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker
```

현재 API Worker는 응답 생성과 report까지 담당합니다. 실제 파일 수정, Git branch 생성, 테스트 실행은 다음 단계에서 연결합니다.

## Workspace Worker

Workspace Worker는 Task를 lease하고, Project repo의 `worker/*` branch를 준비한 뒤, 지정한 명령을 실제 게임 workspace에서 실행합니다. 변경 파일이 있으면 commit하고 Task report를 서버에 저장합니다.

예시:

```bash
./scripts/run_workspace_worker.sh \
  --worker-id workspace-code-1 \
  --role code_worker \
  --command "python scripts/apply_task.py"
```

특정 Task를 report 없이 실험:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

특정 Task를 실행하고 report까지 올리기:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --report \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

안전 규칙:

- Task branch는 `worker/*`여야 합니다.
- 실행 전 workspace가 dirty면 기본적으로 중단합니다.
- 명령 성공 후 변경 파일이 있으면 자동 commit합니다.
- `--task-id` 모드는 기본적으로 report하지 않습니다.

## Git Workspace

Git Workspace Runner는 Task의 `Branch` 값을 사용해 게임 프로젝트 repo에서 `worker/*` 브랜치를 준비합니다.

추천 방식은 Project에 repo/workspace를 저장하는 것입니다. 엔진은 나중에 게임별로 고르면 되고, 현재는 `undecided`, `unity`, `unreal`, `godot`, `custom` 같은 메모 값으로만 사용합니다.

Project 생성 예시:

```bash
curl -X POST http://localhost:8080/projects \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"First Game",
    "description":"Prototype game",
    "engine":"undecided",
    "repo_url":"https://github.com/your-account/your-game-repo.git",
    "workspace_path":"/home/powerpunch/game-workspaces/first-game",
    "base_branch":"main"
  }'
```

기존 Project 설정 수정:

```bash
curl -X PATCH http://localhost:8080/projects/1/config \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "engine":"unity",
    "repo_url":"https://github.com/your-account/your-game-repo.git",
    "workspace_path":"/home/powerpunch/game-workspaces/first-game",
    "base_branch":"main"
  }'
```

전역 fallback `.env` 설정:

```env
GAME_COMPANY_GAME_REPO_URL=https://github.com/your-account/your-game-repo.git
GAME_COMPANY_GAME_WORKSPACE=/home/powerpunch/game-workspace
GAME_COMPANY_GAME_BASE_BRANCH=main
```

Task 1의 branch 준비:

```bash
./scripts/prepare_git_workspace.sh --task-id 1
```

메인컴퓨터에서 엔진 미정 테스트용 repo 만들기:

```bash
./scripts/bootstrap_demo_game_repo.sh
```

기본 생성 위치:

```text
/home/powerpunch/game-repos/demo-game.git
```

로컬 package 파일로 준비:

```bash
./scripts/prepare_git_workspace.sh --package runs/api-task-1/task_package.json
```

안전 규칙:

- Task branch는 반드시 `worker/`로 시작해야 합니다.
- Workspace가 이미 다른 origin을 바라보면 중단합니다.
- 기본 branch를 최신화한 뒤 Task branch를 checkout합니다.

## Owner Run

Owner는 `/owner/runs`로 호출합니다. v1에서는 Owner 프롬프트와 실행 결과를 DB에 저장하고, 실제 CLI 실행은 `.env`의 `GAME_COMPANY_OWNER_COMMAND`로 연결합니다.

Codex CLI가 아직 설정되지 않았거나 테스트만 하고 싶을 때:

```bash
curl -X POST http://localhost:8080/owner/runs \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"objective":"전투 시스템을 Epic/Sub Epic/Task로 분해","context":"게임 엔진은 아직 미정","dry_run":true}'
```

명령 설정 예시:

```env
GAME_COMPANY_OWNER_COMMAND=cat {prompt_file}
GAME_COMPANY_OWNER_TIMEOUT_SECONDS=900
GAME_COMPANY_OWNER_RUNS_DIR=./owner-runs
```

`GAME_COMPANY_OWNER_COMMAND`는 `{prompt_file}`과 `{run_dir}` placeholder를 사용할 수 있습니다. placeholder가 없으면 서버가 Owner 프롬프트를 표준 입력으로 전달합니다.

## Ubuntu 메인 서버 배포 초안

현재 추천 배포 경로는 sudo 없이 운영 가능한 `/home/powerpunch/ai-game-company-server`입니다.

Windows 노트북에서 메인컴퓨터로 배포:

```powershell
.\scripts\deploy_main_server.ps1
```

배포 스크립트가 하는 일:

- 현재 Git 커밋을 archive로 묶어 SSH 전송
- Python venv 생성
- requirements 설치
- `.env` 생성
- 최초 DB seed

메인컴퓨터에서 서버 시작:

```bash
./scripts/run_dev.sh
```

또는 백그라운드 실행:

```bash
./scripts/start_server.sh
```

중지:

```bash
./scripts/stop_server.sh
```

외부에서도 접근하려면 공유기/방화벽에서 8080 포트 접근을 허용해야 합니다. 공개 인터넷에 열 경우 `GAME_COMPANY_API_TOKEN` 없이 실행하지 마세요.

## DB 백업

추천 기본값은 `./backups`에 SQLite 백업을 남기는 방식입니다.

```bash
./scripts/backup_db.sh
```

백업은 Python 표준 라이브러리의 SQLite backup API를 사용하므로 별도 `sqlite3` CLI 설치가 필요 없습니다.

## 머신 설정

실제 Tailscale/SSH 정보는 Git에 올리지 않습니다.

```bash
cp config/machines.example.json config/machines.json
```

그 뒤 `config/machines.json`에 메인 서버와 게임 개발 머신의 `host`, `ssh_user`, `workspace`를 채웁니다.

SSH 연결 확인:

```bash
./scripts/check_remote.sh ubuntu@100.x.y.z
```

Windows:

```powershell
.\scripts\check_remote.ps1 ubuntu@100.x.y.z
```

## 기본 흐름

1. Owner가 Project/Epic/Sub Epic/Task 생성
2. Worker가 `/workers/{worker_id}/lease`로 자기 역할의 Task 1개 임대
3. Worker가 브랜치에서 작업
4. Worker가 `/workers/{worker_id}/tasks/{task_id}/report`로 결과 보고
5. Owner가 `/owner/dashboard`에서 상태 확인

## 역할 이름

- `code_worker`
- `image_worker`
- `voice_worker`
- `test_runner`

## 다음 구현 후보

- SSH로 게임 개발 머신에서 브랜치 생성/테스트 실행 자동화
- LLM 모델 설정 테이블
- 실제 LLM Worker 어댑터
- 실패 2회 반복 시 검색 트리거
- task_history 메모리 자동 생성
- systemd 서비스 파일
