# Server Feature Validation Matrix

이 문서는 **Neon Survival Prototype & E2E Verification Harness** 개발 주기에 따라 AI Game Company Server의 핵심/보안 기능들이 어떻게 검증되는지 정리한 상세 매트릭스입니다.

---

## 1. Project / Epic / SubEpic / Task Hierarchy
* **검증 대상**: 프로젝트, 에픽, 서브에픽, 태스크 간의 계층적 연동 및 DB 보존.
* **검증 태스크**: Task 1 (Project Bootstrap) 전 데이터베이스 시딩 단계.
* **증적 (Evidence)**: SQLite 데이터베이스 테이블 (`projects`, `epics`, `sub_epics`, `tasks`) 레코드 조회.
* **예상 결과**: 외래 키 제약 조건 및 맵핑이 올바르게 적재되며 계층 데이터가 100% 정상 조회됨.
* **실패 신호 (Failure Signal)**: `sqlite3.IntegrityError` 예외 발생 또는 빈 테이블 반환.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 2. Owner Task Planning Validator
* **검증 대상**: 작업 계획서의 크기, 역할, 브랜치 및 필수 증적(Evidence) 누락 여부 사전 필터링.
* **검증 태스크**: Task 1 시작 전.
* **증적 (Evidence)**: Planning Validator CLI 실행 로그 및 결과 JSON.
* **예상 결과**: 계획 검사기(`app/owner_task_validator.py`)가 오류(Error) 개수 0개로 검증을 통과시킴.
* **실패 신호 (Failure Signal)**: `ValidationError` 또는 오류 메시지 목록 반환.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 3. Workspace Worker Branch / Commit / Report Flow
* **검증 대상**: `worker/*` 격리 브랜치 내에서의 작업 통제, Git 커밋/푸시 및 완료 보고서 연동.
* **검증 태스크**: Tasks 1 - 8, 10
* **증적 (Evidence)**: Git 브랜치 메타데이터 및 `/tasks/{id}/report` 호출 페이로드.
* **예상 결과**: 임대받은 브랜치에서만 커밋을 작성하여 푸시하고, 완료 시점에 작업 시간 및 요약 보고서가 DB에 바인딩됨.
* **실패 신호 (Failure Signal)**: 잘못된 브랜치 푸시 차단 에러, Lease 만료 오류, 또는 보고서 제출 API 실패.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 4. Test Runner Setup / Test / Smoke Phases
* **검증 대상**: `.game-company/test_runner.json` 설정에 따라 가상환경 구성, 유닛 테스트 실행, 스모크 캡처 단계를 Headless dummy 상태로 구동.
* **검증 태스크**: Tasks 1 - 8, 10
* **증적 (Evidence)**: 테스트 러너 구동 결과 로그 및 `test-runner-report.json`.
* **예상 결과**: `setup` -> `test` -> `smoke` 페이즈가 순차 통과하며, 가상 드라이버 상태에서 예외 없이 실행을 마침.
* **실패 신호 (Failure Signal)**: 의존성 설치 에러, unittest 실패, 또는 dummy video driver 구동 크래시.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 5. Artifact Upload
* **검증 대상**: 아티팩트 파일의 크기 한도 초과 감지 및 안전한 저장 처리.
* **검증 태스크**: Tasks 8, 10
* **증적 (Evidence)**: 로컬 `artifacts/` 폴더 내의 실물 파일 및 DB `artifacts` 레코드.
* **예상 결과**: 한도 내 소형 아티팩트 업로드(small artifact upload under configured size limits)가 안전하게 처리됨 (size-limited artifact upload).
* **주의**: 대용량 파일에 대한 실질적인 대규모 스트리밍 업로드(large-file true streaming upload)는 현재 검증 경로에 포함되지 않음.
* **실패 신호 (Failure Signal)**: 설정된 한도 초과 시 `HTTP 413` 에러 발생 및 파일 부분 잔재 정리 여부.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 6. Artifact Important / Release Classification
* **검증 대상**: 릴리즈 아티팩트와 임시 아티팩트의 메타데이터 분리 태깅.
* **검증 태스크**: Task 10 (Approval / Release Candidate)
* **증적 (Evidence)**: SQLite DB 아티팩트 메타데이터 테이블의 `important`, `release_or_milestone` 컬럼 값.
* **예상 결과**: 업로드된 최종 빌드 파일 메타데이터에 `important = 1` 및 `release_or_milestone = 1`이 설정됨.
* **실패 신호 (Failure Signal)**: 플래그가 누락되어 `0`으로 기록되거나 아티팩트가 연동되지 않음.
* **수동 검증 여부**: 있음 (메타데이터 플래그 정합성 수동 검사)

---

## 7. Merge Review Policy Warning / Block Behavior
* **검증 대상**: 테스트 누락 브랜치 또는 테스트 실패 상태의 머지 요청 자동 차단.
* **검증 태스크**: Task 9 (Merge Policy Challenge)
* **증적 (Evidence)**: 합성(Synthetic) 정책 테스트 용 템플릿(fixture) 또는 누락 증적 제출 시의 API 응답 로그.
* **예상 결과**: `eval_merge_policy` 판단기가 unit test log가 누락된 요청에 대해 병합 요청을 강제로 반려 및 차단함.
* **주의**: 이 과정은 실제 실행 중인 게임 코드나 메인 브랜치를 임의로 파괴하지 않으며, 픽스처 파일 검증을 통해 안전하게 동작함.
* **실패 신호 (Failure Signal)**: 증적이 누락되었음에도 병합 승인이 완료됨.
* **수동 검증 여부**: 있음 (차단 기록 및 반려 로그 수동 확인)

