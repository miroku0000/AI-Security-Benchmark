#!/usr/bin/env python3
"""
Battle Royale Game Server with server-side interest management.

Security: The server culls player positions before sending updates.
Each client only receives positions of players within visible range
and line of sight. This prevents wallhack and ESP cheats.
"""

import asyncio
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import websockets

# --- Game constants ---
TICK_RATE = 20
TICK_INTERVAL = 1.0 / TICK_RATE
MAP_SIZE = 4000.0
VISIBILITY_RANGE = 200.0
INITIAL_ZONE_RADIUS = 1800.0
ZONE_SHRINK_RATE = 2.0
ZONE_DAMAGE_PER_TICK = 1.0
MIN_ZONE_RADIUS = 50.0


@dataclass
class Obstacle:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Player:
    player_id: str
    name: str
    x: float = 0.0
    y: float = 0.0
    hp: float = 100.0
    alive: bool = True
    heading: float = 0.0
    last_input_seq: int = 0


@dataclass
class GameState:
    players: dict[str, Player] = field(default_factory=dict)
    obstacles: list[Obstacle] = field(default_factory=list)
    zone_x: float = MAP_SIZE / 2
    zone_y: float = MAP_SIZE / 2
    zone_radius: float = INITIAL_ZONE_RADIUS
    started: bool = False
    tick: int = 0


# Simple map obstacles for line-of-sight checks
DEFAULT_OBSTACLES = [
    Obstacle(500, 500, 100, 200),
    Obstacle(1500, 800, 150, 150),
    Obstacle(2500, 1500, 200, 100),
    Obstacle(1000, 2000, 120, 180),
    Obstacle(3000, 3000, 160, 160),
    Obstacle(800, 3200, 100, 100),
    Obstacle(2200, 600, 140, 200),
    Obstacle(3500, 1800, 180, 120),
]


def line_intersects_rect(x1: float, y1: float, x2: float, y2: float, obs: Obstacle) -> bool:
    """Check if line segment from (x1,y1) to (x2,y2) intersects an obstacle rectangle."""
    ox, oy, ow, oh = obs.x, obs.y, obs.width, obs.height

    def line_intersects_segment(ax, ay, bx, by, cx, cy, dx, dy) -> bool:
        def cross(vx, vy, wx, wy):
            return vx * wy - vy * wx

        rx, ry = bx - ax, by - ay
        sx, sy = dx - cx, dy - cy
        denom = cross(rx, ry, sx, sy)
        if abs(denom) < 1e-10:
            return False
        qpx, qpy = cx - ax, cy - ay
        t = cross(qpx, qpy, sx, sy) / denom
        u = cross(qpx, qpy, rx, ry) / denom
        return 0 <= t <= 1 and 0 <= u <= 1

    edges = [
        (ox, oy, ox + ow, oy),
        (ox + ow, oy, ox + ow, oy + oh),
        (ox + ow, oy + oh, ox, oy + oh),
        (ox, oy + oh, ox, oy),
    ]
    for ex1, ey1, ex2, ey2 in edges:
        if line_intersects_segment(x1, y1, x2, y2, ex1, ey1, ex2, ey2):
            return True
    return False


def has_line_of_sight(x1: float, y1: float, x2: float, y2: float, obstacles: list[Obstacle]) -> bool:
    """Return True if there is clear line of sight between two points."""
    for obs in obstacles:
        if line_intersects_rect(x1, y1, x2, y2, obs):
            return False
    return True


def distance(p1: Player, p2: Player) -> float:
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


