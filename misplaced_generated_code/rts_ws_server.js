/* eslint-disable no-console */
const http = require('http');
const crypto = require('crypto');
const WebSocket = require('ws');

const PORT = Number.parseInt(process.env.PORT || '8080', 10);
const TICK_RATE_HZ = Number.parseInt(process.env.TICK_RATE_HZ || '20', 10);
const SNAPSHOT_RATE_HZ = Number.parseInt(process.env.SNAPSHOT_RATE_HZ || '5', 10);
const MAX_MSG_BYTES = Number.parseInt(process.env.MAX_MSG_BYTES || '65536', 10);

const MAP = {
  width: Number.parseFloat(process.env.MAP_WIDTH || '2000'),
  height: Number.parseFloat(process.env.MAP_HEIGHT || '2000'),
};

const UNIT_TYPES = {
  worker: { maxHp: 50, speed: 170, attackRange: 0, attackDamage: 0, attackCooldownMs: 0 },
  soldier: { maxHp: 100, speed: 220, attackRange: 240, attackDamage: 12, attackCooldownMs: 600 },
  tank: { maxHp: 300, speed: 130, attackRange: 320, attackDamage: 28, attackCooldownMs: 900 },
};

const BUILDING_TYPES = {
  hq: { maxHp: 1200, footprint: 90, canTrain: ['worker', 'soldier'] },
  barracks: { maxHp: 700, footprint: 75, canTrain: ['soldier'] },
  factory: { maxHp: 850, footprint: 80, canTrain: ['tank'] },
  turret: { maxHp: 450, footprint: 55, attackRange: 380, attackDamage: 18, attackCooldownMs: 700 },
};

const COSTS = {
  worker: { gold: 50 },
  soldier: { gold: 80 },
  tank: { gold: 180 },
  hq: { gold: 0 },
  barracks: { gold: 200 },
  factory: { gold: 300 },
  turret: { gold: 140 },
};

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function dist2(ax, ay, bx, by) {
  const dx = ax - bx;
  const dy = ay - by;
  return dx * dx + dy * dy;
}

function nowMs() {
  return Date.now();
}

function uid(prefix) {
  return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
}

function safeNum(v, fallback = 0) {
  if (typeof v !== 'number' || !Number.isFinite(v)) return fallback;
  return v;
}

function safeStr(v, fallback = '') {
  if (typeof v !== 'string') return fallback;
  return v;
}

function safeArr(v) {
  return Array.isArray(v) ? v : [];
}

function withinMap(x, y) {
  return x >= 0 && y >= 0 && x <= MAP.width && y <= MAP.height;
}

function normalizeVec(dx, dy) {
  const len = Math.hypot(dx, dy);
  if (!len) return { x: 0, y: 0, len: 0 };
  return { x: dx / len, y: dy / len, len };
}

function jsonSend(ws, obj) {
  if (ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(obj));
}

function broadcast(server, obj) {
  const msg = JSON.stringify(obj);
  for (const client of server.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(msg);
  }
}

function teamColor(team) {
  const colors = ['#4C8BF5', '#E74C3C', '#2ECC71', '#F1C40F', '#9B59B6', '#1ABC9C'];
  return colors[Math.abs(team) % colors.length];
}

const game = {
  startedAt: nowMs(),
  tick: 0,
  players: new Map(), // playerId -> player
  sockets: new Map(), // ws -> playerId
  units: new Map(), // unitId -> unit
  buildings: new Map(), // buildingId -> building
  projectiles: new Map(), // projectileId -> projectile
};

function makePlayer({ name }) {
  const id = uid('p');
  return {
    id,
    name: name || `Player-${id.slice(-4)}`,
    team: game.players.size,
    resources: { gold: 500 },
    connected: true,
    lastInputAt: nowMs(),
  };
}

function makeUnit({ ownerId, type, x, y }) {
  const def = UNIT_TYPES[type];
  const id = uid('u');
  return {
    id,
    ownerId,
    type,
    x,
    y,
    hp: def.maxHp,
    maxHp: def.maxHp,
    target: null, // {x,y} or {entityId}
    order: { kind: 'idle' }, // idle|move|attack|gather|hold
    attack: {
      cooldownMs: def.attackCooldownMs,
      lastAttackAt: 0,
      range: def.attackRange,
      damage: def.attackDamage,
      targetId: null,
    },
    speed: def.speed,
    createdAt: nowMs(),
  };
}

