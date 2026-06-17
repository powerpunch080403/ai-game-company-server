# Long Term Project Memory Design

이 문서는 AI 개발 서버가 몇 달 전 변경 내용까지 찾아서 이해할 수 있도록
프로젝트 메모리와 변경 요약 로그를 어떻게 관리할지 정의한다.

목표는 게임뿐 아니라 앱, 웹, 도구, 서버 프로젝트에도 적용되는 장기 개발 기억
구조를 만드는 것이다.

## Goals

- AI가 프로젝트의 현재 상태와 과거 변경 이유를 이해한다.
- 몇 달 전에 수정한 내용도 검색할 수 있다.
- Discord 대화 원문 전체에 의존하지 않는다.
- task/report/git/artifact/decision을 연결한다.
- context window를 안전하게 사용한다.
- 나중에 vector search를 붙일 수 있게 구조화한다.

## Source of Truth

최종 기록은 서버 DB와 프로젝트 repo다.

Discord:

- 대화와 운영 UX.
- message/thread/channel id는 참조 id.

Server DB:

- project hierarchy.
- task queue.
- reports.
- task events.
- memory.
- decision records.
- artifact metadata.
- summary logs.

Git repo:

- 실제 파일 변경.
- commit hash.
- branch.
- diff.
- release tags.

AI가 과거를 이해할 때는 Discord 원문보다 서버 DB + git history + 요약 memory를
우선한다.

## Memory Layers

메모리는 아래 계층으로 관리한다.

```text
global memory
project memory
thread memory
task memory
change summary log
artifact memory
release/milestone memory
```

### Global Memory

모든 프로젝트에 적용되는 운영 규칙.

예:

- worker branch는 `worker/`로 시작한다.
- API key는 DB에 저장하지 않는다.
- 비용 증가 전 사용자 승인이 필요하다.

### Project Memory

한 프로젝트의 오래가는 지식.

예:

- 프로젝트 목적.
- architecture decisions.
- coding rules.
- repo layout.
- engine/framework.
- known constraints.
- active roadmap.

### Thread Memory

Discord project thread 안에서 나온 단기 논의 요약.

Thread memory는 계속 커지면 project memory로 승격하거나 change summary log로
압축한다.

### Task Memory

Task 수행에 필요한 좁은 맥락과 결과.

예:

- task goal.
- requirements.
- worker report.
- changed files.
- tests.
- issues.
- commit hash.

### Change Summary Log

프로젝트에서 수정된 내용을 시간순으로 축적하는 장기 로그다.

이 로그가 몇 달 뒤 검색의 핵심이다.

각 change summary는 아래를 포함한다:

```text
project_id
project_slug
date
actor_role
task_id
branch
commit_hash
files_changed
summary
reason
tests
issues
memory_refs
discord_thread_id optional
artifact_ids optional
tags
```

예:

```text
2026-06-15
Project: demo-game
Task: 42
Branch: worker/test-runner-contract
Commit: abc123
Files: .game-company/test_runner.json, docs/TESTING.md
Summary: Added test runner config and documented smoke test command.
Reason: Needed a repeatable validation contract before enabling test machine.
Tests: python --version smoke command documented.
Issues: Real Unity/Godot build command still pending engine selection.
Tags: test-runner, template, validation
```

## Required Summaries

AI가 프로젝트를 잘 이해하려면 아래 요약이 필요하다.

### Project Status Summary

항상 최신 상태로 갱신되는 짧은 요약.

포함:

- 현재 목표.
- 완료된 큰 기능.
- 진행 중인 epic/sub epic.
- 막힌 점.
- 다음 추천 작업.
- 최근 테스트 상태.

### Architecture Summary

큰 구조와 이유.

포함:

- 주요 모듈.
- 데이터 흐름.
- external services.
- framework/engine 선택 이유.
- 바꾸면 위험한 부분.

### Recent Changes Summary

최근 N일 또는 최근 N개 task의 변경 요약.

Owner가 진행 상황 질문에 답할 때 가장 먼저 본다.

### Decision Log

사용자나 Owner가 결정한 사항.

포함:

- 결정 내용.
- 날짜.
- 이유.
- 대안.
- 누가 승인했는지.
- 되돌릴 조건.

### Open Questions

아직 결정되지 않은 질문.

예:

- engine 선택.
- public access 방식.
- merge warning 정책.

## Retrieval Policy

Owner가 질문에 답하거나 task를 만들 때 memory를 이렇게 가져온다.

