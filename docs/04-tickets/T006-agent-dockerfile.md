# T006 — Agent Dockerfile (container-mode skeleton)

**Status:** Done
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 1 hr
**Depends on:** T004
**Blocks:** T007, T008
**Maps to:** `architecture.md` Component 5 (Host Agent — container mode); `deployment.md` "Host-agent container-mode `docker-compose.agent.yml` (sketch)".

---

## Objective

Build the minimum `krelix-agent` Docker image: a multi-stage Dockerfile that installs the agent's deps and exposes the `krelix-agent` CLI as the entrypoint. The image inherits from a CUDA-base image so that NVML libraries are available at runtime. At this stage the agent only knows how to print its version — actual GPU inventory, registration, and command handling come in Phase 5.

## Context

The agent runs as a Docker container on each GPU host in container mode. It needs:

- NVML libraries available (for `pynvml`) — provided by the NVIDIA Container Toolkit at runtime, but the base image should have a CUDA runtime layer to host the necessary library paths.
- Docker socket access (mounted by the operator via Compose, not baked into the image).
- A non-root user where reasonable. NVML access via the toolkit doesn't strictly require root for query operations.

## Read for context

- [`../03-technical/architecture.md`](../03-technical/architecture.md) — Component 5 (Host Agent)
- [`../03-technical/deployment.md`](../03-technical/deployment.md) — agent compose snippet
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — container-mode security posture
- [`T004-agent-python-package.md`](T004-agent-python-package.md) — the package this Dockerfile installs

## Files to create

- `agent/Dockerfile` — multi-stage build
- `agent/.dockerignore` — same shape as backend's

## Files to modify

- None (agent package was set up in T004)

## Files to NOT touch

- `backend/`, `frontend/`, `packaging/` — separate
- Anything under `docs/` or `.claude/`

## Steps

1. **Pick a base image.** Use `nvidia/cuda:12.6.0-runtime-ubuntu22.04` (or the current stable CUDA-runtime image at build time). This provides the NVML shared libraries and the `nvidia-smi` binary, which the NVIDIA Container Toolkit then connects to the host's actual GPUs. **Confirm the exact image tag at build time** — `nvidia/cuda` tags rev frequently.