function makeBuilding({ ownerId, type, x, y }) {
  const def = BUILDING_TYPES[type];
  const id = uid('b');
  return {
    id,
    ownerId,
    type,
    x,
    y,
    hp: def.maxHp,
    maxHp: def.maxHp,
    footprint: def.footprint,
    canTrain: def.canTrain || [],
    attack: def.attackRange
      ? {
          cooldownMs: def.attackCooldownMs,
          lastAttackAt: 0,
          range: def.attackRange,
          damage: def.attackDamage,
          targetId: null,
        }
      : null,
    createdAt: nowMs(),
  };
}

function getEntity(entityId) {
  if (!entityId || typeof entityId !== 'string') return null;
  if (entityId.startsWith('u_')) return game.units.get(entityId) || null;
  if (entityId.startsWith('b_')) return game.buildings.get(entityId) || null;
  return null;
}

function entityPos(e) {
  return { x: e.x, y: e.y };
}

function isAlive(e) {
  return e && typeof e.hp === 'number' && e.hp > 0;
}

function ownedBy(playerId, e) {
  return e && e.ownerId === playerId;
}

function trySpend(player, cost) {
  if (!cost) return true;
  const gold = cost.gold || 0;
  if (player.resources.gold < gold) return false;
  player.resources.gold -= gold;
  return true;
}

function refund(player, cost) {
  if (!cost) return;
  player.resources.gold += cost.gold || 0;
}

function spawnStarterBase(player) {
  const pad = 220;
  const cols = 2;
  const row = Math.floor(player.team / cols);
  const col = player.team % cols;
  const baseX = clamp(200 + col * (MAP.width - 400), 200, MAP.width - 200);
  const baseY = clamp(200 + row * (MAP.height - 400), 200, MAP.height - 200);

  const hq = makeBuilding({ ownerId: player.id, type: 'hq', x: baseX, y: baseY });
  game.buildings.set(hq.id, hq);

  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2;
    const u = makeUnit({
      ownerId: player.id,
      type: 'worker',
      x: clamp(baseX + Math.cos(a) * pad, 0, MAP.width),
      y: clamp(baseY + Math.sin(a) * pad, 0, MAP.height),
    });
    game.units.set(u.id, u);
  }
}

function snapshotFor(playerId) {
  const players = [];
  for (const p of game.players.values()) {
    players.push({
      id: p.id,
      name: p.name,
      team: p.team,
      color: teamColor(p.team),
      connected: p.connected,
      resources: p.id === playerId ? p.resources : undefined,
    });
  }

  const units = [];
  for (const u of game.units.values()) {
    if (!isAlive(u)) continue;
    units.push({
      id: u.id,
      ownerId: u.ownerId,
      type: u.type,
      x: u.x,
      y: u.y,
      hp: u.hp,
      maxHp: u.maxHp,
      order: u.order,
    });
  }

  const buildings = [];
  for (const b of game.buildings.values()) {
    if (!isAlive(b)) continue;
    buildings.push({
      id: b.id,
      ownerId: b.ownerId,
      type: b.type,
      x: b.x,
      y: b.y,
      hp: b.hp,
      maxHp: b.maxHp,
    });
  }

  return {
    type: 'snapshot',
    tick: game.tick,
    map: MAP,
    players,
    units,
    buildings,
  };
}

function validateIds(ids, prefix) {
  const out = [];
  for (const v of safeArr(ids)) {
    if (typeof v === 'string' && v.startsWith(prefix)) out.push(v);
  }
  return out;
}

function handleMove(player, msg) {
  const unitIds = validateIds(msg.unitIds, 'u_');
  const x = safeNum(msg.x, NaN);
  const y = safeNum(msg.y, NaN);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return { ok: false, error: 'invalid_target' };
  if (!withinMap(x, y)) return { ok: false, error: 'out_of_bounds' };

  let changed = 0;
  for (const id of unitIds) {
    const u = game.units.get(id);
    if (!isAlive(u) || !ownedBy(player.id, u)) continue;
    u.order = { kind: 'move', x, y };
    u.target = { x, y };
    u.attack.targetId = null;
    changed++;
  }
  return { ok: true, changed };
}

