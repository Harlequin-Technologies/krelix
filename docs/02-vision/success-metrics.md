# Success Metrics — Krelix

## Minimum Viable Definition

The single operator can register **any local Docker-host GPU endpoint** with Krelix (architecture handles 1..N endpoints; one endpoint is a special case of N), browse HuggingFace for a model from the Krelix UI, see a fit prediction for that endpoint, click "deploy," and have Krelix download the model and launch a vLLM container with appropriate config on the endpoint — auto-iterating on common config failures within a bounded retry budget — producing a working OpenAI-compatible inference URL that responds to a `curl` test. The full flow happens **without the operator opening a terminal on the GPU host** beyond initial endpoint setup.

**Canonical MVD demo:**

Deploy `Qwen2.5-14B-Instruct-AWQ` to the RTX A4000 endpoint (on `epyc-proxmox.dropthe8.com`) via vLLM in **≤ 30 minutes**, end-to-end, through the Krelix UI.

---

## Measurable Success Criteria for v1

Each criterion is observable. Where useful, the measurement method and concrete target are stated; binary criteria are marked Yes/No.

| # | Criterion | How it's measured | Target value |
|---|-----------|-------------------|--------------|
| 1 | **Time-to-endpoint** for first-time deploy of a new model | Wall-clock from the operator clicking "deploy" in the UI to the inference URL responding successfully to a standard chat-completions `curl`, for the canonical MVD demo (`Qwen2.5-14B-Instruct-AWQ` on the RTX A4000 via vLLM). Includes download time and any internal auto-iteration. | **≤ 30 minutes** |
| 2 | **Endpoint scale** | Number of distinct local Docker-host GPU endpoints simultaneously registered, operable (deployments succeed), and observable in Krelix. | **Up to 5 endpoints** working simultaneously |
| 3 | **Fit-prediction accuracy** | Krelix's pre-deploy prediction (`fits comfortably` / `needs CPU offload` / `won't fit`) compared against actual observed deployment outcome across a hand-curated set of ~20 model × endpoint combinations the operator personally verifies. | **≥ 90%** (95% ideal) |
| 4 | **Zero-terminal post-onboarding** | After a GPU endpoint is initially registered with Krelix, the operator can perform US-M-01 through US-M-09 — including diagnosing a failed deployment via logs — without opening any ssh session to the GPU host. | **Binary: Yes** |
| 5 | **Engine coverage** | The vLLM adapter is implemented end-to-end and validated against the canonical MVD demo. No other engine adapter required in v1. | **vLLM working: Yes** |
| 6 | **MVD demo passes** | The canonical MVD demo (criterion #1 specifics) is reproducible by the operator on demand, end-to-end, with no manual intervention beyond the UI clicks. | **Binary: Yes** |
| 7 | **Quietly-public release readiness** | Public GitHub repo (`Harlequin-Technologies/krelix`) contains the v1 code, a basic README, and install steps sufficient for another technically-capable multi-GPU homelab operator to install and reach criterion #6 on their own hardware (with their own model and endpoint substituted). | **Binary: Yes** (subjective verification: at least one independent technically-capable person can follow the README to a working deployment, even if recruitment of that person is deferred post-v1) |

---

## Anti-Metrics

Things we explicitly do **NOT** want to optimize for in v1, even though we could:

- **Number of supported engines.** One engine adapter (vLLM) done well is better than five half-broken adapters. Engine breadth is v2+ deliberately.
- **Number of UI screens or features.** v1 should feel small and tight. Resist adding screens for the sake of completeness.
- **User adoption count or velocity.** v1's primary user is the operator himself; broader adoption is an opportunistic side effect, not a v1 KPI. Counting users or chasing GitHub stars distracts from the actual goal.
- **Compatibility with arbitrary hardware.** Krelix v1 must work on the operator's own fleet (Proxmox + Docker hosts, the listed GPU mix). Working on other hardware is a happy side effect of building it cleanly, not a primary v1 goal.
- **Deployment time below the 30-minute target.** Once 30 minutes is consistently achievable for the canonical demo, do not invest in pushing it lower. Premature optimization here trades against scope completion.
- **Cloud-readiness signals.** Cloud is explicitly parked. Don't optimize the v1 design around speculative cloud requirements — that drags scope.
- **Polish for first-time-non-author users.** v1's release posture is "quietly public," not "first-class onboarding." Polish for new-user onboarding is a v1.x+ concern, not v1-ship.
