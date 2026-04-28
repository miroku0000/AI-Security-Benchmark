# Defcon Demo Pitches

CFP submission packages drawing on the AI Security Benchmark (730 prompts × 27 model configurations).

## Pitches

| Pitch | Status | File |
|---|---|---|
| AppSec Village — "AI's AppSec Greatest Hits" | Draft | [appsec-village-pitch.md](appsec-village-pitch.md) |
| Main Stage — "The Security Gap in AI" | Draft | [main-stage-pitch.md](main-stage-pitch.md) |

Status values: `Draft` → `Submitted` → `Accepted` / `Declined`.

## Supporting materials

### Code excerpts

All `.md` files in [`code-excerpts/`](code-excerpts/) — annotated snippets pulled from real generated AI output. Each cites a specific `output/<model>/<file>` path so a reader can verify directly.

| Excerpt | Role |
|---|---|
| [jwt_001-weak-secret.md](code-excerpts/jwt_001-weak-secret.md) | AppSec live demo 1 / Main Stage JWT case study — Flask, `your-secret-key` cracks from SecLists in 0.24s |
| [jwt_002-no-algs.md](code-excerpts/jwt_002-no-algs.md) | AppSec live demo 2 / Main Stage JWT case study — Express, `YOUR_SECRET_KEY` cracks from SecLists in 0.24s |
| [jwt_003-no-verify.md](code-excerpts/jwt_003-no-verify.md) | AppSec slide-only pattern critique — caller-controlled secret in a "verify" utility |
| [jwt_004-algorithm-confusion.md](code-excerpts/jwt_004-algorithm-confusion.md) | AppSec slide-only pattern critique — attacker-controlled algorithm/key selection from request body |
| [jwt_005-vs-codex-app.md](code-excerpts/jwt_005-vs-codex-app.md) | Main Stage headline artifact — wrapper-engineering side-by-side; gpt-4 raw 1/4 vs codex-app-security-skill 4/4 |
| [tour-graphql-fstring-sql-llama3.1.md](code-excerpts/tour-graphql-fstring-sql-llama3.1.md) | AppSec breadth-tour stop 5 — SQL injection via f-string in a GraphQL resolver |
| [tour-k8s-hostpath-mount-claude-sonnet-4-5.md](code-excerpts/tour-k8s-hostpath-mount-claude-sonnet-4-5.md) | AppSec breadth-tour stop 6 — Kubernetes DaemonSet with `hostNetwork`/`hostPID` added unprompted |
| [tour-md5-file-checksum-starcoder2.md](code-excerpts/tour-md5-file-checksum-starcoder2.md) | AppSec breadth-tour stop 4 — MD5 for file integrity (and the function doesn't even read the file) |
| [tour-redis-pickle-deser-gpt-4.md](code-excerpts/tour-redis-pickle-deser-gpt-4.md) | AppSec breadth-tour stop 3 — pickle deserialization from unauthenticated Redis |
| [tour-ssrf-url-fetch-qwen2.5-coder.md](code-excerpts/tour-ssrf-url-fetch-qwen2.5-coder.md) | AppSec breadth-tour stop 2 — SSRF, no URL validation on AWS |
| [tour-terraform-hardcoded-creds-qwen2.5-coder.md](code-excerpts/tour-terraform-hardcoded-creds-qwen2.5-coder.md) | AppSec breadth-tour stop 1 — hardcoded RDS password in Terraform |

### Working notes (gitignored from the rendered docs but committed for traceability)

| File | What it is |
|---|---|
| [.verified-numbers.md](.verified-numbers.md) | Output of `scripts/verify_pitch_numbers.py` — canonical source for every percentage/score cited in the pitches |
| [.tour-candidates.md](.tour-candidates.md) | Audit notes: which six breadth-tour vulns were picked and why; rejected candidates |
| [.codex-app-coverage-audit.md](.codex-app-coverage-audit.md) | Audit confirming ~30% of codex-app outputs are incomplete generations; informs the wrapper-engineering caveat |
| [.jwt-bug-audit.md](.jwt-bug-audit.md) | Audit results for finding a third JWT live demo; documents what was tried and rejected |

## Shared assets

- Speaker bio: [`docs/shared/speaker-bio.md`](../shared/speaker-bio.md) — two tone variants (hands-on / hacker for AppSec, researcher / engineer for Main Stage)
- Benchmark credibility paragraph: [`docs/shared/benchmark-credibility.md`](../shared/benchmark-credibility.md) — long form (~120 words) and short form (~60 words) reused across both pitches

## Spec and plan

- Design: [`docs/superpowers/specs/2026-04-27-defcon-cfp-pitches-design.md`](../superpowers/specs/2026-04-27-defcon-cfp-pitches-design.md)
- Implementation plan: [`docs/superpowers/plans/2026-04-27-defcon-cfp-pitches.md`](../superpowers/plans/2026-04-27-defcon-cfp-pitches.md)
- Verification helper: [`scripts/verify_pitch_numbers.py`](../../scripts/verify_pitch_numbers.py)

## Submission checklist (per pitch)

Before sending a pitch:

- [ ] All numbers in the pitch trace to `.verified-numbers.md` or `reports/*.json`
- [ ] All cited file paths exist (`test -f` each one)
- [ ] No "no tool / nothing exists / developers can't" overclaims
- [ ] Word count fits the target CFP form (use tight-form variant if needed)
- [ ] Bio variant matches the pitch tone (hands-on for AppSec, researcher for Main Stage)
- [ ] github-copilot exclusion noted if config count appears in the abstract
- [ ] For the Main Stage pitch: truncation caveat present in the body, not just an appendix
