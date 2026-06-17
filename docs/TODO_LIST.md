# AI Game Company Server - 개발 진행 현황 및 TODO 리스트

이 문서는 AI Game Company Server v1 개발을 위해 Antigravity와 Codex(혹은 다른 AI 에이전트) 간 작업을 원활하게 주고받기 위한 **공동 작업 가이드 및 Task 관리 판**입니다. 

---

## 1. 현재 개발 상태 요약 (Current Status)

현재 v1 기능은 **약 85%** 구현 완료되었으며, 로컬 단위 테스트 84개가 모두 정상 통과(Pass)하는 안정적인 상태입니다.

**2026-06-17**: Golden Path 리허설 스크립트(`scripts/rehearse_golden_path.ps1`)가 전체 루프를 성공적으로 완주함.
- 버그 수정: `app/workspace_worker.py`의 `git_status_files()`에서 `run_git()`의 `stdout.strip()`이 porcelain 형식의 선행 공백을 제거하여 파일 경로가 깨지는 문제 해결.

- **서버 코어**: FastAPI와 SQLite 기반 데이터베이스 및 토큰 인증 기능.
- **계층 구조**: Project > Epic > Sub Epic > Task 구조 구현 완료.
- **워크플로우**: Workspace Worker의 브랜치 생성(`worker/*`), 커밋, 푸시, 실행 보고(Report) 완료.
- **테스트 러너**: `.game-company/test_runner.json` 설정에 따라 빌드/테스트/실행 단계를 돌고 결과를 서버에 보고하는 Test Runner 루프 구현 완료.
- **Registry & Heartbeat**: Worker 및 Machine Registry와 주기적인 Heartbeat 전송 기능 구현 완료.
- **Artifacts**: 파일 메타데이터 등록 및 바이너리 파일 업로드/다운로드 API 구현 완료.
- **Discord 연동**: Discord bot dry-run 라우터, context compaction(컨텍스트 요약/압축), Discord Gateway 뼈대 구현 완료.

---

## 2. 우선순위 작업 리스트 (TODO List)

### 🚀 [우선순위 1] 골든 패스 안정화 (Golden Path Stabilization)
가장 중요한 Task입니다. 추가 기능 개발보다 **AISurvivalMini(Pygame 데모 프로젝트)를 활용하여 실제 전체 루프가 매끄럽게 돌아가는지 리허설**해야 합니다.
- [x] **수동 골든 패스 리허설 수행** ✅ (2026-06-17 완료):
  - `scripts/rehearse_golden_path.ps1`로 전체 루프 자동화 완료.
  - scaffold → seed → server → worker lease/commit/push → test runner (build/test/smoke) → artifact upload → owner merge 성공.
- [x] **README.md 가이드 업데이트**: 실제 리허설에 사용된 정확한 셸 명령어를 README에 추가하여 다른 에이전트가 쉽게 똑같이 실행할 수 있도록 함. (2026-06-17 완료)
- [x] **Pygame 테스트 러너 프리셋 보완**: 실제 윈도우 창이 없는 headless 환경(CI/CD 등)에서도 스모크 테스트 및 렌더링이 문제없이 작동하도록 캡처 기능 안정화. (2026-06-17 완료)

### 🔐 [우선순위 2] 보안 및 대용량 파일 전송
- [ ] **대용량 파일 스트리밍 업로드 구현**: 현재 100MiB 업로드 제한이 설정되어 있으나, 리퀘스트 바디 전체를 메모리에 올리는 방식에서 스트리밍 방식으로 개선 필요.

### 🤖 [우선순위 3] Discord 봇 및 승인(Approval) 시스템 연동
- [ ] **실제 Discord 서버 연동 테스트**: 현재 구현된 Discord Gateway를 실제 테스트용 Discord 서버에 띄워서 정상 작동 확인.
- [ ] **자연어 기반 승인/의사결정 플로우 연결**: `#approval-inbox` 채널에서 AI가 요청한 위험/중요 작업에 대해 사용자가 자연어로 승인했을 때, 서버 API와 연동되어 Task가 승인 상태로 전송되는 흐름 완성.

---

## 3. 진행 가이드 (Handoff Instructions)

에이전트 전환 시 아래 가이드라인을 따릅니다.

1. **현재 작업 내용 파악**:
   - `docs/CONTEXT_HANDOFF.md` 및 이 파일(`docs/TODO_LIST.md`)을 먼저 확인하십시오.
   - 로컬 테스트 상태를 점검하려면 `python -m pytest`를 실행하십시오.
2. **게임 엔진에 대한 제약**:
   - 특정 게임 엔진(Unity, Unreal, Godot 등)이나 특정 웹 프레임워크에 종속되도록 서버 코어를 수정하지 마십시오. 서버는 모든 프로젝트 타입에 독립적(Engine-agnostic)이어야 합니다.
3. **머지 정책**:
   - `main` 브랜치는 워커가 직접 수정할 수 없으며 반드시 `worker/`로 시작하는 브랜치에서 작업 후 승인을 통해 머지되어야 합니다.
