# Contributing

## Workflow

1. Pick up an issue from the board, assign yourself, move it to "In Progress"
2. Branch off `main`: `feature/<yourname>-<short-desc>`
3. Commit in small, logical chunks. Reference the issue number: `Add SQS consumer skeleton (#12)`
4. Open a PR into `main` when ready. Fill in the PR template — link the issue with `Closes #12` so it auto-closes on merge
5. At least one teammate reviews before merge. Don't self-merge except for trivial docs/config fixes
6. Delete the branch after merge

## Commit messages

Short imperative summary, issue number at the end if applicable:

```
Add role check middleware to recipe routes (#8)
```

## PR size

Keep PRs reviewable — one feature or fix per PR, not a week's worth of work bundled together. Large PRs don't get properly reviewed, they get rubber-stamped, and that's where the async pipeline's failure points hide.

## Before opening a PR

- [ ] Code runs locally against a test event / test DB
- [ ] No secrets or `.env` values committed
- [ ] Updated `/docs` if you changed the API contract or architecture
