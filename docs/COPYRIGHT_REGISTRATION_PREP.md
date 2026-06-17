# Copyright Registration Preparation

This document contains information the repository owner can use when preparing for
official copyright registration. This is **not legal advice**. Fees, requirements,
document formats, and deadlines must be verified directly on the official registration
website relevant to your country of residence.

---

## Work Identification

| Field | Value |
|---|---|
| **Work title** | AI Game Company Server v1 |
| **Work type** | Computer program / software |
| **Author** | yeongha SON |
| **Repository URL** | https://github.com/powerpunch080403/ai-game-company-server |
| **First publication** | 2026 (publicly visible on GitHub) |

---

## Short Description (English)

AI Game Company Server v1 is a server-side control plane for managing AI-assisted software
development workflows. It provides planning management at the project, epic, sub-epic, and
task levels; worker task lease and execution reporting; test runner validation; artifact
management; approval and merge review; long-term memory; and Discord operator console
integration. This software is **not** a game runtime server — it is a development workflow
control server for managing the process of building games and software.

---

## Short Description (Korean)

AI Game Company Server v1은 AI 보조 소프트웨어 개발 워크플로우를 관리하기 위한 서버형
제어 평면 소프트웨어입니다. 프로젝트, 에픽, 서브에픽, 작업 단위의 계획 관리, 워커 작업
임대 및 실행 보고, 테스트 러너 검증, 산출물 관리, 승인 및 병합 검토, 장기 메모리,
Discord 운영 콘솔 연동 방향을 포함합니다. 본 소프트웨어는 게임 런타임 서버가 아니라
게임 및 소프트웨어 개발 과정을 관리하기 위한 개발 워크플로우 제어 서버입니다.

---

## Suggested Materials to Archive for Registration

When preparing a submission package, the following materials are recommended:

1. **Source code snapshot** — A ZIP or tarball of the repository at the baseline commit.
2. **README.md** — English overview of the software.
3. **docs/README.ko.md** — Korean overview of the software.
4. **Commit hash / release tag** — The specific baseline commit or tagged release (see below).
5. **Golden Path rehearsal evidence** — Screenshots, logs, or test result outputs demonstrating
   the working end-to-end workflow.
6. **Test result summary** — Output from `pytest` (108 tests passed as of v1 public baseline).

> [!IMPORTANT]
> Do **not** include `.env` files, private tokens, private IPs, SSH credentials, or local
> personal file paths in any publicly submitted materials.

---

## Suggested GitHub Tag and Release

| Field | Value |
|---|---|
| **Tag name** | `v1-public-baseline` |
| **Release title** | `v1 Public Baseline` |
| **Description** | First publicly visible stable baseline. Includes core task lifecycle, worker lease/claim, test runner, artifact management, Golden Path rehearsal, Discord setup, and multi-node config foundation. |

To create the tag and release later (when ready):

```bash
git tag v1-public-baseline
git push origin v1-public-baseline
```

Then create a GitHub Release from this tag through the GitHub UI or GitHub CLI.

---

## Official Registration Note

> [!NOTE]
> Official copyright registration must be completed by the **owner (yeongha SON)** through
> the relevant government or official registration body for your country.
>
> This document is a preparation guide only. Requirements, fees, accepted formats, and
> processing timelines vary by jurisdiction. Consult the official copyright registration
> website for your country before submitting any materials.
>
> This file does not constitute legal advice.
