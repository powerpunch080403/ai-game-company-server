# AI 게임 개발 회사 v1 서버

Owner가 설계하고 Worker가 실행하는 게임 개발 조직을 위한 최소 서버입니다.

현재 v1 구현 범위:

- Project > Epic > Sub Epic > Task 계층
- Task 필수 필드: Goal, Requirements, Success Criteria, Estimated Time, Memory Refs, Branch
- SQLite 기반 Memory DB
- Worker 작업 임대 API
- Worker 결과 보고 저장
- Worker 실행용 Task Package 생성
- Worker Runner CLI
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

## Ubuntu 메인 서버 배포 초안

현재 추천 배포 경로는 sudo 없이 운영 가능한 `/home/powerpunch/ai-game-company-server`입니다.

Windows 노트북에서 메인컴퓨터로 배포:

```powershell
.\scripts\deploy_main_server.ps1
```

배포 스크립트가 하는 일:

- GitHub repo clone 또는 pull
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

Ubuntu에 `sqlite3`가 없다면 설치하세요.

```bash
sudo apt update
sudo apt install -y sqlite3
```

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
