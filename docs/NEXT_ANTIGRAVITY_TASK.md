# Next Session Handoff Task Guide

이 문서는 다음 개발자 혹은 AI 에이전트(Codex 등)가 바로 이어서 작업을 수행할 수 있도록 현재 구현 상태와 다음 마일스톤을 인계하는 Durable Handoff 가이드라인입니다.

---

## 1. 현재 구현 상태 요약 (Current Status)

v1 핵심 서버 기능 및 실전 대비 기능 개발은 **약 90% 이상 완료**되었습니다. 로컬 단위 테스트 97개가 모두 성공적으로 통과(Passed)하는 안정적인 상태입니다.

### 완료된 것 (What is Done)
* **골든패스 완주 및 하드닝**: `scripts/rehearse_golden_path.ps1`을 사용해 scaffold → seed → server → workspace worker → test runner → artifact → owner merge까지 전체 e2e 루프가 완벽히 검증되었습니다. Headless 환경을 위해 SDL dummy 드라이버 주입 설정을 완료했습니다.
* **대용량 파일 스트리밍 업로드**: `request.stream()`을 사용하는 청크 단위 디스크 스트리밍 방식으로 업로드를 처리하여 메모리 부하를 방지했으며, 한도(1024B/100MiB) 초과 시 부분 파일 청소 로직을 보강했습니다.
* **자연어 결재/승인 핸들러**: 디스코드 채널 메시지의 긍정/부정 의도를 룰 기반 파서(`parse_approval_decision`)로 해석하여 `/approvals/{id}/decision` API를 자동 호출하고 결과를 한글로 응답합니다.
* **Owner Task Planning Validator**: 태스크 생성 전, goal/role/branch 유효성 검사, 15분/30분/60분 크기 검증, code/game 태스크의 필수 에비던스(logs, screenshots 등) 명시 여부, workspace 태스크의 프로젝트 매핑 여부를 사전 검증하는 `app/owner_task_validator.py`를 구현했습니다.
* **Merge Review Policy**: 태스크 역할(docs, code, game runtime, release)에 따른 자동 머지/블록 판단 도구인 `app/merge_policy.py`를 완성했습니다.

---

## 2. 보안 및 주의 사항 (Constraints & Risks)

### 아직 위험한 것 / 주의 깊게 봐야 할 사항 (Risks)
* **실제 디스코드 채널 맵핑 에러**: 디스코드 봇이 unmapped 채널/스레드에서 불필요하게 텍스트를 파싱하려 할 때, `unmapped_context`로 무시하도록 설계했으나 실제 라이브 서버에서 봇 권한(Message Content Intent 등) 설정 누락 시 동작하지 않을 수 있습니다.
* **자동 머지 거절(Block) 가능성**: Code/Game Task 머지 시 `eval_merge_policy` 모듈이 작동해 `changed_files` 누락이나 `runtime log` 미업로드 시 머지를 강제 블록합니다. 에이전트 작업 시 반드시 success_criteria에 부합하는 로그/스크린샷 아티팩트를 등록한 뒤 머지를 시도해야 합니다.

### 하지 말아야 할 일 (Out of Scope for V1)
* **Web UI 구현 금지** (FastAPI / Swagger 및 CLI/Discord Console 중심 유지).
* **Vector Memory 구현 금지** (SQLite와 JSON 파일 기반 compaction 유지).
* **MCP 대량 연결 금지** (필요시 standard read-only 및 filesystem mcp로 제한).
* **Unity/Godot 완전 자동화 금지** (현 단계에서는 templates 이식 수준으로 제한).
* **병렬 Worker 스케줄러 개발 금지** (단일 worker loop 동작으로 유지).

---

## 3. 다음에 시킬 일 (Next Action Items)

1. **실제 Discord 서버 라이브 테스트**: 
   - 현재 로컬에서 Gateway 봇이 구동 중이므로, 실제 디스코드 테스트 채널에 `/discord/mappings`로 맵핑을 생성하고, 자연어 결재("승인", "거절")가 DB에 정상적으로 반영되는지 확인.
2. **첫 포트폴리오 게임 시작**:
   - `docs/V1_PORTFOLIO_GAME_READINESS.md`에 기재된 체크리스트와 프로젝트 생성 절차를 그대로 따라서 첫 실전 게임 저장소 및 초기 태스크 큐 구성을 셋업.
3. **Task Planning Validator 활용**:
   - Owner가 태스크를 분해하여 생성할 때 `python -m app.owner_task_validator <task.json>`를 활용해 규격에 맞는지 검증하여 실전 투입.
