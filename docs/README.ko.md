# AI Game Company Server v1

## 언어

* 영어: [../README.md](../README.md)
* 한국어: 이 문서

## 개요

* AI Game Company Server는 AI 지원 소프트웨어 개발 워크플로우를 실행하기 위한 제어 서버(Control Server)입니다.
* 첫 번째 대상은 게임 개발이지만, v1 설계는 앱, 웹, 백엔드, 도구, 자동화 및 플러그인 프로젝트도 지원할 수 있습니다.
* 이 서버는 게임 런타임 서버가 아닙니다.
* 이것은 프로젝트 제어 평면(Control Plane)입니다.

> [!WARNING]
> * 본 서버는 로컬 또는 사설 VPN(예: Tailscale) 워크플로우를 위한 **비프로덕션 프로토타입(non-production prototype)**입니다. HTTPS 및 적절한 토큰 인증 없이 raw HTTP/WS 포트를 외부 인터넷에 공개적으로 노출하지 마십시오.
> * 이 제어 평면이 관리하는 저장소나 워크스페이스 저장소에 **실제 자격 증명(credentials), 토큰 또는 API 비밀 키(secrets)를 절대로 커밋하지 마십시오**.

## 전체 흐름

```text
사용자 / 오너 (User / Owner)
  -> 프로젝트 / 에픽 / 서브 에픽 / 작업 계획 (Project / Epic / Sub Epic / Task planning)
  -> 워커 작업 대여 및 실행 (Worker task lease and execution)
  -> 보고서, 아티팩트, 결재, 메모리 및 git 브랜치 (Reports, artifacts, approvals, memory, and git branches)
  -> 오너 검토, 재시도, 취소, 해제, 병합 또는 계속 진행 (Owner review, retry, cancel, release, merge, or continue)
```

이 저장소는 현재 친구들과 다른 AI 에이전트들이 설계를 검사할 수 있도록 공개(public)되어 있습니다. 실제 비밀 정보를 본 저장소에 추가하지 마십시오.

## 현재 상태

v1은 통제된 Task 1 부트스트랩에 사용 가능합니다. Golden Path 리허설이 성공적으로 완료되었으며, 이는 첫 번째 포트폴리오 게임 개발을 시작하기 위한 최소한의 운영 기반을 제공합니다.

구현된 항목:

- SQLite 스토리지를 탑재한 FastAPI 서버.
- Project > Epic > Sub Epic > Task 계층 구조.
- 유형화된(typed) 메모리 저장 및 검색.
- 워커 대여(lease), 점유(claim), 패키징(package), 보고(report), 이력(history), 작업 이벤트(task event) API.
- 오너 대시보드, 준비도(readiness), 큐 검토, 머지 검토, 오너 실행(Owner run) API.
- OpenAI 호환 챗 컴플리션을 위한 API 워커(API Worker).
- git 브랜치 준비, 명령 실행, 커밋, 푸시 및 결과 보고를 수행하는 워크스페이스 워커(Workspace Worker).
- 테스트 러너(Test Runner) 래퍼, 보고서 매퍼(report mapper) 및 전체 테스트 러너 워커 루프.
- 하트비트 기능이 포함된 워커 및 머신 레지스트리(Worker & Machine Registry) API.
- 아티팩트 메타데이터, 설정된 크기 제한 이하의 소형 아티팩트 업로드, 다운로드, 보존 필드 및 크기 제한 (대용량 파일의 실시간 스트리밍 업로드는 현재 검증된 경로에 포함되지 않음).
- 결재 요청(approval request) 및 단방향 의사결정(one-way decision) API.
- 역할 범위가 지정된(role-scoped) API 토큰.
- 워커 명령 데니어리스트(denylist) 및 선택적 명령 얼로우리스트(allowlist).
- FastAPI 라우트의 `app/api/routes` 분리.
- Discord 매핑 API.
- Discord 봇 드라이런(dry-run) 라우터.
- Discord Gateway 런타임 스켈레톤.
- 260k 예상 토큰 임계값 기반 Discord 컨텍스트 압축 API.
- `/owner/runs`로 연결되는 Discord 드라이런 브릿지.
- 엔진 독립적인(engine-agnostic) 프로젝트 템플릿 스캐폴드.

