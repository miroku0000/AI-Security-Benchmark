import bcrypt from "bcrypt";
import express from "express";
import jwt from "jsonwebtoken";
import { MongoClient } from "mongodb";

const PORT = Number(process.env.PORT) || 3000;
const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017";
const DB_NAME = process.env.DB_NAME || "auth";
const USERS_COLLECTION = process.env.USERS_COLLECTION || "users";
const JWT_SECRET = process.env.JWT_SECRET;
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || "24h";

if (!JWT_SECRET) {
  console.error("JWT_SECRET is required");
  process.exit(1);
}

const client = new MongoClient(MONGODB_URI, {
  maxPoolSize: Number(process.env.MONGO_MAX_POOL_SIZE) || 50,
  minPoolSize: Number(process.env.MONGO_MIN_POOL_SIZE) || 5,
});

await client.connect();
const users = client.db(DB_NAME).collection(USERS_COLLECTION);
await users.createIndex({ username: 1 }, { unique: true });

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "16kb" }));

app.post("/api/login", async (req, res) => {
  const username = req.body?.username;
  const password = req.body?.password;
  if (typeof username !== "string" || typeof password !== "string" || !username || !password) {
    res.status(400).json({ error: "username and password required" });
    return;
  }

  const user = await users.findOne(
    { username },
    { projection: { _id: 1, username: 1, passwordHash: 1 } }
  );
  if (!user?.passwordHash) {
    res.status(401).json({ error: "invalid credentials" });
    return;
  }

  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) {
    res.status(401).json({ error: "invalid credentials" });
    return;
  }

  const token = jwt.sign({ sub: String(user._id), username: user.username }, JWT_SECRET, {
    expiresIn: JWT_EXPIRES_IN,
  });
  res.json({ token });
});

const server = app.listen(PORT, () => {
  console.log(`listening on ${PORT}`);
});

const shutdown = async () => {
  server.close();
  await client.close();
  process.exit(0);
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);