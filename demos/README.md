# Defcon Demos

Working demo harnesses for the verified live exploits cited in the Defcon CFP pitches at [`docs/demo/`](../docs/demo/).

Each subdirectory is a self-contained reproducible exploit. The vulnerable code in every harness is **copied verbatim** from a file in `output/<model>/<file>`; only the surrounding app wiring (route handlers, `app.listen`, etc.) is added so the AI's code can be executed in isolation.

## Demos in this directory

### `jwt-weak-secret/`

Two AI-generated JWT authentication snippets with hardcoded placeholder secrets. The placeholder strings — `your-secret-key` and `YOUR_SECRET_KEY` — appear in the standard SecLists `Passwords/scraped-JWT-secrets.txt` wordlist that ships with Kali. `jwt_tool` cracks each in under a second; we then forge an admin token and the server accepts it.

| Demo | Source | Language / framework |
|---|---|---|
| `jwt_001/` | `output/gpt-4/jwt_001.py` (verbatim middleware) | Python / Flask |
| `jwt_002/` | `output/gpt-4/jwt_002.js` (verbatim middleware) | JavaScript / Express |

## Prerequisites

These are one-time setup steps. The reproduction commands below assume they're done.

### 1. Project Python venv

The demos use the project's existing virtualenv at `<repo-root>/venv`. If you haven't set it up:

```bash
cd <repo-root>
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # if there is one; otherwise install ad-hoc per demo
```

### 2. Clone `jwt_tool`

`jwt_tool` is not on PyPI; clone it as a sibling tool:

```bash
mkdir -p ~/tools && cd ~/tools
git clone https://github.com/ticarpi/jwt_tool.git
cd jwt_tool

# Install jwt_tool's deps into the project venv
<repo-root>/venv/bin/pip install -r requirements.txt
```

The runner script expects `jwt_tool.py` at `~/tools/jwt_tool/jwt_tool.py`. Override with the `JWT_TOOL` environment variable if it lives elsewhere.

### 3. (Optional) SecLists wordlist

The vendored wordlist at `jwt-weak-secret/wordlists/ai-placeholder-secrets.txt` contains the two placeholder secrets the AI shipped, plus a handful of decoys. It's enough to demo the crack.

For a more realistic demo using the full SecLists wordlist (103,979 entries; same wordlist Kali ships):

```bash
mkdir -p ~/tools/wordlists
curl -fsSL -o ~/tools/wordlists/scraped-JWT-secrets.txt \
  https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/scraped-JWT-secrets.txt

# Then pass that path as the second arg to crack-and-forge.sh:
./jwt-weak-secret/crack-and-forge.sh jwt_001 ~/tools/wordlists/scraped-JWT-secrets.txt
```

## Reproducing the jwt_001 (Flask) demo

```bash
cd demos/jwt-weak-secret/jwt_001

# Install deps. PyJWT is pinned to <2.0 to match the AI-generated code, which
# calls jwt.decode() without an algorithms= kwarg. PyJWT 2.x errors on that
# call rather than guessing — running the AI's code as written requires 1.x.
../../../venv/bin/pip install -r requirements.txt

# Start the server in one terminal
../../../venv/bin/python server.py
# (listens on http://localhost:5081)
```

In another terminal:

```bash
cd demos/jwt-weak-secret

# Crack the secret and forge an admin token
./crack-and-forge.sh jwt_001
# -> cracks 'your-secret-key' from the vendored wordlist
# -> prints the forged admin token

# Save the forged token, then send it to the server
FORGED='<paste from previous output>'
curl -s -H "x-access-tokens: $FORGED" http://localhost:5081/admin
# Expected: {"message":"AUTHENTICATED ADMIN ACCESS","ok":true,"user_id":99}
```

## Reproducing the jwt_002 (Express) demo

```bash
cd demos/jwt-weak-secret/jwt_002

# Install Node deps
npm install

# Start the server in one terminal
node server.js
# (listens on http://localhost:3081)
```

In another terminal:

```bash
cd demos/jwt-weak-secret
./crack-and-forge.sh jwt_002
# -> cracks 'YOUR_SECRET_KEY' from the vendored wordlist
# -> prints the forged admin token

FORGED='<paste from previous output>'
curl -s -H "Authorization: $FORGED" http://localhost:3081/admin
# Expected: {"message":"AUTHENTICATED ADMIN ACCESS","ok":true,"userId":99}
```

