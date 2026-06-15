# Discord Operator Console Design

이 문서는 AI Game Company Server v1에서 Discord를 운영 콘솔로 사용하는 설계를
정리한다. 이름은 game company지만, 장기적으로는 게임뿐 아니라 앱, 웹, 도구,
서버 개발도 관리할 수 있는 AI 개발 서버를 목표로 한다.

v1에서는 별도 웹 관리 프로그램을 바로 만들지 않고, Discord를 사람이 보기
좋은 알림/승인/대화 화면으로 사용한다. 서버 DB가 최종 기록과 상태의 source
of truth이고, Discord는 운영 창구다.

## Current Decisions

- Discord 새 서버를 만든다.
- Discord 역할은 `B: 알림 + 승인/명령`이다.
- 나중에 별도 관리 프로그램을 만들 수 있다.
- AI는 역할별 계정처럼 보이게 한다.
- 구현은 Bot 1개 + 역할별 Webhook 여러 개를 우선 추천한다.
- 채널 구조는 운영 채널 + 프로젝트 채널 혼합 방식이다.
- 초기에는 신뢰 확보를 위해 AI 내부 대화를 사람에게 투명하게 공개한다.
- AI context에는 기본적으로 내부 대화 전체가 아니라 요약만 사용한다.
- 사용자는 대부분 Owner와 대화한다.
- Worker와는 필요할 때만 직접 대화한다.
- Owner와 사용자 대화 채널, AI끼리 대화하는 채널은 분리한다.
- 프로젝트별 Owner 대화는 `owner-design`과 `owner-tasks`로 나눈다.
- `owner-design`과 `owner-tasks`에서는 사용자와 Owner만 대화한다.
- Task 생성과 작업 분해의 책임자는 Owner다.
- 프로젝트 대화는 프로젝트 thread 안에서만 한다.
- 일상 대화와 프로젝트 대화는 섞지 않는다.
- 사용자가 AI에게 말하면 필요한 project channel/thread를 만들 수 있어야 한다.
- 대부분의 관리는 slash command보다 자연어 대화로 가능해야 한다.
- 프로젝트 타입은 Owner가 대화 내용을 보고 자동 추정하고, 애매할 때만 질문한다.
- 새 프로젝트는 Discord channel/thread와 서버 Project record를 자동 생성한다.
- GitHub private repo/template/workspace 생성은 `#approval-inbox` 승인 후 자동 실행한다.
- 진짜 프로젝트는 GitHub private repo를 기본으로 쓰고, 임시/테스트 프로젝트는
  main server local bare repo를 쓸 수 있다.
- Template은 타입별 template과 공통 `.ai-company/` 폴더를 함께 사용한다.

## Discord Is Not the Database

Discord에 표시되는 메시지, 이미지, 영상, 버튼, thread는 운영 UX다.

최종 상태는 반드시 서버 DB에 저장한다:

- project
- epic
- sub epic
- task
- task event
- worker report
- owner run
- memory
- approval decision
- artifact metadata

Discord message id, channel id, thread id는 서버 DB 레코드를 찾기 위한 외부
참조로만 사용한다.

## Channel Structure

초기 채널 구조:

```text
#owner-room
#ai-dev-chat
#approval-inbox
#task-feed
#worker-reports
#test-runner
#artifacts
#project-demo-game
#project-next-game
```

채널 역할:

- `#owner-room`: 일상 대화, Owner와의 일반 질문, 프로젝트와 무관한 운영 대화.
- `#ai-dev-chat`: AI끼리 논의하는 전역 피드. 프로젝트별 AI 내부 대화 thread로
  연결하고, 중요한 이벤트를 요약해서 보여준다.
- `#approval-inbox`: 결재함. 위험하거나 중요한 작업을 실행하기 전에 Owner가
  결재 요청을 올리고, 사용자가 자연어 또는 버튼으로 승인/보류/수정한다.
