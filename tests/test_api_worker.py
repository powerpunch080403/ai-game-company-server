from __future__ import annotations

import pytest

from app.api_worker import (
    build_worker_prompt,
    chat_completions_url,
    extract_message_content,
    infer_status,
    resolve_profile_value,
    resolve_worker_api_config,
)


def test_build_worker_prompt_contains_task_contract() -> None:
    package = {
        "task": {
            "id": 7,
            "role": "code_worker",
            "goal": "Implement inventory save",
            "branch": "worker/inventory-save",
            "estimated_minutes": 15,
            "requirements": ["Save item ids", "Load on startup"],
            "success_criteria": ["Round trip succeeds"],
        },
        "memories": [
            {
                "key": "inventory_system",
                "title": "Inventory System",
                "body": "InventoryManager already exists.",
            }
        ],
    }
    prompt = build_worker_prompt(package)
    assert "Implement inventory save" in prompt
    assert "worker/inventory-save" in prompt
    assert "InventoryManager already exists." in prompt
    assert "Status: SUCCESS | BLOCKED | FAILED" in prompt


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
        ("https://example.test", "https://example.test/v1/chat/completions"),
        ("https://example.test/v1/chat/completions", "https://example.test/v1/chat/completions"),
    ],
)
def test_chat_completions_url(base_url: str, expected: str) -> None:
    assert chat_completions_url(base_url) == expected


def test_extract_message_content() -> None:
    response = {"choices": [{"message": {"content": "Status: SUCCESS\nSummary: Done"}}]}
    assert extract_message_content(response) == "Status: SUCCESS\nSummary: Done"


def test_extract_message_content_rejects_empty_response() -> None:
    with pytest.raises(ValueError):
        extract_message_content({"choices": []})


def test_resolve_profile_value_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_MODEL_ENV", "cheap-worker-model")
    assert resolve_profile_value("WORKER_MODEL_ENV") == "cheap-worker-model"
    assert resolve_profile_value("literal-model") == "literal-model"


def test_resolve_worker_api_config_uses_profile_and_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_BASE_URL_ENV", "https://api.example.test/v1")
    monkeypatch.setenv("WORKER_KEY_ENV", "secret")
    monkeypatch.setenv("WORKER_MODEL_ENV", "worker-model")
    config = resolve_worker_api_config(
        {
            "base_url": "WORKER_BASE_URL_ENV",
            "api_key_env": "WORKER_KEY_ENV",
            "model": "WORKER_MODEL_ENV",
            "temperature": 0.4,
        }
    )
    assert config == {
        "base_url": "https://api.example.test/v1",
        "api_key": "secret",
        "model": "worker-model",
        "temperature": 0.4,
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Status: SUCCESS\nSummary: Done", "success"),
        ("Status: BLOCKED\nIssues: Missing repo", "blocked"),
        ("Status: FAILED\nIssues: API error", "failed"),
        ("Summary only", "success"),
    ],
)
def test_infer_status(text: str, expected: str) -> None:
    assert infer_status(text) == expected