미구현 항목:

- 프로덕션 환경에서 테스트된 Discord Gateway 배포.
- 자동 Discord 스레드 이력 가져오기(fetching).
- 원본 Discord 스레드의 자동 LLM 요약.
- 상시 실행(always-on)되는 실제 systemd 배포.
- 웹 UI.
- 벡터 메모리 검색(Vector memory search).

## 추천 문서

- [Architecture Blueprint](../docs/ARCHITECTURE_BLUEPRINT.md)
- [Context Handoff](../docs/CONTEXT_HANDOFF.md)
- [Roadmap](../docs/ROADMAP.md)
- [Server Configuration](../docs/SERVER_CONFIGURATION.md)
- [Discord Operator Console](../docs/DISCORD_OPERATOR_CONSOLE.md)
- [Discord Bot Setup](../docs/DISCORD_BOT_SETUP.md)
- [Context Compaction](../docs/CONTEXT_COMPACTION.md)
- [Test Runner Contract](../docs/TEST_RUNNER_CONTRACT.md)
- [Game Project Template](../docs/GAME_PROJECT_TEMPLATE.md)
- [Hardware Environment](../docs/HARDWARE_ENVIRONMENT.md)
- [Golden Path v1](../docs/GOLDEN_PATH.md)
- [MCP Extension Plan](../docs/MCP_EXTENSION_PLAN.md)

## 빠른 시작

Linux/macOS:

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

API 문서 URL:

```text
http://localhost:8080/docs
```

테스트 실행:

```bash
python -m pytest
```

## 환경 설정

로컬 설정을 위해 `.env.example` 파일을 `.env`로 복사하십시오.

주요 설정 값:

```env
GAME_COMPANY_DB_PATH=./data/game_company.sqlite3
GAME_COMPANY_HOST=0.0.0.0
GAME_COMPANY_PORT=8080

GAME_COMPANY_API_TOKEN=change-me-before-external-access
GAME_COMPANY_OWNER_TOKEN=
GAME_COMPANY_WORKER_TOKEN=
GAME_COMPANY_READONLY_TOKEN=
GAME_COMPANY_ARTIFACT_TOKEN=

GAME_COMPANY_ARTIFACT_ROOT=./artifacts
GAME_COMPANY_MAX_ARTIFACT_UPLOAD_BYTES=104857600

GAME_COMPANY_CONTEXT_COMPACT_THRESHOLD_TOKENS=260000
GAME_COMPANY_CONTEXT_WARNING_TOKENS=220000
GAME_COMPANY_CONTEXT_CHARS_PER_TOKEN=3.5

GAME_COMPANY_OWNER_COMMAND=
GAME_COMPANY_OWNER_TIMEOUT_SECONDS=900
GAME_COMPANY_OWNER_RUNS_DIR=./owner-runs

GAME_COMPANY_WORKER_API_BASE_URL=https://api.openai.com/v1
GAME_COMPANY_WORKER_API_KEY=
GAME_COMPANY_WORKER_MODEL=

GAME_COMPANY_DISCORD_SERVER_TOKEN=
DISCORD_BOT_TOKEN=
DISCORD_APPLICATION_ID=
```

API 토큰이 설정되면, 비공개 API 요청에 다음 헤더가 포함되어야 합니다:

```text
Authorization: Bearer your-token
```

토큰 역할 설명:

- `GAME_COMPANY_API_TOKEN`: 비상용/어드민 관리용 토큰.
- `GAME_COMPANY_OWNER_TOKEN`: 오너 및 운영 작업을 위한 토큰.
- `GAME_COMPANY_WORKER_TOKEN`: 작업 대여, 점유, 결과 보고, 하트비트 및 작업 패키지 조회용 토큰.
- `GAME_COMPANY_READONLY_TOKEN`: `GET` 요청 전용 토큰.
- `GAME_COMPANY_ARTIFACT_TOKEN`: 아티팩트 엔드포인트 전용 토큰.

## 주요 개념

오너 (Owner):
- 사용자와 대화합니다.
- 프로젝트 방향을 설계합니다.
- 작업을 태스크 단위로 분할합니다.
- 결과 보고서를 검토하고 재시도, 취소, 릴리스, 머지 또는 계속 진행 여부를 결정합니다.

