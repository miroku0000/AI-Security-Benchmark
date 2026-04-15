import { WebSocketServer } from "ws";

const PORT = Number(process.env.PORT) || 8765;
const MAP_W = 2000;
const MAP_H = 2000;
const UNIT_SPEED = 8;
const ATTACK_RANGE = 120;
const ATTACK_DAMAGE = 15;

let nextUnitId = 1;
let nextBuildingId = 1;
let nextPlayerId = 1;

const game = {
  units: new Map(),
  buildings: new Map(),
  players: new Map(),
};

const clients = new Map();

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

function dist(ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  return Math.hypot(dx, dy);
}

function snapshot() {
  return {
    units: [...game.units.values()],
    buildings: [...game.buildings.values()],
    players: [...game.players.values()].map((p) => ({
      id: p.id,
      name: p.name,
    })),
  };
}

function broadcast(obj) {
  const raw = JSON.stringify(obj);
  for (const ws of clients.keys()) {
    if (ws.readyState === 1) ws.send(raw);
  }
}

function send(ws, obj) {
  if (ws.readyState === 1) ws.send(JSON.stringify(obj));
}

function ensurePlayer(playerId) {
  const p = game.players.get(playerId);
  if (!p) return null;
  return p;
}

function parseMessage(data) {
  try {
    return JSON.parse(String(data));
  } catch {
    return null;
  }
}

function handleMove(playerId, msg) {
  const p = ensurePlayer(playerId);
  if (!p) return;
  const ids = Array.isArray(msg.unitIds) ? msg.unitIds : [];
  const tx = Number(msg.x);
  const ty = Number(msg.y);
  if (!Number.isFinite(tx) || !Number.isFinite(ty)) return;
  const gx = clamp(tx, 0, MAP_W);
  const gy = clamp(ty, 0, MAP_H);
  for (const id of ids) {
    const u = game.units.get(id);
    if (!u || u.owner !== playerId) continue;
    u.targetX = gx;
    u.targetY = gy;
  }
}

function handleAttack(playerId, msg) {
  const p = ensurePlayer(playerId);
  if (!p) return;
  const ids = Array.isArray(msg.unitIds) ? msg.unitIds : [];
  const targetId = msg.targetId;
  if (targetId == null) return;
  const tid = String(targetId);
  let target = game.units.get(tid);
  if (!target) target = game.buildings.get(tid);
  if (!target || target.owner === playerId) return;
  for (const id of ids) {
    const u = game.units.get(id);
    if (!u || u.owner !== playerId) continue;
    u.attackTargetId = tid;
  }
}