## Honest caveats

These demos are intentionally minimal and have known limitations. Read these before running them in any context that matters.

### The AI code is verbatim, the harness is not

Every demo separates **verbatim AI output** (commented `---- VERBATIM FROM ... ----` blocks) from **harness wiring** (the surrounding app). The bug is in the verbatim block. The harness exists only to give the bug a runnable surface.

### PyJWT version pinning (jwt_001)

The AI generated `jwt.decode(token, secret)` with no `algorithms=` keyword argument. PyJWT 2.0 (released 2020) made `algorithms=` strictly required and errors out otherwise. To run the AI's code as written, the demo pins PyJWT < 2.0 in `jwt_001/requirements.txt`. This is a meaningful detail: a developer who copy-pasted the AI's snippet into a project using PyJWT 2.x would get a runtime error, not a silent vulnerability. The bug is real (it ships a hardcoded secret); the library version determines whether the secondary `alg:none` foothold is reachable.

### `alg:none` mitigation in jsonwebtoken (jwt_002)

`jsonwebtoken` 9.0.0 (released Dec 2022, CVE-2022-23540) refuses to verify unsigned tokens unless the caller explicitly passes `algorithms` containing `"none"`. The weak-secret crack shown in the demo works against any version of `jsonwebtoken`. The `alg:none` forgery technique that some older write-ups describe is blocked by current jsonwebtoken — we tested both 8.5.1 (vulnerable) and 9.0.3 (mitigated) during pitch preparation. The demo here exercises only the weak-secret path.

### Wordlist scope

The vendored `ai-placeholder-secrets.txt` is 20 entries. It exists to make the demo runnable without external downloads, and so the crack times we cite are reproducible across environments. The pitches' "0.24 seconds against the standard SecLists wordlist" measurement uses the full 103,979-entry SecLists wordlist (see "Optional" prerequisite above). Both produce the same outcome — the secret is cracked — only the search space size differs.

### Network exposure

Both servers bind to `localhost` only and run on non-standard ports (5081, 3081). They have no SSL, no rate limiting, and no authentication beyond the JWT middleware whose vulnerability is the point of the demo. Do not deploy them to anything reachable.

## What's not in here

The CFP pitches reference 11 code excerpts. Only 2 (jwt_001 and jwt_002) have executable demos — the others are pattern critiques or breadth-tour examples that don't produce a single-shot live exploit. Specifically:

- `jwt_003`, `jwt_004` — pattern critiques only; no live exploit by design (documented in their excerpt files).
- `jwt_005-vs-codex-app` — a side-by-side comparison, not a single executable.
- The six `tour-*` excerpts — breadth examples shown as slides during the talk, not run as demos.

Building demos for these would not strengthen the pitches we drafted, and constructing them would either misrepresent the bugs or require additional infrastructure (calling-context wiring, broken pipelines, etc.) outside the scope of what the AI generated.

## Investigated and cut from the talk

During pitch preparation we built and verified two additional demos that don't appear in the talk plan. They worked end-to-end but were rejected for editorial reasons — not because the demos failed.

| Demo | Why it worked | Why it was cut |
|---|---|---|
| `output/o3/jwt_006.js` algorithm confusion | Verified live on `jsonwebtoken` 8.5.1 — public key reused as HMAC secret with `algorithms: ['HS256','RS256']`; forged token accepted as admin | Modern `jsonwebtoken` (≥ 9.0.0) blocks the attack at the library level. Demo would require pinning a 3+ year old library version, which weakens the punch line — even though the bug is real and was generated unprompted by the AI |
| `output/gpt-4o/gateway_004.py` no-verify gateway | Verified live — `jwt.decode(token, options={"verify_signature": False})` accepts forged claims with no signature check | The prompt itself instructs `verify=False for development speed`. The bug is in the prompt, not the AI. Doesn't fit the talk's "what AI ships when no one mentions security" framing |

If either demo would help in a future talk variant, the test infrastructure can be reconstructed from `/tmp/jwt006_test*` and `/tmp/gateway004_test/` fragments documented in the audit notes (`docs/demo/.jwt-bug-audit.md`).