1. project_id를 찾는다.
2. tags로 후보를 먼저 좁힌다.
3. project status summary를 가져온다.
4. architecture summary를 가져온다.
5. open questions를 가져온다.
6. 최근 change summary log를 가져온다.
7. 질문 키워드와 관련된 오래된 change summary를 검색한다.
8. 관련 task/report/git commit/Discord thread를 필요할 때만 펼친다.

Worker prompt에는 전체 project memory를 넣지 않는다.

Worker에게는:

- task package.
- 관련 project rules.
- 관련 architecture snippet.
- 관련 최근 변경 요약.
- 필요한 파일/commit 참조.

만 제공한다.

## Tag-First Search

로그와 memory 검색은 tag로 먼저 거른다.

기본 흐름:

```text
1. 자연어 질문에서 project, type, actor, status, area, tool 등을 추론한다.
2. tag filter로 후보를 줄인다.
3. 제목과 요약을 검색한다.
4. 필요한 경우 본문을 읽는다.
5. 마지막에 원본 task/report/commit/Discord thread/artifact를 펼친다.
6. 답변에는 출처를 같이 보여준다.
```

추천 tag 체계:

```text
project:{slug}
type:{memory_type}
task:{id}
thread:{name_or_id}
actor:{role}
status:{success|failed|blocked}
area:{feature_area}
tool:{tool_name}
repo:{repo_name}
commit:{short_hash}
date:{YYYY-MM}
```

예:

```text
project:demo-game
type:change_log
task:42
actor:workspace-worker
status:success
area:combat
tool:unity
commit:abc123
date:2026-06
```

질문 예:

```text
demo-game에서 테스트 실패했던 거 찾아줘.
```

검색 추론:

```text
project:demo-game
type:test_report
status:failed
```

질문 예:

```text
Blender로 만든 보스 모델 preview 어디 있어?
```

검색 추론:

```text
project:demo-game
tool:blender
type:artifact
area:boss
```

대부분의 tag는 Owner나 Worker가 자동으로 붙인다. 사용자가 직접 tag를 관리하지
않아도 되게 한다.

## Discord Thread Summarization

프로젝트 thread는 계속 길어지므로 rolling summary가 필요하다.

권장 방식:

- 최근 메시지 N개는 raw로 보관.
- 오래된 메시지는 thread summary로 압축.
- 중요한 결정은 decision log로 승격.
- 구현 관련 내용은 task/change summary로 승격.
- 잡담은 프로젝트 memory에 넣지 않는다.

사용자-Owner 대화와 AI 내부 대화는 따로 요약한다.

```text
owner_conversation_summary
ai_internal_summary
thread_summary
task_coordination_summary
```

Owner conversation summary:

- 사용자의 의도.
- 결정된 방향.
- 보류된 질문.
- Owner가 답한 진행 상황.
- `owner-design` thread의 설계/아키텍처 요약.
- `owner-tasks` thread의 작업 분해/우선순위 요약.

AI internal summary:

- AI끼리 논의한 구현 경로.
- 충돌이나 대안.
- 선택한 접근.
- Worker에게 전달된 제약.
- 첨부된 파일, 이미지, 영상, 로그의 artifact 참조.

둘을 섞지 않는다. Owner가 사용자에게 답할 때는 AI internal summary를 짧게
참고할 수 있지만, Worker prompt에는 사용자 잡담을 넣지 않는다.

`owner-design`과 `owner-tasks`는 사용자와 Owner만 대화하는 thread다. API Worker나
Code Worker는 이 thread에서 직접 지시권을 갖지 않는다. API Worker가 만든 요약
또는 초안은 Owner가 검토한 뒤 task/change/decision memory로 승격한다.

초기 운영에서는 AI internal thread를 사람에게 투명하게 공개한다. 단, 투명하게
공개된 원문 전체를 매번 AI context에 넣지 않는다. 토큰 사용을 줄이기 위해
기본 retrieval은 요약 로그와 관련 artifact metadata를 사용한다.

토큰 원칙:

- Discord에 내부 대화를 표시하는 것 자체는 AI token을 거의 늘리지 않는다.
- 내부 대화를 다시 AI prompt에 넣을 때 token이 증가한다.
- 파일 첨부를 보여주는 것 자체는 token을 거의 쓰지 않는다.
- 이미지/영상/로그를 AI가 분석할 때 token 또는 별도 모델 비용이 든다.
- task별 summary log를 만들 때 token이 들지만, 장기적으로 전체 thread를 다시
  읽지 않아도 되어 비용을 줄인다.

요약 단위:

```text
thread:{discord_thread_id}:summary:current
thread:{discord_thread_id}:summary:YYYY-MM
```

## Thread Rotation

컨텍스트가 길어지면 thread를 삭제하거나 clear하지 않는다.