- `#task-feed`: task 생성, lease, 시작, 완료, 실패 요약.
- `#worker-reports`: worker report 상세 요약.
- `#test-runner`: 12400/3060 테스트 머신의 build/test/run 결과.
- `#artifacts`: 이미지, 영상, gif, 로그, 빌드 산출물 링크/프리뷰.
- `#project-*`: 프로젝트별 thread를 담는 채널. 프로젝트는 game/app/web/tool/server
  등 여러 타입일 수 있다.

## Conversation Channels

사용자와 Owner 대화, AI끼리 대화는 분리한다.

```text
#owner-room
  user <-> Owner
  casual conversation
  global status questions
  project status summaries

#ai-dev-chat
  global AI internal feed
  links to project AI internal threads
  cross-project coordination summaries
  important internal events
```

규칙:

- 사용자는 대부분 `#owner-room`에서 Owner와 대화한다.
- AI끼리의 자세한 논의는 프로젝트별 AI internal thread에 둔다.
- `#ai-dev-chat`에는 프로젝트별 AI internal thread 링크와 전역 요약을 올린다.
- 초기 신뢰 확보 기간에는 프로젝트별 AI internal thread에 내부 대화와 첨부를
  가능한 한 투명하게 남긴다.
- 프로젝트별 상세 대화는 project thread에 둔다.
- AI internal thread에서 나온 결정은 project thread 또는 decision log로 승격한다.

프로젝트마다 Owner-facing thread와 AI-internal thread를 분리한다:

```text
owner-design: user <-> Owner project design conversation
owner-tasks: user <-> Owner task planning and assignment conversation
ai-internal: Owner <-> Workers project coordination
```

둘은 같은 project memory를 공유하지만, prompt에는 필요한 요약만 가져온다.

프로젝트별 권장 thread 구조:

```text
#project-demo-game
  thread: owner-design
  thread: owner-tasks
  thread: ai-internal
  thread: ai-internal-task-42
  thread: artifacts
  thread: test-runner
```

Thread responsibilities:

- `owner-design`: 사용자와 Owner가 설계, 기획, 아키텍처, 방향을 이야기한다.
- `owner-tasks`: Owner가 설계 내용을 보고 작업을 쪼개고, 우선순위와 worker 배정을
  정리한다. 사용자와 Owner만 대화한다.
- `ai-internal`: Owner와 Workers가 작업 실행에 필요한 내부 조율을 한다.
- `ai-internal-task-*`: 특정 task에 대한 AI 내부 상세 논의와 첨부를 남긴다.
- `artifacts`: 이미지, 영상, 로그, 빌드 산출물을 모은다.
- `test-runner`: 테스트 머신의 실행 결과를 모은다.

Role boundary:

- Owner만 project design을 task로 분해하고 task queue에 넣는다.
- API Worker는 task를 만들거나 Code Worker에게 직접 지시하지 않는다.
- API Worker는 Owner가 요청한 요약, 로그 분석, 초안 정리, 자료 조사 같은 보조
  작업만 수행한다.
- Workspace/Code Worker는 task queue에서 lease한 작업만 실행한다.
- Test Runner는 실행/검증/화면 캡처를 담당한다.

AI internal transparency mode:

- 사람에게는 내부 대화와 첨부를 볼 수 있게 한다.
- task별 상세 thread를 만든다.
- 작업마다 searchable summary log를 남긴다.
- Discord에 보여준 내부 대화를 다음 AI prompt에 자동으로 전부 넣지는 않는다.
- AI context는 기본적으로 요약, 관련 memory, 최근 핵심 메시지만 사용한다.
- 사용자가 "상세 로그까지 보고 판단해"라고 요청할 때만 필요한 범위의 raw
  thread를 읽힌다.

## Project Types

서버는 장기적으로 게임 전용이 아니라 일반 개발 서버가 된다.

프로젝트 타입 예:

```text
game
web
app
backend
tool
automation
research
plugin
```

Discord 채널 이름은 project slug 중심으로 둔다:

```text
#project-demo-game
#project-dashboard-web
#project-mobile-app
#project-build-tool
```

프로젝트 타입은 서버 DB의 project metadata 또는 project memory에 저장한다.

## Project Threads

프로젝트와 관련된 대화는 프로젝트 thread 안에서만 한다.

