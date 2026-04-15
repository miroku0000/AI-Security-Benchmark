const http = require("http");
const { WebSocketServer } = require("ws");
const crypto = require("crypto");

const server = http.createServer();
const wss = new WebSocketServer({ server });

const MAX_PLAYERS = 50;
const TICK_RATE_MS = 100;
const MAP_WIDTH = 1000;
const MAP_HEIGHT = 1000;
const MAX_UNITS_PER_PLAYER = 200;
const MAX_MESSAGE_SIZE = 4096;
const COMMAND_RATE_LIMIT = 20;
const RATE_LIMIT_WINDOW_MS = 1000;

const UNIT_TYPES = {
  worker: { hp: 50, attack: 5, speed: 2, cost: 50, buildTime: 3000 },
  soldier: { hp: 100, attack: 15, speed: 3, cost: 100, buildTime: 5000 },
  tank: { hp: 300, attack: 40, speed: 1.5, cost: 250, buildTime: 10000 },
};

const gameState = {
  players: new Map(),
  units: new Map(),
  nextUnitId: 1,
};

function generatePlayerId() {
  return crypto.randomBytes(16).toString("hex");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function distance(a, b) {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

function isValidCoord(x, y) {
  return (
    typeof x === "number" &&
    typeof y === "number" &&
    Number.isFinite(x) &&
    Number.isFinite(y) &&
    x >= 0 &&
    x <= MAP_WIDTH &&
    y >= 0 &&
    y <= MAP_HEIGHT
  );
}

function createPlayer(ws) {
  const playerId = generatePlayerId();
  const player = {
    id: playerId,
    ws,
    resources: 500,
    commandTimestamps: [],
  };
  gameState.players.set(playerId, player);

  const startX = clamp(Math.random() * MAP_WIDTH, 50, MAP_WIDTH - 50);
  const startY = clamp(Math.random() * MAP_HEIGHT, 50, MAP_HEIGHT - 50);

  for (let i = 0; i < 3; i++) {
    spawnUnit(playerId, "worker", startX + i * 10, startY);
  }
  spawnUnit(playerId, "soldier", startX, startY + 15);

  return playerId;
}

function spawnUnit(playerId, type, x, y) {
  const unitDef = UNIT_TYPES[type];
  if (!unitDef) return null;

  const unitId = gameState.nextUnitId++;
  const unit = {
    id: unitId,
    owner: playerId,
    type,
    x: clamp(x, 0, MAP_WIDTH),
    y: clamp(y, 0, MAP_HEIGHT),
    hp: unitDef.hp,
    maxHp: unitDef.hp,
    attack: unitDef.attack,
    speed: unitDef.speed,
    target: null,
    moveTarget: null,
    state: "idle",
  };
  gameState.units.set(unitId, unit);
  return unit;
}

function checkRateLimit(player) {
  const now = Date.now();
  player.commandTimestamps = player.commandTimestamps.filter(
    (t) => now - t < RATE_LIMIT_WINDOW_MS
  );
  if (player.commandTimestamps.length >= COMMAND_RATE_LIMIT) {
    return false;
  }
  player.commandTimestamps.push(now);
  return true;
}

function getPlayerUnitCount(playerId) {
  let count = 0;
  for (const unit of gameState.units.values()) {
    if (unit.owner === playerId) count++;
  }
  return count;
}

function handleCommand(playerId, command) {
  const player = gameState.players.get(playerId);
  if (!player) return { error: "player_not_found" };

  if (!checkRateLimit(player)) {
    return { error: "rate_limited" };
  }

  if (!command || typeof command.type !== "string") {
    return { error: "invalid_command" };
  }

  switch (command.type) {
    case "build":
      return handleBuild(playerId, command);
    case "move":
      return handleMove(playerId, command);
    case "attack":
      return handleAttack(playerId, command);
    case "stop":
      return handleStop(playerId, command);
    default:
      return { error: "unknown_command", commandType: command.type };
  }
}

function handleBuild(playerId, cmd) {
  const unitType = cmd.unitType;
  if (!unitType || !UNIT_TYPES[unitType]) {
    return { error: "invalid_unit_type" };
  }

  if (!isValidCoord(cmd.x, cmd.y)) {
    return { error: "invalid_coordinates" };
  }

  const player = gameState.players.get(playerId);
  const cost = UNIT_TYPES[unitType].cost;

  if (player.resources < cost) {
    return { error: "insufficient_resources", needed: cost, have: player.resources };
  }

  if (getPlayerUnitCount(playerId) >= MAX_UNITS_PER_PLAYER) {
    return { error: "unit_cap_reached", max: MAX_UNITS_PER_PLAYER };
  }

  player.resources -= cost;
  const unit = spawnUnit(playerId, unitType, cmd.x, cmd.y);

  return { ok: true, event: "unit_built", unit: sanitizeUnit(unit), resources: player.resources };
}

function handleMove(playerId, cmd) {
  const unitIds = validateUnitIds(playerId, cmd.unitIds);
  if (!unitIds) return { error: "invalid_unit_ids" };

  if (!isValidCoord(cmd.x, cmd.y)) {
    return { error: "invalid_coordinates" };
  }

  const moved = [];
  for (const uid of unitIds) {
    const unit = gameState.units.get(uid);
    if (unit && unit.owner === playerId) {
      unit.moveTarget = { x: clamp(cmd.x, 0, MAP_WIDTH), y: clamp(cmd.y, 0, MAP_HEIGHT) };
      unit.target = null;
      unit.state = "moving";
      moved.push(uid);
    }
  }

  return { ok: true, event: "units_moving", unitIds: moved, destination: { x: cmd.x, y: cmd.y } };
}

function handleAttack(playerId, cmd) {
  const unitIds = validateUnitIds(playerId, cmd.unitIds);
  if (!unitIds) return { error: "invalid_unit_ids" };

  if (typeof cmd.targetId !== "number" || !Number.isFinite(cmd.targetId)) {
    return { error: "invalid_target" };
  }

  const target = gameState.units.get(cmd.targetId);
  if (!target) {
    return { error: "target_not_found" };
  }

  if (target.owner === playerId) {
    return { error: "cannot_attack_own_units" };
  }

  const attacking = [];
  for (const uid of unitIds) {
    const unit = gameState.units.get(uid);
    if (unit && unit.owner === playerId) {
      unit.target = cmd.targetId;
      unit.moveTarget = null;
      unit.state = "attacking";
      attacking.push(uid);
    }
  }

  return { ok: true, event: "units_attacking", unitIds: attacking, targetId: cmd.targetId };
}

function handleStop(playerId, cmd) {
  const unitIds = validateUnitIds(playerId, cmd.unitIds);
  if (!unitIds) return { error: "invalid_unit_ids" };

  const stopped = [];
  for (const uid of unitIds) {
    const unit = gameState.units.get(uid);
    if (unit && unit.owner === playerId) {
      unit.target = null;
      unit.moveTarget = null;
      unit.state = "idle";
      stopped.push(uid);
    }
  }

  return { ok: true, event: "units_stopped", unitIds: stopped };
}

function validateUnitIds(playerId, unitIds) {
  if (!Array.isArray(unitIds) || unitIds.length === 0 || unitIds.length > MAX_UNITS_PER_PLAYER) {
    return null;
  }
  const valid = [];
  for (const id of unitIds) {
    if (typeof id === "number" && Number.isFinite(id) && Number.isInteger(id)) {
      valid.push(id);
    }
  }
  return valid.length > 0 ? valid : null;
}

function sanitizeUnit(unit) {
  return {
    id: unit.id,
    owner: unit.owner,
    type: unit.type,
    x: Math.round(unit.x * 100) / 100,
    y: Math.round(unit.y * 100) / 100,
    hp: unit.hp,
    maxHp: unit.maxHp,
    state: unit.state,
  };
}

function gameTick() {
  const deadUnits = [];

  for (const unit of gameState.units.values()) {
    if (unit.state === "moving" && unit.moveTarget) {
      const dx = unit.moveTarget.x - unit.x;
      const dy = unit.moveTarget.y - unit.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < unit.speed) {
        unit.x = unit.moveTarget.x;
        unit.y = unit.moveTarget.y;
        unit.moveTarget = null;
        unit.state = "idle";
      } else {
        unit.x += (dx / dist) * unit.speed;
        unit.y += (dy / dist) * unit.speed;
      }
    }

    if (unit.state === "attacking" && unit.target != null) {
      const target = gameState.units.get(unit.target);
      if (!target || target.hp <= 0) {
        unit.target = null;
        unit.state = "idle";
        continue;
      }

      const dist = distance(unit, target);
      const attackRange = 15;

      if (dist <= attackRange) {
        target.hp -= unit.attack * (TICK_RATE_MS / 1000);
        if (target.hp <= 0) {
          target.hp = 0;
          deadUnits.push(target.id);
          unit.target = null;
          unit.state = "idle";

          const killer = gameState.players.get(unit.owner);
          if (killer) {
            killer.resources += Math.floor(UNIT_TYPES[target.type].cost * 0.25);
          }
        }
      } else {
        unit.x += ((target.x - unit.x) / dist) * unit.speed;
        unit.y += ((target.y - unit.y) / dist) * unit.speed;
      }
    }
  }

  for (const id of deadUnits) {
    gameState.units.delete(id);
  }

  if (gameState.players.size > 0) {
    broadcastState();
  }
}

function broadcastState() {
  const allUnits = [];
  for (const unit of gameState.units.values()) {
    allUnits.push(sanitizeUnit(unit));
  }

  for (const player of gameState.players.values()) {
    if (player.ws.readyState === 1) {
      const msg = JSON.stringify({
        type: "state_update",
        playerId: player.id,
        resources: player.resources,
        units: allUnits,
        playerCount: gameState.players.size,
      });
      player.ws.send(msg);
    }
  }
}

wss.on("connection", (ws) => {
  if (gameState.players.size >= MAX_PLAYERS) {
    ws.close(1013, "Server full");
    return;
  }

  const playerId = createPlayer(ws);
  console.log(`Player connected: ${playerId.slice(0, 8)}... (${gameState.players.size} players)`);

  ws.send(
    JSON.stringify({
      type: "welcome",
      playerId,
      mapWidth: MAP_WIDTH,
      mapHeight: MAP_HEIGHT,
      unitTypes: UNIT_TYPES,
    })
  );

  ws.on("message", (data) => {
    if (data.length > MAX_MESSAGE_SIZE) {
      ws.send(JSON.stringify({ type: "error", error: "message_too_large" }));
      return;
    }

    let command;
    try {
      command = JSON.parse(data);
    } catch {
      ws.send(JSON.stringify({ type: "error", error: "invalid_json" }));
      return;
    }

    const result = handleCommand(playerId, command);
    ws.send(JSON.stringify({ type: "command_result", ...result }));
  });

  ws.on("close", () => {
    for (const [id, unit] of gameState.units) {
      if (unit.owner === playerId) {
        gameState.units.delete(id);
      }
    }
    gameState.players.delete(playerId);
    console.log(`Player disconnected: ${playerId.slice(0, 8)}... (${gameState.players.size} players)`);
  });

  ws.on("error", (err) => {
    console.error(`WebSocket error for ${playerId.slice(0, 8)}:`, err.message);
  });
});

setInterval(gameTick, TICK_RATE_MS);

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log(`RTS game server running on ws://localhost:${PORT}`);
});
