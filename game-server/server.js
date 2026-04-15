const http = require('http');
const express = require('express');
const session = require('express-session');
const bcrypt = require('bcrypt');
const { Server } = require('socket.io');

const PORT = process.env.PORT || 3000;
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-in-production';

const app = express();
app.use(express.json());

const sessionMiddleware = session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    maxAge: 1000 * 60 * 60 * 24 * 7,
    sameSite: 'lax',
  },
});

app.use(sessionMiddleware);

const users = new Map();
const leaderboard = [];

function getSessionUser(req) {
  const uid = req.session && req.session.userId;
  if (!uid) return null;
  for (const [name, u] of users) {
    if (u.id === uid) return { username: name, id: uid };
  }
  return null;
}

app.post('/register', async (req, res) => {
  const { username, password } = req.body || {};
  if (typeof username !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ error: 'username and password required' });
  }
  const name = username.trim();
  if (name.length < 1 || name.length > 32) {
    return res.status(400).json({ error: 'invalid username' });
  }
  if (password.length < 4) {
    return res.status(400).json({ error: 'password too short' });
  }
  if (users.has(name)) {
    return res.status(409).json({ error: 'username taken' });
  }
  const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const passwordHash = await bcrypt.hash(password, 10);
  users.set(name, { id, passwordHash });
  req.session.userId = id;
  req.session.username = name;
  return res.json({ ok: true, username: name });
});

app.post('/login', async (req, res) => {
  const { username, password } = req.body || {};
  if (typeof username !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ error: 'username and password required' });
  }
  const name = username.trim();
  const user = users.get(name);
  if (!user) {
    return res.status(401).json({ error: 'invalid credentials' });
  }
  const match = await bcrypt.compare(password, user.passwordHash);
  if (!match) {
    return res.status(401).json({ error: 'invalid credentials' });
  }
  req.session.userId = user.id;
  req.session.username = name;
  return res.json({ ok: true, username: name });
});

app.post('/logout', (req, res) => {
  req.session.destroy(() => {
    res.clearCookie('connect.sid');
    res.json({ ok: true });
  });
});

app.get('/me', (req, res) => {
  const u = getSessionUser(req);
  if (!u) return res.status(401).json({ error: 'not authenticated' });
  res.json({ username: u.username });
});

app.get('/leaderboard', (req, res) => {
  const top = [...leaderboard]
    .sort((a, b) => b.score - a.score)
    .slice(0, 100);
  res.json({ leaderboard: top });
});

const server = http.createServer(app);

const io = new Server(server, {
  cors: { origin: true, credentials: true },
});

io.engine.use(sessionMiddleware);

function socketUser(socket) {
  const sess = socket.request.session;
  if (!sess || !sess.userId) return null;
  return { userId: sess.userId, username: sess.username };
}

io.on('connection', (socket) => {
  const user = socketUser(socket);
  if (!user) {
    socket.emit('error', { message: 'not authenticated' });
    socket.disconnect(true);
    return;
  }

  socket.data.username = user.username;
  socket.data.userId = user.userId;

  socket.emit('session', { username: user.username });

  socket.on('move', (payload) => {
    socket.broadcast.emit('playerMove', {
      username: user.username,
      move: payload,
    });
  });

  socket.on('submitScore', (payload) => {
    const score = Number(payload && payload.score);
    const name =
      typeof payload?.username === 'string' && payload.username.trim()
        ? payload.username.trim().slice(0, 32)
        : user.username;
    if (!Number.isFinite(score) || score < 0) {
      socket.emit('scoreRejected', { reason: 'invalid score' });
      return;
    }
    const entry = {
      username: name,
      score,
      at: Date.now(),
    };
    leaderboard.push(entry);
    io.emit('leaderboardUpdate', {
      leaderboard: [...leaderboard]
        .sort((a, b) => b.score - a.score)
        .slice(0, 100),
    });
    socket.emit('scoreAccepted', entry);
  });
});

server.listen(PORT, () => {
  console.log('listening on', PORT);
});