권장 구조:

```text
#project-demo-game
  thread: owner-design
  thread: owner-tasks
  thread: ai-internal
  thread: test-runner
  thread: artifacts
```

규칙:

- 프로젝트 요구사항, 기획, 일정, 구현 판단은 프로젝트 thread에 남긴다.
- `#owner-room`에서 프로젝트 이야기가 시작되면 Owner는 적절한 프로젝트 thread로
  이동하자고 안내한다.
- 설계 이야기는 `owner-design`으로 이동한다.
- 작업 분해와 worker 배정 이야기는 `owner-tasks`로 이동한다.
- Worker와 AI 내부 조율은 `ai-internal`으로 이동한다.
- 프로젝트 thread는 `project_id`와 연결한다.
- thread 안의 중요한 결정은 서버 memory 또는 task event로 저장한다.
- thread 안의 파일/이미지/영상은 artifact metadata로 저장한다.

## Natural Language Channel and Thread Creation

사용자는 대부분 대화로 운영할 수 있어야 한다.

예:

```text
Owner, 새 웹 대시보드 프로젝트 하나 만들어줘.
테스트러너 연결용 스레드 만들어줘.
demo-game에 아트 방향 스레드 하나 추가해줘.
이 대화는 dashboard-web 프로젝트 planning 스레드로 옮겨줘.
```

Owner 동작:

1. 요청이 프로젝트/채널/thread 생성인지 판단한다.
2. 위험하지 않은 생성 작업이면 계획을 짧게 확인하고 실행한다.
3. 새 project/channel/thread를 서버 DB에 등록한다.
4. Discord channel/thread id와 project_id를 연결한다.
5. 기본 memory scaffold를 만든다.

위험한 작업이 아니므로 새 thread/channel 생성은 대체로 사용자에게 긴 승인 절차를
요구하지 않아도 된다. 단, 공개 권한, 외부 초대, 삭제, archive, secret 관련
작업은 승인 대상으로 둔다.

초기 기본 thread 세트:

```text
owner-design
owner-tasks
decisions
ai-internal
artifacts
test-runner
```

프로젝트 타입에 따라 추가할 수 있다:

```text
game: art-direction, combat, narrative
web: frontend, backend, design-system
app: mobile, api, release-store
tool: cli, packaging, docs
```

타입별 thread는 기본으로 너무 많이 만들지 않는다. 필요할 때 사용자가 Owner에게
말하면 자연어로 추가한다.

## New Project Creation Defaults

새 프로젝트 생성은 자연어 대화 중심으로 한다.

기본 흐름:

```text
1. User asks Owner to create a project.
2. Owner infers project type, asking only if ambiguous.
3. Owner creates Discord project channel and default threads.
4. Owner creates server Project record.
5. Owner creates initial memory scaffold.
6. Owner prepares repo/template/workspace setup proposal.
7. Proposal is posted to #approval-inbox.
8. User approves.
9. Server creates GitHub private repo or local bare repo.
10. Server applies template, initial commit, workspace config, and reports back.
```

Default project threads:

```text
owner-design
owner-tasks
decisions
ai-internal
artifacts
test-runner
```

Repo defaults:

- Real projects: GitHub private repo.
- Temporary/test projects: main server local bare repo.
- GitHub repo creation: automatic only after `#approval-inbox` approval.
- Default visibility: private.
- Public repo creation requires separate approval.

Repo approval message should show:

```text
Project name
Project type
Repo location
GitHub owner or local path
Repo name
Visibility
Template
Workspace path
Base branch
Expected generated files
Risks or notes
```

Approval buttons:

```text
Approve Repo Setup
Edit
Hold
Cancel
```

Project type defaults:

- Owner infers project type from conversation.
- If ambiguous, Owner asks one short clarifying question.
- Supported initial types: `game`, `web`, `app`, `backend`, `tool`,
  `automation`, `research`, `plugin`.

## Decision Style

앞으로는 하나씩 모든 항목을 질문하지 않는다.

기본 방식:

