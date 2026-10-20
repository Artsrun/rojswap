# RojSwap Agents

Four-role OpenCode Lite Bridge loop for the RojSwap pipeline.

| Role | File | Job |
|------|------|-----|
| Commander | `commander.md` | Own the loop, delegate, stop |
| Planner | `planner.md` | Break objective into file-scoped steps + prover |
| Worker | `worker.md` | Execute one step, no done-claim |
| Reviewer | `reviewer.md` | Fresh prover + mission_gate |

State lives in `.opencode/mission-loop.json`.  
No role may mark the mission done without a PROVEN gate.
