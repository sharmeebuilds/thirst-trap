---
description: Estimate the water footprint of your Claude Code token usage
argument-hint: [days]
---
Run the water usage estimator script using the Bash tool with this exact command (default to 30 days if no argument was given):

python3 ${CLAUDE_PLUGIN_ROOT}/water_usage.py --days ${ARGUMENTS:-30}

Then show me its full output as-is, without summarizing or altering the numbers.
