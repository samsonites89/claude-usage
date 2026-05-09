from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load API key from ~/.claude_usage.env (user-level config, never committed)
load_dotenv(Path.home() / ".claude_usage.env")

CLAUDE_DIR = Path.home() / ".claude" / "projects"
CONFIG_FILE = Path.home() / ".claude_usage_config.json"
CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"
LIMITS_CACHE_FILE = Path.home() / ".claude_usage_limits_cache.json"

# Approximate Sonnet 4.x pricing per million tokens
PRICE_INPUT = 3.00
PRICE_OUTPUT = 15.00
PRICE_CACHE_WRITE = 3.75
PRICE_CACHE_READ = 0.30

PLANS: dict[str, dict] = {
    "pro": {
        "label": "Pro",
        "monthly_budget": 20.0,
    },
    "max_5x": {
        "label": "Max 5×",
        "monthly_budget": 100.0,
    },
    "max_20x": {
        "label": "Max 20×",
        "monthly_budget": 200.0,
    },
}


@dataclass
class PlanConfig:
    plan_key: str
    label: str
    monthly_budget: float

    @property
    def daily_budget(self) -> float:
        return self.monthly_budget / 30

    @property
    def weekly_budget(self) -> float:
        return self.monthly_budget / 4.33


def load_plan_config() -> PlanConfig | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        obj = json.loads(CONFIG_FILE.read_text())
        key = obj.get("plan", "").lower()
        plan = PLANS.get(key)
        if plan:
            return PlanConfig(plan_key=key, label=plan["label"], monthly_budget=plan["monthly_budget"])
    except (json.JSONDecodeError, OSError):
        pass
    return None


@dataclass
class RateLimits:
    session_utilization: float       # 0.0–1.0
    session_reset_at: datetime
    weekly_utilization: float        # 0.0–1.0
    weekly_reset_at: datetime
    fetched_at: datetime

    @property
    def session_pct(self) -> float:
        return self.session_utilization * 100

    @property
    def weekly_pct(self) -> float:
        return self.weekly_utilization * 100


def load_rate_limits_cache() -> RateLimits | None:
    if not LIMITS_CACHE_FILE.exists():
        return None
    try:
        obj = json.loads(LIMITS_CACHE_FILE.read_text())
        return RateLimits(
            session_utilization=obj["session_utilization"],
            session_reset_at=datetime.fromisoformat(obj["session_reset_at"]),
            weekly_utilization=obj["weekly_utilization"],
            weekly_reset_at=datetime.fromisoformat(obj["weekly_reset_at"]),
            fetched_at=datetime.fromisoformat(obj["fetched_at"]),
        )
    except (KeyError, ValueError, OSError, json.JSONDecodeError):
        return None


def _get_auth_headers() -> dict[str, str] | None:
    """Returns auth headers, preferring Claude Code OAuth then ANTHROPIC_API_KEY."""
    try:
        creds = json.loads(CREDENTIALS_FILE.read_text())
        token = creds["claudeAiOauth"]["accessToken"]
        return {"Authorization": f"Bearer {token}"}
    except (OSError, KeyError, json.JSONDecodeError):
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return {"x-api-key": api_key}

    return None


def fetch_rate_limits() -> RateLimits | None:
    """Makes a minimal API call (Haiku, 1 token) to get real rate limit headers from Anthropic."""
    auth = _get_auth_headers()
    if auth is None:
        return None

    body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "x"}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            **auth,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        headers = {k.lower(): v for k, v in e.headers.items()}
    except OSError:
        return None

    try:
        s_util = float(headers.get("anthropic-ratelimit-unified-5h-utilization", 0))
        s_reset = datetime.fromtimestamp(int(headers["anthropic-ratelimit-unified-5h-reset"]), tz=timezone.utc)
        w_util = float(headers.get("anthropic-ratelimit-unified-7d-utilization", 0))
        w_reset = datetime.fromtimestamp(int(headers["anthropic-ratelimit-unified-7d-reset"]), tz=timezone.utc)
    except (KeyError, ValueError):
        return None

    now = datetime.now(tz=timezone.utc)
    limits = RateLimits(
        session_utilization=s_util,
        session_reset_at=s_reset,
        weekly_utilization=w_util,
        weekly_reset_at=w_reset,
        fetched_at=now,
    )
    try:
        LIMITS_CACHE_FILE.write_text(json.dumps({
            "session_utilization": s_util,
            "session_reset_at": s_reset.isoformat(),
            "weekly_utilization": w_util,
            "weekly_reset_at": w_reset.isoformat(),
            "fetched_at": now.isoformat(),
        }))
    except OSError:
        pass
    return limits


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


def today_totals(records: list[UsageRecord]) -> Totals:
    today = datetime.now(tz=timezone.utc).astimezone().date()
    t = Totals()
    for r in records:
        if r.timestamp.astimezone().date() == today:
            t.add(r)
    return t


def week_totals(records: list[UsageRecord]) -> Totals:
    today = datetime.now(tz=timezone.utc).astimezone().date()
    week_start = today - timedelta(days=today.weekday())
    t = Totals()
    for r in records:
        if r.timestamp.astimezone().date() >= week_start:
            t.add(r)
    return t


def window_totals(records: list[UsageRecord], start: datetime, end: datetime) -> Totals:
    t = Totals()
    for r in records:
        if start <= r.timestamp <= end:
            t.add(r)
    return t


def by_day(records: list[UsageRecord]) -> dict[date, Totals]:
    result: dict[date, Totals] = defaultdict(Totals)
    for r in records:
        day = r.timestamp.astimezone().date()
        result[day].add(r)
    return dict(sorted(result.items()))


def by_week(records: list[UsageRecord]) -> dict[date, Totals]:
    """Returns totals keyed by the Monday of each week."""
    result: dict[date, Totals] = defaultdict(Totals)
    for r in records:
        day = r.timestamp.astimezone().date()
        monday = day - timedelta(days=day.weekday())
        result[monday].add(r)
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
