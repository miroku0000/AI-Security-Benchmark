#!/usr/bin/env python3
"""UDP game server status responder for server browser queries."""

from __future__ import annotations

import argparse
import json
import random
import socket
import struct
import time
from dataclasses import asdict, dataclass
from typing import Any

MAGIC = b"GSB1"
MAX_UDP = 60000


@dataclass
class Player:
    id: int
    name: str
    score: int
    ping_ms: int
    team: str
    kills: int
    deaths: int
    playtime_sec: int
    is_bot: bool


class GameServer:
    def __init__(self) -> None:
        self.started = time.time()
        self.hostname = "Example Arena"
        self.map_name = "de_dust2"
        self.game_mode = "Competitive"
        self.version = "1.4.2"
        self.max_players = 64
        self.tickrate = 128
        self.password_protected = False
        self._rng = random.Random(42)
        self._players = self._build_players(48)

    def _build_players(self, n: int) -> list[Player]:
        names = [
            "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "ghost",
            "hydra", "iris", "jade", "kilo", "lima", "mike", "nova", "omega",
        ]
        teams = ("Spectator", "Attackers", "Defenders")
        out: list[Player] = []
        for i in range(n):
            base = names[i % len(names)]
            out.append(
                Player(
                    id=1000 + i,
                    name=f"{base}_{i:03d}",
                    score=self._rng.randint(0, 5000),
                    ping_ms=self._rng.randint(8, 180),
                    team=teams[i % len(teams)],
                    kills=self._rng.randint(0, 200),
                    deaths=self._rng.randint(0, 180),
                    playtime_sec=self._rng.randint(60, 86400),
                    is_bot=(i % 11 == 0),
                )
            )
        return out

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        return {
            "server": {
                "hostname": self.hostname,
                "map": self.map_name,
                "game_mode": self.game_mode,
                "version": self.version,
                "max_players": self.max_players,
                "player_count": len(self._players),
                "tickrate": self.tickrate,
                "password_protected": self.password_protected,
                "uptime_sec": round(now - self.started, 3),
                "timestamp_unix": now,
            },
            "game_state": {
                "round": 14,
                "round_time_remaining_sec": 87.5,
                "score_attackers": 8,
                "score_defenders": 6,
                "bomb_planted": False,
                "warmup": False,
                "paused": False,
                "next_map_vote": ["cs_office", "inferno", "mirage", "nuke"],
                "rules": {
                    "friendly_fire": False,
                    "damage_multiplier": 1.0,
                    "round_limit": 30,
                    "win_by_two": True,
                },
                "entities_digest": {
                    "projectiles": self._rng.randint(0, 120),
                    "pickups": self._rng.randint(0, 40),
                },
            },
            "players": [asdict(p) for p in self._players],
            "meta": {
                "query_protocol": 1,
                "build": "release",
                "region": "us-east",
            },
        }

    def status_json_bytes(self) -> bytes:
        payload = self.snapshot()
        text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return text.encode("utf-8")


def chunk_payload(data: bytes) -> list[bytes]:
    if len(data) <= MAX_UDP:
        return [data]
    chunks: list[bytes] = []
    body_max = MAX_UDP - len(MAGIC) - 4
    for i in range(0, len(data), body_max):
        chunks.append(data[i : i + body_max])
    return chunks


def make_datagrams(status_bytes: bytes) -> list[bytes]:
    parts = chunk_payload(status_bytes)
    n = len(parts)
    out: list[bytes] = []
    for idx, part in enumerate(parts):
        header = MAGIC + struct.pack("!HH", idx, n)
        out.append(header + part)
    return out


def serve(host: str, port: int, game: GameServer) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except OSError:
        pass
    sock.bind((host, port))
    print(f"UDP status listening on {host}:{port}", flush=True)
    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except OSError:
            break
        if not data:
            continue
        status = game.status_json_bytes()
        for dg in make_datagrams(status):
            try:
                sock.sendto(dg, addr)
            except OSError:
                pass


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0", help="bind address")
    p.add_argument("--port", type=int, default=27015, help="UDP port")
    args = p.parse_args()
    game = GameServer()
    serve(args.host, args.port, game)


if __name__ == "__main__":
    main()
