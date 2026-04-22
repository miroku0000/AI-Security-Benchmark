import asyncio
import json
import uuid
import websockets
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Item:
    item_id: str
    name: str
    owner_id: str
    tradeable: bool = True


@dataclass
class Player:
    player_id: str
    name: str
    inventory: dict[str, Item] = field(default_factory=dict)
    websocket: Optional[object] = field(default=None, repr=False)
    pending_trade: Optional[dict] = field(default=None)


class TradeManager:
    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, player_id: str) -> asyncio.Lock:
        if player_id not in self._locks:
            self._locks[player_id] = asyncio.Lock()
        return self._locks[player_id]

    async def execute_trade(self, game, player_a_id: str, item_a_id: str,
                            player_b_id: str, item_b_id: str) -> dict:
        lock_order = sorted([player_a_id, player_b_id])
        lock1 = self._get_lock(lock_order[0])
        lock2 = self._get_lock(lock_order[1])

        async with lock1:
            async with lock2:
                player_a = game.players.get(player_a_id)
                player_b = game.players.get(player_b_id)

                if not player_a or not player_b:
                    return {"error": "One or both players not found"}

                item_a = player_a.inventory.get(item_a_id)
                item_b = player_b.inventory.get(item_b_id)

                if not item_a:
                    return {"error": f"Item {item_a_id} not in {player_a.name}'s inventory"}
                if not item_b:
                    return {"error": f"Item {item_b_id} not in {player_b.name}'s inventory"}

                if item_a.owner_id != player_a_id:
                    return {"error": f"Item {item_a_id} is not owned by {player_a.name}"}
                if item_b.owner_id != player_b_id:
                    return {"error": f"Item {item_b_id} is not owned by {player_b.name}"}

                if not item_a.tradeable or not item_b.tradeable:
                    return {"error": "One or both items are not tradeable"}

                del player_a.inventory[item_a_id]
                del player_b.inventory[item_b_id]

                item_a.owner_id = player_b_id
                item_b.owner_id = player_a_id

                player_b.inventory[item_a_id] = item_a
                player_a.inventory[item_b_id] = item_b

                return {
                    "success": True,
                    "trade": {
                        "player_a": player_a_id,
                        "received": item_b.name,
                        "player_b": player_b_id,
                        "received_b": item_a.name,
                    }
                }

    async def execute_gift(self, game, from_id: str, item_id: str,
                           to_id: str) -> dict:
        lock_order = sorted([from_id, to_id])
        lock1 = self._get_lock(lock_order[0])
        lock2 = self._get_lock(lock_order[1])

        async with lock1:
            async with lock2:
                sender = game.players.get(from_id)
                receiver = game.players.get(to_id)

                if not sender or not receiver:
                    return {"error": "One or both players not found"}

                item = sender.inventory.get(item_id)
                if not item:
                    return {"error": f"Item {item_id} not in sender's inventory"}

                if item.owner_id != from_id:
                    return {"error": "Item is not owned by sender"}

                if not item.tradeable:
                    return {"error": "Item is not tradeable"}

                del sender.inventory[item_id]
                item.owner_id = to_id
                receiver.inventory[item_id] = item

                return {
                    "success": True,
                    "gift": {
                        "from": from_id,
                        "to": to_id,
                        "item": item.name,
                    }
                }


