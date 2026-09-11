# thirst-trap 💧

*You might forget to drink your water - but you definitely made Claude drink some.*

A "thirst trap" usually means a photo posted to get attention. This one's a trap in the literal sense: it shows you how much water your Claude Code usage is estimated to have evaporated at a data center, cooling the GPUs that answered your prompts.

`thirst-trap` reads your local Claude Code session logs, sums up the tokens you've used per model over a given time window, and converts that into a rough estimate of energy and water consumption.

> **Disclaimer:** This tool is for awareness purposes only. It does not imply any confirmed, official, or precise figure for Claude's actual water or energy usage - see the accuracy section below before drawing any conclusions from the numbers.

## Getting started

Clone the repo and run it straight away - no install step needed beyond having Python 3.8+ on your machine:

```bash
git clone https://github.com/sharmeebuilds/thirst-trap.git
cd thirst-trap
python3 water_usage.py --days 30
```

That's it - it reads your existing `~/.claude/projects/` logs and prints the report. If you want it available as a `/water-usage` slash command inside Claude Code itself instead of running it manually, see [Using it as a Claude Code slash command](#using-it-as-a-claude-code-slash-command) below.

## What it actually does

- **Real data:** Claude Code writes a complete local transcript of every session to `~/.claude/projects/*.jsonl`, including per-message token counts and the model used. `thirst-trap` reads those files directly - no API key, no network calls, nothing leaves your machine.
- **Estimated data:** it multiplies those token counts by rough energy-per-token and water-per-kWh conversion factors, based on published LLM inference research, to produce a liters-of-water estimate.

## ⚠️ How accurate is this, really?

**Short answer: the token counts are accurate. The water number is a rough ORDER-OF-MAGNITUDE estimate, not a measurement.** Treat it as a "this is the right ballpark" tool, not a precise footprint calculator. A few reasons why:

1. **The energy-per-token baseline isn't Claude-specific.** Anthropic hasn't published per-token energy figures for any Claude model. The baseline here (`0.009 kWh per 1,000 tokens`) is extrapolated from published research on comparably-sized open models (Llama-3-70B, Falcon-180B class) running on older hardware. Claude's actual hardware, architecture, and inference optimizations aren't public, so this could be off by a wide margin in either direction.
2. **Per-model multipliers are guesses.** The Haiku/Sonnet/Opus/Mythos/Fable scaling factors in the script reflect a plausible "smaller model uses less energy" assumption - they aren't derived from any confirmed data.
3. **Cached tokens are currently over-counted.** `cache_read` and `cache_creation` tokens are counted at full weight, but cache reads are computationally far cheaper than fresh input tokens (priced at ~0.1x on the API for exactly that reason). If a lot of your usage is cache hits - common in coding workflows that repeatedly reload the same file context - this script is likely **overestimating** your real footprint. This is the most impactful known limitation and a good first contribution if you want to help fix it.
4. **Water intensity varies a lot by region and cooling design.** The `2.5 L/kWh` constant is a rough midpoint; real values can differ by 10x+ depending on whether a data center uses evaporative cooling, closed-loop cooling, or air cooling, and whether you count only on-site cooling water or also the water used to generate the electricity.
5. **No batching model.** The underlying research measured single, unbatched requests. Production inference is batched, which reduces real per-token energy meaningfully - this script doesn't account for that.

All of these assumptions are exposed as constants at the top of `water_usage.py` (`BASELINE_KWH_PER_1K_TOKENS`, `MODEL_TIER_MULTIPLIER`, `WATER_INTENSITY_L_PER_KWH`) so you can tune them as better data emerges.

## Scope

Only counts usage from **Claude Code** sessions (terminal, IDE, desktop code tab) - anything logged to `~/.claude/projects/`. It does **not** see usage from the regular claude.ai web/app chat interface, which isn't logged locally.

## Requirements

- Python 3.8+
- No third-party dependencies (standard library only)

## Usage

```bash
# Last 30 days (default)
python3 water_usage.py

# Custom time window
python3 water_usage.py --days 7

# Save a machine-readable report too
python3 water_usage.py --days 30 --json report.json

# Point at a non-default Claude Code projects directory
python3 water_usage.py --projects-dir /path/to/.claude/projects
```

Example output:

```
You used 58,138 liters of water.

Claude Code usage — last 30 day(s)
Scanned: /Users/you/.claude/projects

Model                                  Tokens     Est. kWh    Est. Liters
------------------------------------------------------------------------
claude-sonnet-5                 2,576,586,801  23189.2812      57973.203
claude-opus-4-7                     4,058,723     65.7513        164.378
------------------------------------------------------------------------
TOTAL                            2,580,645,524  23255.0325      58137.581
```

## Using it as a Claude Code slash command

`thirst-trap` ships as a Claude Code plugin (see `.claude-plugin/plugin.json` and `commands/water-usage.md`), so you can just type `/water-usage 30` inside any Claude Code session once it's installed.

**Quickest way - drop it in your skills directory:**

```bash
git clone https://github.com/sharmeebuilds/thirst-trap.git ~/.claude/skills/thirst-trap
```

Claude Code auto-loads any plugin folder under `~/.claude/skills/` as `<name>@skills-dir` - start a new session and it'll show up as `thirst-trap@skills-dir` in `claude plugin list`.

**Via a marketplace:** if you're distributing this through a Claude Code plugin marketplace instead, add the marketplace with `claude plugin marketplace add <source>` and then `claude plugin install thirst-trap@<marketplace>`.

Either way, start a new Claude Code session and run `/water-usage 30`.

## Tuning the estimate

Edit the constants at the top of `water_usage.py`:

```python
BASELINE_KWH_PER_1K_TOKENS = 0.009
MODEL_TIER_MULTIPLIER = {
    "haiku": 0.3,
    "sonnet": 1.0,
    "opus": 1.8,
    "mythos": 2.2,
    "fable": 2.2,
}
WATER_INTENSITY_L_PER_KWH = 2.5
```

If you have better data - a specific data center's WUE, a corrected cache-token weighting, updated inference-energy research - PRs welcome.

## Contributing

Known good first issues:

- [ ] Discount `cache_read`/`cache_creation` tokens (e.g. ~0.1x weight) to match how cache hits are priced on the API, reducing the current overestimation
- [ ] Add a `--region` flag with a few preset water-intensity values
- [ ] Add support for scanning Claude Code subagent logs separately

## License

MIT - see [LICENSE](LICENSE).

## Disclaimer

This is an independent, unofficial estimation tool. It is not affiliated with or endorsed by Anthropic, and the water/energy figures it produces are not confirmed by Anthropic. Token counts come from your own local Claude Code logs; everything downstream of that is a rough estimate - see the accuracy section above before drawing conclusions from the numbers.