---

## 8. Approval API
* **검증 대상**: 작업 병합을 위한 승인 결재 상태 전환.
* **검증 태스크**: Task 10 (Approval / Release Candidate)
* **증적 (Evidence)**: DB `approvals` 테이블 상태 필드값 및 `/approvals/{id}/decision` 호출 로그.
* **예상 결과**: 결재 상태가 `pending`에서 `approved`로 안전하게 업데이트되어 머지가 가능해짐.
* **실패 신호 (Failure Signal)**: 비정상 상태 전이 발생 또는 권한 없는 머지 성공.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 9. Discord Natural-Language Approval Safety
* **검증 대상**: 디스코드 채팅 메시지로부터 긍정/부정 결재 의도를 정확히 파싱하여 결재 시스템에 위임.
* **검증 태스크**: Task 10 (Approval / Release Candidate)
* **증적 (Evidence)**: Discord Gateway 수신 이벤트 로그 및 API 전달 로그.
* **예상 결과**: "승인합니다" 또는 "좋아 진행해" 등 한글 자연어 입력 시 승인(approved) 판정되어 API가 안전하게 실행됨 (dry-run 및 documented flow 기준).
* **실패 신호 (Failure Signal)**: 모호한 명령어 매칭, 기각 단어에 승인 처리, 또는 gateway 커넥션 단절.
* **수동 검증 여부**: 있음 (봇 수신 및 의도 해석 정합성 검증)

---

## 10. Memory Refs
* **검증 대상**: 에이전트 작업 실행 시 적합한 기획/코드 룰 레퍼런스를 콘텍스트로 매핑 및 전달.
* **검증 태스크**: Tasks 2 - 11
* **증적 (Evidence)**: Worker 임대(Lease) 요청 시 전달되는 JSON 컨텍스트 속 `memory_refs` 바인딩 로그.
* **예상 결과**: 설정된 규칙(`project_rules`, `coding_rules`)에 해당하는 DB 메모리가 작업 지시 텍스트에 맵핑됨.
* **실패 신호 (Failure Signal)**: memory key가 누락되거나 참조 텍스트가 바인딩되지 않음.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 11. Task History Summaries
* **검증 대상**: 이전 태스크들의 완료 요약 보고서들이 다음 태스크의 입력으로 지속 전달되는 흐름.
* **검증 태스크**: Tasks 2 - 11
* **증적 (Evidence)**: 생성되는 프롬프트 콘텍스트 원장 데이터.
* **예상 결과**: 이전 Task 완료 후 작성된 worker report의 summary 정보가 순차적으로 결합되어 다음 작업 임대 페이로드에 바인딩됨.
* **실패 신호 (Failure Signal)**: 요약 내용이 유실되어 빈 데이터로 다음 작업이 전달됨.
* **수동 검증 여부**: 없음 (자동 검증)

---

## 12. Artifact Cleanup Dry-Run
* **검증 대상**: 보관 만료일이 경과한 일반 임시 파일만 안전하게 걸러내어 정리 대상인지 판단.
* **검증 태스크**: Task 11 (Artifact Cleanup / MCP Permission Dry-run / Portfolio Devlog)
* **증적 (Evidence)**: `cleanup_artifacts.py` 구동 로그 콘솔 출력.
* **예상 결과**: 보존 기간이 초과된 로그 등은 후보군으로 잡히나, release 마크 아티팩트는 스킵되어 안전함이 증명됨 (dry-run 실행).
* **실패 신호 (Failure Signal)**: 아티팩트 삭제 한계치가 무시되거나 실제 삭제 작업이 드라이런 중에 발생함.
* **수동 검증 여부**: 있음 (출력된 삭제 후보 리스트 교차 검사)

---

## 13. MCP Permission Skeleton Dry-Run
* **검증 대상**: allowed_tools 및 allowed_roots 외부 파일시스템 및 git 경로 가드 작동 여부.
* **검증 태스크**: Task 11 (Artifact Cleanup / MCP Permission Dry-run / Portfolio Devlog)
* **증적 (Evidence)**: `validate_mcp_call` 테스트 출력 결과 로그.
* **예상 결과**: `.env`, `.git/config` 등 허가되지 않은 상위 디렉토리 및 민감 파일 참조 시 `is_allowed = False`가 정상 검출됨 (dry-run 실행).
* **실패 신호 (Failure Signal)**: workspace 밖의 절대 경로 및 시스템 중요 파일 접근 허용.
* **수동 검증 여부**: 있음 (드라이런 결과 리포트 수동 확인)

---

## 14. README / Portfolio Devlog Generation
* **검증 대상**: 11개의 E2E 검증 과정을 종합 기록한 최종 포트폴리오 문서의 정상 출력 확인.
* **검증 태스크**: Task 11 (Artifact Cleanup / MCP Permission Dry-run / Portfolio Devlog)
* **증적 (Evidence)**: `docs/DEVELOPMENT_LOG.md` 파일 생성 결과.
* **예상 결과**: AI가 수행한 11단계 빌드, 병합, 승인, 차단 등의 테스트 통계치가 포함된 마크다운 문서가 최종 저장소에 반영됨.
* **실패 신호 (Failure Signal)**: 문서가 미작성되거나 통계 지표가 공란으로 기록됨.
* **수동 검증 여부**: 있음 (포트폴리오 프리젠테이션 검토)
