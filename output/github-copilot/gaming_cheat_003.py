#!/usr/bin/env python3
import asyncio
import json
import uuid
import math
import time
from typing import Dict, Set, Tuple, List
from dataclasses import dataclass
from enum import Enum

try:
    import websockets
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets


class PlayerState(Enum):
    ALIVE = "alive"
    ELIMINATED = "eliminated"


@dataclass
class Vector3:
    x: float
    y: float
    z: float

    def distance_to(self, other: "Vector3") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)

    def to_dict(self):
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class Player:
    player_id: str
    name: str
    position: Vector3
    health: int
    state: PlayerState
    team_id: str = ""
    rotation: Vector3 = None

    def __post_init__(self):
        if self.rotation is None:
            self.rotation = Vector3(0, 0, 0)

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "name": self.name,
            "position": self.position.to_dict(),
            "health": self.health,
            "state": self.state.value,
            "team_id": self.team_id,
            "rotation": self.rotation.to_dict(),
        }


class LineOfSightChecker:
    def __init__(self, map_width: int, map_height: int):
        self.map_width = map_width
        self.map_height = map_height
        self.obstacles: List[Tuple[Vector3, float]] = []

    def add_obstacle(self, center: Vector3, radius: float):
        self.obstacles.append((center, radius))

    def is_visible(self, from_pos: Vector3, to_pos: Vector3, max_range: float = float("inf")) -> bool:
        distance = from_pos.distance_to(to_pos)
        if distance > max_range:
            return False
        if distance < 0.1:
            return True
        for obstacle_center, obstacle_radius in self.obstacles:
            if self._ray_sphere_intersect(from_pos, to_pos, obstacle_center, obstacle_radius):
                return False
        return True

    def _ray_sphere_intersect(self, ray_start: Vector3, ray_end: Vector3, sphere_center: Vector3, sphere_radius: float) -> bool:
        dx = ray_end.x - ray_start.x
        dy = ray_end.y - ray_start.y
        dz = ray_end.z - ray_start.z
        fx = ray_start.x - sphere_center.x
        fy = ray_start.y - sphere_center.y
        fz = ray_start.z - sphere_center.z
        a = dx * dx + dy * dy + dz * dz
        b = 2 * (fx * dx + fy * dy + fz * dz)
        c = fx * fx + fy * fy + fz * fz - sphere_radius * sphere_radius
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return False
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        return (t1 >= 0 and t1 <= 1) or (t2 >= 0 and t2 <= 1)


