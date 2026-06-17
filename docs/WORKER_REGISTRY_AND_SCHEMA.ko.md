# Worker Registry and Core Schema Design

이 문서는 v1에서 Discord, Worker, Artifact, Approval, Memory를 안전하게 연결하기
위한 최소 등록부와 저장 양식을 정의한다.

구현 문서가 아니라 설계 기준이다.

## Current Decisions

- Discord Bot은 FastAPI 서버와 같은 main server에서 돌릴 수 있지만, 별도
  프로세스/서비스로 분리한다.
- Discord Bot은 SQLite DB에 직접 접근하지 않고 FastAPI API만 사용한다.
- Artifact는 test runner나 worker 머신에서 main server로 업로드한다.
- Artifact 저장소는 프로젝트별로 분리한다.
- GitHub repo 자동 생성 인증은 우선 GitHub CLI 로그인 방식을 추천한다.
- 외부 관리는 우선 Discord 자연어 운영을 사용한다. 공개 HTTPS API/UI는 필요할
  때 추가한다.
- Worker Registry는 v1에 최소 설계로 넣고, 나중에 친구 컴퓨터/여러 서버/테스트
  머신이 붙을 수 있게 확장 가능성을 남긴다.
- Discord, approval, artifact, worker, memory는 최소 schema를 먼저 정한다.

## Process Boundary

권장 프로세스 구조:

```text
main server
  FastAPI service
  Discord Bot service
  API Worker service
  Workspace Worker service
  backup job

test runner machine
  Test Runner service
  game/app/web workspace clones
  screenshot/video/log capture tools
```

원칙:

- FastAPI는 업무 장부와 API의 중심이다.
- Discord Bot은 Discord 입출력만 담당하고, 모든 상태 변경은 FastAPI API로 요청한다.
- Worker들은 task lease/report API만 사용한다.
- SQLite는 FastAPI만 직접 만진다.

## Worker Registry

Worker Registry는 AI 직원/컴퓨터 직원 명부다.

최소 필드:

```text
worker_id
display_name
role
machine_id
status
capabilities
assigned_projects
workspace_root
trust_level
last_seen_at
notes
```

role 예:

```text
owner
api_worker
workspace_worker
test_runner
art_worker
tool_worker
blender_worker
browser_worker
local_llm_worker
```

capabilities 예:

```text
chat_completion
code_edit
git_commit
git_push
build
test
run_game
screenshot
video_capture
blender
browser
gpu
```

trust level 예:

```text
trusted
limited
experimental
external
```

v1에서는 worker가 report/heartbeat를 보낼 때 registry를 갱신하면 충분하다.

## Machine Registry

여러 서버와 친구 컴퓨터를 붙이려면 machine 정보도 필요하다.

최소 필드:

```text
machine_id
display_name
kind
host_hint
os
workspace_root
artifact_root
status
capabilities
last_seen_at
notes
```

kind 예:

```text
main_server
test_runner_machine
friend_worker_machine
gpu_worker_machine
local_dev_machine
```

main server는 Intel Core i5-14600KF, NVIDIA RTX 4070, 32 GB DDR5 RAM으로
등록한다. v1에서는 `main_server`와 control-plane 역할을 우선하고, RTX 4070은
나중에 별도 `local_llm_worker` 또는 `gpu_worker_machine` 역할로 확장할 수 있게
capabilities에 남긴다.

12400 / RTX 3060 테스트 머신은 `test_runner_machine`으로 등록한다.

## Discord Mapping Schema

Discord는 운영 UX이고 서버 DB가 source of truth다.

최소 필드:

```text
discord_guild_id
discord_channel_id
discord_thread_id
project_id optional
conversation_kind
thread_role
created_by
created_at
archived_at optional
summary_memory_key optional
notes
```

conversation_kind 예:

```text
owner_room
approval_inbox
project
ai_internal
artifact
test_runner
worker_report
```

thread_role 예:

```text
owner-design
owner-tasks
decisions
ai-internal
ai-internal-task
artifacts
test-runner
```

## Approval / Decision Schema

결재는 자연어 우선, 버튼은 보조다.

최소 필드:

```text
approval_id
project_id optional
target_type
target_id optional
requested_by
approved_by optional
status
request_summary
risk_summary
approval_message
discord_message_id optional
discord_thread_id optional
created_at
decided_at optional
decision_memory_key optional
```

status 예:

```text
pending
approved
rejected
held
edited
canceled
expired
```

target_type 예:

```text
repo_setup
merge
public_access
secret_change
paid_model_change
systemd_worker_enable
destructive_git
release
```

## Artifact Schema

Artifact는 서버로 업로드하고 프로젝트별로 저장한다.

권장 경로:

```text
artifacts/{project_slug}/{task_id_or_manual}/{artifact_id}/
```

최소 필드:

```text
artifact_id
project_id
task_id optional
worker_id optional
machine_id optional
artifact_type
path_or_url
thumbnail_path_or_url optional
summary
tags
retention_policy
important
release_or_milestone
size_bytes optional
created_at
discord_message_id optional
discord_thread_id optional
```

retention_policy 예:

```text
standard_30_days
important_keep_forever
release_keep_forever
manual
```

## Memory / Log Schema Direction

v1은 기존 `memories` table을 최대한 사용한다.

추가로 구조화가 필요한 필드:

```text
memory_key
project_id optional
task_id optional
artifact_id optional
discord_thread_id optional
memory_type
title
summary/body
tags
source_refs
created_at
updated_at
```

검색은 tag-first로 한다.

## GitHub Auth Decision

GitHub repo 자동 생성은 approval 후 실행한다.

v1 추천:

```text
gh auth login
gh repo create owner/name --private
```

원칙:

- GitHub token을 DB에 저장하지 않는다.
- GitHub CLI 인증은 main server OS 계정에 둔다.
- public repo 생성은 별도 결재가 필요하다.
- repo 생성 결과는 decision log와 project config에 기록한다.

## External Access Decision

사람의 기본 운영 인터페이스는 Discord다. Discord는 외부에서도 접근 가능하므로,
v1 초기에 별도 public web UI나 public API를 급하게 열 필요는 없다.

현재 방향:

- Admin/recovery: Tailscale + SSH.
- Human operation: Discord.
- Worker/test machine API access: Tailscale 또는 제한된 HTTPS.
- Public HTTPS UI/API: 필요할 때 추가.
- Raw `:8080` public exposure는 금지.

나중에 공개 웹 관리 화면이 필요해지면 Cloudflare Tunnel, Caddy/Nginx reverse
proxy, Tailscale Funnel 중에서 다시 선택한다.

## v1 Implementation Later

Implemented:

- Worker registry API.
- Machine registry API.
- Worker heartbeat API.
- Machine heartbeat API.
- Worker `last_seen_at` updates from task lease, claim, and report activity.
- Artifact metadata API.
- Artifact raw content upload/download API.
- Approval decision table/API.
- Discord mapping table/API.

Next:

- Artifact cleanup job.
- GitHub repo setup command using `gh`.
- Memory tag/search helper.

## v1.5 Later

- Worker capability matching.
- Trust-based task routing.
- Multi-machine workspace allocation.
- Object storage for artifacts.
- Postgres migration.
- Web UI for registry/artifacts/approvals.
