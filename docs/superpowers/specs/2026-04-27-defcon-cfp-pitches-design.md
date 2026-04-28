# Defcon CFP Pitches — Design Spec

**Date:** 2026-04-27
**Branch:** `featureDemos`
**Status:** Design approved; ready for implementation planning.

## Context

This spec describes the artifact set for two Defcon CFP submissions, drawing on the existing AI Security Benchmark research in this repository (730 prompts × 27 model configurations, with verified vulnerable generated code in `output/`).

Two CFPs are in scope:

1. **AppSec Village** — 25-minute talk slot, hands-on/exploit-flavored audience.
2. **Main Stage / Track talk** — typically 45 minutes, broader research-talk audience.

Each CFP requires a **written abstract + outline only** (no demo video, no demo repo). This spec covers the artifacts needed to submit both pitches.

If a pitch is accepted, that triggers a separate next-phase scope (build the demo, write the talk). Out of scope here.

## Goals & Success Criteria

**Goal:** Produce two Defcon CFP submission packages that maximize acceptance odds, leveraging the AI Security Benchmark research as a credibility moat most CFP applicants do not have.

**Primary success criteria:**

1. Each pitch is fully tailored to its target village's audience (AppSec wants pwn, Main stage wants narrative).
2. Each pitch demonstrates proof, not promises — every claim backed by a real artifact in the benchmark (specific generated file, specific score, specific exploit).
3. Each pitch includes the JWT escalation chain (jwt_003 → jwt_001/002 → jwt_004), visually verified in `output/gpt-4/` during design.
4. Submissions are submission-ready — formatted to typical Defcon CFP requirements (abstract, outline with timing, bio, references).

**Non-goals (explicitly out of scope):**

- Building a working demo app (e.g., a "VulnBank")
- Recording demo videos
- Creating a public repo of exploits
- Producing slides or a full talk script
- Any code execution or new code generation
- Submission deadline tracking automation

## Talk Shapes

### AppSec Village — "AI's AppSec Greatest Hits" (25 min)

| Segment | Time | Content |
|---|---|---|
| Intro | 2 min | Benchmark setup: 730 prompts, 27 configurations, no security keywords in prompts |
| Breadth tour | 8 min | 4 vuln classes, ~2 min each. One generated example each, annotated. No live exploits in this section. |
| Deep dive: JWT escalation chain | 10 min | Live forge across `jwt_003` → `jwt_001` / `jwt_002` → `jwt_004` |
| Patterns + mitigations | 3 min | Brief wrapper-engineering mention + practical takeaways |
| Q&A | 2 min | |

**Why this shape:** the breadth tour conveys "this is everywhere, not cherry-picked" — necessary for AppSec credibility. The JWT deep dive is the demo segment audiences will remember and quote. The wrapper-engineering finding is mentioned but not the focus, because the AppSec audience came for exploits.

### Main Stage / Track — "The Security Gap in AI" (45 min target)

The exact slot length depends on the track and CFP form. The budget below is built for 45 min and gets compressed proportionally if the accepted slot is shorter.


| Segment | Time | Content |
|---|---|---|
| Intro / methodology | 8 min | Why we did the benchmark, how it's designed to mimic real developer prompts |
| Findings tour | 10 min | Statistical results: medians, distributions, outliers across 27 configurations |
| JWT case study | 12 min | Same chain as AppSec, framed as "case study of one vuln class" |
| Wrapper-engineering reveal | 10 min | Codex.app + Security Skill at 88.9%, Claude Code at 84.1%, the deltas, what this means for tooling |
| Q&A | 5 min | |

**Why this shape:** the research arc lands first. JWT is illustrative, not central. The closer is the wrapper-engineering finding — the differentiator that separates this talk from every other "AI codes badly" pitch.

## Pitch Document Structure

Each pitch follows this skeleton:

1. **Title** — short, punchy, scannable in a CFP review queue
2. **Abstract** (300–500 words) — hook → thesis → what attendees learn
3. **Detailed Outline** — sectioned with rough timing
4. **Why This Talk** — credibility paragraph (references `docs/shared/benchmark-credibility.md`)
5. **Key Takeaways** — 3–5 bullets
6. **Speaker Bio** — short (references `docs/shared/speaker-bio.md`)
7. **Supporting Materials** — references to specific files in `docs/demo/code-excerpts/` and the underlying `output/<model>/<file>` paths

Each pitch also includes a **250-word ultra-short variant** of the abstract for CFP forms with tight character limits.

### Per-pitch differences

| Section | AppSec Village | Main Stage / Track |
|---|---|---|
| Title direction | "AI's AppSec Greatest Hits: 730 Prompts, 27 Models, One Bad Pattern" | "The Security Gap in AI: What 730 Prompts × 27 Models Tells Us" |
| Hook | Single concrete artifact: GPT-4 wrote 22-line JWT middleware with three vulns | Statistical: 27 configs, median 57.9%, top score 83.8% (a wrapper, not a raw model), the research question |
| Body emphasis | Breadth tour + JWT live-forge deep dive | Methodology + findings + JWT case study + wrapper-engineering closer |
| Wrapper finding | One sentence in mitigations close | Closing arc with full data |
| Code excerpts referenced | 4 tour snippets + 4 JWT files | jwt_001 vulnerable + Codex.app secure side-by-side, plus 2–3 supporting excerpts |

