from __future__ import annotations

from app.context_compaction import context_status, estimate_context_tokens, estimate_tokens_for_text


def test_estimate_tokens_for_text_uses_configurable_character_ratio() -> None:
    assert estimate_tokens_for_text("abcd", chars_per_token=2) == 2
    assert estimate_tokens_for_text("", chars_per_token=2) == 0


def test_context_status_marks_260k_threshold_as_compact_now() -> None:
    estimate = context_status(
        estimated_tokens=260000,
        threshold_tokens=260000,
        warning_tokens=220000,
    )

    assert estimate.status == "compact_now"
    assert estimate.compact_required is True
    assert estimate.compact_recommended is True
    assert estimate.remaining_tokens == 0


def test_estimate_context_tokens_includes_extra_projected_tokens() -> None:
    tokens = estimate_context_tokens(["aaaa", "bbbb"], estimated_extra_tokens=10, chars_per_token=2)

    assert tokens == 14
