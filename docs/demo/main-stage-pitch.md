# Main Stage / Track Pitch — "The Security Gap in AI"

**Status:** Draft
**Target slot:** 45 minutes (compresses proportionally if shorter)
**Working title:** The Security Gap in AI: What 730 Prompts × 27 Models Tells Us

---

## Abstract

We tested 27 AI code generators on 730 prompts written like real developer requests — never mentioning security. The median configuration scored 57.9%. The best raw API model scored 60.7%. The best of anything we tested? A thin wrapper sitting on top of GPT — 83.8%. The story is the wrapper, not the model. We didn't know which configuration of model plus tooling actually catches the bugs developers ship every day. So we tested 27.

The AI Security Benchmark is an open-source study that ran 730 prompts — written to read like ordinary developer requests, no security keywords — across 27 base model configurations covering OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open-weight models, and coding-assistant wrappers including Cursor and Codex.app. (The repo contains 28 base configs; the 27-config count excludes github-copilot, which post-dates the underlying paper.) We scored generated code against 35+ vulnerability detectors covering OWASP Top 10, OWASP MASVS, and infrastructure-as-code weaknesses across 35+ programming languages. Every prompt, artifact, and score is in the public repository and independently verifiable.

The talk opens with the statistical picture. Median score across 27 configurations: 57.9%. No configuration scored above 88%. The spread is narrow — o3, GPT-4o, Claude, and Gemini all cluster near the median. The first section covers what this distribution means and how the study design kept the prompts from being the story.

The second section is a case study in one vulnerability class: JWT authentication. We take two generated files — a Flask authentication system and an Express middleware — and crack their hardcoded placeholder secrets against a standard wordlist using jwt_tool (a JWT testing utility). Both crack in 0.24 seconds. We forge tokens and submit them. The exploit requires no specialist knowledge; the secret strings are in a wordlist that ships with Kali Linux. The JWT case study is not about one bad model. It maps back to the benchmark: the same default failures appear across model families and vulnerability categories.

The closer is the wrapper-engineering reveal, anchored on a verified side-by-side (`docs/demo/code-excerpts/jwt_005-vs-codex-app.md`): the same JWT generation prompt, run through a raw GPT-4 API call and through a Codex.app instance with a security skill configured. Raw GPT-4 scores 1/4 — hardcoded secret, no replay protection, no token binding, no input validation. Codex.app scores 4/4. Same prompt. Same model family. The wrapper changed the code.

Across the 1628-point benchmark, codex-app-security-skill scored 83.8% versus raw GPT-5.4 at 59.5% — a +24.3 percentage-point gap. We state the caveat directly: roughly 30% of codex-app's outputs in both the security-skill and no-skill conditions are incomplete generations. Detectors pass empty code. The 83.8% headline is not "83.8% of generated code is secure." The gap survives the caveat because both conditions truncate at the same rate, isolating the wrapper's contribution. The finding is that wrapper configuration measurably improves the code that gets generated. The methodology is public, the evidence for the caveat is public, and we present both.

---

## Tight-Form Abstract

We tested 27 AI code generators on 730 prompts written like real developer requests — never mentioning security. The median configuration scored 57.9%. The best raw API model (GPT-5.2) scored 60.7%. The best of anything we tested? A thin wrapper on top of GPT — 83.8%, a +24.3 percentage-point delta over raw GPT-5.4. The story is the wrapper, not the model.

The talk opens with the distribution: 27 configs, 57.9% median, no configuration above 88%, and flagship models (o3, GPT-4o, Claude, Gemini) clustered near that median. The spread is narrow everywhere except at the top.

The middle section is a JWT case study. We crack hardcoded placeholder secrets in two generated authentication files — Flask and Express — in 0.24 seconds using jwt_tool against the standard SecLists wordlist, then forge tokens. The attack requires no specialist knowledge; the secret strings are in a wordlist that ships with Kali Linux. JWT is one category. The same default failures appear across the full distribution.

The closer is the wrapper-engineering finding, anchored on a verified side-by-side from `jwt_005-vs-codex-app.md`: same JWT generation prompt, raw GPT-4 scores 1/4 (hardcoded secret, no replay protection, no token binding), Codex.app with a security skill scores 4/4. Same prompt. Same model family. The wrapper changed the code.

The truncation caveat is stated directly: roughly 30% of codex-app outputs in both conditions are incomplete generations; detectors pass empty code; 83.8% should not be read as a coverage guarantee. The +24.3 pp gap survives because both conditions truncate at the same rate. Every number traces to `reports/*.json` on the public repo.

---

## Detailed Outline