1. Owner proposes a recommended default bundle.
2. User says "좋아" or lists changes.
3. Owner proceeds with the recommended defaults.
4. Owner asks separately only for high-risk decisions.

High-risk decisions:

- paid model or major cost increase
- public exposure or permission change
- public GitHub repo
- destructive git or file operation
- credential/secret handling
- engine/framework lock-in when ambiguous
- merge despite failing tests or warnings

## Natural Understanding and Action Plans

Owner 대화는 단일 intent 분류를 강제하지 않는다.

사용자 메시지는 한 번에 여러 요청을 담을 수 있다. 예:

```text
demo-game 진행상황 알려주고, 테스트 실패한 거 있으면 다시 돌려봐.
```

Owner는 자연어 추론을 우선 사용한다. 다만 실행 전에는 필요한 경우 action plan으로
쪼개서 설명한다.

기본 흐름:

```text
1. User message
2. Owner understands natural language
3. Owner extracts one or more proposed actions
4. Owner asks if an action is ambiguous or risky
5. Owner executes safe actions or records approval request
6. Server stores actions, tags, decisions, and summaries
```

단일 `intent` 값은 필수로 저장하지 않는다. 대신 한 메시지나 action에 여러 tag를
붙일 수 있다.

예:

```text
tags:
- project:demo-game
- action:status_query
- action:test_request
- type:owner_conversation
- area:test-runner
```

Owner가 사용자의 의도를 잘 파악하는 것을 기본으로 하되, 애매하거나 위험하면
멈추고 묻는다.

## Casual Conversation

`#owner-room`은 일상적인 Owner 대화와 운영 질문에 사용한다.

허용:

- 오늘 뭘 할지 묻기.
- 전체 진행 상황 묻기.
- Owner에게 일반 조언 묻기.
- 프로젝트와 직접 관련 없는 잡담.

제한:

- 구체적인 프로젝트 요구사항 확정.
- task 변경 지시.
- merge 승인.
- 엔진 선택.
- 비용/보안/외부 공개 결정.

위 항목은 프로젝트 thread 또는 `#approval-inbox`로 이동한다.

## Asking Project Status From Owner Room

사용자가 `#owner-room`에서 프로젝트 진행 상황을 물어볼 수 있어야 한다.

예:

```text
demo-game 어디까지 됐어?
테스트러너 붙이는 건 얼마나 남았어?
지금 막힌 작업 있어?
```

Owner 응답 방식:

1. 서버 API에서 project tree, task queue, reports, readiness, recent memory를
   조회한다.
2. `#owner-room`에는 짧은 요약을 답한다.
3. 프로젝트 세부 논의가 필요하면 관련 project thread 링크를 붙인다.
4. 새로운 결정이나 요구사항이 생기면 project thread로 이동한다.

이 방식이면 일상 채널에서 전체 상황은 물어볼 수 있지만, 프로젝트 문맥은
프로젝트 thread에 안전하게 유지된다.

## Memory Scope

메모리는 범위별로 나눈다.

```text
global
project:{project_slug}
thread:{discord_thread_id}
task:{task_id}
artifact:{artifact_id}
```

권장 원칙:

- `global`: 운영 규칙, 보안 규칙, 공통 worker 규칙.
- `project`: 게임별 설계, 기획, art/narrative guide, repo 지식.
- 일반 개발 프로젝트에서는 framework, architecture, API contract, design system,
  deployment, release rules 등을 저장한다.
- `thread`: thread 안에서만 필요한 단기 논의 요약.
- `task`: task 수행 중 생긴 근거와 결과.
- `artifact`: 이미지/영상/로그/빌드 결과의 설명과 링크.

프로젝트 thread 안의 채널/스레드는 같은 project memory를 공유한다. 단, 모든
과거 메시지를 매번 prompt에 넣지 않는다.

장기 변경 요약과 검색 정책은 [LONG_TERM_PROJECT_MEMORY.md](LONG_TERM_PROJECT_MEMORY.md)를
따른다.

## Safe Context Window Use

컨텍스트 창을 안전하게 쓰기 위한 v1 전략:

