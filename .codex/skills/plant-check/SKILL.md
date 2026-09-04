---
name: plant-check
description: Validate Plant planning documents after creating or updating them. Do not use for ordinary implementation-only work.
---

# Plant check

Run the repository's checker after changing governed planning documents:

```bash
./plant check plans
```

Use `./plant --json check plans` only when another tool needs structured
output. Resolve every reported error before accepting the planning change.

For implementation context, follow the Current focus route in `plans/README.md`
instead; do not use the checker to discover the plan.