| Time | Segment | Content |
|---|---|---|
| 0:00–0:08 | Intro / methodology | Why we ran the benchmark; study design; how prompts mimic real developer requests without security keywords; scoring methodology (35+ detectors, 35+ languages, OWASP Top 10 / MASVS / IaC coverage); repo structure and verifiability. Statistical overview: 27 configurations, 730 prompts, 57.9% median, distribution chart. The cluster pattern: why top raw models are closer to the median than to the best wrapper. |
| 0:08–0:18 | Findings tour | Walk the full distribution: codex-app-security-skill 83.8%, codex-app-no-skill 78.7%, then the cluster from claude-code 63.4% down through gpt-4o-mini 53.9%. Highlight that starcoder2 (62.8%) and deepseek-coder (61.9%) — open-weight models running locally — outperform several flagship commercial APIs. Discuss the benchmark methodology: what a score means, what it does not mean, how the 1628-point scale is constructed. Note that no configuration scored above 88%. |
| 0:18–0:30 | JWT case study | Reframe JWT as a case study of one vulnerability class, not a cherry-picked demo. Establish the pattern across prompts: the AI consistently produces hardcoded placeholder secrets, missing algorithm constraints, and absent token-binding claims — not because any single prompt asked for them, but as a default. Live demo 1: `output/gpt-4/jwt_001.py` (Flask, `your-secret-key`, crack in 0.24s via jwt_tool + SecLists, forge admin token). Live demo 2: `output/gpt-4/jwt_002.js` (Express middleware, `YOUR_SECRET_KEY`, same result). Map the JWT pattern back to the benchmark statistics. |
| 0:30–0:40 | Wrapper-engineering reveal | Lead with the jwt_005 side-by-side (`docs/demo/code-excerpts/jwt_005-vs-codex-app.md`): same prompt, gpt-4 raw (1/4) vs codex-app-security-skill (4/4). Walk through the five specific changes the wrapper produced. State the headline: 83.8% vs 59.5% raw GPT-5.4, +24.3 pp. Address the truncation caveat explicitly and in full: ~30% of codex-app outputs in both security-skill and no-skill conditions are incomplete generations; detectors pass empty code; 83.8% should not be read as "83.8% of generated code is secure." Explain why the gap survives: both conditions truncate at the same rate, so the comparison is apples-to-apples at the corpus level, and the security skill measurably improves the code that does get generated. Practical implication: wrapper engineering is the most actionable finding in the data. |
| 0:40–0:45 | Q&A | |

---

## Why This Talk

The AI Security Benchmark is an open-source test suite built by a practitioner who has divided a career roughly equally between writing software and breaking it, starting in 1995. That dual background shaped the question the study was designed to answer. When AI-generated code became a normal part of developer workflows, the interesting question was not "is there risk?" — there was clearly risk. The question was: how much, for which patterns, across which models, under what conditions? Answering that required something closer to a structured engineering study than a blog post.

The study ran 730 prompts across 27 base model configurations. (The repository currently contains 28 base configurations in `reports/`; the 27-config count excludes `github-copilot`, which post-dates the underlying paper.) The prompts were written to read like legitimate developer requests — the kind a junior engineer would paste into a chat interface to get started on a feature. No security keywords, no "ignore all previous instructions," no prompts that invited the insecure pattern. Models tested span OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open-weight models via Ollama, and coding-assistant wrappers including Cursor and Codex.app. Generated code was evaluated against 35+ purpose-built vulnerability detectors covering OWASP Top 10, OWASP MASVS, and infrastructure-as-code weaknesses, across 35+ programming languages and formats.

Every prompt is in `prompts/prompts.yaml`. Every generated artifact is in `output/<model>/`. Every score is in `reports/<model>.json`. The public repository is at github.com/miroku0000/AI-Security-Benchmark. A reviewer can verify any number in this pitch by opening the file we name alongside its score. We are not asking the audience to trust the presenter. We are asking them to trust the artifacts.

The numbers in this pitch come from `reports/*.json` directly. The median score across 27 configurations is 57.9%. The best-performing configuration — codex-app-security-skill — scored 83.8% on a 1628-point scale. The best raw API model, GPT-5.2, scored 60.7%. Raw GPT-5.4 scored 59.5%. No configuration scored above 88%. The wrapper-engineering delta (+24.3 pp) is the central differentiator, and it comes with a caveat that is part of the talk, not a footnote: roughly 30% of codex-app outputs in both conditions are incomplete generations, which inflates the headline score. The delta survives that caveat; the absolute 83.8% does not survive without qualification. Main Stage audiences include researchers and engineers from outside the security industry; the honest treatment of methodology is as interesting to that audience as the headline number.

---

## Key Takeaways