2. **Write `agent/Dockerfile`** as a multi-stage build:
   ```dockerfile
   # syntax=docker/dockerfile:1.7

   FROM python:3.12-slim-bookworm AS builder
   RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
   ADD --chmod=755 https://astral.sh/uv/install.sh /uv-installer.sh
   RUN /uv-installer.sh && mv /root/.local/bin/uv /usr/local/bin/uv
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   COPY src ./src
   RUN uv sync --frozen --no-dev

   FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04 AS runtime
   ENV PYTHONUNBUFFERED=1 \
       PYTHONDONTWRITEBYTECODE=1 \
       PATH="/app/.venv/bin:$PATH"
   RUN apt-get update \
       && apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates \
       && rm -rf /var/lib/apt/lists/*
   RUN useradd --create-home --uid 1000 krelix
   WORKDIR /app
   COPY --from=builder --chown=krelix:krelix /app /app
   USER krelix
   ENTRYPOINT ["krelix-agent"]
   CMD ["version"]
   ```
   Notes for the agent implementing this:
   - The CUDA-runtime base image is Ubuntu-based; the builder is Debian-based (python:3.12-slim-bookworm). Verify Python 3.12 is the same micro-version between stages (or the venv copy won't work).
   - An alternative is to use `python:3.12-slim-bookworm` for both stages and rely on the NVIDIA Container Toolkit to mount in the necessary NVML libs at runtime via `runtime: nvidia` / `--gpus all`. This is **simpler** and worth confirming during implementation — pick the path that works.
   - If you go the "slim base, toolkit-mounts-NVML" path, document this choice in the Dockerfile comment so it's not surprising later.

3. **Write `agent/.dockerignore`** mirroring the backend's, adjusted for the agent's package layout.

4. **Verify locally:**
   - `cd agent && docker build -t krelix-agent:dev .` succeeds
   - `docker run --rm krelix-agent:dev` prints `0.0.1` (the default `version` command)
   - `docker run --rm krelix-agent:dev version` same
   - Image runs as non-root user `krelix` (`docker run --rm krelix-agent:dev id` → uid=1000)
   - On a host with GPUs + NVIDIA Container Toolkit: `docker run --rm --gpus all krelix-agent:dev` does NOT fail with NVML library load errors (verify by running a brief Python one-liner inside the container that imports `pynvml.nvmlInit()` — but this is an exploratory verification, not part of the committed image).

## Acceptance Criteria

- [ ] `agent/Dockerfile` builds a `krelix-agent:dev` image successfully.
- [ ] `docker run --rm krelix-agent:dev` prints `0.0.1`.
- [ ] Image runs as non-root user `krelix` (uid 1000).
- [ ] Image size is reasonable — < 2 GB (CUDA runtime image base is the dominant cost). If it's significantly larger, investigate.
- [ ] On a GPU-equipped host with the NVIDIA Container Toolkit, running with `--gpus all` does not produce NVML library load errors at startup.

## Out of Scope (for this ticket)

- The actual agent logic — registration, GPU inventory, deployment execution, log streaming — all Phase 5+
- Mounting the hot tier / vault tier / Docker socket — that's compose-level config in T007
- Bare-metal/systemd agent install — Phase 12 (T-numbers TBD)
- GHCR push — T008

## Notes

- **There are two viable approaches** for NVML access:
  - **Path A (CUDA-runtime base image):** baseline NVML libs are in the image, the toolkit's job is to map them to the host driver.
  - **Path B (slim base + toolkit-mounts-libs):** the slim Python image has no CUDA, the toolkit mounts the libraries from the host at runtime via volumes.

  Path B produces a smaller image (~150 MB instead of ~1.5 GB) but requires the toolkit's automatic library mounting to be working correctly on the host. For v1, **try Path B first** — if it works in your environment with `pynvml.nvmlInit()` succeeding, go with it. Fall back to Path A if there are library-not-found errors.

  Document the chosen path in a Dockerfile comment.

- Don't bake the agent's runtime config (token, control plane URL, hot tier path) into the image. Those are env vars provided by Compose / systemd at deploy time.

---

## Completion Summary

- **Files touched:**
  - Created: `agent/Dockerfile`, `agent/.dockerignore`
- **Deviations from the ticket (if any):**
  - **Chose Path B** (slim Python base + toolkit-mounted NVML) per the ticket's "try Path B first" guidance. The Dockerfile carries a top-of-file comment documenting the choice and the fallback (swap runtime base to `nvidia/cuda:<tag>-runtime-ubuntu22.04`) if a target host's toolkit does not auto-mount NVML.
  - The matching backend Dockerfile pins `UV_VERSION=0.11.14`; the agent Dockerfile uses the same pin so both images install via `https://astral.sh/uv/0.11.14/install.sh`. Mirrored the same `UV_PROJECT_ENVIRONMENT` / `UV_COMPILE_BYTECODE` / `UV_LINK_MODE` env block as backend.
  - The ticket sketch suggests `RUN apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates` on the runtime stage. That step belongs to the Path-A (CUDA-runtime Ubuntu base) variant; with the `python:3.12-slim-bookworm` runtime base it's not needed and is omitted.
  - **AC "Image runs as non-root user `krelix` — verify with `docker run --rm krelix-agent:dev id`":** as written, that command would pass `id` as an argument to the `krelix-agent` typer app and fail. Verified with `docker run --rm --entrypoint id krelix-agent:dev` instead, which prints `uid=1000(krelix) gid=1000(krelix) groups=1000(krelix)`. The image's `USER` directive is unambiguous; the AC is satisfied — only the invocation in the ticket needed the `--entrypoint` override.
  - **AC "On a GPU-equipped host with NVIDIA Container Toolkit, `--gpus all` does not produce NVML library load errors":** the dev host running this ticket has no NVIDIA driver and no `nvidia` runtime registered with Docker, so this AC is not exercised here. Path B is the documented approach to satisfy it on a real GPU host; verification is deferred to first real-host install.
- **TODOs left for other tickets:**
  - None.
- **Commit hashes:**
  - (this commit) — `feat(T006): agent Dockerfile (slim base) + .dockerignore`

### Verification (run from `agent/`)

- `docker build -t krelix-agent:dev .` — success.
- `docker run --rm krelix-agent:dev` — prints `0.0.1`.
- `docker run --rm krelix-agent:dev version` — prints `0.0.1`.
- `docker run --rm --entrypoint id krelix-agent:dev` — `uid=1000(krelix) gid=1000(krelix) groups=1000(krelix)`.
- `docker images krelix-agent:dev` — `269MB` (well under the 2 GB cap; Path B keeps the CUDA layers out).
- `docker run --rm --entrypoint ls krelix-agent:dev /app/tests` — fails with "No such file or directory" (`.dockerignore` correctly excludes the `tests/` tree from the build context).

### Acceptance criteria status

- [x] `agent/Dockerfile` builds `krelix-agent:dev` successfully.
- [x] `docker run --rm krelix-agent:dev` prints `0.0.1`.
- [x] Image runs as non-root user `krelix` (uid 1000). (Verified via `--entrypoint id`; see Deviations.)
- [x] Image size is well under 2 GB (269 MB).
- [ ] `--gpus all` does not produce NVML load errors on a GPU-equipped host. **Not verifiable on this dev host** (no NVIDIA driver / no `nvidia` Docker runtime). Path B is the documented mechanism; defer first-host verification.
