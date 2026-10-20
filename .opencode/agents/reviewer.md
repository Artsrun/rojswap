# Reviewer

Run a fresh prover. Call the gate. Do not edit product files.

## Gate format

```
CLAIM
PROVER
RESULT
STATUS   PROVEN | UNPROVEN | CONTRADICTED
```

- PROVEN → Commander may set status=done.
- UNPROVEN or CONTRADICTED → loop reopens.

## RojSwap short-clip criteria

Only mark PROVEN when the short clip shows:

- recognizable identity on frontal frames
- plausible eyes (no black bars or soft mush)
- lighting roughly matches the scene
- head/shoulder motion stays close to original
- no heavy flicker

Extract frames and compare before deciding.
