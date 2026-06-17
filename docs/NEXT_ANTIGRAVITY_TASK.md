# Next Session Handoff Task Guide

이 문서는 다음 개발자 혹은 AI 에이전트가 이어서 작업을 수행할 수 있도록 현재 구현 상태와 실제 테스트 가능 시점의 검증 체크리스트를 전달하는 가이드라인입니다.

---

## 1. 현재 구현 상태 요약 (Current Status)

v1.0의 골든패스 안착 이후, v1.5 준비 작업(MCP Permission Guard 설계, Artifact Cleanup 드라이런, 첫 포트폴리오 게임 Task Pack 추가)을 완료하였습니다. 실제 외부 연동이나 위험한 런타임 변경 없이 순수 설계 및 권한/드라이런 검증 레이어만 구축되었습니다.

### 완료된 것 (What is Done)
* **V1.5 로드맵 (`docs/V1_5_ROADMAP.md`)**: v1.5의 목표 범위(In-Scope / Out-of-Scope)와 V1과의 차이점 기술.
* **MCP 확장 설계 (`docs/MCP_EXTENSION_PLAN.md`)**: MCP Registry, Permission Guard, Audit Log, Dry-Run 모드 및 allowed_tools/roots 세부 명세 보강.
* **MCP 패키지 Skeleton (`app/mcp/`)**:
  - `schemas.py`: `MCPServerConfig`, `MCPCallResult` 모델.
  - `permissions.py`: `validate_mcp_call()`을 통한 툴 허용 목록, 역할 계층 구조, 경로 격리(Path Confinement), 수동 승인 유무 검사.
  - `registry.py`: `filesystem`, `git`, `sqlite` 기본 Config 매핑.
* **Artifact Cleanup 드라이런 (`scripts/cleanup_artifacts.py`)**:
  - `--apply`가 지정되지 않으면 실제로 파일을 삭제하지 않고 삭제 대상 후보 목록만 출력하는 안전한 드라이런 기본값 적용.
  - important / release / milestone 아티팩트는 삭제에서 제외. DB 메타데이터는 보존.
* **첫 게임 Task Pack (`templates/task_packs/pygame_survival_v1.json`)**:
  - project bootstrap부터 smoke test, readme update까지 9단계의 세부 task 명세화.

---

## 2. 실제 테스트 가능 시점의 검증 체크리스트 (Verification Checklist)

향후 로컬 실행 및 대규모 테스트가 가능한 시점이 되면 아래 검증 목록을 순서대로 수행하여 기능 작동 여부를 확인하십시오.

### 2.1. 전체 로컬 단위 테스트 수행
```bash
python -m pytest
```
* 전체 90여 개 이상의 테스트 스위트가 오류 없이 통과하는지 확인합니다.

### 2.2. MCP 권한 제어 유효성 검증
```bash
python -m pytest tests/test_mcp_permissions.py
```
* 다음 항목들을 검증합니다:
  - 허용된 role/tool은 정상 통과하는지.
  - 금지된 tool은 즉각 차단되는지.
  - role 권한이 부족할 때 차단되는지.
  - `allowed_roots` 영역 밖의 `target_path` 또는 `.env`, `.git/config` 접근 시 차단되는지.
  - `approval_required` 도구인 경우 approval 필요 상태(`approval_required=True`)로 반환되는지.
  - 실행 없이 planned action만 담은 dry-run 응답 구조가 반환되는지.

### 2.3. 아티팩트 정리(Cleanup) 기능 검증
```bash
python -m pytest tests/test_artifact_cleanup.py
```
* 다음 항목들을 검증합니다:
  - 기본 실행(dry-run) 시 파일이 보존되는지.
  - `--apply` 옵션 실행 시 만료된 파일만 삭제되는지.
  - important / release / milestone 파일이 삭제 후보에서 정상 제외되는지.
  - DB 메타데이터 테이블은 보존되는지.
  - raw 파일이 존재하지 않아도 예외가 발생하지 않는지.

### 2.4. 골든패스 전체 e2e 리허설 수행
```powershell
# Windows PowerShell에서 실행
powershell -ExecutionPolicy Bypass -File .\scripts\rehearse_golden_path.ps1
```
* v1.5 뼈대 코드가 추가된 상태에서도 핵심 골든패스(scaffold -> seed -> server -> workspace worker -> test runner -> artifact upload -> merge)가 온전히 유지되는지 검증합니다.

### 2.5. 첫 번째 포트폴리오 게임 Scaffold Smoke 검증
* `templates/task_packs/pygame_survival_v1.json`을 기반으로 태스크 팩을 임대하여 실제 게임 저장소 초기 Scaffold 생성 및 스모크 테스트가 정상 작동하는지 확인합니다.