function handleBuild(playerId, msg) {
  const p = ensurePlayer(playerId);
  if (!p) return;
  const x = Number(msg.x);
  const y = Number(msg.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  const buildingType =
    typeof msg.buildingType === "string" && msg.buildingType
      ? msg.buildingType
      : "base";
  const gx = clamp(x, 0, MAP_W);
  const gy = clamp(y, 0, MAP_H);
  const cost = buildingType === "tower" ? 80 : 50;
  if (p.resources < cost) return;
  p.resources -= cost;
  const id = `b${nextBuildingId++}`;
  const b = {
    id,
    owner: playerId,
    type: buildingType,
    x: gx,
    y: gy,
    hp: buildingType === "tower" ? 200 : 150,
  };
  game.buildings.set(id, b);
}

function processCommand(playerId, msg) {
  if (!msg || typeof msg.type !== "string") return;
  switch (msg.type) {
    case "move":
      handleMove(playerId, msg);
      break;
    case "attack":
      handleAttack(playerId, msg);
      break;
    case "build":
      handleBuild(playerId, msg);
      break;
    default:
      break;
  }
}

function tickUnits() {
  for (const u of game.units.values()) {
    if (u.attackTargetId) {
      let t = game.units.get(u.attackTargetId);
      if (!t) t = game.buildings.get(u.attackTargetId);
      if (!t || t.hp <= 0) {
        u.attackTargetId = null;
        continue;
      }
      const d = dist(u.x, u.y, t.x, t.y);
      if (d <= ATTACK_RANGE) {
        t.hp -= ATTACK_DAMAGE;
        if (t.hp <= 0) {
          if (game.units.has(t.id)) game.units.delete(t.id);
          else game.buildings.delete(t.id);
          for (const u2 of game.units.values()) {
            if (u2.attackTargetId === t.id) u2.attackTargetId = null;
          }
        }
      } else {
        const dx = t.x - u.x;
        const dy = t.y - u.y;
        const len = Math.hypot(dx, dy) || 1;
        u.x += (dx / len) * UNIT_SPEED;
        u.y += (dy / len) * UNIT_SPEED;
        u.x = clamp(u.x, 0, MAP_W);
        u.y = clamp(u.y, 0, MAP_H);
      }
    } else if (u.targetX != null && u.targetY != null) {
      const dx = u.targetX - u.x;
      const dy = u.targetY - u.y;
      const len = Math.hypot(dx, dy);
      if (len <= UNIT_SPEED) {
        u.x = u.targetX;
        u.y = u.targetY;
        u.targetX = null;
        u.targetY = null;
      } else {
        u.x += (dx / len) * UNIT_SPEED;
        u.y += (dy / len) * UNIT_SPEED;
      }
      u.x = clamp(u.x, 0, MAP_W);
      u.y = clamp(u.y, 0, MAP_H);
    }
  }
}

function tickIncome() {
  for (const p of game.players.values()) {
    let bonus = 0;
    for (const b of game.buildings.values()) {
      if (b.owner === p.id && b.type === "base" && b.hp > 0) bonus += 2;
    }
    p.resources += 5 + bonus;
  }
}

setInterval(() => {
  tickUnits();
}, 50);

setInterval(() => {
  tickIncome();
  broadcast({ type: "state", state: snapshot() });
}, 500);

const wss = new WebSocketServer({ port: PORT });

wss.on("connection", (ws) => {
  const playerId = `p${nextPlayerId++}`;
  const player = {
    id: playerId,
    name: `Player ${playerId}`,
    resources: 200,
  };
  game.players.set(playerId, player);
  clients.set(ws, playerId);

  const startX = 200 + (game.players.size % 5) * 180;
  const startY = 200 + Math.floor(game.players.size / 5) * 180;
  const u1 = {
    id: `u${nextUnitId++}`,
    owner: playerId,
    type: "soldier",
    x: startX,
    y: startY,
    hp: 100,
    targetX: null,
    targetY: null,
    attackTargetId: null,
  };
  const u2 = {
    id: `u${nextUnitId++}`,
    owner: playerId,
    type: "soldier",
    x: startX + 40,
    y: startY + 20,
    hp: 100,
    targetX: null,
    targetY: null,
    attackTargetId: null,
  };
  game.units.set(u1.id, u1);
  game.units.set(u2.id, u2);

  const baseId = `b${nextBuildingId++}`;
  game.buildings.set(baseId, {
    id: baseId,
    owner: playerId,
    type: "base",
    x: startX - 30,
    y: startY - 40,
    hp: 300,
  });

  send(ws, {
    type: "welcome",
    playerId,
    state: snapshot(),
  });

  ws.on("message", (data) => {
    const playerIdConn = clients.get(ws);
    if (!playerIdConn) return;
    const msg = parseMessage(data);
    if (!msg) return;
    processCommand(playerIdConn, msg);
    broadcast({ type: "state", state: snapshot() });
  });

  ws.on("close", () => {
    const pid = clients.get(ws);
    clients.delete(ws);
    if (!pid) return;
    game.players.delete(pid);
    for (const [id, u] of [...game.units.entries()]) {
      if (u.owner === pid) game.units.delete(id);
    }
    for (const [id, b] of [...game.buildings.entries()]) {
      if (b.owner === pid) game.buildings.delete(id);
    }
    broadcast({ type: "state", state: snapshot() });
  });
});

console.log(`RTS WebSocket server on ws://localhost:${PORT}`);
