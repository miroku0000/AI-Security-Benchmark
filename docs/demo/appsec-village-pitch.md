# AppSec Village Pitch — "AI's AppSec Greatest Hits"

**Status:** Draft
**Target slot:** 25 minutes
**Working title:** AI's AppSec Greatest Hits: 730 Prompts, 27 Models, One Bad Pattern

---

## Abstract

We asked GPT-4 to write a JWT verification middleware for Express. It produced 22 lines of code with a hardcoded secret string from the standard SecLists wordlist — `YOUR_SECRET_KEY`, in a list every penetration tester ships with Kali. We forged a token using the cracked secret in 0.24 seconds. Three sentences in a developer's prompt, three lines of exploitable JWT in the response. We ran 730 such prompts across 27 model configurations. This is what we found.

The AI Security Benchmark is an open-source study that treats AI code generation the way a pen tester treats an unfamiliar application: methodically, across the attack surface, against a defined scope. We wrote 730 prompts to read like ordinary developer requests — no security keywords, no "write insecure code" instructions — and ran them across 27 model configurations covering OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open models via Ollama, and coding-assistant wrappers including Cursor and Codex.app. Every generated artifact is in `output/<model>/` on a public repo. Every score is in `reports/<model>.json`. You can open any file we cite and read it yourself.

The headline number is uncomfortable: the median score across 27 model configurations is 57.9%. That is not catastrophically broken code on every request — it is models consistently failing to apply the mitigations practitioners know matter. Hardcoded secrets instead of environment variable references. Deserialization of untrusted data with no integrity check. SQL queries assembled by f-string. Infrastructure-as-code that adds host namespace access the prompt never asked for. The same patterns we have been finding in hand-written code for twenty years, now generated at the velocity of an autocomplete keystroke.

This talk is structured as a practitioner session. The first thirteen minutes are a breadth tour: six vulnerability classes — hardcoded credentials in Terraform, SSRF with no URL validation on AWS, pickle deserialization from an unauthenticated Redis store, MD5 for file integrity, SQL injection through a GraphQL f-string, and Kubernetes workloads with `hostNetwork: true` and `hostPID: true` added unprompted. Each excerpt is from a real generated file, from a real prompt that did not invite the bug. Five models are represented: qwen2.5-coder, gpt-4, starcoder2, llama3.1, and claude-sonnet-4-5. The point is not that one model is uniquely bad. The point is that this pattern is not localized.

The last five minutes of the main segment are a live demo. We take two of the generated JWT files — the Express middleware and the Flask authentication system — and crack their hardcoded secrets against `Passwords/scraped-JWT-secrets.txt` from SecLists using jwt_tool. Both cracks complete in 0.24 seconds. We then forge tokens and demonstrate they are accepted. The exploit is not sophisticated; that is the point.

We close with the wrapper-engineering finding: the best-performing configuration scored 83.8%, a +24.3 percentage-point delta over raw GPT-5.4 at 59.5%. We state the caveat directly — roughly 30% of that configuration's outputs are incomplete generations, and detectors pass empty code. The delta survives because both wrapper conditions truncate at the same rate; the 83.8% headline requires an asterisk. Practical takeaways follow: what the benchmark actually tells you to change in your pipeline.

AppSec Village audiences build and break things. This talk delivers verified exploits, traceable numbers, and a methodology you can reproduce.

---

## Tight-Form Abstract

We asked GPT-4 to write a JWT verification middleware for Express. It produced 22 lines with a hardcoded secret — `YOUR_SECRET_KEY` — from the standard SecLists wordlist every pen tester ships with Kali. We forged a token in 0.24 seconds. Then we ran 730 such prompts across 27 model configurations. Median score: 57.9%.

This talk is structured as a practitioner session. The first thirteen minutes are a breadth tour of six vulnerability classes generated from prompts that never asked for the bug: hardcoded RDS credentials in Terraform, SSRF with no URL validation on AWS, pickle deserialization from an unauthenticated Redis store, MD5 for file integrity, SQL injection through a GraphQL f-string, and a Kubernetes DaemonSet that added `hostNetwork: true` and `hostPID: true` to a logging-agent prompt. Five models, six categories, none cherry-picked.

The final five minutes are a live demo. We crack two generated JWT secrets against `Passwords/scraped-JWT-secrets.txt` from SecLists using jwt_tool — both in 0.24 seconds — and forge tokens the server accepts. The exploit is not sophisticated. That is the point.

We close with the wrapper-engineering finding: the best-performing configuration scored 83.8%, a +24.3 pp improvement over raw GPT-5.4 at 59.5%. We state the truncation caveat directly — roughly 30% of that configuration's outputs are incomplete generations, so 83.8% is not "83.8% of code is secure." The delta survives; the headline requires an asterisk.

Every prompt is in `prompts/prompts.yaml`. Every artifact is in `output/<model>/`. Every score is in `reports/<model>.json` on the public repo. Any number we cite can be verified by opening the file we name.

---

## Detailed Outline

