# V1.5 Roadmap

이 문서는 AI Game Company Server v1.5의 범위와 목표, 그리고 실전 투입 준비 단계인 v1.0 이후의 확장 마일스톤을 기술합니다.

> [!NOTE]
> AI Project Control Server의 전체적인 제품 정의, 장기 비전 및 다년도 개발 단계(Phases)는 [PRODUCT_VISION.md](PRODUCT_VISION.md)를 참조하십시오. 이 로드맵 문서는 그 비전 아래에서 구체적인 v1.5 마일스톤과 범위(In-Scope/Out-of-Scope)에 집중합니다.

> [!IMPORTANT]
> **V1.5 Transition Gate**: 이 v1.5 로드맵은 v1.0 오너 스모크 테스트(Owner Smoke Test) 승인 통과 후에 공식적으로 개시되는 다음 단계의 계획입니다. 일부 v1.5 스타일의 테스트 뼈대나 기초 스키마가 현재 코드베이스에 이미 구성되어 있을 수 있으나, 공식적인 v1.5 확장 단계는 v1 승인 결과가 PASS로 기록된 이후에 본격적으로 시작됩니다.

---

## 1. V1.5 목표 (Objectives)
v1.0의 골든패스 안착 이후, AI 에이전트들의 독립성과 외부 도구(MCP) 연결성 및 서버 관리 안정성을 강화하여 **다중 에이전트(Multi-agent) 협업 파이프라인의 실전 투입 준비**를 완성하는 것을 목표로 합니다.

---

## 2. 범위 정의 (In-Scope vs Out-of-Scope)

### v1.5에서 할 것 (In-Scope)
* **Model Context Protocol (MCP) 준비 설계 및 뼈대 구축**
  - AI 에이전트가 로컬 파일, Git, DB 리소스에 안전하게 접근할 수 있도록 하는 권한 규칙/레지스트리 가드 구현.
  - 실제 네트워크 연동 전, 드라이런(dry-run) 모드를 제공하여 사전에 에이전트의 오작동 시나리오를 모의 평가.
* **아티팩트 정리(Cleanup) 자동화 도구**
  - 디렉토리 용량 확보를 위해 보관 주기가 지난 임시 파일( logs 등)을 정기적으로 수동/자동 정리할 수 있는 안전한 dry-run 중심 스크립트 구축.
* **실전 포트폴리오 게임 태스크 팩(Task Pack) 규격화**
  - 첫 게임 개발 투입 및 E2E 기능 검증에 필요한 11단계 태스크의 세부 스키마와 요구사항을 JSON 템플릿으로 제공하여 Owner가 일관된 품질의 태스크를 생성하도록 가이드.

### v1.5에서 하지 않을 것 (Out-of-Scope)
* **외부 MCP 서버 실제 네트워크/프로세스 직접 호출 구현** (본 단계에서는 보안과 오프라인 검증을 위해 registry와 guard 검증까지만 진행).
* **Workspace Worker의 병렬 스케줄링 및 분산 락 구현** (단일 worker 실행 모델 유지).
* **Web UI 어드민 대시보드 개발** (Discord 및 API/CLI 통제 유지).
* **Vector Memory / Semantic Search 검색 엔진 탑재** (SQLite 기본 search 유지).
* **Unity/Godot 엔진 완전 자동화 파이프라인 구축** (Pygame 기반 데모 및 이식 수준으로 제한).

---

## 3. V1과 V1.5의 차이점

| 구분 | V1.0 (Core Engine) | V1.5 (Production Ready) |
| --- | --- | --- |
| **에이전트 통제** | Owner 및 Worker API에 의한 순차 실행 | MCP Server/Registry를 통한 도구 실행 권한 세분화 |
| **운영 관리** | 수동 아티팩트 보관 및 DB 로깅 | 백그라운드 아티팩트 정리 드라이런 및 자동 Purge 뼈대 |
| **태스크 생성** | Owner 모델 프롬프트 가이드 의존 | 구조화된 Task Pack JSON 템플릿 바인딩 |
| **안전성** | API 키 노출 방지 및 명령 데니어스트 | 룰 기반 자연어 결재 검증 및 validator 사전 검사 |

---

## 4. 첫 포트폴리오 게임 개발과 V1.5의 관계
* 첫 포트폴리오 게임(Survival Game 등)은 V1.0의 안정화된 코어(FastAPI + Git Workspace + Test Runner)를 사용하여 우선 개발을 개시합니다.
* V1.5의 MCP 설계 및 Validator, Task Pack은 포트폴리오 개발이 시작되는 동안 **AI 에이전트들의 오작동률을 낮추고(Task Validator), 휴먼 에러에 의한 부정 머지를 방지(Merge Review Policy)하며, 축적되는 아티팩트 용량을 제어(Artifact Cleanup)하는 실전 가드레일** 역할을 합니다.

