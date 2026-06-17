# V1 Portfolio Game Readiness Checklist

이 문서는 AI Game Company Server v1을 사용해 **첫 번째 포트폴리오 게임 개발을 시작하기 전**, 시스템이 실전 투입 준비가 되었는지 검증하고 운영하는 방법을 기술한 체크리스트입니다.

---

## 1. Golden Path 통과 사실 요약

* **리허설 검증 완료 (2026-06-17)**
  - `game-pygame-mini` 템플릿 프로젝트(AI Survival Mini)를 활용하여 `scaffold → seed → server → workspace worker → test runner → artifact → owner merge`에 이르는 13단계 전체 e2e 파이프라인 루프를 성공적으로 완주했습니다.
  - `modify_code.py`를 활용해 워커가 코드를 수정하고, Git 브랜치 생성/커밋/푸시가 제대로 수행됨을 확인했습니다.
  - Test Runner가 Headless 환경에서도 SDL(Pygame) dummy 드라이버 주입을 통해 무사히 빌드/테스트 단계를 거쳐 `test-runner-report.json`을 남김을 검증했습니다.
* **Unity 데모 프로젝트 태스크 성공**
  - 로컬 bare 저장소(`unity-game.git`) 및 워크스페이스를 연동하여 첫 번째 워커 태스크(초기 프로젝트 스켈레톤 및 `.gitignore` 구성)를 정상적으로 임대, 커밋, 푸시 후 오너 승인 머지까지 성공시켰습니다.

---

## 2. 현재 V1에서 가능한 것 vs 수동으로 해야 하는 것

### 가능한 것 (Implemented & Automated)
* **서버 코어**: FastAPI 및 SQLite 기반의 토큰 인증(`Role-scoped tokens`) 및 Task 라이프사이클(lease, claim, report, event log) 관리.
* **Git 워크스페이스 자동화**: Workspace Worker가 자동으로 브랜치(`worker/*`)를 생성하고, 작업 후 커밋 및 origin 푸시를 처리.
* **테스트 및 검증**: `.game-company/test_runner.json` 기반의 4단계(setup, build, test, run) 검증 실행 및 리포트 파싱.
* **대용량 파일 스트리밍 업로드**: `request.stream()`을 통해 메모리 부하 없이 기가바이트급 아티팩트를 청크 단위로 안전하게 서버에 업로드.
* **디스코드 자연어 결재**: 사용자가 디스코드 `#approval-inbox` 채널에서 자연어("좋아 진행해", "거절해")로 타이핑하면, 봇이 의도를 파싱하여 서버 결재 API를 자동으로 호출 및 처리.

### 수동으로 해야 하는 것 (Manual Setup Required)
* **GitHub Private Repository 생성**: 깃허브 상에 실제 게임용 비공개 저장소를 생성하는 일은 수동으로 진행해야 합니다.
* **초기 데이터베이스 시딩**: 신규 프로젝트와 최초의 Epic, Sub-Epic, Bootstrap Task 구조를 SQLite DB에 입력하는 것(`sqlite3` 직접 수정 혹은 `seed` 스크립트 작성).
* **디스코드 채널 매핑 설정**: 디스코드 채널/스레드 ID와 서버 프로젝트 간의 맵핑 레코드를 `/discord/mappings` API를 통해 직접 등록해야 합니다.

---

## 3. 첫 포트폴리오 게임 Repo 생성 및 시작 절차

### [1단계] 저장소 및 로컬 환경 준비
1. GitHub에서 비공개 저장소(예: `portfolio-game`)를 생성합니다.
2. 메인 서버(혹은 로컬)의 작업 디렉토리에 저장소를 클론합니다.
3. 프로젝트 스캐폴딩 스크립트를 실행하여 공통 `.game-company/` 폴더와 뼈대를 이식합니다.
   ```bash
   python -m app.project_template /path/to/portfolio-game --name "My Portfolio Game" --type game-pygame-mini --force
   ```
4. `.gitignore`에 `.game-company/artifacts/**`, `.env`, `.venv/` 등의 필수 제외 패턴이 들어가 있는지 확인합니다.