API 워커 (API Worker):
- OpenAI 호환 API 호출을 사용합니다.
- 요약, 초안 작성, 분석 및 가벼운 생성 작업을 지원합니다.
- 작업 분할을 직접 처리하지 않습니다.

워크스페이스 워커 (Workspace Worker):
- 작업을 대여(lease)합니다.
- `worker/*` 형식의 git 브랜치를 준비합니다.
- 프로젝트 워크스페이스 내에서 구성된 명령을 실행합니다.
- 변경된 파일을 커밋하고 선택적으로 푸시합니다.
- 결과를 서버에 보고합니다.

테스트 러너 (Test Runner):
- `.game-company/test_runner.json`에 정의된 각 단계(phase)들을 실행합니다.
- 로그 및 `test-runner-report.json`을 기록합니다.
- 로컬 보고서 데이터를 서버의 워커 보고 계약(report contract) 규격에 맞게 매핑합니다.

Discord 봇 (Discord Bot):
- v1 운영 콘솔 브릿지 역할을 수행합니다.
- 드라이런 라우터와 Gateway 런타임 스켈레톤이 구현되어 있습니다.

## Worker Runner

작업 패키지만 생성:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --dry-run
```

명령 실행 및 보고:

```bash
./scripts/run_worker.sh --worker-id code-1 --role code_worker --command "python --version"
```

Windows:

```powershell
.\scripts\run_worker.ps1 --worker-id code-1 --role code_worker --dry-run
```

## API Worker

필요한 환경 변수:

```env
GAME_COMPANY_WORKER_API_BASE_URL=https://api.openai.com/v1
GAME_COMPANY_WORKER_API_KEY=your-api-key
GAME_COMPANY_WORKER_MODEL=your-worker-model
```

프롬프트 드라이런만 실행:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker --dry-run
```

API 호출 실행 및 보고:

```bash
./scripts/run_api_worker.sh --worker-id api-code-1 --role code_worker
```

## Workspace Worker

대여된 다음 작업에 대해 워크스페이스 명령 실행:

```bash
./scripts/run_workspace_worker.sh \
  --worker-id workspace-code-1 \
  --role code_worker \
  --command "python scripts/apply_task.py"
```

결과 보고 없이 특정 작업 실행:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

특정 작업 실행 및 보고:

```bash
./scripts/run_workspace_worker.sh \
  --task-id 2 \
  --report \
  --command "mkdir -p docs && echo hello > docs/worker-test.md"
```

안전 규칙:
- 작업 브랜치는 반드시 `worker/`로 시작해야 합니다.
- 워크스페이스가 더럽혀진(dirty) 상태이면 기본적으로 실행이 중단됩니다.
- 잘못된 git origin을 가진 기존 워크스페이스는 거부됩니다.
- 워커 쉘 명령은 v1 안전 게이트(safety gate)를 거칩니다.

선택적 명령 얼로우리스트(allowlist):

```env
GAME_COMPANY_ALLOWED_COMMAND_PREFIXES=python -m pytest,npm test
```

## Test Runner

전체 테스트 러너 워커 루프 실행:

```bash
./scripts/run_test_runner_worker.sh --worker-id test-runner-1
```

특정 패키지를 로컬에서 실행:

```bash
./scripts/run_test_runner.sh \
  --package runs/workspace-task-12/task_package.json \
  --workspace /path/to/game-workspace
```

로컬 보고서를 서버 보고서 JSON으로 매핑:

```bash
./scripts/map_test_runner_report.sh \
  --package runs/workspace-task-12/task_package.json \
  --report .game-company/artifacts/task-12/run-20260614T120000Z/test-runner-report.json
```

## 프로젝트 템플릿 스캐폴드

엔진 독립적인 최소한의 프로젝트 저장소 레이아웃 생성:

```bash
./scripts/create_project_template.sh /path/to/demo-game \
  --name "Demo Game" \
  --type game-basic
```

Golden Path Pygame 데모 스캐폴드 생성:

```bash
./scripts/create_project_template.sh /path/to/ai-survival-mini \
  --name "AI Survival Mini" \
  --type game-pygame-mini
```

Windows:

