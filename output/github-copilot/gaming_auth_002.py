#!/usr/bin/env python3

import asyncio
import json
import uuid
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, Set, Optional, Tuple
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Item:
    item_id: str
    name: str
    item_type: str
    owner_id: str
    rarity: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Inventory:
    player_id: str
    items: Dict[str, Item] = field(default_factory=dict)
    max_slots: int = 20
    
    def add_item(self, item: Item) -> bool:
        if len(self.items) >= self.max_slots:
            return False
        self.items[item.item_id] = item
        return True
    
    def remove_item(self, item_id: str) -> Optional[Item]:
        return self.items.pop(item_id, None)
    
    def get_item(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)
    
    def has_item(self, item_id: str) -> bool:
        return item_id in self.items
    
    def list_items(self):
        return [item.to_dict() for item in self.items.values()]


@dataclass
class Player:
    player_id: str
    username: str
    level: int = 1
    gold: int = 100
    experience: int = 0
    inventory: Inventory = field(default_factory=lambda: Inventory(''))
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        self.inventory.player_id = self.player_id
    
    def to_dict(self):
        return {'player_id': self.player_id, 'username': self.username, 'level': self.level, 'gold': self.gold, 'experience': self.experience, 'connected_at': self.connected_at}


class TradeRequest:
    def __init__(self, trade_id: str, initiator_id: str, receiver_id: str, initiator_items: Set[str], receiver_items: Set[str]):
        self.trade_id = trade_id
        self.initiator_id = initiator_id
        self.receiver_id = receiver_id
        self.initiator_items = initiator_items
        self.receiver_items = receiver_items
        self.initiator_accepted = False
        self.receiver_accepted = False
        self.created_at = datetime.utcnow()
        self.lock = asyncio.Lock()
    
    def is_valid(self) -> bool:
        return (datetime.utcnow() - self.created_at).total_seconds() < 300
    
    async def accept_by_initiator(self) -> bool:
        async with self.lock:
            self.initiator_accepted = True
            return self.initiator_accepted and self.receiver_accepted
    
    async def accept_by_receiver(self) -> bool:
        async with self.lock:
            self.receiver_accepted = True
            return self.initiator_accepted and self.receiver_accepted


