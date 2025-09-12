TASK: Resume from the last checkpoint file. Do not change any app code.

DO:
- Read `.claude/state/SESSION_SAVE.md`.
- Print a **RESUME SNAPSHOT** with:
  • REPO + BRANCH
  • CURRENT FOCUS (verbatim)
  • DONE SINCE LAST CHECKPOINT (condensed to 3 bullets)
  • OPEN ITEMS (ordered)
  • DECISIONS/ASSUMPTIONS (bulleted)
  • HANDOFF NEXT-STEP (verbatim)
- Then propose a tiny “NEXT TICKET” (single task, ≤3 bullet DO, ≤2 bullet ACCEPTANCE), and wait.

DON’T:
- Don’t run shell commands or network calls
- Don’t search for secrets
- Don’t modify code

ACCEPTANCE:
- I see the RESUME SNAPSHOT and a one-ticket proposal, and you stop.