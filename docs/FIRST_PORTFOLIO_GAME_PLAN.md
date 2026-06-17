# First Portfolio Game Plan: Neon Survival Prototype & Verification Harness

이 문서는 AI Game Company Server의 첫 번째 실전 프로젝트이자 포트폴리오용 게임인 **Neon Survival Prototype**의 개발 계획서입니다. 
본 프로젝트는 단순한 게임 빌드에 그치지 않고, **AI Game Company Server의 Core v1 및 v1.5 기능 전부를 End-to-End로 실전 테스트하고 증명하기 위한 검증 하네스(Verification Harness)**로서 기능하도록 설계되었습니다.

---

## 1. 프로젝트의 이중 목적 (Dual Objectives)

1. **포트폴리오 게임 빌드**: 2D 네온 아트 스타일의 탑다운 생존 미니게임을 기획부터 릴리즈까지 완전 자율 에이전트 협업으로 완수합니다.
2. **서버 기능 종합 검증 Harness**: 에이전트가 각 단계를 실행하는 과정에서 AI Game Company Server의 모든 규격, 정책 가드, 통제 체계를 엄격하게 실행하고 검증합니다.

---

## 2. 서버 기능 검증 매트릭스 (Server Verification Matrix)

개발 과정 전반에 걸쳐 아래 서버 핵심 기능들이 자동으로 검증됩니다. 상세한 검증 시나리오, 예상 결과, 실패 판단 및 승인 증적 기준은 [SERVER_FEATURE_VALIDATION_MATRIX.md](SERVER_FEATURE_VALIDATION_MATRIX.md)를 참조하십시오.

| 검증 대상 서버 기능 | 실전 검증 시나리오 및 방법 | 관련 Task |
| --- | --- | --- |
| **Project / Epic / SubEpic / Task Hierarchy** | 시드 데이터 삽입 스크립트를 통해 프로젝트 구조가 SQLite DB에 정교하게 적재되고 계층 구조가 정상 보존되는지 검증. | 전체 Task (Task 1~11) |
| **Owner Task Planning Validator** | Task 등록 전 `owner_task_validator.py`를 작동시켜 goal, role, branch, estimated time 유효성 및 필수 evidence(로그, 스크린샷) 지정 여부를 자동 판정. | Task 1 시작 시 사전 검증 |
| **Workspace Worker Branch / Commit Flow** | Worker가 임대(Lease)받은 `worker/*` 브랜치 내에서만 작업하고, Commit 및 Push가 서버에 연동되는지 검증. | 전체 Task |
| **Test Runner Build/Test/Smoke Phases** | `.game-company/test_runner.json` 스펙에 맞춰 가상 환경 구성(setup), Pytest 유닛 테스트(test), Headless dummy 스크린샷 캡처(smoke) 단계를 순서대로 구동. | Task 1~8, 10 |
| **Artifact Upload & Classification** | `scripts/smoke_check.py` 결과물인 `screenshot.png`와 `test.log`를 스트리밍 업로드하고, `important=1` 및 `release_or_milestone=1`로 분류 지정 및 보존 테스트. | Task 8, 10 |
| **Merge Review Policy Warning/Block** | **일부러 테스트 로그가 누락되었거나 테스트가 실패하는 작업을 제출(Merge Policy Challenge)**하여, `eval_merge_policy`가 병합을 강제 차단하고 반려하는지 검증. | Task 9 (Merge Policy Challenge) |
| **Approval API & Discord NL Approval Safety** | RC 빌드 머지 요청 시 디스코드 채널에 결재 요청을 발송하고, 사용자가 입력한 자연어("좋아 진행해", "반려")를 게이트웨이 봇이 해석해 API를 통해 안전하게 머지/기각 처리하는지 검증. | Task 10 (Approval / RC) |
| **Memory Refs & Task History Summaries** | 각 Task가 시작될 때 이전 Task의 실행 요약 정보 및 `project_rules`, `coding_rules` 등의 기억 레퍼런스가 프롬프트 콘텍스트에 정확히 압축 반영되는지 검증. | 전체 Task |
| **Artifact Cleanup Dry-Run** | 보존 주기가 지난 태스크 폴더 및 로그 파일을 대상으로 `cleanup_artifacts.py` 드라이런을 구동하여 삭제 후보가 정확히 출력되는지 검증. | Task 11 (Cleanup/MCP Dry-run) |
| **MCP Permission Skeleton Dry-Run** | `validate_mcp_call()`을 호출하여 파일 접근 및 git 명령어 수행 시 workspace 경로 격리(Path Confinement)와 롤 권한 가드가 정상 동작하는지 모의 검증. | Task 11 (Cleanup/MCP Dry-run) |

---

## 3. 게임 개요 (Game Overview)

* **게임명**: Neon Survival Prototype
* **장르**: 2D 탑다운 서바이벌 미니 게임
* **컨셉**: 어두운 네온 스타일 공간에서 무한히 몰려드는 붉은 적들을 피하며 60초 동안 생존하는 액션 아케이드 데모.
* **조작법**: 
  - `W`, `A`, `S`, `D`: 플레이어 캐릭터 이동
  - `Space`: 게임 오버 시 모든 상태 리셋 후 재시작
* **목표**: 60초 생존 성공. 적과의 충돌을 피하며 생존한 시간과 충돌 횟수를 바탕으로 최종 스코어를 산출.

---

## 4. MVP 범위 (Minimum Viable Product Scope)