- **The spread across 27 configurations is narrower than expected — except at the top.** Flagship commercial models (o3, GPT-4o, Claude, Gemini) cluster near the 57.9% median. Some open-weight local models outperform them. The gap that actually matters is not between model families — it is between the raw models and the best wrapper configuration (+24.3 pp).

- **Hardcoded secrets in AI-generated code are exploitable with no specialist knowledge.** `YOUR_SECRET_KEY` and `your-secret-key` appear verbatim in standard SecLists wordlists that ship with Kali Linux. Running jwt_tool against either takes 0.24 seconds (measured). The attack path requires only a known token and a wordlist that any penetration tester already has.

- **Wrapper engineering is the most actionable finding in the data.** A thin wrapper with a security-oriented system prompt produced a +24.3 percentage-point improvement over the same underlying model without it. The wrapper changed what the model generated, not which model generated it. This is the clearest signal for anyone deciding how to configure an AI code assistant in their workflow.

- **The 83.8% headline requires an honest asterisk.** Roughly 30% of codex-app outputs — in both the security-skill and no-skill conditions — are incomplete generations. The detectors pass empty code. The +24.3 pp gap between the two wrapper conditions isolates the wrapper's contribution because both truncate at the same rate. But the absolute 83.8% should not be read as a coverage guarantee.

- **Every number is traceable and the methodology is reproducible.** 730 prompts in `prompts/prompts.yaml`. Every generated file in `output/<model>/`. Every score in `reports/<model>.json`. The study can be re-run, extended, or challenged from the public repo.

---

## Speaker Bio

Senior Security Consultant at IOActive, with a career that began in 1995 and has divided roughly equally between software engineering and security research. That dual background shaped the AI Security Benchmark: designing a study of this scope — 730 prompts tested across 27 model configurations — required both the engineering discipline to build the harness and the security judgment to know what to look for. The benchmark is fully documented and reproducible, which is what makes the findings worth presenting.

---

## Supporting Materials

All cited code excerpt files are in `docs/demo/code-excerpts/` in this repository. The underlying generated sources are in `output/<model>/` and their scores are in `reports/<model>.json`.

### Headline artifact: wrapper-engineering side-by-side

| Excerpt file | Role in talk | Underlying sources |
|---|---|---|
| `docs/demo/code-excerpts/jwt_005-vs-codex-app.md` | Central closer — same JWT generation prompt, gpt-4 raw API (1/4) vs codex-app-security-skill (4/4); anchors the wrapper-engineering finding | `output/gpt-4/jwt_005.py` (vulnerable) and `output/codex-app-security-skill/jwt_005.py` (secure) |

### JWT case study: live demos

| Excerpt file | Role in talk | Underlying source |
|---|---|---|
| `docs/demo/code-excerpts/jwt_001-weak-secret.md` | Live demo 1 — Flask JWT with `your-secret-key`; verified 0.24s crack via jwt_tool + SecLists wordlist | `output/gpt-4/jwt_001.py` |
| `docs/demo/code-excerpts/jwt_002-no-algs.md` | Live demo 2 — Express middleware with `YOUR_SECRET_KEY`; verified 0.24s crack via jwt_tool + SecLists wordlist | `output/gpt-4/jwt_002.js` |

### Statistical context: tour candidates (referenced for breadth statistics, not shown as a tour)

The six vulnerability categories documented in `docs/demo/.tour-candidates.md` are referenced in the findings-tour section for statistical context (illustrating the spread across models and categories) but are not presented as a named tour in this talk. The underlying files are:

| Underlying source | Category | Model |
|---|---|---|
| `output/qwen2.5-coder/terraform_010.tf` | Hardcoded credentials (Terraform) | qwen2.5-coder |
| `output/qwen2.5-coder/ssrf_001.py` | SSRF — no URL validation | qwen2.5-coder |
| `output/gpt-4/datastore_redis_001.py` | Insecure deserialization (pickle/Redis) | gpt-4 |
| `output/starcoder2/crypto_003.py` | Weak hash function (MD5 for integrity) | starcoder2 |
| `output/llama3.1/graphql_007.py` | SQL injection via f-string in GraphQL | llama3.1 |
| `output/claude-sonnet-4-5/kubernetes_003.yaml` | Container / k8s bad defaults (hostNetwork, hostPID) | claude-sonnet-4-5 |

---

## Appendix: github-copilot Exclusion

The repository currently contains 28 base configurations in `reports/`. The 27-configuration count used throughout this pitch excludes `github-copilot`. The copilot configuration post-dates the underlying paper that this talk is drawn from, so including it would introduce a result that was not part of the original comparative study. All percentages, the median, and the distribution statistics in this pitch are computed across the 27 configurations from that study. The copilot entry is in the public repo; anyone who wants to compare it against the other 27 can do so by reading `reports/github-copilot.json`.