### [2단계] 데이터베이스 등록 및 시딩
1. 서버 DB에 `projects` 테이블 레코드를 추가합니다 (`repo_url` 및 `workspace_path` 지정).
2. 프로젝트 산하의 최초의 Epic(예: "프로젝트 부트스트랩")과 Sub-Epic("초기 환경 설정")을 등록합니다.
3. 첫 번째 Task("초기 저장소 스켈레톤 구축")를 서브에픽 하위에 생성합니다.

### [3단계] 디스코드 맵핑 연동
1. 디스코드 서버에 프로젝트 전용 텍스트 채널(혹은 스레드)을 만듭니다.
2. 서버의 `/discord/mappings` API에 이 채널/스레드 ID를 등록하여 `project` 대화 채널로 연동합니다.
3. `#approval-inbox` 채널 맵핑 정보 역시 DB에 연동하여 승인 알림이 한곳으로 모이도록 구성합니다.

---

## 4. 실전 가이드라인 및 기준 (Standards)

### Worker Task 크기 기준 (Task Sizing)
* **15분 기본 원칙**: 워커가 처리하는 태스크는 15분 단위의 집중된 작업이어야 합니다 (예: 단일 파일 수정, 엔드포인트 1개 추가).
* **최대 30분**: 2개 이상의 밀접한 파일 수정이나 검증 루프 연동이 필요한 경우에만 제한적으로 허용합니다.
* **60분 초과 금지**: 60분을 초과하는 거대 작업은 반드시 기획/구현/테스트 단계로 세분화하여 Task를 쪼개야 합니다.

### Test Runner Evidence 기준
* **Docs Task**: 변경된 마크다운 파일들의 디스크 반영 여부.
* **Code Task**: 컴파일 로그, 유닛 테스트 통과 리포트(`test-runner-report.json`).
* **Game Runtime Task**: 스모크 테스트 실행 확인 로그 및 캡처된 스크린샷 아티팩트(`screenshots/`).

### Artifact 보관 기준
* **영구 보관 (`important_keep_forever`)**: 테스트 결과 리포트(`test-runner-report.json`), 실전 구동 스크린샷/비디오, 디자인 결정 마크다운.
* **30일 보관 (`standard_30_days`)**: 빌드 컴파일 로그(`build.log`), 테스트 전체 콘솔 출력 로그(`test.log`), 임시 캐시.

### Merge / Retry 판단 기준
* **자동 Merge 승인 조건**:
  - 태스크의 모든 `success_criteria`를 만족하고, `test_runner` 상태가 `success`인 경우.
  - Merge Policy 검증 결과 Warning만 존재하고 Block 사유가 없는 경우.
* **Retry(반려) 조건**:
  - `exit_code`가 0이 아니거나, 컴파일 실패 시.
  - 성공 기준에 적힌 에비던스(스크린샷, 로그 등)가 누락되었거나 비어 있는 경우.
  - 변경된 파일이 아예 없는 빈 커밋인 경우.

---

## 5. 보안 및 모듈 제한 (Security & MCP Limits)

* **Discord 사용 한도**:
  - V1에서는 봇을 통한 `/context` 확인, 결재함 수신 및 승인, 기본적인 Owner 지시 전달만 허용됩니다.
  - 전체 대화 히스토리의 자동 요약 및 롤링 컨텍스트 관리(`context compaction`)는 토큰 경고 수치(220k/260k)를 엄격히 준수합니다.
* **MCP 제약 사항**:
  - 대규모 외부 MCP 도구의 활성화는 금지합니다.
  - 오프라인 환경에 대비한 Read-only DB 및 Filesystem 범위 내의 MCP 도구로만 범위를 제한하고, 임의의 셸 명령 실행 권한을 MCP에 부여하지 않습니다.

---

## 6. 7월 초 포트폴리오 게임 시작 전 남은 작업 (Next Items)

1. **Owner Task Planning Validator**를 통해 생성되는 태스크들이 15/30분 크기 요건과 필수 에비던스 명시 요건을 잘 지키는지 자동 검사 체계 도입.
2. **Merge Review Policy**에 코딩/기획/배포 태스크 별 Block 기준을 적용하여, 휴먼 에러로 인한 오작동 머지를 방지.
3. 실제 디스코드 서버 환경에 Gateway 봇을 상주 프로세스(`systemd` 데몬 등)로 영구 구동되도록 배포 테스트.
