from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path


CLAUDE_DIR = Path.home() / ".claude" / "projects"

# Approximate Sonnet 4.x pricing per million tokens
PRICE_INPUT = 3.00
PRICE_OUTPUT = 15.00
PRICE_CACHE_WRITE = 3.75
PRICE_CACHE_READ = 0.30


@dataclass
class UsageRecord:
    timestamp: datetime
    session_id: str
    workspace: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT / 1_000_000
            + self.output_tokens * PRICE_OUTPUT / 1_000_000
            + self.cache_creation_tokens * PRICE_CACHE_WRITE / 1_000_000
            + self.cache_read_tokens * PRICE_CACHE_READ / 1_000_000
        )


@dataclass
class Totals:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    record_count: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT / 1_000_000
            + self.output_tokens * PRICE_OUTPUT / 1_000_000
            + self.cache_creation_tokens * PRICE_CACHE_WRITE / 1_000_000
            + self.cache_read_tokens * PRICE_CACHE_READ / 1_000_000
        )

    def add(self, rec: UsageRecord) -> None:
        self.input_tokens += rec.input_tokens
        self.output_tokens += rec.output_tokens
        self.cache_creation_tokens += rec.cache_creation_tokens
        self.cache_read_tokens += rec.cache_read_tokens
        self.record_count += 1


def _parse_record(line: str, workspace: str) -> UsageRecord | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    if obj.get("type") != "assistant":
        return None

    msg = obj.get("message", {})
    usage = msg.get("usage")
    if not usage:
        return None

    ts_raw = obj.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        ts = datetime.now(tz=timezone.utc)

    return UsageRecord(
        timestamp=ts,
        session_id=obj.get("sessionId", "unknown"),
        workspace=workspace,
        model=msg.get("model", "unknown"),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
    )


def load_records() -> list[UsageRecord]:
    records: list[UsageRecord] = []

    if not CLAUDE_DIR.exists():
        return records

    for jsonl_file in CLAUDE_DIR.rglob("*.jsonl"):
        # Derive workspace label from the path segment under projects/
        parts = jsonl_file.relative_to(CLAUDE_DIR).parts
        workspace = parts[0].replace("-", "/").lstrip("/") if parts else "unknown"

        try:
            text = jsonl_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            rec = _parse_record(line, workspace)
            if rec:
                records.append(rec)

    records.sort(key=lambda r: r.timestamp)
    return records


def totals(records: list[UsageRecord]) -> Totals:
    t = Totals()
    for r in records:
        t.add(r)
    return t


def by_day(records: list[UsageRecord]) -> dict[date, Totals]:
    result: dict[date, Totals] = defaultdict(Totals)
    for r in records:
        day = r.timestamp.astimezone().date()
        result[day].add(r)
    return dict(sorted(result.items()))


def by_session(records: list[UsageRecord]) -> dict[str, Totals]:
    result: dict[str, Totals] = defaultdict(Totals)
    for r in records:
        result[r.session_id].add(r)
    return result


def session_last_seen(records: list[UsageRecord]) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for r in records:
        existing = result.get(r.session_id)
        if existing is None or r.timestamp > existing:
            result[r.session_id] = r.timestamp
    return result
