#!/usr/bin/env python3
"""
Game Server Browser - UDP Status Server

Implements a game server query protocol with protections
against UDP amplification/reflection attacks.
"""

import socket
import struct
import json
import time
import hashlib
import threading
from collections import defaultdict

HOST = "0.0.0.0"
PORT = 27015
MAX_RESPONSE_SIZE = 1400  # Stay within typical MTU to avoid fragmentation
RATE_LIMIT_WINDOW = 10    # seconds
RATE_LIMIT_MAX = 5        # max queries per window per IP
CHALLENGE_TIMEOUT = 30    # seconds

# --- Simulated game state ---
game_state = {
    "server_name": "My Game Server",
    "map": "de_dust2",
    "max_players": 32,
    "players": [
        {"name": f"Player{i}", "score": i * 10, "duration": i * 60}
        for i in range(1, 17)
    ],
}

# --- Rate limiting ---
query_counts = defaultdict(list)
rate_lock = threading.Lock()

# --- Challenge-response to prevent IP spoofing ---
pending_challenges = {}
challenge_lock = threading.Lock()


def is_rate_limited(addr):
    """Limit queries per IP to prevent abuse."""
    ip = addr[0]
    now = time.time()
    with rate_lock:
        query_counts[ip] = [t for t in query_counts[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(query_counts[ip]) >= RATE_LIMIT_MAX:
            return True
        query_counts[ip].append(now)
    return False


def generate_challenge(addr):
    """Create a challenge token that the client must echo back."""
    token = hashlib.sha256(f"{addr}{time.time()}".encode()).hexdigest()[:16]
    with challenge_lock:
        pending_challenges[token] = (addr, time.time())
    return token


def verify_challenge(token, addr):
    """Verify a challenge response to confirm the source IP is real."""
    with challenge_lock:
        entry = pending_challenges.pop(token, None)
    if entry is None:
        return False
    stored_addr, ts = entry
    if time.time() - ts > CHALLENGE_TIMEOUT:
        return False
    return stored_addr[0] == addr[0]


def cleanup_challenges():
    """Remove expired challenge tokens."""
    now = time.time()
    with challenge_lock:
        expired = [k for k, (_, ts) in pending_challenges.items() if now - ts > CHALLENGE_TIMEOUT]
        for k in expired:
            del pending_challenges[k]


def build_status_response():
    """Build a truncated status response that fits within MTU."""
    info = {
        "name": game_state["server_name"],
        "map": game_state["map"],
        "players": len(game_state["players"]),
        "max_players": game_state["max_players"],
        "player_list": [
            {"n": p["name"], "s": p["score"]}
            for p in game_state["players"]
        ],
    }
    data = json.dumps(info, separators=(",", ":")).encode()
    # Truncate to stay within safe UDP size
    if len(data) > MAX_RESPONSE_SIZE:
        info["player_list"] = info["player_list"][:10]
        info["truncated"] = True
        data = json.dumps(info, separators=(",", ":")).encode()
    return data


def handle_query(sock, data, addr):
    if is_rate_limited(addr):
        return

    msg = data.decode(errors="replace").strip()

    # Step 1: Client sends "status" -> server replies with a challenge
    if msg == "status":
        token = generate_challenge(addr)
        sock.sendto(f"challenge:{token}".encode(), addr)
        return

    # Step 2: Client echoes back "response:<token>" -> server sends real data
    if msg.startswith("response:"):
        token = msg[len("response:"):]
        if verify_challenge(token, addr):
            response = build_status_response()
            sock.sendto(response, addr)
        return


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"Game server query listening on {HOST}:{PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(512)
            handle_query(sock, data, addr)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    sock.close()


if __name__ == "__main__":
    main()