function handleAttack(player, msg) {
  const unitIds = validateIds(msg.unitIds, 'u_');
  const targetId = safeStr(msg.targetId, '');
  const target = getEntity(targetId);
  if (!isAlive(target)) return { ok: false, error: 'invalid_target' };
  if (target.ownerId === player.id) return { ok: false, error: 'friendly_target' };

  let changed = 0;
  for (const id of unitIds) {
    const u = game.units.get(id);
    if (!isAlive(u) || !ownedBy(player.id, u)) continue;
    if (!u.attack.range || !u.attack.damage) continue;
    u.order = { kind: 'attack', targetId };
    u.attack.targetId = targetId;
    u.target = { entityId: targetId };
    changed++;
  }
  return { ok: true, changed };
}

function handleHold(player, msg) {
  const unitIds = validateIds(msg.unitIds, 'u_');
  let changed = 0;
  for (const id of unitIds) {
    const u = game.units.get(id);
    if (!isAlive(u) || !ownedBy(player.id, u)) continue;
    u.order = { kind: 'hold' };
    u.target = null;
    u.attack.targetId = null;
    changed++;
  }
  return { ok: true, changed };
}

function handleBuild(player, msg) {
  const buildingType = safeStr(msg.buildingType, '');
  if (!BUILDING_TYPES[buildingType]) return { ok: false, error: 'invalid_building_type' };

  const x = safeNum(msg.x, NaN);
  const y = safeNum(msg.y, NaN);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return { ok: false, error: 'invalid_position' };
  if (!withinMap(x, y)) return { ok: false, error: 'out_of_bounds' };

  const cost = COSTS[buildingType] || { gold: 0 };
  if (!trySpend(player, cost)) return { ok: false, error: 'insufficient_resources' };

  const b = makeBuilding({ ownerId: player.id, type: buildingType, x, y });
  game.buildings.set(b.id, b);
  return { ok: true, buildingId: b.id };
}

function handleTrain(player, msg) {
  const buildingId = safeStr(msg.buildingId, '');
  const unitType = safeStr(msg.unitType, '');
  const building = game.buildings.get(buildingId);
  if (!isAlive(building) || !ownedBy(player.id, building)) return { ok: false, error: 'invalid_building' };
  if (!UNIT_TYPES[unitType]) return { ok: false, error: 'invalid_unit_type' };
  if (!building.canTrain.includes(unitType)) return { ok: false, error: 'cannot_train' };

  const cost = COSTS[unitType] || { gold: 0 };
  if (!trySpend(player, cost)) return { ok: false, error: 'insufficient_resources' };

  const jitter = building.footprint + 35;
  const angle = Math.random() * Math.PI * 2;
  const x = clamp(building.x + Math.cos(angle) * jitter, 0, MAP.width);
  const y = clamp(building.y + Math.sin(angle) * jitter, 0, MAP.height);
  const u = makeUnit({ ownerId: player.id, type: unitType, x, y });
  game.units.set(u.id, u);
  return { ok: true, unitId: u.id };
}

function handlePing(player) {
  player.lastInputAt = nowMs();
  return { ok: true, serverTime: nowMs(), tick: game.tick };
}

function applyCommand(player, msg) {
  const type = safeStr(msg.type, '');
  if (!type) return { ok: false, error: 'missing_type' };

  if (type === 'move') return handleMove(player, msg);
  if (type === 'attack') return handleAttack(player, msg);
  if (type === 'hold') return handleHold(player, msg);
  if (type === 'build') return handleBuild(player, msg);
  if (type === 'train') return handleTrain(player, msg);
  if (type === 'ping') return handlePing(player);
  if (type === 'chat') {
    const text = safeStr(msg.text, '').slice(0, 300);
    return { ok: true, text };
  }

  return { ok: false, error: 'unknown_type' };
}

function damageEntity(target, amount) {
  target.hp = Math.max(0, target.hp - amount);
  if (target.hp <= 0) {
    if (target.id.startsWith('u_')) game.units.delete(target.id);
    if (target.id.startsWith('b_')) game.buildings.delete(target.id);
  }
}