1. Discord 원문 전체를 매번 넣지 않는다.
2. 서버 DB의 구조화된 상태를 먼저 조회한다.
3. 관련 memory key만 고른다.
4. thread별 최근 요약을 넣는다.
5. 최근 메시지는 필요한 범위만 넣는다.
6. 오래된 대화는 rolling summary로 압축한다.
7. 중요한 결정은 raw conversation이 아니라 memory로 저장한다.

컨텍스트가 가득 찰 때는 채널을 지우지 않는다. 대신 아래 순서로 처리한다.

1. 현재 thread를 요약한다.
2. 요약을 `thread_summary` memory와 change summary log에 저장한다.
3. 중요한 결정은 decision log로 승격한다.
4. 진행 중 task와 artifact 링크를 보존한다.
5. 기존 thread를 archive 또는 read-only로 둔다.
6. 새 continuation thread를 만든다.
7. 새 thread 첫 메시지에 이전 summary와 링크를 붙인다.

권장 thread 이름:

```text
planning-2026-06
planning-2026-07
combat-system-part-1
combat-system-part-2
ai-internal-task-42
```

Thread를 clear/delete하는 것은 추천하지 않는다. 검색 가능성과 추적성을 잃기
때문이다.

Owner prompt 권장 구성:

```text
System rules
User request
Project status summary
Relevant memories
Recent thread summary
Recent messages, limited
Open decisions
Task/report evidence
```

Worker prompt 권장 구성:

```text
Task package
Relevant project memory
Specific files/artifacts needed
Recent task events
No unrelated Discord chatter
```

## Conversation Isolation

Bot은 하나여도 conversation/session은 분리한다.

서버가 저장해야 하는 key:

```text
discord_guild_id
discord_channel_id
discord_thread_id
project_id
conversation_id
actor_role
task_id optional
owner_run_id optional
```

충돌 방지 규칙:

- `#owner-room` 대화는 worker task를 직접 덮어쓰지 않는다.
- 진행 중 task를 바꾸려면 새 owner note, interrupt request, 또는 새 task로 남긴다.
- Worker report는 lease/claim이 있어야만 서버에 저장된다.
- 같은 task에 두 worker가 동시에 report하지 못하게 한다.
- 프로젝트 thread의 결정은 project memory로 승격되기 전까지 thread scope에 둔다.

## Role Presentation

겉보기:

```text
Owner
Code Worker
Test Runner
Art Worker
Narrative Worker
```

권장 구현:

```text
AI Game Company Bot 1개
역할별 Webhook 여러 개
```

Bot:

- slash command 처리
- 버튼/승인 interaction 처리
- 서버 API 호출
- 권한은 최소화

Webhook:

- 역할별 이름과 avatar로 메시지 표시
- 특정 채널에만 연결
- webhook URL은 secret으로 관리

Worker에게 Discord token/webhook을 직접 주지 않는다. Worker는 서버 API에
report하고, 서버가 Discord에 표시한다.

## Approval Flow

`#approval-inbox`는 버튼 중심 UI가 아니라 "상사 결재함"에 가깝다.

사용자는 대부분 Owner와 대화하면서 자연어로 결재한다.

예:

```text
좋아 진행해
승인
그대로 가자
repo 이름만 바꿔서 진행해
잠깐 보류
설명 더 해줘
```

버튼은 보조 수단이다. 모바일에서 빠르게 처리하거나, 실수를 줄이기 위해 붙일
수 있지만, 버튼을 반드시 누르게 만들 필요는 없다.

결재는 고정 목록만 보고 판단하지 않는다. Owner가 상황을 보고 멈출지 판단한다.

Owner는 아래 성격의 작업을 감지하면 멈추고 결재 요청을 올린다:

- 비용이 늘 수 있음.
- 보안, secret, token, 권한과 관련 있음.
- 외부 공개, 도메인, 네트워크 노출과 관련 있음.
- 삭제, force push, repo 변경처럼 되돌리기 어렵거나 파괴적임.
- main/release branch에 영향을 줌.
- 엔진, 프레임워크, 제품 방향을 바꿈.
- 사용자 의도가 애매함.
- 실패한 테스트나 경고를 무시해야 함.

