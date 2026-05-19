# T059 — main.yml + release.yml CI workflows (image push to GHCR)

**Status:** Not started
**Phase:** 13 — Release prep
**Estimated session length:** 1.5 hr
**Depends on:** T008
**Blocks:** T060
**Maps to:** `deployment.md` "CI/CD Detail" → `main.yml` + `release.yml`.

---

## Objective

Add two GitHub Actions workflows: `main.yml` pushes both Docker images to GHCR on every push to `main` (tags `:edge` and `:sha-<short>`), `release.yml` re-tags images as `:X.Y.Z` and `:latest` when a Git tag `vX.Y.Z` is pushed.

## Files to create

- `.github/workflows/main.yml`
- `.github/workflows/release.yml`

## Steps

1. `main.yml` — triggered on push to `main`:
   - Run the PR pipeline (lint, test, build).
   - Build + push both images to `ghcr.io/harlequin-technologies/krelix-control` and `.../krelix-agent` with tags `:edge` and `:sha-<short>`.
   - Auth via `${{ secrets.GITHUB_TOKEN }}` (default Actions token, has `packages: write` for the repo's GHCR namespace).
   - Use `docker/login-action@v3`, `docker/build-push-action@v6`, `docker/metadata-action@v5`.
2. `release.yml` — triggered on tag push `v*.*.*`:
   - Re-builds (or pulls + re-tags) the images with the version tag and `:latest`.
   - Creates a GitHub Release with the CHANGELOG entry for that version.
3. Document the release flow in CONTRIBUTING.md: bump version in `pyproject.toml`, update CHANGELOG, tag `vX.Y.Z`, push.

## Acceptance Criteria

- [ ] Pushing to `main` results in two GHCR images tagged `:edge` and `:sha-<commit>`.
- [ ] Tagging `v1.0.0` results in both images tagged `:1.0.0` and `:latest`, plus a GitHub Release.
- [ ] No manual operator intervention required for either flow.
- [ ] Image-pull is verified to work from a separate test VM (`docker pull ghcr.io/harlequin-technologies/krelix-control:latest`).

## Out of Scope

- Multi-arch builds (arm64) — not v1 priority; amd64 only.
- Signed images / Sigstore / SBOM — backlog.
- Auto-release-notes generation — operator writes the CHANGELOG manually.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
