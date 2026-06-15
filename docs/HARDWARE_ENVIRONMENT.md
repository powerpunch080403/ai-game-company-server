# Hardware and Machine Environment

This document is the shared machine inventory for AI Game Company Server v1.

It exists so future AI sessions do not guess the available computers, GPU
capacity, network paths, or deployment assumptions.

## Current Rule

If a hardware detail is not listed as known here, do not assume it.

The main server may be powered off. Continue local design, documentation, and
repo work when SSH is unavailable.

## Known Machines

| Machine ID | Kind | Known role | Known details | Unknown details |
| --- | --- | --- | --- | --- |
| `local_windows_codex` | local dev machine | Current Codex Desktop workspace, local design, docs, tests | Windows workspace at `C:\Users\user2\Documents\게임 개발 서버 v1개발` | Not intended as always-on server |
| `main_server` | main server | FastAPI control plane, SQLite, Owner runs, Discord Bot service, API Worker, optional Workspace Worker, backups, future local GPU worker | CPU: Intel Core i5-14600KF; GPU: NVIDIA RTX 4070; RAM: 32 GB DDR5; OS: Ubuntu Desktop; SSH target `powerpunch@100.92.73.19`; deployment path `/home/powerpunch/ai-game-company-server`; API URL currently documented as `http://100.92.73.19:8080`; Linux/systemd target | Disk size, uptime, firewall, public HTTPS setup |
| `test_runner_12400_3060` | test runner machine | Build/test/run projects, capture screenshots/videos/logs, upload artifacts | Planned CPU/GPU: Intel i5-12400 and NVIDIA RTX 3060 | OS, hostname, Tailscale IP, workspace root, artifact root, installed engines/tools |
| `future_friend_worker` | future worker machine | Friend or additional worker server for parallel development | Direction only | Owner, host, specs, trust level, workspace root |
| `future_gpu_worker` | future GPU/local LLM worker | Local model server, graphics or GPU-heavy worker tasks | Direction only | GPU model, model server, API endpoint, cost/power limits |

## Main Server Placement

The main server is the control plane. It has enough CPU/GPU capacity to host
future local GPU or local LLM worker services, but v1 should still keep the
control plane reliable and simple first.

Recommended responsibilities:

- FastAPI API server.
- SQLite database.
- Owner run records.
- Model profile settings.
- Task queue and memory.
- Discord Bot service.
- API Worker service.
- Optional one-at-a-time Workspace Worker service.
- Backup job.

Do not run heavy game builds, GPU rendering, local LLM service, or long visual
tests on the main server as part of v1 unless that worker service is explicitly
enabled. Treat those as separate worker responsibilities so the FastAPI/SQLite
control plane stays stable.

Known main server hardware:

```text
CPU: Intel Core i5-14600KF
GPU: NVIDIA RTX 4070
RAM: 32 GB DDR5
OS: Ubuntu Desktop
```

## Test Runner Placement

The `test_runner_12400_3060` machine is the first planned execution machine for
heavy validation.

Recommended responsibilities:

- Clone project workspaces separately from the main server.
- Run build/test/run commands.
- Capture screenshots, videos, logs, and visual evidence.
- Upload artifacts to the main server.
- Report through the normal worker lease/report API.

This machine should be registered as:

```text
machine_id: test_runner_12400_3060
kind: test_runner_machine
capabilities: build, test, run_game, screenshot, video_capture, gpu
```

## Repository and Workspace Placement

Server repo:

```text
/home/powerpunch/ai-game-company-server
```

Main server project paths:

```text
/home/powerpunch/game-repos/{project}.git
/home/powerpunch/game-workspaces/{project}
```

Future multi-machine workspace convention:

```text
/home/powerpunch/game-workspaces/{project}/main
/home/powerpunch/game-workspaces/{project}/workers/{worker_id}
/home/powerpunch/game-workspaces/{project}/test-runners/{machine_id}
```

Test runner local paths are not confirmed yet. Do not hard-code them until the
machine is online and its OS/path layout is chosen.

## Network Assumptions

Known:

- Main server Tailscale/SSH target: `powerpunch@100.92.73.19`
- Current documented API URL: `http://100.92.73.19:8080`
- Raw public `:8080` exposure is not allowed.
- Discord is the primary human operation interface.
- Tailscale/SSH is the admin and recovery path.

Unknown:

- Whether public HTTPS is configured.
- Whether the main server is currently powered on.
- Test runner hostname or Tailscale IP.
- Friend worker hostnames.

## Secrets and Auth Placement

Secrets must not be committed.

Recommended placement:

- Main server `.env`: API token, model API keys, Owner command, DB path.
- GitHub CLI auth: main server OS account, after approval.
- Test runner `.env`: server API URL/token, local workspace root, tool paths.
- Discord bot token: main server `.env` or service manager environment.

SQLite may store environment variable names, but not raw secret values.

## What Future AI Sessions Should Ask Before Assuming

Ask the user or inspect the machine before deciding:

- Main server disk capacity and filesystem layout.
- Test runner OS and workspace path.
- Whether the test runner is online.
- Whether a public HTTPS endpoint should be enabled.
- Whether a machine is trusted enough to run destructive commands.
- Whether a worker machine may push to GitHub directly.

Do not ask for these details when doing local-only docs, schema design, or tests
that do not require the machines.

## Hardware-Aware Defaults

Until more specs are known:

- Keep SQLite on the main server.
- Keep the main server focused on control-plane work for v1.
- Treat the RTX 4070 as a future local LLM/GPU worker option, not a default v1
  dependency.
- Put heavy build/run/visual validation on `test_runner_12400_3060`.
- Use one workspace-mutating worker per project workspace.
- Treat future friend machines as external/limited trust until registered.
- Treat local LLM/GPU workers as v1.5 extensions.