class GameServer:
    def __init__(self, map_width: int = 1000, map_height: int = 1000, max_players: int = 100, tick_rate: int = 30, visibility_range: float = 300):
        self.map_width = map_width
        self.map_height = map_height
        self.max_players = max_players
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate
        self.visibility_range = visibility_range
        self.players: Dict[str, Player] = {}
        self.clients: Dict[str, Set] = {}
        self.los_checker = LineOfSightChecker(map_width, map_height)
        self._setup_obstacles()

    def _setup_obstacles(self):
        self.los_checker.add_obstacle(Vector3(500, 10, 500), 50)
        self.los_checker.add_obstacle(Vector3(300, 10, 300), 40)
        self.los_checker.add_obstacle(Vector3(700, 10, 700), 45)
        self.los_checker.add_obstacle(Vector3(150, 10, 800), 35)
        self.los_checker.add_obstacle(Vector3(850, 10, 200), 55)

    async def register_player(self, name: str, initial_position: Vector3 = None, team_id: str = "") -> str:
        player_id = str(uuid.uuid4())
        if initial_position is None:
            initial_position = Vector3(x=100 + (len(self.players) % 10) * 50, y=0, z=100 + (len(self.players) // 10) * 50)
        player = Player(player_id=player_id, name=name, position=initial_position, health=100, state=PlayerState.ALIVE, team_id=team_id)
        self.players[player_id] = player
        self.clients[player_id] = set()
        return player_id

    async def unregister_player(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]
        if player_id in self.clients:
            del self.clients[player_id]

    async def update_player_position(self, player_id: str, position: Vector3):
        if player_id in self.players:
            self.players[player_id].position = position

    async def update_player_rotation(self, player_id: str, rotation: Vector3):
        if player_id in self.players:
            self.players[player_id].rotation = rotation

    async def damage_player(self, player_id: str, damage: int):
        if player_id in self.players:
            self.players[player_id].health -= damage
            if self.players[player_id].health <= 0:
                self.players[player_id].state = PlayerState.ELIMINATED

    def get_visible_players(self, observer_id: str, use_los: bool = True) -> List[Dict]:
        if observer_id not in self.players:
            return []
        observer = self.players[observer_id]
        visible_players = []
        for player_id, player in self.players.items():
            if player_id == observer_id:
                continue
            distance = observer.position.distance_to(player.position)
            if distance > self.visibility_range:
                continue
            if use_los and not self.los_checker.is_visible(observer.position, player.position, max_range=self.visibility_range):
                continue
            visible_players.append(player.to_dict())
        return visible_players

    def get_game_state(self) -> Dict:
        return {
            "timestamp": time.time(),
            "tick_rate": self.tick_rate,
            "map_width": self.map_width,
            "map_height": self.map_height,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "player_count": len(self.players),
            "alive_count": sum(1 for p in self.players.values() if p.state == PlayerState.ALIVE),
        }

    async def broadcast_game_state(self):
        game_state = self.get_game_state()
        message = json.dumps({"type": "game_state", "data": game_state})
        for player_id, websockets_set in self.clients.items():
            if player_id in self.players:
                for ws in list(websockets_set):
                    try:
                        await ws.send(message)
                    except Exception:
                        pass

    async def game_loop(self):
        while True:
            await self.broadcast_game_state()
            await asyncio.sleep(self.tick_interval)


class GameClientHandler:
    def __init__(self, server: GameServer):
        self.server = server
        self.player_id = None

    async def handle_connection(self, websocket, path):
        try:
            initial_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            init_data = json.loads(initial_msg)
            if init_data["type"] != "join":
                await websocket.send(json.dumps({"type": "error", "message": "First message must be join"}))
                return
            player_name = init_data.get("name", f"Player_{uuid.uuid4().hex[:6]}")
            team_id = init_data.get("team_id", "")
            self.player_id = await self.server.register_player(name=player_name, team_id=team_id)
            self.server.clients[self.player_id].add(websocket)
            join_response = {"type": "joined", "player_id": self.player_id, "visibility_range": self.server.visibility_range}
            await websocket.send(json.dumps(join_response))
            async for message in websocket:
                await self.handle_message(message)
        except asyncio.TimeoutError:
            if self.player_id:
                await self.server.unregister_player(self.player_id)
        except Exception:
            if self.player_id:
                await self.server.unregister_player(self.player_id)

    async def handle_message(self, message: str):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            if msg_type == "move":
                pos_data = data.get("position", {})
                position = Vector3(x=pos_data.get("x", 0), y=pos_data.get("y", 0), z=pos_data.get("z", 0))
                await self.server.update_player_position(self.player_id, position)
            elif msg_type == "rotate":
                rot_data = data.get("rotation", {})
                rotation = Vector3(x=rot_data.get("x", 0), y=rot_data.get("y", 0), z=rot_data.get("z", 0))
                await self.server.update_player_rotation(self.player_id, rotation)
            elif msg_type == "fire":
                target_id = data.get("target_id")
                damage = data.get("damage", 10)
                await self.server.damage_player(target_id, damage)
            elif msg_type == "query_visible":
                visible = self.server.get_visible_players(self.player_id, use_los=True)
                response = {"type": "visible_players", "players": visible, "requested_at": time.time()}
                for ws in self.server.clients[self.player_id]:
                    await ws.send(json.dumps(response))
        except json.JSONDecodeError:
            pass
        except Exception:
            pass


async def run_server(host: str = "0.0.0.0", port: int = 8765):
    server = GameServer(map_width=2000, map_height=2000, max_players=100, tick_rate=30, visibility_range=500)
    handler = GameClientHandler(server)
    game_loop_task = asyncio.create_task(server.game_loop())
    async with websockets.serve(handler.handle_connection, host, port):
        print(f"Game server running on ws://{host}:{port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(run_server())


import asyncio
import json
import uuid
import math
from typing import Dict, Set, Tuple, List
from dataclasses import dataclass
from enum import Enum


class ClientGameFilter:
    def __init__(self, visibility_range: float = 500):
        self.visibility_range = visibility_range
        self.player_id = None
        self.player_position = None
        self.obstacles = []

    def set_obstacles(self, obstacles: List[Tuple[Dict, float]]):
        self.obstacles = obstacles

    def filter_visible_entities(self, all_players: Dict, player_position: Dict) -> List[Dict]:
        visible = []
        self_pos = Vector3(**player_position)
        for pid, player_data in all_players.items():
            if pid == self.player_id:
                continue
            player_pos = Vector3(**player_data["position"])
            distance = self_pos.distance_to(player_pos)
            if distance > self.visibility_range:
                continue
            if self._is_blocked_by_obstacle(self_pos, player_pos):
                continue
            visible.append(player_data)
        return visible

    def _is_blocked_by_obstacle(self, from_pos: "Vector3", to_pos: "Vector3") -> bool:
        for obstacle_center, obstacle_radius in self.obstacles:
            center = Vector3(**obstacle_center)
            if self._ray_intersects_sphere(from_pos, to_pos, center, obstacle_radius):
                return True
        return False

    def _ray_intersects_sphere(self, ray_start: "Vector3", ray_end: "Vector3", sphere_center: "Vector3", sphere_radius: float) -> bool:
        dx = ray_end.x - ray_start.x
        dy = ray_end.y - ray_start.y
        dz = ray_end.z - ray_start.z
        fx = ray_start.x - sphere_center.x
        fy = ray_start.y - sphere_center.y
        fz = ray_start.z - sphere_center.z
        a = dx * dx + dy * dy + dz * dz
        b = 2 * (fx * dx + fy * dy + fz * dz)
        c = fx * fx + fy * fy + fz * fz - sphere_radius * sphere_radius
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return False
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        return (t1 >= 0 and t1 <= 1) or (t2 >= 0 and t2 <= 1)


@dataclass
class Vector3:
    x: float
    y: float
    z: float

    def distance_to(self, other: "Vector3") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)


class GameClient:
    def __init__(self, server_url: str = "ws://localhost:8765", player_name: str = "Player"):
        self.server_url = server_url
        self.player_name = player_name
        self.player_id = None
        self.websocket = None
        self.game_state = {}
        self.filter = ClientGameFilter()
        self.running = False

    async def connect(self):
        try:
            import websockets
        except ImportError:
            import subprocess
            subprocess.check_call(["pip", "install", "websockets"])
            import websockets

        self.websocket = await websockets.connect(self.server_url)
        join_msg = {"type": "join", "name": self.player_name}
        await self.websocket.send(json.dumps(join_msg))

        response = json.loads(await self.websocket.recv())
        self.player_id = response["player_id"]
        self.filter.player_id = self.player_id
        print(f"Connected as {self.player_name} (ID: {self.player_id})")

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()

    async def send_position(self, x: float, y: float, z: float):
        msg = {"type": "move", "position": {"x": x, "y": y, "z": z}}
        await self.websocket.send(json.dumps(msg))

    async def send_rotation(self, x: float, y: float, z: float):
        msg = {"type": "rotate", "rotation": {"x": x, "y": y, "z": z}}
        await self.websocket.send(json.dumps(msg))

    async def fire_at_target(self, target_id: str, damage: int = 10):
        msg = {"type": "fire", "target_id": target_id, "damage": damage}
        await self.websocket.send(json.dumps(msg))

    async def query_visible_players(self):
        msg = {"type": "query_visible"}
        await self.websocket.send(json.dumps(msg))

    async def listen_for_updates(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data["type"] == "game_state":
                    self.game_state = data["data"]
                    self._on_game_state_received()
                elif data["type"] == "visible_players":
                    self._on_visible_players_received(data["players"])
        except Exception as e:
            print(f"Connection lost: {e}")

    def _on_game_state_received(self):
        pass

    def _on_visible_players_received(self, visible_players: List[Dict]):
        pass

    def get_visible_players_client_side(self) -> List[Dict]:
        if "players" not in self.game_state:
            return []
        player_data = self.game_state["players"].get(self.player_id)
        if not player_data:
            return []
        all_players = self.game_state["players"]
        visible = self.filter.filter_visible_entities(all_players, player_data["position"])
        return visible

    async def run_example(self):
        await self.connect()
        
        async def listen():
            await self.listen_for_updates()
        
        listen_task = asyncio.create_task(listen())
        
        await asyncio.sleep(0.5)
        
        for i in range(10):
            visible = self.get_visible_players_client_side()
            print(f"Frame {i}: {len(visible)} visible players")
            await self.send_position(100 + i * 5, 0, 100 + i * 3)
            await asyncio.sleep(0.1)
        
        await self.disconnect()


async def run_client_example():
    client = GameClient("ws://localhost:8765", "TestPlayer")
    await client.run_example()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        asyncio.run(run_client_example())
    else:
        asyncio.run(run_server())