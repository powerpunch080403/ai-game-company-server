# Visual Tool and MCP Integration Design

이 문서는 게임 화면, 앱 화면, Blender 같은 외부 프로그램을 AI 개발 서버와
연결해서 보면서 개발하는 구조를 정의한다.

v1의 목표는 모든 도구를 즉시 자동화하는 것이 아니라, 화면/산출물을 사람이 볼
수 있고 AI가 리뷰할 수 있는 피드백 루프를 먼저 만드는 것이다.

## Goals

- 게임 화면을 보면서 개발할 수 있다.
- 앱/웹 화면도 같은 방식으로 리뷰할 수 있다.
- Test Runner가 screenshot/video/log/artifact를 남긴다.
- Discord에서 이미지, 영상, 로그를 볼 수 있다.
- Owner가 시각 결과를 보고 다음 task를 만들 수 있다.
- Blender, game engine, browser, editor 같은 도구를 나중에 MCP로 붙일 수 있다.

## Non Goals

- v1에서 모든 엔진/툴을 완전 자동화하지 않는다.
- AI가 사용자 승인 없이 큰 에셋이나 scene 구조를 갈아엎지 않는다.
- Discord를 artifact 저장소의 source of truth로 쓰지 않는다.

## Visual Feedback Loop

기본 루프:

```text
Worker changes project
Test Runner builds/runs project
Test Runner captures screenshot/video/log
Server stores artifact metadata
Discord posts preview/link
Owner reviews result
User approves or asks follow-up
Owner creates next task
```

게임 프로젝트 예:

```text
1. Code Worker가 player controller를 수정한다.
2. Test Runner가 게임을 실행한다.
3. 20초 gameplay video와 screenshot을 캡처한다.
4. Discord #artifacts와 프로젝트 thread에 preview를 올린다.
5. Owner가 "점프 타이밍이 느림" 같은 관찰을 memory/task로 남긴다.
```

웹/앱 프로젝트 예:

```text
1. Worker가 dashboard UI를 수정한다.
2. Test Runner 또는 browser runner가 화면을 연다.
3. desktop/mobile screenshot을 캡처한다.
4. Discord에 before/after preview를 올린다.
5. Owner가 layout issue를 task로 만든다.
```

## Artifact Types

지원해야 할 artifact:

```text
screenshot
video
gif
log
build_report
test_report
profile
coverage
asset_preview
blend_file
scene_snapshot
web_snapshot
```

Artifact storage:

```text
artifacts/{project_slug}/{task_id_or_manual}/{artifact_id}/
```

Workers and test runner machines should upload artifacts to the main server.
The server keeps project-separated artifact storage and posts Discord previews
or links.

Artifact metadata:

```text
artifact_id
project_id
task_id optional
worker_id
artifact_type
path_or_url
thumbnail_path_or_url optional
created_at
summary
tags
discord_message_id optional
discord_thread_id optional
retention_policy
important
release_or_milestone
```

## Artifact Retention

Default retention:

- Small artifacts: store on server and post Discord preview.
- Large artifacts: keep original files for 30 days by default.
- Important artifacts: keep forever.
- Release/milestone artifacts: keep forever.

Large file cleanup must not remove metadata, summaries, task reports, decision
logs, or git references.

## Discord Presentation

Discord에는 사람이 바로 볼 수 있는 preview를 올린다.

- 작은 screenshot/gif: Discord attachment.
- 짧은 video: Discord attachment 가능.
- 큰 video/build/log: artifact link + thumbnail.
- 여러 이미지는 thread 안에 gallery처럼 올린다.
- Owner review가 필요한 artifact는 `#approval-inbox` 또는 project thread에 연결한다.

## MCP Tool Bridge

MCP는 AI가 외부 도구와 대화하는 통로로 사용한다.

예상 tool adapters:

```text
Blender MCP
Game engine MCP
Browser MCP
File/artifact MCP
Build/test MCP
Profiler MCP
```

Blender MCP 사용 예:

- scene 열기.
- asset preview render.
- mesh/material 정보 조회.
- 간단한 asset 생성/수정.
- render 이미지를 artifact로 저장.

Browser MCP 사용 예:

- localhost 웹 앱 열기.
- desktop/mobile screenshot.
- button/form interaction.
- console error capture.

Game engine MCP 사용 예:

- editor 열기.
- scene 실행.
- screenshot/video capture.
- compile/test result 조회.

## Safety Rules

- Tool MCP는 프로젝트 workspace 범위 안에서만 작업한다.
- destructive action은 Owner/user approval이 필요하다.
- Blender/engine scene 저장 전에는 task와 branch가 있어야 한다.
- AI가 만든 asset은 artifact와 commit으로 연결한다.
- 자동 실행은 test runner machine에서 먼저 격리한다.

## Test Runner Machine

12400 / RTX 3060 테스트 머신은 visual feedback의 첫 번째 실행 장소다.

역할:

- 게임 실행.
- screenshot/video capture.
- Blender render/preview.
- GPU가 필요한 visual check.
- build/test/profile artifact 생성.

이 머신은 서버 API로 task를 lease/report하고, artifact는 서버나 project
workspace에 저장한 뒤 Discord에 preview를 올린다.

## Context Integration

이미지/영상 자체를 긴 prompt에 직접 넣지 않는다.

Owner에게 전달할 정보:

- artifact summary.
- thumbnail or selected frame.
- test/run result.
- linked task/report.
- user-visible issue.

필요할 때만 selected frame이나 screenshot을 vision-capable model에 보낸다.

## v1 Implementation Later

- Artifact metadata schema.
- Artifact upload endpoint.
- Project-separated server artifact storage.
- Test Runner screenshot/video convention.
- Discord artifact preview sender.
- Blender MCP adapter registration.
- Browser visual check runner.
- Visual review task template.
- Owner prompt section for artifact review.

## v1.5 Later

- In-browser artifact gallery.
- Side-by-side before/after diff viewer.
- Automated visual regression.
- Engine-specific capture plugins.
- Blender asset pipeline.
- Model-based screenshot critique.