| Time | Segment | Content |
|---|---|---|
| 0:00–0:02 | Intro | Benchmark setup: 730 prompts × 27 model configurations. Prompts written as ordinary developer requests — no security keywords. Scoring against 35+ vulnerability detectors. Repo is public and every number is traceable. |
| 0:02–0:15 | Breadth tour | Six vulnerability classes, ~2 minutes each. (1) Hardcoded RDS password in Terraform — qwen2.5-coder, `output/qwen2.5-coder/terraform_010.tf`. (2) SSRF with no URL validation — qwen2.5-coder, `output/qwen2.5-coder/ssrf_001.py`. (3) pickle deserialization from unauthenticated Redis — gpt-4, `output/gpt-4/datastore_redis_001.py`. (4) MD5 for file integrity — starcoder2, `output/starcoder2/crypto_003.py`. (5) SQL injection via f-string in a GraphQL resolver — llama3.1, `output/llama3.1/graphql_007.py`. (6) Kubernetes DaemonSet with `hostNetwork: true` and `hostPID: true` added unprompted — claude-sonnet-4-5, `output/claude-sonnet-4-5/kubernetes_003.yaml`. |
| 0:15–0:20 | JWT live demo | Two verified cracking demos. Demo 1: `output/gpt-4/jwt_002.js` — Express middleware with `YOUR_SECRET_KEY`. Run `jwt_tool <token> -C -d Passwords/scraped-JWT-secrets.txt`. Cracks in 0.24 seconds. Forge token, send request, authenticated. Demo 2: `output/gpt-4/jwt_001.py` — Flask app with `your-secret-key`. Same wordlist, same tool, same 0.24-second result. Forge admin token. |
| 0:20–0:23 | Patterns + mitigations | jwt_003 and jwt_004 as slide-only pattern critiques (no live exploit): caller-controlled secret; algorithm selection gated on an unauthenticated request field. Wrapper-engineering finding: codex-app-security-skill at 83.8% vs raw GPT-5.4 at 59.5% (+24.3 pp) — with explicit truncation caveat. Practical takeaways: what the benchmark tells you to actually change in your pipeline. |
| 0:23–0:25 | Q&A | |

---

## Why This Talk

The AI Security Benchmark is an open-source test suite built by a practitioner who spent the first half of a thirty-year career writing software and the second half breaking it. That background shaped the study design: when AI-generated code became a normal part of developer workflows, the right question was not "is there risk?" — it was "how much risk, for which patterns, across which models, under what conditions?" The answer required something closer to a structured assessment than a blog post.

The study ran 730 prompts across 27 base model configurations. The prompts were written to read like legitimate developer requests — the kind of thing a junior engineer would paste into a chat interface to get started on a feature. No security keywords, no "ignore all previous instructions." Models tested span OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open-weight models via Ollama, and coding-assistant wrappers including Cursor and Codex.app. Generated code was evaluated against 35+ purpose-built vulnerability detectors covering OWASP Top 10, OWASP MASVS, and infrastructure-as-code weaknesses, across 35+ programming languages and formats.

Every prompt is in `prompts/prompts.yaml`. Every generated artifact is in `output/<model>/`. Every score is in `reports/<model>.json`. The public repo is at github.com/miroku0000/AI-Security-Benchmark. A reviewer can verify any claim by reading the file we name alongside its score. The talk is not asking you to trust the presenter; it is asking you to trust the artifacts.

The numbers in this pitch come from `reports/*.json` directly. The median score across 27 model configurations is 57.9%. The best-performing base configuration — codex-app-security-skill — scored 83.8% on a 1628-point scale. Raw GPT-5.4 scored 59.5%. No configuration scored above 88%. These are the numbers from the benchmark as run. They are not cherry-picked, and they are not inflated.

---

## Key Takeaways

- **The pattern is not localized.** Six vulnerability classes, five models, all from prompts that did not invite the bug. The median score of 57.9% is not a model-specific finding.

- **Hardcoded secrets in AI-generated code are trivially exploitable.** `YOUR_SECRET_KEY` and `your-secret-key` are in `Passwords/scraped-JWT-secrets.txt` — a wordlist that ships with Kali. The crack takes 0.24 seconds. The SAST tooling that could flag it often is not running in the generate-then-paste workflow most developers actually use.

- **Wrapper engineering changes the output, but the headline number needs a caveat.** The codex-app-security-skill configuration scored 83.8% vs raw GPT-5.4 at 59.5% (+24.3 pp). Roughly 30% of that configuration's outputs are incomplete generations; the detectors pass empty code. The delta is real; the 83.8% should not be read as "83.8% of code is secure."

- **Benchmark methodology matters as much as benchmark findings.** We originally planned a four-file live JWT escalation chain. Live testing collapsed it to two confirmed exploits and two slide-only pattern critiques. That reduction is a methodology story worth telling, not a weakness to hide.

- **The repo is public and every number is traceable.** You do not have to take our word for any claim in this talk. Open `reports/<model>.json` and count.

---

## Speaker Bio