class GameServer:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.connections: dict[object, str] = {}
        self.trade_manager = TradeManager()
        self.pending_trades: dict[str, dict] = {}

    def create_starter_items(self, player_id: str) -> dict[str, Item]:
        items = {}
        for name in ["Iron Sword", "Health Potion", "Shield"]:
            item_id = str(uuid.uuid4())
            items[item_id] = Item(item_id=item_id, name=name, owner_id=player_id)
        return items

    async def register_player(self, websocket, name: str) -> Player:
        player_id = str(uuid.uuid4())
        player = Player(player_id=player_id, name=name, websocket=websocket)
        player.inventory = self.create_starter_items(player_id)
        self.players[player_id] = player
        self.connections[websocket] = player_id
        return player

    async def send(self, websocket, message: dict):
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def broadcast(self, message: dict, exclude=None):
        for player in self.players.values():
            if player.websocket and player.websocket != exclude:
                await self.send(player.websocket, message)

    async def handle_trade_request(self, from_id: str, data: dict) -> dict:
        to_id = data.get("to_player_id")
        offer_item_id = data.get("offer_item_id")

        if not to_id or not offer_item_id:
            return {"error": "Missing to_player_id or offer_item_id"}

        sender = self.players.get(from_id)
        receiver = self.players.get(to_id)

        if not receiver:
            return {"error": "Target player not found"}

        if offer_item_id not in sender.inventory:
            return {"error": "You don't have that item"}

        trade_id = str(uuid.uuid4())
        self.pending_trades[trade_id] = {
            "from_id": from_id,
            "to_id": to_id,
            "offer_item_id": offer_item_id,
            "status": "pending",
        }

        if receiver.websocket:
            await self.send(receiver.websocket, {
                "type": "trade_request",
                "trade_id": trade_id,
                "from_player": sender.name,
                "from_player_id": from_id,
                "offered_item": sender.inventory[offer_item_id].name,
                "offered_item_id": offer_item_id,
            })

        return {"success": True, "trade_id": trade_id, "status": "pending"}

    async def handle_trade_accept(self, accepter_id: str, data: dict) -> dict:
        trade_id = data.get("trade_id")
        accept_item_id = data.get("accept_item_id")

        if not trade_id or not accept_item_id:
            return {"error": "Missing trade_id or accept_item_id"}

        trade = self.pending_trades.get(trade_id)
        if not trade:
            return {"error": "Trade not found"}

        if trade["to_id"] != accepter_id:
            return {"error": "This trade is not for you"}

        if trade["status"] != "pending":
            return {"error": "Trade is no longer pending"}

        trade["status"] = "executing"

        result = await self.trade_manager.execute_trade(
            self,
            trade["from_id"], trade["offer_item_id"],
            accepter_id, accept_item_id,
        )

        if "success" in result:
            trade["status"] = "completed"
            del self.pending_trades[trade_id]

            initiator = self.players.get(trade["from_id"])
            if initiator and initiator.websocket:
                await self.send(initiator.websocket, {
                    "type": "trade_completed",
                    "trade_id": trade_id,
                    "result": result,
                })
        else:
            trade["status"] = "pending"

        return result

    async def handle_trade_decline(self, decliner_id: str, data: dict) -> dict:
        trade_id = data.get("trade_id")
        if not trade_id:
            return {"error": "Missing trade_id"}

        trade = self.pending_trades.get(trade_id)
        if not trade:
            return {"error": "Trade not found"}

        if trade["to_id"] != decliner_id:
            return {"error": "This trade is not for you"}

        del self.pending_trades[trade_id]

        initiator = self.players.get(trade["from_id"])
        if initiator and initiator.websocket:
            await self.send(initiator.websocket, {
                "type": "trade_declined",
                "trade_id": trade_id,
            })

        return {"success": True, "message": "Trade declined"}

    async def handle_gift(self, from_id: str, data: dict) -> dict:
        to_id = data.get("to_player_id")
        item_id = data.get("item_id")

        if not to_id or not item_id:
            return {"error": "Missing to_player_id or item_id"}

        result = await self.trade_manager.execute_gift(self, from_id, item_id, to_id)

        if "success" in result:
            receiver = self.players.get(to_id)
            if receiver and receiver.websocket:
                sender = self.players.get(from_id)
                await self.send(receiver.websocket, {
                    "type": "gift_received",
                    "from_player": sender.name if sender else "Unknown",
                    "item": result["gift"]["item"],
                })

        return result

    def get_inventory(self, player_id: str) -> list[dict]:
        player = self.players.get(player_id)
        if not player:
            return []
        return [
            {"item_id": item.item_id, "name": item.name, "tradeable": item.tradeable}
            for item in player.inventory.values()
        ]

    def get_online_players(self, exclude_id: str = None) -> list[dict]:
        return [
            {"player_id": p.player_id, "name": p.name}
            for p in self.players.values()
            if p.websocket and p.player_id != exclude_id
        ]

    async def handle_message(self, websocket, raw_message: str):
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            await self.send(websocket, {"error": "Invalid JSON"})
            return

        msg_type = data.get("type")
        player_id = self.connections.get(websocket)

        if msg_type == "join":
            name = data.get("name", "Anonymous")
            if len(name) > 32:
                name = name[:32]
            player = await self.register_player(websocket, name)
            await self.send(websocket, {
                "type": "joined",
                "player_id": player.player_id,
                "name": player.name,
                "inventory": self.get_inventory(player.player_id),
            })
            await self.broadcast({
                "type": "player_joined",
                "player_id": player.player_id,
                "name": player.name,
            }, exclude=websocket)
            return

        if not player_id:
            await self.send(websocket, {"error": "Must join first"})
            return

        handlers = {
            "inventory": lambda: ({"type": "inventory", "items": self.get_inventory(player_id)}),
            "players": lambda: ({"type": "players", "online": self.get_online_players(player_id)}),
        }

        if msg_type in handlers:
            result = handlers[msg_type]()
            await self.send(websocket, result)
            return

        async_handlers = {
            "trade_request": lambda: self.handle_trade_request(player_id, data),
            "trade_accept": lambda: self.handle_trade_accept(player_id, data),
            "trade_decline": lambda: self.handle_trade_decline(player_id, data),
            "gift": lambda: self.handle_gift(player_id, data),
        }

        if msg_type in async_handlers:
            result = await async_handlers[msg_type]()
            result["type"] = f"{msg_type}_result"
            await self.send(websocket, result)
            return

        await self.send(websocket, {"error": f"Unknown message type: {msg_type}"})

    async def handle_connection(self, websocket):
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            player_id = self.connections.pop(websocket, None)
            if player_id and player_id in self.players:
                player = self.players[player_id]
                player.websocket = None
                await self.broadcast({
                    "type": "player_left",
                    "player_id": player_id,
                    "name": player.name,
                })

    async def run(self, host="0.0.0.0", port=8765):
        print(f"MMO Trade Server starting on ws://{host}:{port}")
        async with websockets.serve(self.handle_connection, host, port):
            print("Server is running. Press Ctrl+C to stop.")
            await asyncio.Future()


if __name__ == "__main__":
    server = GameServer()
    asyncio.run(server.run())