function acquireNearestEnemyTarget(attacker) {
  const attackerOwner = attacker.ownerId;
  const ax = attacker.x;
  const ay = attacker.y;
  const range = attacker.attack?.range || 0;
  const r2 = range * range;
  if (!range || !attacker.attack?.damage) return null;

  let best = null;
  let bestD2 = Infinity;

  for (const u of game.units.values()) {
    if (!isAlive(u) || u.ownerId === attackerOwner) continue;
    const d2 = dist2(ax, ay, u.x, u.y);
    if (d2 <= r2 && d2 < bestD2) {
      best = u;
      bestD2 = d2;
    }
  }
  for (const b of game.buildings.values()) {
    if (!isAlive(b) || b.ownerId === attackerOwner) continue;
    const d2 = dist2(ax, ay, b.x, b.y);
    if (d2 <= r2 && d2 < bestD2) {
      best = b;
      bestD2 = d2;
    }
  }
  return best ? best.id : null;
}

function tickMovement(dtSec) {
  for (const u of game.units.values()) {
    if (!isAlive(u)) continue;
    if (u.order.kind !== 'move') continue;
    const tx = safeNum(u.order.x, u.x);
    const ty = safeNum(u.order.y, u.y);
    const { x: vx, y: vy, len } = normalizeVec(tx - u.x, ty - u.y);
    if (len < 2) {
      u.order = { kind: 'idle' };
      u.target = null;
      continue;
    }
    const step = u.speed * dtSec;
    const nx = u.x + vx * Math.min(step, len);
    const ny = u.y + vy * Math.min(step, len);
    u.x = clamp(nx, 0, MAP.width);
    u.y = clamp(ny, 0, MAP.height);
  }
}

function tickAttacks() {
  const t = nowMs();

  const processAttacker = (attacker) => {
    if (!attacker.attack || !attacker.attack.damage || !attacker.attack.range) return;
    if (t - attacker.attack.lastAttackAt < attacker.attack.cooldownMs) return;

    let targetId = attacker.attack.targetId;
    const orderTarget = attacker.order?.kind === 'attack' ? attacker.order.targetId : null;
    if (orderTarget) targetId = orderTarget;

    let target = targetId ? getEntity(targetId) : null;
    if (!isAlive(target) || target.ownerId === attacker.ownerId) {
      targetId = acquireNearestEnemyTarget(attacker);
      target = targetId ? getEntity(targetId) : null;
    }

    if (!isAlive(target) || target.ownerId === attacker.ownerId) {
      attacker.attack.targetId = null;
      if (attacker.order?.kind === 'attack') attacker.order = { kind: 'idle' };
      return;
    }

    const ax = attacker.x;
    const ay = attacker.y;
    const tx = target.x;
    const ty = target.y;
    const r = attacker.attack.range;
    if (dist2(ax, ay, tx, ty) > r * r) return;

    attacker.attack.lastAttackAt = t;
    attacker.attack.targetId = target.id;
    damageEntity(target, attacker.attack.damage);
  };

  for (const u of game.units.values()) {
    if (!isAlive(u)) continue;
    processAttacker(u);
  }
  for (const b of game.buildings.values()) {
    if (!isAlive(b) || !b.attack) continue;
    processAttacker(b);
  }
}

function cleanupDisconnectedPlayers() {
  const t = nowMs();
  for (const p of game.players.values()) {
    if (!p.connected && t - p.lastInputAt > 60_000) {
      for (const u of Array.from(game.units.values())) {
        if (u.ownerId === p.id) game.units.delete(u.id);
      }
      for (const b of Array.from(game.buildings.values())) {
        if (b.ownerId === p.id) game.buildings.delete(b.id);
      }
      game.players.delete(p.id);
    }
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, tick: game.tick, players: game.players.size }));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

const wss = new WebSocket.Server({ server, maxPayload: MAX_MSG_BYTES });

