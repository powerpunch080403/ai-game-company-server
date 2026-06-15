from __future__ import annotations

from dataclasses import dataclass


DEFAULT_CHARS_PER_TOKEN = 3.5


@dataclass(frozen=True)
class ContextEstimate:
    estimated_tokens: int
    threshold_tokens: int
    warning_tokens: int
    remaining_tokens: int
    usage_ratio: float
    status: str
    compact_required: bool
    compact_recommended: bool


def estimate_tokens_for_text(text: str, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    if not text:
        return 0
    return max(1, int((len(text) / chars_per_token) + 0.999))


def estimate_context_tokens(
    text_parts: list[str],
    estimated_extra_tokens: int = 0,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
) -> int:
    text_tokens = sum(estimate_tokens_for_text(part, chars_per_token) for part in text_parts if part)
    return text_tokens + max(0, estimated_extra_tokens)


def context_status(
    estimated_tokens: int,
    threshold_tokens: int,
    warning_tokens: int,
) -> ContextEstimate:
    compact_required = estimated_tokens >= threshold_tokens
    compact_recommended = estimated_tokens >= warning_tokens
    if compact_required:
        status = "compact_now"
    elif compact_recommended:
        status = "warning"
    else:
        status = "ok"
    remaining_tokens = max(0, threshold_tokens - estimated_tokens)
    usage_ratio = round(estimated_tokens / threshold_tokens, 4) if threshold_tokens > 0 else 1.0
    return ContextEstimate(
        estimated_tokens=estimated_tokens,
        threshold_tokens=threshold_tokens,
        warning_tokens=warning_tokens,
        remaining_tokens=remaining_tokens,
        usage_ratio=usage_ratio,
        status=status,
        compact_required=compact_required,
        compact_recommended=compact_recommended,
    )
