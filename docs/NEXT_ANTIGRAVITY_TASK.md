# Next Session Handoff Task Guide

이 문서는 Codex CLI 사용량 제한이 해제된 이후 작업을 수행할 개발자 혹은 AI 에이전트를 위한 검증 체크리스트 및 작업 이행 가이드라인입니다.

---

## 1. 개발 복구 시 핵심 원칙 (Rules for Recovery)

> [!WARNING]
> * **Codex CLI 복구 전 실제 구현 금지**: 사용량이 충전되어 CLI 실행이 활성화되기 전까지는 로컬에서의 코드 구현, DB seed 변경, 또는 worker/test_runner 구동을 일절 금지합니다.
> * **첫 실행 타겟 제약**: 재개 시 첫 실행은 오직 [FIRST_PORTFOLIO_GAME_RESUMPTION_PROMPT.md](FIRST_PORTFOLIO_GAME_RESUMPTION_PROMPT.md)에 지정된 **Task 1 Project Bootstrap**만 수행하여야 합니다.
> * **Task 1 수동 승인 대기**: Task 1은 자동 머지(Merge)나 Discord 자동 승인 결재를 거치지 않고, 브랜치 푸시 및 report 작성을 완료한 뒤 **수동 Owner review를 대기하는 상태에서 반드시 정지**해야 합니다. (Do not lease Task 2. Do not merge automatically. Stop after bootstrap branch/report is ready for manual Owner review.)
> * **순차 실행 엄수**: Task 1이 완전히 성공하여 main 브랜치에 정상 병합(Merge)되기 전까지는 Task 2 Basic Game Loop 등 후속 작업을 절대로 시작해서는 안 됩니다.
> * **Artifact Upload 제한**: 현재 서버 환경에서는 size-limited artifact upload(설정된 max_artifact_upload_bytes 범위 내 소형 아티팩트 업로드) 규격만 지원합니다. 대용량 파일에 대한 실질적인 streaming upload(large-file true streaming upload)는 현재 검증 경로에 포함되어 있지 않습니다.
> * **MCP의 드라이런 제약**: MCP 연동 시 실제 외부 MCP 프로세스를 구동하지 않고 오직 드라이런 뼈대(skeleton/dry-run) 모드만 사용해야 합니다.

---

## 2. 프로젝트 역할 정의 (Project Classification)

* **Neon Survival Prototype**은 단순히 결과물만 내는 2D 탑다운 서바이벌 미니게임(playable mini game) 프로젝트가 아닙니다.
* 이 프로젝트는 **AI Game Company Server의 v1/v1.5 모든 정책 가드레일과 검증 체계가 End-to-End로 올바르게 작동하는지 입증하기 위한 검증 하네스(E2E server validation harness)**입니다.
* 모든 에이전트 기여는 이 검증 하네스 스펙에 부합하여 각 작업의 성공 증적(Evidence)을 안전하게 업로드하고 검사받아야 합니다.

---

## 3. 다음 작업 시 반드시 확인/검토할 파일 목록 (Required Files to Check)

작업 착수 전 다음 설계/기획 및 템플릿 파일들의 정합성을 우선 검토하십시오.

1. **프로젝트 종합 계획서**: [FIRST_PORTFOLIO_GAME_PLAN.md](FIRST_PORTFOLIO_GAME_PLAN.md)
2. **시드 데이터 명세 초안**: [FIRST_PORTFOLIO_GAME_SEED_DRAFT.md](FIRST_PORTFOLIO_GAME_SEED_DRAFT.md)
3. **서버 기능 검증 매트릭스**: [SERVER_FEATURE_VALIDATION_MATRIX.md](SERVER_FEATURE_VALIDATION_MATRIX.md)
4. **최초 실행 프롬프트 및 가이드**: [FIRST_PORTFOLIO_GAME_RESUMPTION_PROMPT.md](FIRST_PORTFOLIO_GAME_RESUMPTION_PROMPT.md)
5. **서버 템플릿 태스크 팩**: [pygame_survival_v1.json](../templates/task_packs/pygame_survival_v1.json)

---

## 4. 검증 체크리스트 (Verification Checklist for Next Session)

실제 실행이 활성화되면 다음 순서대로 CLI 및 스크립트를 검증하십시오.

### 4.1. 전체 로컬 단위 테스트 수행
```bash
python -m pytest
```
* 전체 107개 테스트 스위트가 에러 없이 성공적으로 통과하는지 확인합니다.

### 4.2. MCP 권한 제어 유효성 검증
```bash
python -m pytest tests/test_mcp_permissions.py
```

### 4.3. 아티팩트 정리(Cleanup) 기능 검증
```bash
python -m pytest tests/test_artifact_cleanup.py
```

### 4.4. 골든패스 전체 e2e 리허설 수행
```powershell
# Windows PowerShell에서 실행
powershell -ExecutionPolicy Bypass -File .\scripts\rehearse_golden_path.ps1
```