### 포함 사항 (In-Scope)
* **기본 프레임워크**: Python 3.12 및 Pygame 라이브러리.
* **플레이어 제어**: 화면 경계 밖으로 나갈 수 없는 WASD 기반 이동 메커니즘.
* **적 생성**: 주기적으로 화면 바깥(Off-screen) 랜덤 위치에서 스폰되어 플레이어 방향으로 가속 추적하는 적 무리.
* **충돌 및 체력**: 플레이어와 적의 충돌 감지(AABB Bounding Box Rects), 충돌 시 체력(Health) 감소, 체력이 0 이하가 될 시 즉각 게임 오버 상태로 전환.
* **게임 상태 제어**: PLAYING 상태와 GAME_OVER 상태 구분 및 스페이스바 입력 시 모든 점수/상태 리셋 후 재시작.
* **네온 UI 오버레이**: 폰트를 활용한 실시간 생존 시간(초) 및 스코어 렌더링.
* **자동 스모크 테스트**: 실제 게임 렌더링 창을 띄우지 않아도 되는 Headless dummy video driver 기반 100프레임 실행 후 스크린샷 캡처 및 자동 종료 스크립트.

### 하지 않을 것 (Out-of-Scope)
* **무기 발사 및 전투 기능**: 적을 총으로 쏘거나 파괴하는 기능 제외.
* **아이템 및 파워업 시스템**: 속도 증가, 무적 등 아이템 수집 기능 배제.
* **사운드 효과 및 배경음악**: 오디오 디바이스 의존성을 줄이고 Headless 테스트 용이성을 위해 제외.
* **화려한 스프라이트 리소스 사용**: 별도의 이미지 로딩 실패 리스크를 없애기 위해 Pygame 도형 그리기(Draw) 명령어로 도형 렌더링 처리.
* **다양한 적 패턴**: 직선 유도 방식 이외의 복잡한 AI 패턴 제외.

---

## 5. 저장소 구조 (Repository Structure)

```text
neon-survival-prototype/
│
├── src/                          # 게임 로직 소스 코드
│   ├── game/
│   │   ├── __init__.py
│   │   ├── main.py               # 메인 게임 루프 및 초기화
│   │   ├── player.py             # 플레이어 클래스 (이동, 경계 처리)
│   │   ├── enemy.py              # 적 클래스
│   │   ├── collision.py          # 충돌 감지 유틸리티
│   │   ├── ui.py                 # 텍스트, 상태 오버레이 렌더러
│   │   └── settings.py           # 화면 해상도, 속도, 스폰 시간 등 설정값
│   └── __init__.py
│
├── tests/                        # 자동화 단위 테스트
│   ├── test_player.py            # 플레이어 이동/경계 유닛 테스트
│   └── test_collision.py         # 충돌 판정 유닛 테스트
│
├── scripts/                      # 자동화 스모크 테스트 스크립트
│   └── smoke_check.py            # Headless 100프레임 기동 후 스크린샷 저장
│
├── assets/                       # 기획 리소스 및 폰트 파일
│   └── README.md
│
├── docs/                         # 기획/설계 및 에이전트 개발 기록
│   └── DEVELOPMENT_LOG.md
│
├── .game-company/                # AI Game Company Server 검증 설정
│   ├── project.json              # 프로젝트 설정 메타
│   └── test_runner.json          # Test Runner 빌드/테스트 스키마
│
├── README.md                     # 포트폴리오 겸 설치 설명서
└── requirements.txt              # 의존성 정의 파일 (pygame)
```

---

## 6. 개발 및 검증 순서 (Development & Verification Sequence)

실제 데이터베이스에 적재될 Seed의 11단계 개발 및 검증 흐름입니다:

1. **Project Bootstrap**: 워크스페이스 구조 생성, .gitignore 및 `.game-company/` 파일 구성.
2. **Basic Game Loop**: `main.py` 중심의 기본 pygame 초기화 및 빈 화면 렌더링 루프 가동.
3. **Player Movement**: `player.py` 구현, 키보드 입력 핸들러 및 화면 이탈 방지 경계 검사 구현.
4. **Enemy Spawn**: `enemy.py` 및 스폰 주기 관리, 플레이어로의 가속 추격 로직 구현.
5. **Collision & Health**: 충돌 이벤트 연계, 플레이어 체력 하락 및 체력 0 도달 시 사망 판정.
6. **Score & Time UI**: 생존 시간, 스코어 계산 및 Pygame Font 렌더링 시스템 구현.
7. **Game Over & Restart**: PLAYING / GAME_OVER 상태 제어 및 space 키를 통한 리셋 제어.
8. **Smoke Test Artifact**: `scripts/smoke_check.py` 구현, 스크린샷 아티팩트 자동 저장 기능 구축.
9. **Merge Policy Challenge**: 일부러 테스트 로그를 누락시키거나 실패하도록 브랜치를 병합 요청하여, Merge Review Policy 가드에 의해 자동으로 머지가 차단 및 거절되는지 고의 검증.
10. **Approval / Release Candidate (RC)**: 최종 Release Candidate 빌드를 구성하여 디스코드로 결재 알림을 전송하고, 긍정 자연어 답변을 통해 API로 최종 머지 및 `release_or_milestone=1` 지정 아티팩트 업로드를 완료하는 통합 테스트.
11. **Artifact Cleanup / MCP Permission Dry-run**: 서버 백그라운드 아티팩트 정리 도구의 안전성(`cleanup_artifacts.py`)을 검사하고, MCP Permission Guard(`validate_mcp_call`)를 구동해 에이전트의 경로 격리 및 권한 가드 동작을 최종 드라이런으로 교차 검증.
