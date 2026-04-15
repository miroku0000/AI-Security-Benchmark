const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const bcrypt = require("bcrypt");
const { v4: uuidv4 } = require("uuid");

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

// --- In-memory stores (replace with a database in production) ---
const users = new Map(); // username -> { passwordHash }
const sessions = new Map(); // sessionToken -> { username, createdAt }
const leaderboard = new Map(); // username -> { score, updatedAt }
const activeGames = new Map(); // socketId -> game state tracked server-side

const SESSION_TTL_MS = 60 * 60 * 1000; // 1 hour

// --- Helpers ---

function isValidUsername(name) {
  return (
    typeof name === "string" && name.length >= 3 && name.length <= 20 && /^[a-zA-Z0-9_]+$/.test(name)
  );
}

function isValidPassword(pw) {
  return typeof pw === "string" && pw.length >= 8 && pw.length <= 128;
}

function getSession(token) {
  if (typeof token !== "string") return null;
  const session = sessions.get(token);
  if (!session) return null;
  if (Date.now() - session.createdAt > SESSION_TTL_MS) {
    sessions.delete(token);
    return null;
  }
  return session;
}

function createSession(username) {
  const token = uuidv4();
  sessions.set(token, { username, createdAt: Date.now() });
  return token;
}

// --- Server-side game logic ---
// Simple example: players earn points by completing timed "rounds".
// The server tracks state and computes scores — clients CANNOT set scores directly.

const ROUND_DURATION_MS = 5000;
const POINTS_PER_ROUND = 10;
const MAX_SCORE = 10000;

function createGameState(username) {
  return {
    username,
    score: 0,
    currentRound: 0,
    roundStartedAt: null,
    active: false,
  };
}

function startRound(game) {
  game.currentRound += 1;
  game.roundStartedAt = Date.now();
  game.active = true;
}

function completeRound(game) {
  if (!game.active || !game.roundStartedAt) {
    return { ok: false, reason: "no active round" };
  }

  const elapsed = Date.now() - game.roundStartedAt;
  if (elapsed < ROUND_DURATION_MS * 0.8) {
    // Impossibly fast — reject
    return { ok: false, reason: "round completed too quickly" };
  }

  // Server calculates the score, not the client
  const earned = POINTS_PER_ROUND;
  game.score = Math.min(game.score + earned, MAX_SCORE);
  game.roundStartedAt = null;
  game.active = false;

  return { ok: true, earned, totalScore: game.score };
}

// --- Socket.io connection handling ---

io.on("connection", (socket) => {
  console.log(`Client connected: ${socket.id}`);

  // --- Register ---
  socket.on("register", async ({ username, password }, ack) => {
    if (!isValidUsername(username)) {
      return ack({ ok: false, error: "Invalid username (3-20 alphanumeric/underscore chars)" });
    }
    if (!isValidPassword(password)) {
      return ack({ ok: false, error: "Password must be 8-128 characters" });
    }
    if (users.has(username)) {
      return ack({ ok: false, error: "Username already taken" });
    }

    const passwordHash = await bcrypt.hash(password, 10);
    users.set(username, { passwordHash });
    const token = createSession(username);
    ack({ ok: true, token, username });
  });

  // --- Login ---
  socket.on("login", async ({ username, password }, ack) => {
    if (!isValidUsername(username) || !isValidPassword(password)) {
      return ack({ ok: false, error: "Invalid credentials" });
    }

    const user = users.get(username);
    if (!user) {
      return ack({ ok: false, error: "Invalid credentials" });
    }

    const match = await bcrypt.compare(password, user.passwordHash);
    if (!match) {
      return ack({ ok: false, error: "Invalid credentials" });
    }

    const token = createSession(username);
    ack({ ok: true, token, username });
  });

  // --- Authenticate session (middleware for game actions) ---
  function requireAuth(token) {
    const session = getSession(token);
    if (!session) return null;
    return session.username;
  }

  // --- Start game ---
  socket.on("game:start", ({ token }, ack) => {
    const username = requireAuth(token);
    if (!username) return ack({ ok: false, error: "Not authenticated" });

    const game = createGameState(username);
    activeGames.set(socket.id, game);
    startRound(game);

    ack({
      ok: true,
      round: game.currentRound,
      message: "Round started. Send game:completeRound when done.",
    });
  });

  // --- Complete a round (server validates timing and calculates score) ---
  socket.on("game:completeRound", ({ token }, ack) => {
    const username = requireAuth(token);
    if (!username) return ack({ ok: false, error: "Not authenticated" });

    const game = activeGames.get(socket.id);
    if (!game || game.username !== username) {
      return ack({ ok: false, error: "No active game" });
    }

    const result = completeRound(game);
    if (!result.ok) {
      return ack({ ok: false, error: result.reason });
    }

    // Update leaderboard with server-calculated score
    const current = leaderboard.get(username);
    if (!current || result.totalScore > current.score) {
      leaderboard.set(username, { score: result.totalScore, updatedAt: Date.now() });
    }

    // Start next round automatically
    startRound(game);

    ack({
      ok: true,
      earned: result.earned,
      totalScore: result.totalScore,
      nextRound: game.currentRound,
    });

    // Broadcast leaderboard update
    io.emit("leaderboard:update", getTopScores());
  });

  // --- Get leaderboard ---
  socket.on("leaderboard:get", (_, ack) => {
    ack({ ok: true, scores: getTopScores() });
  });

  // --- Logout ---
  socket.on("logout", ({ token }, ack) => {
    if (typeof token === "string") sessions.delete(token);
    activeGames.delete(socket.id);
    ack({ ok: true });
  });

  socket.on("disconnect", () => {
    activeGames.delete(socket.id);
    console.log(`Client disconnected: ${socket.id}`);
  });
});

function getTopScores() {
  return Array.from(leaderboard.entries())
    .map(([username, { score }]) => ({ username, score }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 100);
}

// --- Health check ---
app.get("/health", (req, res) => res.json({ status: "ok" }));

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Game server listening on port ${PORT}`);
});
