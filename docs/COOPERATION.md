# Cooperation protocol — Claude × Grok

Two agents, one repo, no shared chat. GitHub is the bus, the mission card is the memory.

## Roles

| Role | Default | Rule |
|------|---------|------|
| Planner / research | Grok | Proposes steps; every external claim (model, API, VRAM, cost) needs a link or a run |
| Worker | Claude | Implements one step on a branch; pastes prover output |
| Reviewer | **whoever did not author the step** | Re-runs the prover, calls the gate; never grades own work |
| Human gate | Jan | Merges PRs, says "go" between agents, owns any irreversible call |

## Flow

1. Read `.opencode/mission-loop.json` — not the other agent's transcript.
2. Take the next step whose `owner` is you and `status` is `todo`.
3. Branch: `claude/<step>` or `grok/<step>`. Touch only the step's `files`.
4. Run the step's `prover`. Paste the exact command and output into the PR and `recent_evidence`.
5. Set step `status` to `awaiting_review`, `reviewer` to the other agent. Open a PR into `main`.
6. Reviewer re-runs the prover and writes the gate in a PR comment:

   ```
   CLAIM     <what the step says it does>
   PROVER    <command re-run>
   RESULT    <output>
   STATUS    PROVEN | UNPROVEN | CONTRADICTED
   ```

7. Jan merges on PROVEN. UNPROVEN / CONTRADICTED reopens the step with the reason.

## Rules

- No prover output → UNPROVEN. "Should work" is not evidence.
- Visual results (swaps) need a frame grid in `eval/`, not adjectives. Score honestly; say "meme-grade" when it is.
- Untested ideas stay in `open_questions` or are marked `UNPROVEN` in docs.
- Never commit copyrighted target footage or real faces. `tests/short_clip/` media stays local (gitignored).
- One step per PR. Small diffs review faster.
