# Changelog

## [1.0.3] - 2026-05-09

### Features
- `--summary` flag: print a plain-text usage summary (all-time, today, this week, cache, rate limits) and exit — no TUI required
- `--json` flag: output the same data as machine-readable JSON and exit

## [1.0.2] - 2026-05-09

### Features
- Gate startup on `claude` CLI presence — exits with a clear error message if `claude` is not found in `PATH`

## [1.0.1] - 2026-05-09

### Chores
- `run.py` now routes through `main()` so `python3 run.py --version` / `-V` works correctly

## [1.0.0] - 2026-05-09

### Features
- `--version` / `-V` flag prints program name and version
- Centered modal popup on `r` and `l` with auto-dismiss; shows timestamp, today's token count/cost, and all-time request count on refresh; shows success/error on rate-limit fetch
- Daily and weekly usage bar charts (last 14 days / last 8 weeks)
- Recent sessions table sorted by last activity (last 20)
- Lifetime token totals with estimated cost (input, output, cache write/read)
- Live rate-limit fetch via Anthropic API (`l`); session and weekly utilisation bars with reset countdown
- Auto-refresh every 30 s; manual refresh with `r`

### Chores
- Split `app.py` into `components/` (one file per widget), `utils.py`, and `styles/app.tcss`
- Added `.idea/` to `.gitignore`
- Packaged as installable CLI (`pipx install .` → `claude-usage`)
- `.env` / `~/.claude_usage.env` support for `ANTHROPIC_API_KEY` and `CLAUDE_USAGE_REFRESH_INTERVAL`