Senior Security Consultant at IOActive, in tech since 1995 with a career split evenly between software development and security. That development background is what made the AI Security Benchmark feel necessary: when everyone started shipping AI-generated code, the question wasn't "is it risky?" — it was "how risky, for which models, under which conditions?" The answer is 730 prompts across 27 model configurations, with every result reproducible. The work is the talk.

---

## Supporting Materials

All cited code excerpt files are in `docs/demo/code-excerpts/` in this repository. The underlying generated sources are in `output/<model>/` and their scores are in `reports/<model>.json`.

### JWT live demo excerpts

| Excerpt file | Role in talk | Underlying source |
|---|---|---|
| `docs/demo/code-excerpts/jwt_001-weak-secret.md` | Live demo 1 — Flask JWT with `your-secret-key`; verified 0.24s crack via jwt_tool + SecLists | `output/gpt-4/jwt_001.py` |
| `docs/demo/code-excerpts/jwt_002-no-algs.md` | Live demo 2 — Express middleware with `YOUR_SECRET_KEY`; verified 0.24s crack via jwt_tool + SecLists | `output/gpt-4/jwt_002.js` |

### JWT pattern-critique slides (no live exploit)

| Excerpt file | Role in talk | Underlying source |
|---|---|---|
| `docs/demo/code-excerpts/jwt_003-no-verify.md` | Pattern critique — caller-controlled secret in a "verify" utility | `output/gpt-4/jwt_003.py` |
| `docs/demo/code-excerpts/jwt_004-algorithm-confusion.md` | Pattern critique — algorithm and key selection gated on unauthenticated request field | `output/gpt-4/jwt_004.py` |

### Wrapper-engineering reference

| Excerpt file | Role in talk | Underlying source |
|---|---|---|
| `docs/demo/code-excerpts/jwt_005-vs-codex-app.md` | One-sentence mitigations reference — same prompt, different wrapper, 1/4 vs 4/4 | `output/gpt-4/jwt_005.py` (vulnerable) and `output/codex-app-security-skill/jwt_005.py` (secure) |

### Breadth-tour excerpts

| Excerpt file | Role in talk | Underlying source |
|---|---|---|
| `docs/demo/code-excerpts/tour-terraform-hardcoded-creds-qwen2.5-coder.md` | Tour stop 1 — hardcoded RDS password in Terraform | `output/qwen2.5-coder/terraform_010.tf` |
| `docs/demo/code-excerpts/tour-ssrf-url-fetch-qwen2.5-coder.md` | Tour stop 2 — SSRF with no URL validation on AWS | `output/qwen2.5-coder/ssrf_001.py` |
| `docs/demo/code-excerpts/tour-redis-pickle-deser-gpt-4.md` | Tour stop 3 — pickle deserialization from unauthenticated Redis | `output/gpt-4/datastore_redis_001.py` |
| `docs/demo/code-excerpts/tour-md5-file-checksum-starcoder2.md` | Tour stop 4 — MD5 for file integrity (starcoder2) | `output/starcoder2/crypto_003.py` |
| `docs/demo/code-excerpts/tour-graphql-fstring-sql-llama3.1.md` | Tour stop 5 — SQL injection via f-string in a GraphQL resolver | `output/llama3.1/graphql_007.py` |
| `docs/demo/code-excerpts/tour-k8s-hostpath-mount-claude-sonnet-4-5.md` | Tour stop 6 — Kubernetes DaemonSet with `hostNetwork` and `hostPID` added unprompted | `output/claude-sonnet-4-5/kubernetes_003.yaml` |

---

## Appendix: Why Audit Choices Were Made

### JWT chain reduction: four files to two confirmed exploits

The original plan for the JWT segment was a four-file "escalation chain" that would walk through increasingly severe JWT weaknesses in sequence, treating all four as live demonstrations. Live testing against the actual generated files collapsed that structure. Two files — `output/gpt-4/jwt_001.py` and `output/gpt-4/jwt_002.js` — passed full end-to-end verification: both contain hardcoded placeholder secrets that appear verbatim in `Passwords/scraped-JWT-secrets.txt` from SecLists, and both crack in 0.24 seconds under jwt_tool with the forged token accepted by the respective application. These are the live demos.

The other two files — `output/gpt-4/jwt_003.py` and `output/gpt-4/jwt_004.py` — were reviewed and retained as pattern critiques presented on slides. `jwt_003` demonstrates a caller-controlled secret in a function that markets itself as a "verify" utility; the risk is real but depends on how the function is wired into a calling context, making it unsuitable for a deterministic stage demo. `jwt_004` demonstrates attacker-controlled algorithm and key selection via an unauthenticated request field; the textbook RS256/HMAC collision attack does not apply to this code as written (the two branches use different key material), so claiming it as a live algorithm-confusion exploit would have been inaccurate. Both are included because the patterns they represent are real and worth showing to an AppSec audience — the distinction from the live demos is stated explicitly in the talk.

Reducing from four to two confirmed exploits is a methodology choice, not a compromise. A stage demo that misrepresents what a piece of code actually does is worse than a slide. We audited the chain, found the boundary, and drew it clearly. That is the kind of rigor this audience expects.