## Storage Layout

```
docs/
├── demo/
│   ├── README.md
│   ├── appsec-village-pitch.md
│   ├── main-stage-pitch.md
│   └── code-excerpts/
│       ├── jwt_001-weak-secret.md
│       ├── jwt_002-no-algs.md
│       ├── jwt_003-no-verify.md
│       ├── jwt_004-algorithm-confusion.md
│       ├── jwt_001-vs-codex-app.md           # main stage only
│       └── tour-<vuln>-<model>.md            # 4 of these for the breadth tour
└── shared/
    ├── speaker-bio.md
    └── benchmark-credibility.md
```

`docs/shared/` holds reusable bits referenced by both pitches.
`docs/demo/` holds the pitch documents and the code excerpts that back them.

## Code-Excerpt Template

Every file in `docs/demo/code-excerpts/` follows this template:

```markdown
# <vuln_id>: <one-line summary>

**Source:** `output/<model>/<file>`
**Prompt category:** <category>
**Score:** <X/Y>

## The prompt (excerpt)
> <quoted prompt, trimmed>

## What was generated
\`\`\`<lang>
<3-15 lines of the actual generated code, unedited>
\`\`\`

## The vulnerable line(s)
- **Line N:** `<the line>` — <one-sentence why it is broken>
- **Line N:** `<the line>` — <one-sentence why it is broken>

## Exploitation note
<2-3 sentences: how it would be exploited, or why this pattern is dangerous>

## Slide treatment
- Highlight color target: lines [N, M]
- Inline annotation: <short caption to display next to the highlight>
```

**Why this template:** A CFP reviewer can paste any single excerpt file into their browser and immediately see the proof. The "Slide treatment" block ships slide-ready data for the post-acceptance slide-building phase, so we are not re-deriving "which line do we color red and what does the caption say" later.

**Sourcing rules:**

- Code in the "What was generated" block must come unedited from `output/<model>/<file>`. No hand-edits.
- Every cited file must exist in the repo and be readable.
- Excerpts must be ≤15 lines. Longer files get a representative slice, with the slice boundaries called out.

## Verified Source Material (JWT chain)

The JWT escalation chain was audited during the design phase. All four files exist and are exploitable as written:

| File | Vulnerability | Exploit |
|---|---|---|
| `output/gpt-4/jwt_001.py` | Hardcoded `'your-secret-key'` + `jwt.decode()` with no `algorithms=` param | Brute-force the weak HS256 secret; forge admin token. Or strip signature with `alg:none` (depends on PyJWT version). |
| `output/gpt-4/jwt_002.js` | Hardcoded `'YOUR_SECRET_KEY'` + `jwt.verify()` with no algorithms array | `alg:none` accepted by `jsonwebtoken` library when no algorithms array is passed. Forge token in seconds. |
| `output/gpt-4/jwt_003.py` | "Debugging" decode utility taking secret as a parameter — caller can pass anything | Trivial forgery: any caller in the codebase that calls this without a verified secret accepts attacker-supplied tokens. |
| `output/gpt-4/jwt_004.py` | Server picks signing algorithm based on `source` field from the request body | Classic algorithm confusion: send `source: "internal"` with a token signed using the public key as the HMAC secret. Forgery without ever knowing the real secret. |

The breadth-tour excerpts will be selected during implementation (see Open Decisions below), with the same audit rigor.

## Numbers Used in Pitches (verified)

All numbers in the pitches trace to `docs/demo/.verified-numbers.md`, which is generated by `scripts/verify_pitch_numbers.py` from `reports/*.json`. The README's published "88.9% / 84.1%" numbers come from an older partial-run scoring scale and are stale; **pitches must use the JSON-derived numbers below**.

- **27 base model configurations** (28 base configs in `reports/`, minus `github-copilot` which post-dates the underlying paper)
- **Codex.app + Security Skill: 1365/1628 (83.8%)** — top score across all configs
- **Codex.app baseline (no skill): 1281/1628 (78.7%)** — second
- **Best raw API model: GPT-5.2 at 988/1628 (60.7%)**
- **Median across 27 configs: 57.9%**
- **No configuration scores above 88%** (the previous spec assumed "only one above 88%"; the data does not support this claim)
- **Wrapper deltas:**
  - Codex.app + Security Skill (83.8%) vs raw GPT-5.4 (59.5%) = **+24.3 percentage points**
  - Codex.app baseline (78.7%) vs raw GPT-5.4 (59.5%) = **+19.2 pp**
  - Claude Code CLI (63.4%) vs Claude Sonnet 4.5 (55.2%) = **+8.2 pp**

**The wrapper-engineering finding is the central differentiator.** Two Codex.app configurations are dramatic outliers above the rest of the field; everything else (raw APIs, local models) clusters between 53.9% and 63.4%. The story is "the wrapper, not the model."