Rotation 절차:

1. 기존 thread의 current summary를 갱신한다.
2. 월별 또는 part별 summary를 저장한다.
3. decision/change/task/artifact 링크를 정리한다.
4. 기존 thread를 archive한다.
5. 새 continuation thread를 만든다.
6. 새 thread에 이전 요약과 서버 memory key를 고정 메시지로 남긴다.

Rotation trigger:

- 메시지 수가 기준을 넘음.
- 최근 요약이 너무 길어짐.
- 하나의 주제가 완료됨.
- milestone/release가 끝남.
- Owner가 context risk를 감지함.

추천 memory keys:

```text
project:{slug}:thread:{thread_id}:summary:current
project:{slug}:thread:{thread_id}:summary:archive:{date}
project:{slug}:thread:{old_thread_id}:continued_by:{new_thread_id}
```

## Change Log Creation Points

Change summary log는 아래 시점에 만들어야 한다.

- Worker report success/failed/blocked.
- Owner merge success.
- Test Runner report.
- User approval decision.
- Artifact upload.
- Release/milestone creation.
- Project config change.
- Important Discord project-thread decision.
- Thread rotation/archive.
- Visual artifact review.
- MCP tool operation that changes project files or assets.
- AI internal task discussion summary.

## Search Examples

사용자가 이렇게 물을 수 있어야 한다.

```text
몇 달 전에 테스트러너 왜 이렇게 설계했지?
demo-game에서 player input 마지막으로 수정한 게 언제야?
외부 접속을 공개로 하기로 한 이유가 뭐였어?
지난번에 실패한 빌드 로그 찾아줘.
Blender에서 만든 보스 모델 preview 어디 있어?
지난달 전투 시스템 AI 내부 논의 요약 보여줘.
```

Owner는 memory + change summary + task reports + git commit을 조합해서 답한다.

## v1 Storage Recommendation

현재 구현의 `memories` table을 우선 활용한다.

추천 memory key:

```text
project:{slug}:status:current
project:{slug}:architecture:current
project:{slug}:decisions:{date}:{topic}
project:{slug}:changes:{date}:{task_id}
project:{slug}:thread:{thread_id}:summary:current
project:{slug}:open_questions
```

추천 tags:

```text
project:{slug}
change_log
decision
architecture
status
thread_summary
task:{task_id}
commit:{short_hash}
```

Forward-compatible normalized tags:

```text
project:{slug}
type:{memory_type}
task:{id}
thread:{name_or_id}
actor:{role}
status:{status}
area:{feature_area}
tool:{tool_name}
repo:{repo_name}
commit:{short_hash}
date:{YYYY-MM}
```

v1.5에서 별도 table과 vector search를 추가한다.

## Retention Policy

기본 보관 정책:

```text
summary / decision / change log:
  keep forever

task report:
  keep forever

git commit / diff reference:
  keep forever as references
  source of truth remains git repo

Discord raw thread:
  keep in Discord
  store message/thread ids and summaries in server DB

small artifacts:
  store on server and post Discord preview

large artifacts:
  store in server artifact storage for 30 days by default
  post Discord preview/link

important artifacts:
  keep forever

release/milestone artifacts:
  keep forever
```

Large artifact examples:

```text
long gameplay videos
large build outputs
full profiler captures
large render sequences
large logs
```

Owner or user can mark an artifact as important. Important and
release/milestone artifacts are excluded from automatic cleanup.

Cleanup must delete only artifact files, not memory summaries, task reports,
decision logs, git commits, or metadata references.

## v1.5 Later

- Dedicated `project_change_logs` table.
- Dedicated `decisions` table.
- Artifact metadata table.
- Vector embedding search.
- Git diff summarizer.
- Monthly memory compaction job.
- UI for browsing project history.

## Rules

- Raw Discord 전체 로그를 장기 memory로 쓰지 않는다.
- 요약에는 "무엇을 바꿨는지"와 "왜 바꿨는지"를 반드시 남긴다.
- commit hash와 task id를 가능한 한 연결한다.
- 검색 가능한 tag를 붙인다.
- 검색은 tag-first로 후보를 줄이고, summary/body/source 순서로 펼친다.
- 사용자 결정은 decision log로 따로 남긴다.
- Thread는 삭제보다 archive/continue를 우선한다.
- AI 내부 대화와 사용자-Owner 대화 요약은 분리한다.
- 시각 artifact와 MCP 작업도 task/change summary에 연결한다.
- 내부 대화를 사람에게 모두 보여줘도, AI prompt에는 기본적으로 요약만 넣는다.
