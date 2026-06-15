# Context Compaction

This document describes how Owner and Discord conversations should avoid
overflowing an AI context window.

The design is intentionally similar to Codex chat compaction:

```text
old raw conversation -> durable summary -> new continuation context
```

The server keeps the useful state, but future prompts do not repeatedly include
the full old conversation.

## Current Status

Implemented:

- `thread_summary` memory type.
- `POST /discord/mappings/{mapping_id}/compact`.
- `POST /discord/mappings/{mapping_id}/context-status`.
- Current summary storage through the mapping `summary_memory_key`.
- Previous current summary archive before replacement.
- Optional old mapping archive.
- Optional continuation Discord thread mapping.
- Context token estimate with default `260000` compact threshold.
- Optional auto-compaction when a compact summary is provided.

Not implemented yet:

- Real Discord Gateway message ingestion.
- Automatic raw Discord message fetching.
- LLM summarization of the raw messages.
- Direct inspection of Codex CLI internal context window.

## Runtime Flow

1. Bot detects a long thread, or Owner asks to compact.
2. Owner/API Worker reads the current summary and recent raw messages.
3. Owner/API Worker writes a new compact summary.
4. Server stores the new summary through `/compact`.
5. Server archives the previous current summary.
6. Server can archive the old mapping.
7. Server can create a continuation thread mapping.
8. Future Owner prompts use the summary, scoped memory, task/report evidence,
   and only a small recent-message window.

## API

Check whether a mapped conversation is close to the configured context limit:

```text
POST /discord/mappings/{mapping_id}/context-status
```

Default thresholds:

```text
warning: 220000 estimated tokens
compact: 260000 estimated tokens
```

Environment overrides:

```env
GAME_COMPANY_CONTEXT_COMPACT_THRESHOLD_TOKENS=260000
GAME_COMPANY_CONTEXT_WARNING_TOKENS=220000
GAME_COMPANY_CONTEXT_CHARS_PER_TOKEN=3.5
```

The v1 estimate uses `characters / GAME_COMPANY_CONTEXT_CHARS_PER_TOKEN`, plus
any explicit `estimated_extra_tokens`. It is a conservative signal for when the
Owner/Discord prompt should be compacted; it is not a direct Codex CLI internal
token meter.

Example request:

```json
{
  "current_summary": "Current thread summary.",
  "project_memory": ["Important project rules."],
  "recent_messages": ["Owner: continue this task.", "Owner: what changed?"],
  "task_context": ["Task report summary."],
  "estimated_extra_tokens": 2000
}
```

If the estimate is above the compact threshold, the response includes:

```json
{
  "status": "compact_now",
  "compact_required": true,
  "compact_action": "summary_required"
}
```

If a compact summary is already available, the same endpoint can store it:

```json
{
  "recent_messages": ["..."],
  "auto_compact": true,
  "compact_summary": "Compact summary to carry forward.",
  "archive_mapping": true,
  "continuation_discord_thread_id": "thread-owner-tasks-part-2"
}
```

Store a compact summary directly:

```text
POST /discord/mappings/{mapping_id}/compact
```

Example request:

```json
{
  "summary": "Owner wants project conversations to continue from compact summaries instead of full raw chat history.",
  "tags": ["context", "owner"],
  "archive_mapping": true,
  "archive_reason": "Thread compacted after context summary.",
  "continuation_discord_thread_id": "thread-owner-tasks-part-2",
  "continuation_notes": "Part 2 after compaction."
}
```

Example response shape:

```json
{
  "mapping": {},
  "memory": {},
  "archived_memory": {},
  "archived_mapping": {},
  "continuation_mapping": {}
}
```

## Prompt Rule

Owner prompts should be assembled in this order:

```text
System rules
User request
Project status summary
Relevant project/thread memory
Recent thread summary
Small recent raw-message window
Task/report/artifact evidence
Open decisions or questions
```

Raw Discord history is used only when the user asks for detailed log review or
when the summarizer needs to refresh the compact summary.

## Why This Matters

Showing every internal message in Discord is fine for human transparency. It
does not significantly increase token use by itself.

Token use increases when raw messages, logs, images, videos, or long files are
fed back into an AI prompt. The compaction rule keeps the UI transparent while
keeping prompts small and stable.