class GameServer:
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.players: Dict[str, Player] = {}
        self.player_connections: Dict[str, WebSocketServerProtocol] = {}
        self.trade_requests: Dict[str, TradeRequest] = {}
        self.global_lock = asyncio.Lock()
        self.all_items: Dict[str, Item] = {}
    
    async def register_player(self, websocket: WebSocketServerProtocol, username: str) -> Optional[str]:
        player_id = str(uuid.uuid4())
        player = Player(player_id=player_id, username=username)
        async with self.global_lock:
            if username in [p.username for p in self.players.values()]:
                await self._send_error(websocket, 'username_taken', f'Username {username} already taken')
                return None
            self.players[player_id] = player
            self.player_connections[player_id] = websocket
        logger.info(f'Player {username} registered: {player_id}')
        await self._broadcast_player_joined(player)
        return player_id
    
    async def unregister_player(self, player_id: str):
        async with self.global_lock:
            if player_id in self.players:
                player = self.players.pop(player_id)
                self.player_connections.pop(player_id, None)
                logger.info(f'Player {player.username} disconnected')
    
    async def add_item_to_inventory(self, player_id: str, item_name: str, item_type: str, rarity: str = 'common') -> Optional[str]:
        if player_id not in self.players:
            return None
        item_id = str(uuid.uuid4())
        item = Item(item_id=item_id, name=item_name, item_type=item_type, owner_id=player_id, rarity=rarity)
        async with self.global_lock:
            player = self.players[player_id]
            if player.inventory.add_item(item):
                self.all_items[item_id] = item
                return item_id
        return None
    
    async def transfer_item(self, from_player_id: str, to_player_id: str, item_id: str) -> Tuple[bool, str]:
        if from_player_id not in self.players or to_player_id not in self.players:
            return False, 'Players not found'
        async with self.global_lock:
            from_player = self.players[from_player_id]
            to_player = self.players[to_player_id]
            item = from_player.inventory.get_item(item_id)
            if not item:
                return False, 'Item not found'
            if len(to_player.inventory.items) >= to_player.inventory.max_slots:
                return False, 'Inventory full'
            from_player.inventory.remove_item(item_id)
            item.owner_id = to_player_id
            to_player.inventory.add_item(item)
            self.all_items[item_id] = item
        logger.info(f'Item {item_id} transferred')
        return True, 'Success'
    
    async def initiate_trade(self, initiator_id: str, receiver_id: str, initiator_items: Set[str], receiver_items: Set[str]) -> Tuple[bool, str]:
        if initiator_id not in self.players or receiver_id not in self.players:
            return False, 'Players not found'
        if initiator_id == receiver_id:
            return False, 'Cannot trade with self'
        async with self.global_lock:
            initiator = self.players[initiator_id]
            receiver = self.players[receiver_id]
            for item_id in initiator_items:
                if not initiator.inventory.has_item(item_id):
                    return False, f'Item {item_id} not found'
            for item_id in receiver_items:
                if not receiver.inventory.has_item(item_id):
                    return False, f'Item {item_id} not found'
            if len(initiator.inventory.items) - len(initiator_items) + len(receiver_items) > 20:
                return False, 'Slots exceeded'
            if len(receiver.inventory.items) - len(receiver_items) + len(initiator_items) > 20:
                return False, 'Slots exceeded'
        trade_id = str(uuid.uuid4())
        self.trade_requests[trade_id] = TradeRequest(trade_id, initiator_id, receiver_id, initiator_items, receiver_items)
        logger.info(f'Trade {trade_id} initiated')
        return True, trade_id
    
    async def accept_trade(self, trade_id: str, player_id: str) -> Tuple[bool, str]:
        if trade_id not in self.trade_requests:
            return False, 'Trade not found'
        trade = self.trade_requests[trade_id]
        if not trade.is_valid():
            del self.trade_requests[trade_id]
            return False, 'Expired'
        if player_id == trade.initiator_id:
            both_accepted = await trade.accept_by_initiator()
        elif player_id == trade.receiver_id:
            both_accepted = await trade.accept_by_receiver()
        else:
            return False, 'Not participant'
        if both_accepted:
            success, message = await self._execute_trade(trade)
            del self.trade_requests[trade_id]
            return success, message
        return True, 'Recorded'
    
    async def _execute_trade(self, trade: TradeRequest) -> Tuple[bool, str]:
        async with self.global_lock:
            initiator = self.players.get(trade.initiator_id)
            receiver = self.players.get(trade.receiver_id)
            if not initiator or not receiver:
                return False, 'Players gone'
            init_items = []
            recv_items = []
            for item_id in trade.initiator_items:
                item = initiator.inventory.get_item(item_id)
                if not item:
                    return False, 'Item missing'
                init_items.append(item)
            for item_id in trade.receiver_items:
                item = receiver.inventory.get_item(item_id)
                if not item:
                    return False, 'Item missing'
                recv_items.append(item)
            for item in init_items:
                initiator.inventory.remove_item(item.item_id)
                item.owner_id = receiver.player_id
                receiver.inventory.add_item(item)
            for item in recv_items:
                receiver.inventory.remove_item(item.item_id)
                item.owner_id = initiator.player_id
                initiator.inventory.add_item(item)
        await self._notify_trade_complete(trade)
        return True, 'Complete'
    
    async def _notify_trade_complete(self, trade: TradeRequest):
        msg = {'type': 'trade_complete', 'trade_id': trade.trade_id, 'status': 'success'}
        for player_id in [trade.initiator_id, trade.receiver_id]:
            ws = self.player_connections.get(player_id)
            if ws:
                await self._send_message(ws, msg)
    
    async def _broadcast_player_joined(self, player: Player):
        msg = {'type': 'player_joined', 'player': player.to_dict()}
        await self._broadcast(msg, exclude_player=player.player_id)
    
    async def _broadcast(self, message: dict, exclude_player: Optional[str] = None):
        for player_id, ws in self.player_connections.items():
            if exclude_player and player_id == exclude_player:
                continue
            try:
                await self._send_message(ws, message)
            except:
                pass
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: dict):
        await websocket.send(json.dumps(message))
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_code: str, message: str):
        await self._send_message(websocket, {'type': 'error', 'error_code': error_code, 'message': message})
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        player_id = None
        try:
            async for msg in websocket:
                data = json.loads(msg)
                response = await self._handle_message(player_id, data, websocket)
                if data.get('type') == 'join' and response.get('success'):
                    player_id = response.get('player_id')
                await self._send_message(websocket, response)
        except:
            pass
        finally:
            if player_id:
                await self.unregister_player(player_id)
    
    async def _handle_message(self, player_id: Optional[str], data: dict, websocket: WebSocketServerProtocol) -> dict:
        msg_type = data.get('type')
        if msg_type == 'join':
            username = data.get('username', '').strip()
            if not username:
                return {'success': False, 'message': 'Username required'}
            new_id = await self.register_player(websocket, username)
            if new_id:
                return {'success': True, 'type': 'join_response', 'player_id': new_id, 'message': f'Welcome {username}!'}
            return {'success': False, 'message': 'Failed'}
        if not player_id:
            return {'success': False, 'message': 'Join first'}
        if msg_type == 'get_inventory':
            player = self.players.get(player_id)
            if not player:
                return {'success': False}
            return {'success': True, 'type': 'inventory', 'items': player.inventory.list_items(), 'slots_used': len(player.inventory.items), 'max_slots': 20}
        elif msg_type == 'add_item':
            item_id = await self.add_item_to_inventory(player_id, data.get('name', 'Item'), data.get('item_type', 'misc'), data.get('rarity', 'common'))
            if item_id:
                return {'success': True, 'type': 'item_added', 'item_id': item_id}
            return {'success': False, 'message': 'Inventory full'}
        elif msg_type == 'transfer_item':
            success, msg = await self.transfer_item(player_id, data.get('to_player_id'), data.get('item_id'))
            return {'success': success, 'message': msg}
        elif msg_type == 'initiate_trade':
            success, result = await self.initiate_trade(player_id, data.get('receiver_id'), set(data.get('initiator_items', [])), set(data.get('receiver_items', [])))
            if success:
                return {'success': True, 'trade_id': result}
            return {'success': False, 'message': result}
        elif msg_type == 'accept_trade':
            success, msg = await self.accept_trade(data.get('trade_id'), player_id)
            return {'success': success, 'message': msg}
        elif msg_type == 'get_player_info':
            player = self.players.get(player_id)
            if not player:
                return {'success': False}
            return {'success': True, 'player': player.to_dict()}
        elif msg_type == 'list_players':
            return {'success': True, 'players': [{'player_id': p.player_id, 'username': p.username} for p in self.players.values()]}
        return {'success': False}
    
    async def start(self):
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f'Game server started on ws://{self.host}:{self.port}')
            await asyncio.Future()


async def main():
    server = GameServer(host='0.0.0.0', port=8765)
    await server.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Server shutdown')