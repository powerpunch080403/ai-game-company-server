# AI 게임 개발 회사 v1 서버

Owner가 설계하고 Worker가 실행하는 게임 개발 조직을 위한 최소 서버입니다.

현재 v1 구현 범위:

- Project > Epic > Sub Epic > Task 계층
- Task 필수 필드: Goal, Requirements, Success Criteria, Estimated Time, Memory Refs, Branch
- SQLite 기반 Memory DB
- Worker 작업 임대 API
- Worker 결과 보고 저장
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

## Ubuntu 메인 서버 배포 초안

이 폴더를 메인 컴퓨터로 복사한 뒤:

```bash
chmod +x scripts/*.sh
./scripts/bootstrap_ubuntu.sh
./scripts/run_dev.sh
```

Tailscale IP에서 접근하려면 방화벽에서 8080 포트를 열거나 Tailscale 내부에서만 접근하세요.

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

- SSH로 게임 개발 머신에서 브랜치 생성/테스트 실행
- LLM 모델 설정 테이블
- Worker 세션 실행기
- 실패 2회 반복 시 검색 트리거
- task_history 메모리 자동 생성
- systemd 서비스 파일