아래 목록은 예시일 뿐 완전한 규칙표가 아니다:

- GitHub repo 생성.
- public repo 생성.
- 외부 공개/HTTPS/도메인 설정.
- 유료 모델 변경.
- secret/token/env 변경.
- main branch merge.
- 실패한 테스트를 무시하고 merge.
- 파일/branch/repo 삭제.
- force push.
- engine/framework 선택.
- systemd always-on worker 활성화.

낮은 위험 작업은 Owner가 추천 기본값으로 진행할 수 있다:

- Discord thread 생성.
- 서버 Project record 생성.
- memory scaffold 생성.
- task 초안 작성.
- 낮은 위험의 문서 작업 task 생성.
- worker report 요약.
- 상태 조회.

Owner가 조금이라도 불확실하면 진행하지 않고 물어본다.

`#approval-inbox`에는 사용자가 결정해야 하는 항목만 올린다.

예:

- engine 선택
- merge warning 무시/차단
- 외부 공개 설정
- 유료 모델 변경
- destructive git operation
- release 승인
- 테스트 실패 후 merge 허용

메시지에는 버튼을 둔다:

```text
Approve
Reject
Hold
Ask Owner
Create Task
Retry
Allow Merge
```

버튼 클릭 결과와 자연어 결재 결과는 Discord 메시지 수정뿐 아니라 서버 DB에
저장한다.

결재 요청에는 반드시 아래 내용이 있어야 한다:

```text
무엇을 하려는지
대상 프로젝트/task/repo
예상 실행 단계
사용할 권한 또는 token
생성/수정/삭제될 것
위험 또는 되돌리는 방법
승인 방법
```

자연어 결재 예:

```text
Owner:
GitHub private repo를 만들 준비가 됐어.

Project: dashboard-web
Repo: powerpunch080403/dashboard-web
Template: web-basic
Workspace: /home/powerpunch/project-workspaces/dashboard-web

승인하려면 "진행해"라고 말해줘.

User:
좋아 진행해
```

서버 decision log 예:

```text
type: approval
target: repo_setup
project: dashboard-web
approved_by: user
source: discord_message
message: "좋아 진행해"
timestamp: ...
```

위험 작업은 결재 없이 실행하지 않는다.

## Artifact Flow

AI들이 올리는 이미지, 영상, gif, 로그, 빌드 결과는 모두 볼 수 있어야 한다.

권장 방식:

- 작은 이미지/짧은 영상: Discord attachment로 미리보기.
- 큰 파일: 서버 artifact storage에 저장하고 Discord에는 링크/썸네일.
- Test Runner logs: 요약은 Discord, 전체 log는 artifact link.
- 생성물은 project/thread/task/artifact id와 연결.

나중에 웹 관리 프로그램을 만들면 같은 artifact metadata를 사용한다.

시각적 개발 루프와 MCP 도구 연결은 [VISUAL_TOOL_INTEGRATION.md](VISUAL_TOOL_INTEGRATION.md)를
따른다.

## v1 Implementation Later

아직 코드 구현 전 설계 항목:

- Discord guild/channel/thread mapping schema.
- Discord Bot command 목록.
- Approval inbox schema.
- Artifact metadata schema.
- Memory scope와 retrieval policy.
- Owner room status query endpoint.
- Project thread creation/registration flow.
- Webhook secret 관리 방식.
- Natural language project/channel/thread creation flow.
- Project type metadata.
- Thread rotation and summarization flow.
- AI internal conversation summary flow.
- Project-level AI internal thread creation.
- Transparent internal conversation mode with summary-only prompt retrieval.

## Open Questions

- 프로젝트 channel/thread 생성 권한을 Owner에게 어디까지 줄지.
- Discord command prefix/slash command 이름.
- Owner가 project thread로 이동을 제안만 할지, 자동으로 thread를 만들지.
- artifact storage를 처음에는 로컬 파일로 둘지, object storage로 둘지.
- 오래된 thread를 자동 archive할 기준.
