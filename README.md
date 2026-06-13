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

이 폴더를 메인 컴퓨터로 복사한 뒤:

```bash
chmod +x scripts/*.sh
./scripts/bootstrap_ubuntu.sh
./scripts/run_dev.sh
```

Tailscale IP에서 접근하려면 방화벽에서 8080 포트를 열거나 Tailscale 내부에서만 접근하세요.

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
