from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from app.worker_runner import build_report, request_json, write_task_package

load_dotenv()


def build_worker_prompt(package: dict[str, Any]) -> str:
    task = package["task"]
    lines = [
        "You are a Worker in AI Game Company v1.",
        "",
        "Operating rules:",
        "- Do the assigned task only.",
        "- Do not redesign the project structure.",
        "- Prefer working output over perfect output.",
        "- Keep the response practical and implementation oriented.",
        "- If code changes are needed, describe exact files and patch intent.",
        "- If the task cannot be completed, explain the blocker clearly.",
        "",
        f"Role: {task['role']}",
        f"Task ID: {task['id']}",
        f"Goal: {task['goal']}",
        f"Branch: {task['branch']}",
        f"Estimated Minutes: {task['estimated_minutes']}",
        "",
        "Requirements:",
    ]
    lines.extend(f"- {item}" for item in task["requirements"])
    lines.extend(["", "Success Criteria:"])
    lines.extend(f"- {item}" for item in task["success_criteria"])
    lines.extend(["", "Relevant Memory:"])
    if package["memories"]:
        for memory in package["memories"]:
            lines.extend([f"- {memory['key']}: {memory['title']}", memory["body"]])
    else:
        lines.append("- No memory refs resolved.")
    lines.extend(
        [
            "",
            "Return format:",
            "Status: SUCCESS | BLOCKED | FAILED",
            "Summary:",
            "Files To Change:",
            "Implementation:",
            "Tests:",
            "Issues:",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def chat_completions_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    if clean.endswith("/v1"):
        return f"{clean}/chat/completions"
    return f"{clean}/v1/chat/completions"


def extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices", [])
    if not choices:
        raise ValueError("worker API response did not include choices")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("worker API response did not include message content")
    return content


def resolve_profile_value(value: str, fallback_env: str = "") -> str:
    clean = value.strip()
    if clean and clean != "configured-by-env":
        return os.getenv(clean, clean).strip()
    if fallback_env:
        return os.getenv(fallback_env, "").strip()
    return ""


def load_model_profile(server: str, role: str) -> dict[str, Any] | None:
    try:
        profile = request_json("GET", f"{server}/owner/model-profiles/{role}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    if not profile.get("enabled", True):
        return None
    return profile


def resolve_worker_api_config(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or {}
    base_url = resolve_profile_value(
        str(profile.get("base_url") or ""),
        "GAME_COMPANY_WORKER_API_BASE_URL",
    )
    api_key_env = str(profile.get("api_key_env") or "GAME_COMPANY_WORKER_API_KEY")
    api_key = os.getenv(api_key_env, "").strip()
    model = resolve_profile_value(str(profile.get("model") or ""), "GAME_COMPANY_WORKER_MODEL")
    temperature = float(profile.get("temperature") if profile.get("temperature") is not None else os.getenv("GAME_COMPANY_WORKER_TEMPERATURE", "0.2"))
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "temperature": temperature,
    }


def call_worker_api(prompt: str, profile: dict[str, Any] | None = None) -> str:
    config = resolve_worker_api_config(profile)
    base_url = config["base_url"]
    api_key = config["api_key"]
    model = config["model"]
    timeout = float(os.getenv("GAME_COMPANY_WORKER_TIMEOUT_SECONDS", "120"))

    if not base_url:
        raise RuntimeError("GAME_COMPANY_WORKER_API_BASE_URL is not configured")
    if not api_key:
        raise RuntimeError("GAME_COMPANY_WORKER_API_KEY is not configured")
    if not model:
        raise RuntimeError("GAME_COMPANY_WORKER_MODEL is not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a careful, low-cost AI game development worker."},
            {"role": "user", "content": prompt},
        ],
        "temperature": config["temperature"],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(chat_completions_url(base_url), headers=headers, json=payload)
        response.raise_for_status()
        return extract_message_content(response.json())


def infer_status(response_text: str) -> str:
    upper = response_text.upper()
    if "STATUS: FAILED" in upper:
        return "failed"
    if "STATUS: BLOCKED" in upper:
        return "blocked"
    return "success"


def run_api_worker(args: argparse.Namespace) -> int:
    started_at = time.monotonic()
    if args.task_id:
        package = request_json("GET", f"{args.server}/tasks/{args.task_id}/package")
    else:
        leased = request_json(
            "POST",
            f"{args.server}/workers/{args.worker_id}/lease",
            json={"role": args.role, "lease_minutes": args.lease_minutes},
        )
        if leased is None:
            print("No task available.")
            return 0
        package = request_json("GET", f"{args.server}/tasks/{leased['id']}/package")

    task = package["task"]
    run_dir = Path(args.runs_dir) / f"api-task-{task['id']}"
    write_task_package(run_dir, package)
    prompt = build_worker_prompt(package)
    (run_dir / "worker_prompt.md").write_text(prompt, encoding="utf-8")
    print(f"Prepared API worker prompt for task {task['id']}: {task['goal']}")

    if args.dry_run:
        print(f"Dry run wrote prompt to {run_dir}")
        return 0

    profile = load_model_profile(args.server, task["role"])
    if profile:
        (run_dir / "model_profile.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    try:
        response_text = call_worker_api(prompt, profile)
    except Exception as exc:
        response_text = ""
        report = build_report(
            package,
            "failed",
            started_at,
            "API worker call failed.",
            str(exc),
            ["api_worker"],
        )
    else:
        (run_dir / "worker_response.md").write_text(response_text, encoding="utf-8")
        status = infer_status(response_text)
        report = build_report(
            package,
            status,
            started_at,
            "API worker generated a task response.",
            "" if status == "success" else response_text[-4000:],
            ["api_worker"],
        )

    (run_dir / "worker_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not args.task_id:
        request_json(
            "POST",
            f"{args.server}/workers/{args.worker_id}/tasks/{task['id']}/report",
            json=report,
        )
        print(f"Reported task {task['id']} as {report['status']}.")
    else:
        print("Task ID mode does not report to avoid changing an unleased task.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one task with an OpenAI-compatible worker API.")
    parser.add_argument("--server", default=os.getenv("GAME_COMPANY_SERVER", "http://127.0.0.1:8080"))
    parser.add_argument("--worker-id", default="api-worker-1")
    parser.add_argument("--role", default="code_worker", choices=["code_worker", "image_worker", "voice_worker", "test_runner"])
    parser.add_argument("--lease-minutes", type=int, default=30)
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--task-id", type=int, help="Fetch a task package without leasing or reporting.")
    parser.add_argument("--dry-run", action="store_true", help="Write prompt only; do not call the worker API.")
    return run_api_worker(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
