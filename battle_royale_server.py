#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import random
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PlayerState:
    player_id: str
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    vx: float
    vy: float
    vz: float
    health: float
    shield: float
    team_id: int
    alive: bool
    stance: str
    weapon_id: str


def _default_obstacles() -> List[List[float]]:
    return [
        [100.0, 100.0, 500.0, 100.0],
        [500.0, 100.0, 500.0, 400.0],
        [-200.0, -300.0, 200.0, -300.0],
        [0.0, 0.0, 0.0, 600.0],
        [-800.0, 200.0, -400.0, 600.0],
        [300.0, -500.0, 900.0, -200.0],
    ]


class BattleRoyaleServer:
    def __init__(
        self,
        tick_hz: float = 20.0,
        world_bounds: float = 2000.0,
    ) -> None:
        self.tick_hz = tick_hz
        self.dt = 1.0 / tick_hz
        self.world_bounds = world_bounds
        self.obstacles = _default_obstacles()
        self.players: Dict[str, PlayerState] = {}
        self.writer_by_pid: Dict[str, asyncio.StreamWriter] = {}
        self.pid_by_writer_id: Dict[int, str] = {}
        self._next_id = 0
        self._lock = asyncio.Lock()
        self._running = True
        self.tick = 0
        self.match_start_mono = time.monotonic()
        self._broadcast_queue: asyncio.Queue[Optional[str]] = asyncio.Queue(maxsize=256)

    def _gen_player_id(self) -> str:
        self._next_id += 1
        return f"p{self._next_id}"

    def _random_spawn(self) -> Tuple[float, float, float]:
        b = self.world_bounds * 0.45
        return (
            random.uniform(-b, b),
            random.uniform(-b, b),
            0.0,
        )

    def _clamp_world(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        lim = self.world_bounds
        return (
            max(-lim, min(lim, x)),
            max(-lim, min(lim, y)),
            max(0.0, min(500.0, z)),
        )

    def _simulate_player(self, p: PlayerState) -> None:
        if not p.alive:
            p.vx = p.vy = p.vz = 0.0
            return
        p.x += p.vx * self.dt
        p.y += p.vy * self.dt
        p.z += p.vz * self.dt
        p.x, p.y, p.z = self._clamp_world(p.x, p.y, p.z)
        damp = 0.85
        p.vx *= damp
        p.vy *= damp
        p.vz *= damp

    def _build_full_snapshot(self) -> Dict[str, Any]:
        server_time = time.time()
        elapsed = time.monotonic() - self.match_start_mono
        players = [asdict(p) for p in self.players.values()]
        return {
            "type": "snapshot",
            "tick": self.tick,
            "server_time": server_time,
            "elapsed_match_s": elapsed,
            "tick_hz": self.tick_hz,
            "dt": self.dt,
            "world": {
                "bounds": self.world_bounds,
                "name": "arena_01",
            },
            "static_geometry": {
                "obstacle_segments": self.obstacles,
            },
            "players": players,
        }

    async def _broadcast_worker(self) -> None:
        while self._running:
            msg = await self._broadcast_queue.get()
            if msg is None:
                break
            dead: List[asyncio.StreamWriter] = []
            for w in list({id(w): w for w in self.writer_by_pid.values()}.values()):
                try:
                    w.write((msg + "\n").encode("utf-8"))
                    await w.drain()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    dead.append(w)
            for w in dead:
                await self._disconnect_writer(w)

    async def _disconnect_writer(self, writer: asyncio.StreamWriter) -> None:
        wid = id(writer)
        pid = self.pid_by_writer_id.pop(wid, None)
        if pid:
            self.writer_by_pid.pop(pid, None)
            async with self._lock:
                if pid in self.players:
                    self.players[pid].alive = False
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        player_id = self._gen_player_id()
        sx, sy, sz = self._random_spawn()
        team_id = random.randint(0, 1)
        async with self._lock:
            self.players[player_id] = PlayerState(
                player_id=player_id,
                x=sx,
                y=sy,
                z=sz,
                yaw=0.0,
                pitch=0.0,
                vx=0.0,
                vy=0.0,
                vz=0.0,
                health=100.0,
                shield=50.0,
                team_id=team_id,
                alive=True,
                stance="stand",
                weapon_id="rifle",
            )
        self.writer_by_pid[player_id] = writer
        self.pid_by_writer_id[id(writer)] = player_id
        welcome = {
            "type": "welcome",
            "player_id": player_id,
            "tick_hz": self.tick_hz,
            "note": "Full snapshots are broadcast; filter by distance/LOS on the client.",
        }
        writer.write((json.dumps(welcome) + "\n").encode("utf-8"))
        await writer.drain()
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                await self._apply_client_message(player_id, msg)
        finally:
            await self._disconnect_writer(writer)
            async with self._lock:
                self.players.pop(player_id, None)

    async def _apply_client_message(self, player_id: str, msg: Dict[str, Any]) -> None:
        t = msg.get("type")
        async with self._lock:
            p = self.players.get(player_id)
            if not p or not p.alive:
                return
            if t == "look":
                p.yaw = float(msg.get("yaw", p.yaw))
                p.pitch = float(msg.get("pitch", p.pitch))
            elif t == "move":
                mx = float(msg.get("mx", 0.0))
                my = float(msg.get("my", 0.0))
                mz = float(msg.get("mz", 0.0))
                speed = float(msg.get("speed", 12.0))
                n = math.hypot(mx, my, mz)
                if n > 1e-6:
                    mx /= n
                    my /= n
                    mz /= n
                cy = math.cos(p.yaw)
                sy = math.sin(p.yaw)
                wx = mx * cy - my * sy
                wy = mx * sy + my * cy
                p.vx = wx * speed
                p.vy = wy * speed
                p.vz = mz * speed * 0.5
            elif t == "stance":
                st = str(msg.get("stance", "stand"))
                if st in ("stand", "crouch", "prone"):
                    p.stance = st
            elif t == "damage_report":
                target = str(msg.get("target_player_id", ""))
                amount = float(msg.get("amount", 0.0))
                if target in self.players and target != player_id:
                    tgt = self.players[target]
                    if tgt.alive and amount > 0:
                        rem = amount
                        if tgt.shield > 0:
                            use = min(tgt.shield, rem)
                            tgt.shield -= use
                            rem -= use
                        tgt.health -= rem
                        if tgt.health <= 0:
                            tgt.health = 0.0
                            tgt.alive = False
                            tgt.vx = tgt.vy = tgt.vz = 0.0

    async def _game_loop(self) -> None:
        interval = self.dt
        while self._running:
            loop_start = time.monotonic()
            async with self._lock:
                self.tick += 1
                for p in self.players.values():
                    self._simulate_player(p)
                snap = self._build_full_snapshot()
            payload = json.dumps(snap, separators=(",", ":"))
            try:
                self._broadcast_queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass
            elapsed = time.monotonic() - loop_start
            await asyncio.sleep(max(0.0, interval - elapsed))

    async def run(self, host: str, port: int) -> None:
        self._running = True
        broadcaster = asyncio.create_task(self._broadcast_worker())
        game = asyncio.create_task(self._game_loop())
        server = await asyncio.start_server(
            self._handle_client, host, port, reuse_address=True
        )
        addrs = ", ".join(str(s.getsockname()) for s in server.sockets or [])
        print(f"Battle royale server on {addrs}", flush=True)
        async with server:
            await server.serve_forever()
        self._running = False
        await self._broadcast_queue.put(None)
        await broadcaster
        game.cancel()
        try:
            await game
        except asyncio.CancelledError:
            pass


async def _amain() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--tick-hz", type=float, default=20.0)
    ap.add_argument("--world-bounds", type=float, default=2000.0)
    args = ap.parse_args()
    srv = BattleRoyaleServer(tick_hz=args.tick_hz, world_bounds=args.world_bounds)
    await srv.run(args.host, args.port)


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
