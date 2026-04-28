# Benchmark Credibility Paragraph

> Reusable boilerplate for both Defcon CFP pitches. Adapt tone per submission.

## Long form (~120 words)

The AI Security Benchmark is an open-source test suite that ran 730 prompts — written to read like ordinary developer requests, with no security keywords — across 27 base model configurations. Models tested span OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open models via Ollama, and coding-assistant wrappers including Cursor and Codex.app. We evaluated generated code against 35+ purpose-built vulnerability detectors covering OWASP Top 10, OWASP MASVS mobile risks, and infrastructure-as-code weaknesses, across 35+ programming languages and formats. Every prompt is in `prompts/prompts.yaml`, every generated artifact is in `output/<model>/`, and every score is in `reports/<model>.json` on the public repo at github.com/miroku0000/AI-Security-Benchmark. A reviewer can verify any claim by reading the cited file alongside its score.

## Short form (~60 words)

The AI Security Benchmark is an open-source test suite that ran 730 prompts — written as ordinary developer requests, no security keywords — across 27 model configurations covering OpenAI's GPT family, Anthropic's Claude, Google's Gemini, locally-hosted open models, and coding-assistant wrappers. We scored results against 35+ vulnerability detectors across 35+ languages. Every prompt, artifact, and score is in the public repo and independently verifiable.

## Note on configuration count

The repository currently contains 28 base configurations in `reports/`. The 27-config number used in pitches excludes `github-copilot`, which post-dates the underlying paper. Pitches that reference findings from the paper use the 27-config number for consistency with the published research.
