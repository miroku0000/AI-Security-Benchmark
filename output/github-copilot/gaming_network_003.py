#!/usr/bin/env python3

import socket
import json
import struct
import time
import threading
from datetime import datetime
from typing import Dict, List, Any


class Player:
    def __init__(self, player_id: int, name: str, score: int, level: int):
        self.player_id = player_id
        self.name = name
        self.score = score
        self.level = level
        self.join_time = time.time()
        self.kills = 0
        self.deaths = 0
        self.ping_ms = 0
        self.is_admin = player_id == 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.player_id,
            "name": self.name,
            "score": self.score,
            "level": self.level,
            "kills": self.kills,
            "deaths": self.deaths,
            "ping_ms": self.ping_ms,
            "is_admin": self.is_admin,
            "join_time": datetime.fromtimestamp(self.join_time).isoformat()
        }


class GameState:
    def __init__(self):
        self.server_name = "Battle Arena Pro"
        self.map_name = "Forest Fortress"
        self.game_mode = "Team Deathmatch"
        self.difficulty = "Hard"
        self.max_players = 32
        self.players: List[Player] = []
        self.server_start_time = time.time()
        self.uptime_seconds = 0
        self.match_start_time = time.time() - 3600
        self.kills_total = 0
        self.rounds_completed = 42
        self.average_ping = 45
        self.tick_rate = 60
        self.fps = 144
        self.port = 27015
        self.region = "US-West"
        self.version = "1.2.4"
        self.anti_cheat_enabled = True
        self.voice_chat_enabled = True
        self.ranked = True
        self.password_protected = False
        self.spectators_allowed = True

    def add_player(self, player: Player):
        if len(self.players) < self.max_players:
            self.players.append(player)

    def update(self):
        self.uptime_seconds = int(time.time() - self.server_start_time)
        for player in self.players:
            player.ping_ms = 20 + (player.player_id % 50)
            self.average_ping = sum(p.ping_ms for p in self.players) // len(self.players) if self.players else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_info": {
                "name": self.server_name,
                "version": self.version,
                "address": "game.example.com",
                "port": self.port,
                "region": self.region,
                "country_code": "US",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": self.uptime_seconds
            },
            "game_state": {
                "map": self.map_name,
                "game_mode": self.game_mode,
                "difficulty": self.difficulty,
                "match_duration_seconds": int(time.time() - self.match_start_time),
                "rounds_completed": self.rounds_completed,
                "status": "in_progress" if self.players else "waiting"
            },
            "performance": {
                "tick_rate": self.tick_rate,
                "fps": self.fps,
                "average_ping_ms": self.average_ping,
                "player_count": len(self.players),
                "max_players": self.max_players,
                "available_slots": self.max_players - len(self.players)
            },
            "settings": {
                "anti_cheat_enabled": self.anti_cheat_enabled,
                "voice_chat_enabled": self.voice_chat_enabled,
                "ranked": self.ranked,
                "password_protected": self.password_protected,
                "spectators_allowed": self.spectators_allowed
            },
            "players": [player.to_dict() for player in self.players],
            "stats": {
                "total_kills": self.kills_total,
                "total_matches": 156,
                "total_hours_played": 2847,
                "player_retention_rate": 0.87
            }
        }


class GameServerUDP:
    def __init__(self, host: str = "0.0.0.0", port: int = 27015, max_payload: int = 65500):
        self.host = host
        self.port = port
        self.max_payload = max_payload
        self.socket = None
        self.running = False
        self.game_state = GameState()
        self.query_count = 0
        self.last_query_time = time.time()
        self.queries_per_second = 0

    def initialize_game_state(self):
        players_data = [
            ("Phoenix", 2450, 28),
            ("ShadowNinja", 1890, 25),
            ("BlazeFury", 2100, 27),
            ("IceStorm", 1650, 24),
            ("Sentinel", 2300, 28),
            ("Phantom", 1750, 26),
            ("Vortex", 1920, 25),
            ("Nexus", 2050, 27),
            ("Cipher", 1800, 24),
            ("Reaper", 1680, 23),
            ("Ghost", 1920, 26),
            ("Titan", 2200, 28),
            ("Rogue", 1550, 22),
            ("Echo", 1780, 25),
            ("Inferno", 2000, 27),
        ]

        for idx, (name, score, level) in enumerate(players_data, start=1):
            player = Player(idx, name, score, level)
            player.kills = 15 + (idx % 20)
            player.deaths = 5 + (idx % 8)
            self.game_state.add_player(player)

    def create_response(self) -> bytes:
        self.game_state.update()
        game_data = self.game_state.to_dict()
        json_str = json.dumps(game_data, separators=(',', ':'))
        
        response = b'\x00\x00\x00\x00'
        response += json_str.encode('utf-8')
        
        return response

    def handle_query(self, data: bytes, addr: tuple) -> bytes:
        self.query_count += 1
        current_time = time.time()
        
        if current_time - self.last_query_time >= 1.0:
            self.queries_per_second = self.query_count
            self.query_count = 0
            self.last_query_time = current_time
        
        query = data.decode('utf-8', errors='ignore').strip()
        
        if query == "STATUS":
            return self.create_response()
        elif query == "PING":
            return b'\x00\x00\x00\x00PONG'
        elif query == "INFO":
            info = {
                "server_name": self.game_state.server_name,
                "player_count": len(self.game_state.players),
                "max_players": self.game_state.max_players
            }
            return b'\x00\x00\x00\x00' + json.dumps(info).encode('utf-8')
        else:
            default_response = self.create_response()
            return default_response

    def chunk_response(self, response: bytes) -> List[bytes]:
        chunk_size = self.max_payload - 100
        chunks = []
        
        if len(response) <= chunk_size:
            return [response]
        
        header = response[:4]
        data = response[4:]
        
        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        
        for i in range(total_chunks):
            chunk_header = struct.pack('>HH', i, total_chunks)
            chunk_data = data[i * chunk_size:(i + 1) * chunk_size]
            chunks.append(header + chunk_header + chunk_data)
        
        return chunks

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if hasattr(socket, 'SO_REUSEPORT'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        self.socket.bind((self.host, self.port))
        self.running = True
        
        print(f"[*] Game Server UDP listening on {self.host}:{self.port}")
        print(f"[*] Max payload: {self.max_payload} bytes")
        self.initialize_game_state()
        print(f"[*] Game state initialized with {len(self.game_state.players)} players")

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        print("[*] Game Server stopped")

    def serve(self):
        try:
            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    data, addr = self.socket.recvfrom(1024)
                    
                    print(f"[+] Query from {addr[0]}:{addr[1]}")
                    
                    response = self.handle_query(data, addr)
                    chunks = self.chunk_response(response)
                    
                    for chunk in chunks:
                        try:
                            self.socket.sendto(chunk, addr)
                            time.sleep(0.001)
                        except Exception as e:
                            print(f"[-] Error sending chunk: {e}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[-] Error handling query: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
        finally:
            self.stop()


def main():
    server = GameServerUDP(host="0.0.0.0", port=27015, max_payload=65500)
    server.start()
    server.serve()


if __name__ == "__main__":
    main()