#!/usr/bin/env python3
"""
water_usage.py — Estimate the water footprint of your Claude Code token usage.

Reads Claude Code's local session transcripts (~/.claude/projects/**/*.jsonl),
sums tokens per model over the last N days, and multiplies by rough
energy-per-token and water-per-kWh estimates drawn from published LLM
inference research (NOT vendor-confirmed figures — see NOTES below).

Usage:
    python3 water_usage.py --days 30
    python3 water_usage.py --days 7 --json report.json
    python3 water_usage.py --days 30 --projects-dir /custom/path

NOTES ON ACCURACY (read this before trusting the number):
  - Anthropic does not publish per-token energy or water figures for Claude
    models. The ENERGY_PER_1K_TOKENS_KWH values below are order-of-magnitude
    estimates extrapolated from public research on comparably-sized open
    models (e.g. Llama-3-70B-class inference energy per request), scaled by
    a rough small/medium/large multiplier per Claude model tier.
  - WATER_INTENSITY_L_PER_KWH varies enormously by which data center region
    and cooling design is actually used (evaporative cooling vs. closed-loop
    vs. air cooling can differ by 10x+), and by whether you count only
    on-site cooling water or also the water used to generate the electricity
    (research suggests the latter roughly triples typical estimates).
  - Treat the output as a rough order-of-magnitude estimate, not a precise
    footprint. Edit the constants below if better data becomes available or
    you want to model a specific data center/region.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Rough energy estimate: kWh per 1,000 tokens (input + output combined) ---
# Baseline derived from published medium-request energy figures for
# comparably sized open models (~0.010-0.016 kWh per ~1,200-1,400 token
# request => roughly 0.007-0.011 kWh per 1,000 tokens for large models).
# Multipliers below scale that baseline down/up per Claude size tier.
# EDIT THESE if you have better information.
BASELINE_KWH_PER_1K_TOKENS = 0.009

MODEL_TIER_MULTIPLIER = {
    "haiku": 0.3,    # smaller model, cheaper/faster inference
    "sonnet": 1.0,   # baseline mid-size tier
    "opus": 1.8,     # larger model
    "mythos": 2.2,   # largest tier
    "fable": 2.2,
}

# Liters of water per kWh of electricity (covers direct cooling + a share of
# electricity-generation water). Published estimates range roughly 1.8-4.35
# L/kWh depending on region/methodology; this uses a mid conservative value.
WATER_INTENSITY_L_PER_KWH = 2.5


def tier_multiplier_for_model(model_name: str) -> float:
    name = model_name.lower()
    for key, mult in MODEL_TIER_MULTIPLIER.items():
        if key in name:
            return mult
    return 1.0  # unknown model: assume baseline mid-tier


def find_transcript_files(projects_dir: Path):
    if not projects_dir.exists():
        return []
    return list(projects_dir.rglob("*.jsonl"))


def parse_timestamp(raw: str):
    try:
        # Claude Code timestamps are ISO 8601, typically with a trailing Z
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def collect_usage(projects_dir: Path, since: datetime):
    """Returns dict: model -> {'input': int, 'output': int, 'cache_read': int, 'cache_write': int}"""
    usage = defaultdict(lambda: defaultdict(int))
    files = find_transcript_files(projects_dir)

    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    message = record.get("message")
                    if not isinstance(message, dict):
                        continue

                    ts_raw = record.get("timestamp") or message.get("timestamp")
                    ts = parse_timestamp(ts_raw) if ts_raw else None
                    if ts is None or ts < since:
                        continue

                    model = message.get("model")
                    tok = message.get("usage")
                    if not model or not isinstance(tok, dict):
                        continue

                    usage[model]["input"] += tok.get("input_tokens", 0) or 0
                    usage[model]["output"] += tok.get("output_tokens", 0) or 0
                    usage[model]["cache_read"] += tok.get("cache_read_input_tokens", 0) or 0
                    usage[model]["cache_write"] += tok.get("cache_creation_input_tokens", 0) or 0
        except OSError:
            continue

    return usage


def estimate_water(usage: dict):
    """Returns dict: model -> {tokens, kwh, liters}, plus totals."""
    results = {}
    total_tokens = 0
    total_kwh = 0.0
    total_liters = 0.0

    for model, counts in usage.items():
        tokens = counts["input"] + counts["output"] + counts["cache_read"] + counts["cache_write"]
        mult = tier_multiplier_for_model(model)
        kwh = (tokens / 1000.0) * BASELINE_KWH_PER_1K_TOKENS * mult
        liters = kwh * WATER_INTENSITY_L_PER_KWH

        results[model] = {
            "tokens": tokens,
            "kwh": kwh,
            "liters": liters,
        }
        total_tokens += tokens
        total_kwh += kwh
        total_liters += liters

    return results, total_tokens, total_kwh, total_liters


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=30, help="Look back this many days (default: 30)")
    parser.add_argument(
        "--projects-dir",
        type=str,
        default=str(Path.home() / ".claude" / "projects"),
        help="Path to Claude Code's projects directory (default: ~/.claude/projects)",
    )
    parser.add_argument("--json", type=str, default=None, help="Optional path to also write a JSON report")
    args = parser.parse_args()

    projects_dir = Path(args.projects_dir)
    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    usage = collect_usage(projects_dir, since)

    if not usage:
        print(f"No Claude Code usage found in {projects_dir} for the last {args.days} day(s).")
        print("(Check --projects-dir if your Claude Code data lives somewhere non-default.)")
        sys.exit(0)

    per_model, total_tokens, total_kwh, total_liters = estimate_water(usage)

    liters_display = f"{total_liters:,.0f}" if total_liters >= 10 else f"{total_liters:,.3f}"
    print(f"\nYou used {liters_display} liters of water.")
    print(f"\nClaude Code usage — last {args.days} day(s)")
    print(f"Scanned: {projects_dir}\n")
    print(f"{'Model':<30} {'Tokens':>14} {'Est. kWh':>12} {'Est. Liters':>14}")
    print("-" * 72)
    for model, vals in sorted(per_model.items(), key=lambda kv: -kv[1]["tokens"]):
        print(f"{model:<30} {vals['tokens']:>14,} {vals['kwh']:>12.4f} {vals['liters']:>14.3f}")
    print("-" * 72)
    print(f"{'TOTAL':<30} {total_tokens:>14,} {total_kwh:>12.4f} {total_liters:>14.3f}")

    print(
        "\nNote: these are rough order-of-magnitude estimates based on published\n"
        "research for comparably-sized models, not figures confirmed by Anthropic.\n"
        "Actual water use depends heavily on data center location, cooling design,\n"
        "and batching efficiency at the time your requests ran. See script header\n"
        "for the assumptions and how to adjust them."
    )

    if args.json:
        report = {
            "days": args.days,
            "since_utc": since.isoformat(),
            "projects_dir": str(projects_dir),
            "assumptions": {
                "baseline_kwh_per_1k_tokens": BASELINE_KWH_PER_1K_TOKENS,
                "model_tier_multiplier": MODEL_TIER_MULTIPLIER,
                "water_intensity_l_per_kwh": WATER_INTENSITY_L_PER_KWH,
            },
            "per_model": per_model,
            "totals": {
                "tokens": total_tokens,
                "kwh": total_kwh,
                "liters": total_liters,
            },
        }
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report written to {args.json}")


if __name__ == "__main__":
    main()