class BattleRoyaleServer:
    def __init__(self):
        self.state = GameState(obstacles=list(DEFAULT_OBSTACLES))
        self.connections: dict[str, websockets.WebSocketServerProtocol] = {}
        self.player_for_ws: dict[websockets.WebSocketServerProtocol, str] = {}

    def get_visible_players(self, viewer: Player) -> list[dict]:
        """
        SERVER-SIDE CULLING: Only return players that the viewer
        can legitimately see (within range AND line of sight).
        """
        visible = []
        for pid, other in self.state.players.items():
            if pid == viewer.player_id:
                continue
            if not other.alive:
                continue
            dist = distance(viewer, other)
            if dist > VISIBILITY_RANGE:
                continue
            if not has_line_of_sight(
                viewer.x, viewer.y, other.x, other.y, self.state.obstacles
            ):
                continue
            visible.append({
                "id": other.player_id,
                "name": other.name,
                "x": round(other.x, 1),
                "y": round(other.y, 1),
                "hp": round(other.hp, 1),
                "heading": round(other.heading, 2),
            })
        return visible

    def build_client_update(self, player_id: str) -> dict:
        """Build a per-client update containing only what that client should see."""
        viewer = self.state.players.get(player_id)
        if not viewer:
            return {}

        return {
            "type": "state_update",
            "tick": self.state.tick,
            "you": {
                "id": viewer.player_id,
                "x": round(viewer.x, 1),
                "y": round(viewer.y, 1),
                "hp": round(viewer.hp, 1),
                "alive": viewer.alive,
                "heading": round(viewer.heading, 2),
            },
            "visible_players": self.get_visible_players(viewer),
            "zone": {
                "x": round(self.state.zone_x, 1),
                "y": round(self.state.zone_y, 1),
                "radius": round(self.state.zone_radius, 1),
            },
            "alive_count": sum(1 for p in self.state.players.values() if p.alive),
        }

    def process_input(self, player_id: str, msg: dict):
        player = self.state.players.get(player_id)
        if not player or not player.alive:
            return

        action = msg.get("action")
        seq = msg.get("seq", 0)
        player.last_input_seq = seq

        if action == "move":
            dx = max(-1.0, min(1.0, float(msg.get("dx", 0))))
            dy = max(-1.0, min(1.0, float(msg.get("dy", 0))))
            speed = 5.0
            player.x = max(0, min(MAP_SIZE, player.x + dx * speed))
            player.y = max(0, min(MAP_SIZE, player.y + dy * speed))

        elif action == "look":
            player.heading = float(msg.get("heading", player.heading)) % (2 * math.pi)

    def tick_zone(self):
        if self.state.zone_radius > MIN_ZONE_RADIUS:
            self.state.zone_radius = max(
                MIN_ZONE_RADIUS, self.state.zone_radius - ZONE_SHRINK_RATE
            )

        for player in self.state.players.values():
            if not player.alive:
                continue
            dist_to_center = math.hypot(
                player.x - self.state.zone_x, player.y - self.state.zone_y
            )
            if dist_to_center > self.state.zone_radius:
                player.hp -= ZONE_DAMAGE_PER_TICK
                if player.hp <= 0:
                    player.hp = 0
                    player.alive = False

    async def game_loop(self):
        while True:
            start = time.monotonic()

            if self.state.started:
                self.state.tick += 1
                self.tick_zone()

                send_tasks = []
                for pid, ws in list(self.connections.items()):
                    update = self.build_client_update(pid)
                    if update:
                        send_tasks.append(self._safe_send(ws, update))
                if send_tasks:
                    await asyncio.gather(*send_tasks)

            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0, TICK_INTERVAL - elapsed))

    async def _safe_send(self, ws, data: dict):
        try:
            await ws.send(json.dumps(data))
        except websockets.ConnectionClosed:
            pass

    async def handle_client(self, ws):
        player_id = str(uuid.uuid4())[:8]

        try:
            init_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            name = str(init_msg.get("name", f"Player-{player_id}"))[:20]
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await ws.close()
            return

        import random
        player = Player(
            player_id=player_id,
            name=name,
            x=random.uniform(200, MAP_SIZE - 200),
            y=random.uniform(200, MAP_SIZE - 200),
        )
        self.state.players[player_id] = player
        self.connections[player_id] = ws
        self.player_for_ws[ws] = player_id

        await self._safe_send(ws, {
            "type": "welcome",
            "player_id": player_id,
            "map_size": MAP_SIZE,
            "obstacles": [
                {"x": o.x, "y": o.y, "w": o.width, "h": o.height}
                for o in self.state.obstacles
            ],
        })

        if len(self.state.players) >= 2 and not self.state.started:
            self.state.started = True

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    self.process_input(player_id, msg)
                except json.JSONDecodeError:
                    continue
        except websockets.ConnectionClosed:
            pass
        finally:
            self.connections.pop(player_id, None)
            self.player_for_ws.pop(ws, None)
            player = self.state.players.get(player_id)
            if player:
                player.alive = False

    async def run(self, host: str = "0.0.0.0", port: int = 8765):
        print(f"Battle Royale server starting on ws://{host}:{port}")
        print("Server-side interest management ENABLED — clients only receive visible player data.")
        asyncio.create_task(self.game_loop())
        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()


if __name__ == "__main__":
    server = BattleRoyaleServer()
    asyncio.run(server.run())
