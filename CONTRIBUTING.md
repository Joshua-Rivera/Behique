# Contributing

## Branches
- `main` is always releasable and protected (PR + passing `ci` checks required, no force-pushes).
- One branch per change, off `main`: `feat/<milestone>-<topic>`, `fix/<topic>`, `ci/<topic>`, `docs/<topic>`.
- One PR per branch, merged by squash after CI passes. Delete the branch after merge.

## Commits
Conventional Commits: `feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`.

## Before opening a PR
```
make lint
make test
make eval   # once the eval set exists
```

## Releases
SemVer tags (`v0.1.0`, ...). Pushing a tag triggers the release workflow.
