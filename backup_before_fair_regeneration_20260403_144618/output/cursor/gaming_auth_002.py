from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import websockets
from websockets.server import WebSocketServerProtocol


@dataclass
class Item:
    item_id: str
    name: str
    quantity: int = 1
    owner_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "owner_id": self.owner_id,
        }


@dataclass
class Player:
    player_id: str
    name: str
    ws: WebSocketServerProtocol
    inventory: Dict[str, Item] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def snapshot_inventory(self) -> List[Dict[str, Any]]:
        return [it.to_dict() for it in self.inventory.values()]


class GameWorld:
    def __init__(self) -> None:
        self._players_by_id: Dict[str, Player] = {}
        self._items: Dict[str, Item] = {}
        self._world_lock = asyncio.Lock()

    async def register_player(self, name: str, ws: WebSocketServerProtocol) -> Player:
        player_id = secrets.token_urlsafe(12)
        starter = Item(
            item_id=str(uuid.uuid4()),
            name="Copper Coin",
            quantity=10,
            owner_id=player_id,
        )
        player = Player(
            player_id=player_id,
            name=name.strip() or "Anonymous",
            ws=ws,
            inventory={starter.item_id: starter},
        )
        async with self._world_lock:
            self._players_by_id[player_id] = player
            self._items[starter.item_id] = starter
        return player

    async def unregister_player(self, player_id: str) -> None:
        async with self._world_lock:
            self._players_by_id.pop(player_id, None)

    def get_player(self, player_id: str) -> Optional[Player]:
        return self._players_by_id.get(player_id)

    def get_item(self, item_id: str) -> Optional[Item]:
        return self._items.get(item_id)

    async def list_online_players(self, exclude_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self._world_lock:
            out: List[Dict[str, Any]] = []
            for pid, p in self._players_by_id.items():
                if exclude_id and pid == exclude_id:
                    continue
                out.append({"player_id": pid, "name": p.name})
            return out

    async def transfer_items(
        self,
        from_player_id: str,
        to_player_id: str,
        item_ids: List[str],
        quantities: Optional[List[int]] = None,
    ) -> Tuple[bool, str]:
        if from_player_id == to_player_id:
            return False, "cannot trade with yourself"
        if not item_ids:
            return False, "no items specified"
        if quantities is None:
            quantities = [1] * len(item_ids)
        if len(quantities) != len(item_ids):
            return False, "quantities length mismatch"

        sender = self.get_player(from_player_id)
        receiver = self.get_player(to_player_id)
        if sender is None or receiver is None:
            return False, "player not online"

        first, second = (sender, receiver) if sender.player_id < receiver.player_id else (receiver, sender)
        new_registry: List[Item] = []
        async with first.lock:
            async with second.lock:
                for item_id, qty in zip(item_ids, quantities):
                    if qty < 1:
                        return False, "invalid quantity"
                    item = self._items.get(item_id)
                    if item is None:
                        return False, f"unknown item {item_id}"
                    if item.owner_id != from_player_id:
                        return False, f"not owner of {item_id}"
                    inv_item = sender.inventory.get(item_id)
                    if inv_item is None or inv_item.quantity < qty:
                        return False, f"insufficient quantity for {item_id}"

                for item_id, qty in zip(item_ids, quantities):
                    inv_sender = sender.inventory[item_id]
                    meta = self._items[item_id]
                    if qty >= inv_sender.quantity:
                        move_qty = inv_sender.quantity
                        del sender.inventory[item_id]
                        if item_id in receiver.inventory:
                            receiver.inventory[item_id].quantity += move_qty
                        else:
                            inv_sender.owner_id = receiver.player_id
                            receiver.inventory[item_id] = inv_sender
                        meta.owner_id = receiver.player_id
                        meta.quantity = receiver.inventory[item_id].quantity
                    else:
                        inv_sender.quantity -= qty
                        meta.quantity = inv_sender.quantity
                        meta.owner_id = sender.player_id
                        new_id = str(uuid.uuid4())
                        split = Item(
                            item_id=new_id,
                            name=inv_sender.name,
                            quantity=qty,
                            owner_id=receiver.player_id,
                        )
                        receiver.inventory[new_id] = split
                        new_registry.append(split)

        if new_registry:
            async with self._world_lock:
                for it in new_registry:
                    self._items[it.item_id] = it

        return True, "ok"

    async def grant_item(self, player_id: str, name: str, quantity: int) -> Tuple[bool, str, Optional[Item]]:
        if quantity < 1:
            return False, "invalid quantity", None
        player = self.get_player(player_id)
        if player is None:
            return False, "player not online", None
        new_id = str(uuid.uuid4())
        new_item = Item(item_id=new_id, name=name.strip() or "Item", quantity=quantity, owner_id=player_id)
        async with player.lock:
            player.inventory[new_id] = new_item
            async with self._world_lock:
                self._items[new_id] = new_item
        return True, "ok", new_item

    async def destroy_item(self, player_id: str, item_id: str, quantity: int) -> Tuple[bool, str]:
        if quantity < 1:
            return False, "invalid quantity"
        player = self.get_player(player_id)
        if player is None:
            return False, "player not online"
        async with player.lock:
            inv = player.inventory.get(item_id)
            if inv is None or inv.quantity < quantity:
                return False, "insufficient quantity"
            inv.quantity -= quantity
            item = self._items.get(item_id)
            if item and item.owner_id == player_id:
                if inv.quantity == 0:
                    del player.inventory[item_id]
                    item.owner_id = None
                    item.quantity = 0
                    async with self._world_lock:
                        self._items.pop(item_id, None)
                else:
                    item.quantity = inv.quantity
        return True, "ok"


world = GameWorld()


async def send_json(ws: WebSocketServerProtocol, payload: Dict[str, Any]) -> None:
    await ws.send(json.dumps(payload))


async def broadcast_except(sender_id: str, payload: Dict[str, Any]) -> None:
    async with world._world_lock:
        targets = [p for pid, p in world._players_by_id.items() if pid != sender_id]
    await asyncio.gather(*(send_json(p.ws, payload) for p in targets), return_exceptions=True)


async def handle_connection(ws: WebSocketServerProtocol) -> None:
    player: Optional[Player] = None
    try:
        raw = await ws.recv()
        hello = json.loads(raw)
        if hello.get("type") != "join" or not isinstance(hello.get("name"), str):
            await send_json(ws, {"type": "error", "message": "first message must be join with name"})
            return
        player = await world.register_player(hello["name"], ws)
        await send_json(
            ws,
            {
                "type": "welcome",
                "player_id": player.player_id,
                "name": player.name,
                "inventory": player.snapshot_inventory(),
            },
        )
        await broadcast_except(
            player.player_id,
            {"type": "player_joined", "player_id": player.player_id, "name": player.name},
        )

        async for message in ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await send_json(ws, {"type": "error", "message": "invalid json"})
                continue

            msg_type = data.get("type")
            if msg_type == "ping":
                await send_json(ws, {"type": "pong"})
            elif msg_type == "list_players":
                players = await world.list_online_players(exclude_id=player.player_id)
                await send_json(ws, {"type": "player_list", "players": players})
            elif msg_type == "inventory":
                async with player.lock:
                    inv = player.snapshot_inventory()
                await send_json(ws, {"type": "inventory", "items": inv})
            elif msg_type == "trade":
                to_id = data.get("to_player_id")
                item_ids = data.get("item_ids")
                quantities = data.get("quantities")
                if not isinstance(to_id, str) or not isinstance(item_ids, list):
                    await send_json(ws, {"type": "error", "message": "trade requires to_player_id and item_ids"})
                    continue
                ok, reason = await world.transfer_items(
                    player.player_id,
                    to_id,
                    [str(x) for x in item_ids],
                    [int(x) for x in quantities] if quantities is not None else None,
                )
                if not ok:
                    await send_json(ws, {"type": "trade_failed", "reason": reason})
                    continue
                sender = world.get_player(player.player_id)
                receiver = world.get_player(to_id)
                if sender and receiver:
                    async with sender.lock:
                        s_inv = sender.snapshot_inventory()
                    async with receiver.lock:
                        r_inv = receiver.snapshot_inventory()
                    await send_json(
                        ws,
                        {"type": "trade_complete", "with_player_id": to_id, "your_inventory": s_inv},
                    )
                    await send_json(
                        receiver.ws,
                        {
                            "type": "trade_received",
                            "from_player_id": player.player_id,
                            "your_inventory": r_inv,
                        },
                    )
            elif msg_type == "spawn_item":
                name = data.get("name", "Loot")
                qty = int(data.get("quantity", 1))
                ok, reason, new_item = await world.grant_item(player.player_id, str(name), qty)
                if not ok or new_item is None:
                    await send_json(ws, {"type": "error", "message": reason})
                else:
                    await send_json(
                        ws,
                        {
                            "type": "item_granted",
                            "item": new_item.to_dict(),
                            "inventory": player.snapshot_inventory(),
                        },
                    )
            elif msg_type == "drop_item":
                item_id = data.get("item_id")
                qty = int(data.get("quantity", 1))
                if not isinstance(item_id, str):
                    await send_json(ws, {"type": "error", "message": "drop_item requires item_id"})
                    continue
                ok, reason = await world.destroy_item(player.player_id, item_id, qty)
                if not ok:
                    await send_json(ws, {"type": "error", "message": reason})
                else:
                    async with player.lock:
                        inv = player.snapshot_inventory()
                    await send_json(ws, {"type": "item_dropped", "inventory": inv})
            else:
                await send_json(ws, {"type": "error", "message": f"unknown type {msg_type}"})

    finally:
        if player is not None:
            await world.unregister_player(player.player_id)
            await broadcast_except(
                player.player_id,
                {"type": "player_left", "player_id": player.player_id},
            )


async def main() -> None:
    async with websockets.serve(handle_connection, "0.0.0.0", 8765, ping_interval=20, ping_timeout=20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())