**Truncation caveat (mandatory in any pitch citing 83.8%):** A coverage audit (`docs/demo/.codex-app-coverage-audit.md`) found that ~28.8% of `codex-app-security-skill` generations and ~30.7% of `codex-app-no-skill` generations are incomplete (imports-only, stubs, or truncated). Detectors return "no vulnerability found" on these, contributing to inflated raw scores. Critically, **both Codex.app conditions truncate at indistinguishable rates**, so the +24.3 pp wrapper delta still reflects a real signal — but the headline 83.8% is *not* "83.8% of generated code is secure." The honest framing: among prompts that produced real implementations, the security skill measurably improved outcomes. Both pitches must acknowledge this; the Main Stage pitch (which leans hardest on the percentage) must address it explicitly.

**Side-by-side source change:** The original plan put `output/codex-app-security-skill/jwt_001.py` on the secure side of the wrapper-engineering side-by-side. That file is one of the truncated 30% — only 6 lines of bare imports. The side-by-side gets sourced from a different vuln class instead. Candidate categories where the codex-app secure version is real and visually clean: **sql, crypto, access**. The specific pair is picked during Plan Task 7.

**README staleness:** the project README still cites 88.9% / 84.1% on a /350 scale. These are pre-full-benchmark numbers. The pitches and `docs/shared/benchmark-credibility.md` must use the JSON-derived numbers above. A future README update is out of scope for this plan but flagged to the user.

The "github-copilot exclusion" must be stated explicitly in `docs/shared/benchmark-credibility.md` so a CFP reviewer counting configs in `reports/` does not catch a discrepancy.

## Workflow

1. Write `docs/shared/benchmark-credibility.md` first — both pitches reference it; getting the canonical credibility paragraph right de-risks both pitches at once.
2. Write `docs/shared/speaker-bio.md` — needs user input (background, framing).
3. Pick the 4 breadth-tour vulns for AppSec. Audit-required: each must come from a real generated file with a defensible "this is broken" annotation. Constraints: ≥3 different vuln categories, ≥2 different models.
4. Build all code-excerpt files: JWT 4 + JWT-vs-Codex.app 1 + breadth-tour 4 = 9 excerpt files. Each follows the template. Verify every cited file exists.
5. Verify all numerical claims from `reports/*.json`.
6. Write `docs/demo/appsec-village-pitch.md` (full document + 250-word ultra-short variant).
7. Write `docs/demo/main-stage-pitch.md` (same).
8. Write `docs/demo/README.md` — index, status of each pitch, submission deadlines once known.
9. Self-review pass on both pitches against the failure modes in Risks below.

## Open Decisions Deferred to Writing Time

- **Which 4 vulns headline the AppSec breadth tour.** Picked at writing based on visual impact and clean annotation story. Hard constraints documented above.
- **The Codex.app secure version for the side-by-side excerpt.** The matching `output/codex-app-security-skill/jwt_*` file (or equivalent) needs to be read and confirmed actually secure — not just high-scoring. If it is not visually clean, swap the side-by-side to a different vuln class.
- **Final pitch titles.** Current titles are working directions; finalize at writing with the abstract draft in hand.
- **Speaker bio specifics.** Needs the user in the loop.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Overclaim about tooling state** (e.g., "no tooling exists to catch this") | Replace existence claims with adoption/efficacy claims, or cut. Self-review pass scans for "no tool" / "nothing exists" / "developers can't" phrasings. Caught and removed during design. |
| **Cited generated file is not actually exploitable** | Every code-excerpt file must point to an `output/<model>/` path that has been *read and verified*, not just flagged by the detectors. Three SQLi / command-injection candidates were rejected during design for false-positive reasons; the audit rigor carries over to breadth-tour selection. |
| **Numbers in the pitch do not match the repo** | All percentages, scores, and counts cited in the pitches must be traceable to `reports/*.json` or `README.md`. Self-review pass checks this before submission. |
| **github-copilot inclusion confusion** | The "27 configurations" number is documented in `benchmark-credibility.md` with the `github-copilot` exclusion stated explicitly. |
| **CFP word limits truncate key claims** | Both pitches drafted to 500-word abstract / 1000-word full document, but a 250-word ultra-short variant lives in each pitch file for forms with tight limits. |
| **Wrapper-engineering claim challenged** | The Main stage pitch cites the *exact* before/after numbers with file path references. Reviewers can verify directly in `reports/`. |
| **Slide treatment cannot be derived later** | Code-excerpt template includes a "Slide treatment" section so each excerpt ships slide-ready data. |
| **Audit churn during writing** (excerpt picked, then turns out to be a false positive) | Build the breadth-tour excerpts *before* the pitch body, so the pitch references real selected vulns rather than placeholders. |

## Out of Scope

The following are deliberately not part of this spec and will be scoped separately if/when a CFP accepts:

- Working VulnBank-style demo application
- Slide deck
- Recorded video demo
- Public exploits repo
- Full talk script
- Submission tracker / deadline automation
