"""Offline password-hash crack against the AI's hashPassword() output.

The AI used PBKDF2-SHA512 with **1,000 iterations**. OWASP's current
recommendation for PBKDF2-SHA512 is **210,000 iterations** (210x more);
NIST's lower bound is 600,000 (600x more). At 1k iterations the work
factor is so low that a single CPU core does ~10,000 password attempts
per second — fast enough that any wordlist-recoverable password falls
in under a minute against a small wordlist, and a sub-day campaign
against rockyou.txt's 14M entries.

This demo uses a 50-entry wordlist (the SecLists Top 50 most common
passwords) so the demo finishes in seconds. A real attack scales by
adding more cores and a bigger wordlist; the per-guess cost the AI
chose is what makes that scaling cheap."""

import hashlib
import multiprocessing as mp
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LEAKED_HASH_FILE = HERE / 'leaked-hash.txt'
WORDLIST = HERE / 'wordlist.txt'

ITERATIONS = 1000      # what the AI chose
DKLEN = 64             # 64 bytes, matches the AI's call
HASH_ALGO = 'sha512'   # matches the AI's call


def parse_leaked(line):
    """Split the AI's `salt$hash` format."""
    salt_hex, hash_hex = line.strip().split('$')
    return salt_hex, hash_hex


def try_password(args):
    """Hash a candidate password with the AI's parameters and check."""
    candidate, salt_hex, target_hex = args
    # pbkdf2_hmac is a single C call; rate is bounded by the iteration count.
    # Note: Node's crypto.pbkdf2Sync uses the salt as a *string of hex chars*
    # (which the AI passed via .toString('hex')), NOT as raw bytes. We mirror
    # that here by treating the salt the same way the AI did — as a hex string.
    digest = hashlib.pbkdf2_hmac(
        HASH_ALGO,
        candidate.encode('utf-8'),
        salt_hex.encode('utf-8'),  # string-of-hex bytes, matching Node
        ITERATIONS,
        DKLEN,
    )
    if digest.hex() == target_hex:
        return candidate
    return None


def main():
    if not LEAKED_HASH_FILE.exists():
        print(f'error: {LEAKED_HASH_FILE} not found. Run `node seed.js` first.', file=sys.stderr)
        return 1

    leaked = LEAKED_HASH_FILE.read_text().strip()
    salt_hex, target_hex = parse_leaked(leaked)
    passwords = [p.strip() for p in WORDLIST.read_text().splitlines() if p.strip()]

    print(f'Target hash:  {leaked[:40]}...')
    print(f'Salt:         {salt_hex}')
    print(f'Iterations:   {ITERATIONS:,} (OWASP min: 210,000 — AI chose 210x too few)')
    print(f'Wordlist:     {WORDLIST.name} ({len(passwords):,} candidates)')
    print(f'Workers:      {mp.cpu_count()} cores')
    print()

    args = [(p, salt_hex, target_hex) for p in passwords]
    start = time.monotonic()
    found = None
    attempts = 0
    with mp.Pool(processes=mp.cpu_count()) as pool:
        for result in pool.imap_unordered(try_password, args, chunksize=4):
            attempts += 1
            if result is not None:
                found = result
                pool.terminate()
                break
            if attempts % 5 == 0:
                rate = attempts / (time.monotonic() - start)
                print(f'  {attempts:>4}/{len(passwords)}  ({rate:.0f} guesses/sec on {mp.cpu_count()} cores)')
    elapsed = time.monotonic() - start

    print()
    if found:
        rate = attempts / elapsed if elapsed > 0 else 0
        per_guess_us = elapsed * 1e6 / max(attempts, 1)
        print(f'CRACKED in {elapsed:.2f} seconds.')
        print(f'  password recovered: {found!r}')
        print(f'  attempts: {attempts}')
        print(f'  guess rate: {rate:.0f} per second on {mp.cpu_count()} CPU cores')
        print(f'  per-guess cost: {per_guess_us:.0f} microseconds')
        print()
        print('Per-guess cost at recommended cost factors (same hardware):')
        scale_owasp = 210      # 210k / 1k
        scale_bcrypt = 60_000  # bcrypt cost 12 ≈ 60k× slower per guess than PBKDF2-1k
        print(f'  PBKDF2-SHA512, 210k iterations (OWASP minimum):     {per_guess_us*scale_owasp/1000:>8.1f} ms     ({scale_owasp}x slower)')
        print(f'  bcrypt, cost factor 12 (also recommended):          {per_guess_us*scale_bcrypt/1000:>8.1f} ms     ({scale_bcrypt:,}x slower)')
        print()
        # GPU baseline: hashcat published benchmarks for PBKDF2-SHA512 at 1k iterations.
        # A single RTX 4090 does ~1.5M guesses/sec; an 8-GPU rig ~12M/sec.
        gpu_rate_1k = 12_000_000  # 8x RTX 4090, PBKDF2-SHA512, 1k iterations
        rockyou_size = 14_344_391
        rockyou_seconds_1k = rockyou_size / gpu_rate_1k
        print(f'Translated to a real attacker on an 8-GPU rig (~{gpu_rate_1k/1e6:.0f}M PBKDF2-SHA512 guesses/sec at 1k iterations):')
        print(f'  Cracking the full rockyou.txt (14.3M passwords) at the AI\'s 1k iterations:    ~{rockyou_seconds_1k:.1f} seconds')
        print(f'  Same crack at OWASP\'s 210k iterations:                                          ~{rockyou_seconds_1k*scale_owasp/60:.0f} minutes')
        print(f'  Same crack at bcrypt cost-12:                                                   ~{rockyou_seconds_1k*scale_bcrypt/3600/24:.0f} days')
        print()
        print('Same wordlist. Same hardware. The AI\'s 1k-iteration choice made the')
        print('crack 210x cheaper than it should have been at OWASP\'s minimum recommendation,')
        print('and 60,000x cheaper than the bcrypt baseline most security guides recommend.')
        return 0

    print(f'No match in this wordlist. Attempts: {attempts}, elapsed: {elapsed:.2f}s')
    return 1


if __name__ == '__main__':
    sys.exit(main())