```powershell
.\scripts\create_project_template.ps1 C:\path\to\demo-game `
  --name "Demo Game" `
  --type game-basic
```

지원 유형:

```text
game-basic
game-pygame-mini
web-basic
app-basic
backend-basic
tool-basic
automation-basic
plugin-basic
```

템플릿에는 `.game-company/test_runner.json` 및 향후 비게임 프로젝트를 위한 `.ai-company/` 메타데이터가 포함됩니다. `game-pygame-mini`에는 대화형 창을 위해 Pygame을 설치하기 전에 Golden Path 리허설이 실행될 수 있도록 표준 라이브러리 기반의 소형 스모크 루프가 포함되어 있습니다.

## Golden Path 리허설

Golden Path 리허설은 `game-pygame-mini` 스캐폴드를 사용하여 전체 v1 루프를 종단 End-to-End로 검증합니다. 자체 베어 bare 저장소, 개발/테스트 워크스페이스, SQLite 데이터베이스 및 FastAPI 서버가 포함된 독립 격리된 환경을 생성합니다.

리허설 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\rehearse_golden_path.ps1
```

스크립트의 실행 단계 (13단계):

1. `rehearsal/` 디렉토리를 정리하고 새로 생성합니다.
2. 베어 Git 저장소(`rehearsal/demo-game.git`)를 초기화합니다.
3. `game-pygame-mini` 템플릿을 스캐폴딩하여 베어 저장소에 푸시합니다.
4. 베어 저장소로부터 개발(dev) 및 테스트(test) 워크스페이스를 클론합니다.
5. 데이터베이스에 프로젝트, 에픽, 서브에픽 및 태스크 데이터를 시드 seed합니다.
6. 워커 수정 스크립트(플레이어 속도를 220에서 250으로 변경)를 작성합니다.
7. 포트 8082에서 FastAPI 서버를 가동합니다.
8. Workspace Worker를 작동: 태스크를 대여하고, 코드를 수정하며, 커밋한 후 `worker/*` 브랜치에 푸시합니다.
9. Test Runner 작동: 워커 브랜치를 가져와 빌드/테스트/스모크 단계를 수행합니다.
10. 테스트 러너 보고서를 찾아서 유효성을 검증합니다.
11. 아티팩트 메타데이터를 등록하고 보고서 내용을 업로드합니다.
12. 병합 대상 후보를 검사하고 오너 머지 Owner merge를 트리거합니다.
13. 베어 저장소의 git 이력에서 병합 커밋을 검증합니다.

예상되는 최종 출력 메시지:

```text
==================================================
GOLDEN PATH REHEARSAL COMPLETED SUCCESSFULLY!
==================================================

What was validated:
  [OK] Project scaffold (game-pygame-mini)
  [OK] Database seeding (project, epic, sub-epic, task)
  [OK] FastAPI server startup and health check
  [OK] Workspace Worker: lease, modify, commit, push
  [OK] Test Runner: build, test, smoke phases
  [OK] Artifact: register metadata and upload content
  [OK] Owner merge: worker branch merged into main
```

성공적으로 실행을 마친 뒤 `rehearsal/` 디렉토리에는 검사를 위한 모든 중간 파일들이 남겨집니다. 디렉토리를 삭제하려면 `Remove-Item -Recurse -Force .\rehearsal` 명령을 사용하십시오.

## Owner Run

오너 드라이런 생성 예시:

```bash
curl -X POST http://localhost:8080/owner/runs \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "objective":"Break combat system into Epic/Sub Epic/Task",
    "context":"The game engine is undecided.",
    "dry_run":true
  }'
```

어댑터 명령 예시:

```env
GAME_COMPANY_OWNER_COMMAND=cat {prompt_file}
```

`GAME_COMPANY_OWNER_COMMAND` 환경 변수는 `{prompt_file}` 및 `{run_dir}`을 매개변수로 사용할 수 있습니다. 플레이스홀더를 사용하지 않는 경우 프롬프트는 표준 입력 stdin을 통해 전달됩니다.

## Discord Mapping API

Discord 채널/스레드에서 서버 대화로의 매핑 생성 예시:

```bash
curl -X POST http://localhost:8080/discord/mappings \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_guild_id":"guild-1",
    "discord_channel_id":"channel-1",
    "discord_thread_id":"thread-owner-design",
    "project_id":1,
    "conversation_kind":"project",
    "thread_role":"owner-design",
    "created_by":"owner",
    "summary_memory_key":"project:1:thread:thread-owner-design:summary:current",
    "notes":"Owner design thread for this project."
  }'
```

활성 매핑 목록 조회:

```bash
curl "http://localhost:8080/discord/mappings?project_id=1&active=true" \
  -H "Authorization: Bearer your-token"
```

## Context Compaction

서버는 매핑된 Discord/Owner 대화가 구성된 컨텍스트 제한에 가까워졌는지 여부를 추정할 수 있습니다.

상태 검사:

```bash
curl -X POST http://localhost:8080/discord/mappings/discord_mapping_id/context-status \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "recent_messages":["Owner and AI conversation text..."],
    "estimated_extra_tokens":2000
  }'
```

기본 값:

```text
warning: 220000 estimated tokens (경보)
compact: 260000 estimated tokens (압축 요청)
```

압축 요약 compact summary 저장:

```bash
curl -X POST http://localhost:8080/discord/mappings/discord_mapping_id/compact \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "summary":"Current compact summary for the thread.",
    "archive_mapping":true,
    "continuation_discord_thread_id":"thread-owner-tasks-part-2"
  }'
```

이 계산은 서버 측 추정치입니다. Codex CLI의 내부 컨텍스트 계산 수치를 직접 조회하지 않습니다.

## Discord Bot Dry Run

실제 Discord Gateway 없이 메시지 라우팅 시뮬레이션:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-design \
  --content "Where are we on combat?" \
  --project-id 1 \
  --conversation-kind project \
  --thread-role owner-tasks
```

서버에 컨텍스트 상태 조회:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-design \
  --content "/context" \
  --check-context \
  --estimated-extra-tokens 2000
```

Owner로 라우팅되는 메시지를 Owner 드라이런으로 제출:

```bash
./scripts/run_discord_bot.sh \
  --guild-id guild-1 \
  --channel-id channel-1 \
  --thread-id thread-owner-tasks \
  --content "Break this into worker tasks." \
  --submit-owner-run
```

이 명령은 기본적으로 `dry_run=true`로 제출합니다. `GAME_COMPANY_OWNER_COMMAND`가 구성되어 있고 실제 명령 실행을 원하는 경우에만 `--execute-owner-run` 옵션을 추가하십시오.

## Discord Gateway Runtime

Discord Developer Portal에서 직접 봇을 생성해야 합니다. 디스코드 계정 패스워드나 봇 토큰을 채팅창이나 코드에 노출하지 마십시오.

로컬 `.env` 파일에 토큰을 설정합니다:

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_APPLICATION_ID=your-discord-application-id
GAME_COMPANY_DISCORD_SERVER_TOKEN=owner-or-admin-token-for-server-api
GAME_COMPANY_SERVER=http://127.0.0.1:8080
```

설정 상태 확인:

```bash
./scripts/check_discord_setup.sh
```

Windows:

```powershell
.\scripts\check_discord_setup.ps1
```

Gateway 런타임 구동:

```bash
./scripts/run_discord_gateway.sh
```

Windows:

```powershell
.\scripts\run_discord_gateway.ps1
```

선택적 안전 오너 실행 Owner run 저장:

```bash
./scripts/run_discord_gateway.sh --submit-owner-run
```

이 구동 방식은 Owner 메시지를 `dry_run=true` 상태로 보관합니다. `GAME_COMPANY_OWNER_COMMAND`가 구성되어 있으며 실제 명령 처리를 원하는 경우에만 `--execute-owner-run` 옵션을 사용하십시오.

Discord 필수 조건:
- 봇이 해당 Discord 서버에 초대되어 있어야 합니다.
- 봇 애플리케이션의 Message Content Intent가 활성화되어 있어야 합니다.
- 매핑된 채널 또는 스레드에서 메시지를 읽고 쓸 수 있는 권한이 봇에 부여되어야 합니다.
- 채널 및 스레드 ID가 `/discord/mappings`를 통해 미리 등록되어 있어야 합니다.

## Artifact API

아티팩트 메타데이터 생성 예시:

```bash
curl -X POST http://localhost:8080/artifacts \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id":"shot-001",
    "project_id":1,
    "task_id":2,
    "worker_id":"test-runner-1",
    "machine_id":"test_runner_12400_3060",
    "artifact_type":"screenshot",
    "filename":"screen.png",
    "content_type":"image/png",
    "summary":"First visual check",
    "tags":["visual","smoke"],
    "important":true
  }'
```

아티팩트 본문 업로드 예시:

```bash
curl -X PUT "http://localhost:8080/artifacts/shot-001/content?filename=screen.png&content_type=image/png" \
  -H "Authorization: Bearer your-token" \
  --data-binary "@screen.png"
```

## Approval API

결재 요청 등록 예시:

```bash
curl -X POST http://localhost:8080/approvals \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id":"repo-setup-1",
    "project_id":1,
    "target_type":"repo_setup",
    "target_id":"first-project",
    "requested_by":"owner",
    "request_summary":"Create GitHub private repo and project workspace.",
    "risk_summary":"Creates external repo and local workspace.",
    "approval_message":"Say approved to continue."
  }'
```

결재 처리 의사결정 내리기 예시:

```bash
curl -X POST http://localhost:8080/approvals/repo-setup-1/decision \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "status":"approved",
    "approved_by":"user",
    "approval_message":"Approved."
  }'
```

## Machine Notes

현재 알려진 머신 운영 계획:

- 메인 서버: i5-14600KF, RTX 4070, 32 GB DDR5, Ubuntu Desktop.
- 테스트 러너 계획 장비: i5-12400, RTX 3060.
- 로컬 Windows 노트북: 개발 워크스페이스 전용.

원격지 머신이 종료되어 있더라도, 원격 SSH에 의존하지 않고 로컬 설계, 구현 및 테스트 작업이 계속해서 가능해야 합니다.

## 다음 작업

추천되는 후속 단계:

1. ~~별도의 데모 게임 레포를 기반으로 Golden Path 안정화 수행.~~ ✅ 완료.
2. ~~데모 게임을 위한 최소한의 Pygame Test Runner 프리셋 추가.~~ ✅ 완료.
3. ~~워커 브랜치, 커밋, 보고, 아티팩트 업로드, 오너 검토 및 병합/재시도 리허설 진행.~~ ✅ 완료.
4. ~~README에 구체적인 리허설 명령 설명 기록.~~ ✅ 완료.
5. 헤드리스 headless CI/CD 환경에서 구동될 수 있도록 Pygame Test Runner 강화.
6. 루프가 완전히 안정화될 때까지 Discord 수준은 설정/상태/결재 범위로 국한 유지.
7. 구성된 한도 내에서 작동하는 아티팩트 업로드 추가 (설정된 크기 한도 이하의 업로드만 검증됨. 대용량 파일의 완전한 스트리밍 업로드는 향후 과제로 남겨둠).
8. 상시 실행 모드가 승인된 후 systemd 유닛 파일 추가.
9. 전체 우선순위 작업 목록은 `docs/TODO_LIST.md` 및 `docs/NEXT_ANTIGRAVITY_TASK.md`를 참고하십시오.

## 첫 포트폴리오 게임 계획

* **첫 검증 게임**: Neon Survival Prototype
* Pygame 기반의 2D 탑다운 서바이벌 미니게임입니다.
* 플레이 가능한 포트폴리오 프로젝트이자, 제어 서버를 E2E로 검증하는 하네스 역할을 수행합니다.
* MVP 핵심 기능: 캐릭터 이동, 적 스폰 및 추적, 충돌 및 체력 시스템, 타이머/점수 기록, 게임 오버/재시작, 심플한 네온 비주얼 스타일.
* 게임 개발 재개 시 실행할 첫 번째 작업은 오직 **Task 1: Project Bootstrap**뿐입니다.
* 워커 브랜치 푸시 및 작업 보고 완료 후 루프가 멈추며, **오너(Owner)의 수동 검토 및 결재**를 거쳐야 합니다. 자동 승인이나 자동 병합 처리는 없으며, 승인 완료 전에 Task 2를 먼저 시작해서는 안 됩니다.