---

## 5. MCP Registry & Dry-Run 설계 원칙
* **안전 우선(Registry & Permission First)**: 외부 LLM이 직접 셸이나 파일 시스템을 조작하도록 외부에 직접 연결하기 전에, 권한 매트릭스(`readonly`, `worker`, `owner`, `admin` 역할 별 허용 목록)와 허용 디렉토리 경로(`allowed_roots`)를 검사하는 Permission Guard를 먼저 구현합니다.
* **드라이런 모드(Dry-run) 기본 탑재**: 실제 파일 시스템 수정이나 Git 조작을 수행하지 않고, 권한 통과 여부 및 수행 예정 액션(Planned Action JSON)만을 반환하는 구조를 제공하여 시뮬레이션을 가능케 합니다.
* **Allowed Roots Preset 주의**: `app/mcp/registry.py`에 기본 정의된 `allowed_roots`는 어디까지나 demo/skeleton 용도의 프리셋입니다. 실제 게임 개발 및 운영 돌입 시에는 환경 설정이나 환경 변수를 통해 실제 게임 워크스페이스 루트 경로를 서버에 공급해주어야 합니다. 또한 첫 게임인 Neon Survival Prototype의 Task 11에서는 실제 삭제/호출 없이 오직 드라이런(dry-run) 모드로만 안전하게 검증을 실행해야 하며, 최초 bootstrap 단계에서는 어떠한 외부 MCP 서버의 직접 호출도 발생하지 않습니다.

---

## 6. 테스트 가능 시점의 검증 체크리스트
향후 AI CLI 사용량 해제 및 원격 서버 복구 등 테스트가 가능한 환경이 갖추어지면 다음 시나리오를 점검해야 합니다:
1. `python -m pytest tests/test_mcp_permissions.py`를 실행하여 MCP 툴 권한 검사 오류 검출 확인.
2. `python -m pytest tests/test_artifact_cleanup.py`를 실행하여 30일 초과 아티팩트 지우기 기능 검증.
3. `python scripts/cleanup_artifacts.py --apply`를 호출하여 실제 만료된 파일만 디스크에서 삭제되고 DB 메타데이터는 안전하게 보존되는지 확인.
4. `.\scripts\rehearse_golden_path.ps1`을 가동하여 v1.5 뼈대 추가 상태에서도 e2e 루프가 온전히 동작하는지 최종 확인.

---

## 7. 태스크 소유권 및 멀티모달 워커 모델 (Task Ownership and Multimodal Workers)
* **상태 (Status)**: V1.5+ 기획 및 설계 단계 (V1.5+ planning only, 구현 제외)
* **태스크 대여 단일성 규칙(Task Lease Invariant)**: 하나의 태스크는 한 번에 최대 하나의 활성 워커 대여(active lease)만 가질 수 있습니다. 여러 워커가 동시에 한 태스크에 대해 수정 및 보고를 수행하는 경우 브랜치 관리, `base_commit` 추적, `changed_files` 검증, `task_locks`, 완료 상태 및 병합 후보(merge candidate) 생성 과정에 모호성이 발생하므로 이 단일성 규칙은 핵심 불변값으로 유지됩니다.
* **멀티모달 작업 분할 모델**: 만약 특정 기능 개발에 여러 모달리티(코드 작성, 컨셉 이미지 생성, 효과음 녹음 등)가 동시에 요구되는 경우, 하나의 태스크에 여러 워커를 배정하는 대신 다음 예시처럼 개별 태스크들로 작업을 쪼개어 생성합니다:
  - **Task A: 에너미 캐릭터 컨셉 이미지 생성** $\rightarrow$ `image_worker`
  - **Task B: 에너미 효과음 리소스 생성** $\rightarrow$ `voice_worker`
  - **Task C: 에너미 기본 AI 동작 구현** $\rightarrow$ `code_worker`
  - **Task D: 에너미 리소스 통합 및 최종 검증** $\rightarrow$ `code_worker` 혹은 `integration_worker`
  - 각 태스크는 자체적인 Discord 스레드와 레퍼런스를 개별적으로 가지며, 이 연관된 태스크 군은 기존의 Epic/SubEpic 계층이나 향후 도입 예정인 `task_group` 혹은 `work_package` 단위로 묶여 오너(Owner)에 의해 통제 및 검증됩니다.
* **V1.5+ 후보 필드 및 개념**:
  - `task_kind` (태스크 유형)
  - `required_worker_role` (필수 워커 역할)
  - `required_capabilities` (요구 기술 역량)
  - `task_group_id` / `work_package_id` (작업 그룹/패키지 식별자)
  - `task dependency ordering` (태스크 의존성 정렬 및 스케줄러)

