# Contributing

## Branches (GitHub flow)

- `main` is always releasable and protected.
- Branch off `main`: `feat/<milestone>-<topic>`, `fix/<topic>`, `ci/<topic>`, `docs/<topic>`.
- One PR per branch, squash-merged after CI passes. Delete the branch after merge.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`.

## Before opening a PR

```sh
make lint
make test
make eval   # once the eval set exists
```

Fill in the PR template, including the eval delta when retrieval changes.

## Releases

SemVer tags (`v0.1.0`, …). Pushing a tag builds and publishes the Docker image.