wss.on('connection', (ws) => {
  ws.binaryType = 'arraybuffer';

  let playerId = null;
  let joined = false;

  const sendError = (code, message) => jsonSend(ws, { type: 'error', code, message });
  const sendAck = (clientMsgId, ok, payload) =>
    jsonSend(ws, { type: 'ack', clientMsgId: clientMsgId ?? null, ok, ...payload });

  ws.on('message', (data, isBinary) => {
    if (isBinary) {
      sendError('invalid_message', 'Binary messages not supported');
      return;
    }

    const raw = typeof data === 'string' ? data : data.toString('utf8');
    if (!raw || raw.length > MAX_MSG_BYTES) {
      sendError('invalid_message', 'Message too large');
      return;
    }

    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      sendError('invalid_json', 'Could not parse JSON');
      return;
    }

    const clientMsgId = msg && Object.prototype.hasOwnProperty.call(msg, 'clientMsgId') ? msg.clientMsgId : null;

    if (!joined) {
      const type = safeStr(msg.type, '');
      if (type !== 'join') {
        sendAck(clientMsgId, false, { error: 'must_join_first' });
        return;
      }
      const name = safeStr(msg.name, '').slice(0, 24);
      const player = makePlayer({ name });
      playerId = player.id;
      game.players.set(player.id, player);
      game.sockets.set(ws, player.id);
      spawnStarterBase(player);
      joined = true;

      sendAck(clientMsgId, true, { playerId: player.id, team: player.team, color: teamColor(player.team) });
      jsonSend(ws, snapshotFor(player.id));
      broadcast(wss, { type: 'event', event: 'player_joined', player: { id: player.id, name: player.name, team: player.team } });
      return;
    }

    const p = playerId ? game.players.get(playerId) : null;
    if (!p) {
      sendAck(clientMsgId, false, { error: 'unknown_player' });
      return;
    }
    p.lastInputAt = nowMs();

    const type = safeStr(msg.type, '');
    if (type === 'leave') {
      sendAck(clientMsgId, true, {});
      ws.close(1000, 'bye');
      return;
    }

    const result = applyCommand(p, msg);
    if (!result.ok) {
      sendAck(clientMsgId, false, { error: result.error || 'command_failed' });
      return;
    }

    sendAck(clientMsgId, true, { result });
    if (type === 'chat') {
      broadcast(wss, {
        type: 'event',
        event: 'chat',
        from: { playerId: p.id, name: p.name, team: p.team },
        text: result.text,
      });
    }
  });

  ws.on('close', () => {
    const pid = game.sockets.get(ws);
    game.sockets.delete(ws);
    if (!pid) return;
    const p = game.players.get(pid);
    if (!p) return;
    p.connected = false;
    p.lastInputAt = nowMs();
    broadcast(wss, { type: 'event', event: 'player_left', playerId: pid });
  });

  ws.on('error', () => {});
});

let lastTickAt = nowMs();
const tickIntervalMs = Math.max(5, Math.floor(1000 / Math.max(1, TICK_RATE_HZ)));
const snapshotIntervalMs = Math.max(50, Math.floor(1000 / Math.max(1, SNAPSHOT_RATE_HZ)));
let lastSnapshotAt = nowMs();

setInterval(() => {
  const t = nowMs();
  const dtSec = Math.min(0.25, Math.max(0, (t - lastTickAt) / 1000));
  lastTickAt = t;
  game.tick++;

  tickMovement(dtSec);
  tickAttacks();
  cleanupDisconnectedPlayers();

  if (t - lastSnapshotAt >= snapshotIntervalMs) {
    lastSnapshotAt = t;
    const units = [];
    for (const u of game.units.values()) {
      if (!isAlive(u)) continue;
      units.push({ id: u.id, x: u.x, y: u.y, hp: u.hp, order: u.order });
    }
    const buildings = [];
    for (const b of game.buildings.values()) {
      if (!isAlive(b)) continue;
      buildings.push({ id: b.id, hp: b.hp });
    }
    broadcast(wss, { type: 'state', tick: game.tick, units, buildings });
  }
}, tickIntervalMs);

server.listen(PORT, () => {
  console.log(`RTS WebSocket server listening on :${PORT}`);
  console.log(`WS endpoint: ws://localhost:${PORT}`);
  console.log(`Health: http://localhost:${PORT}/healthz`);
});

