import express from "express";
import { pool } from "./db.js";
import { searchUsers, type UserSearchParams } from "./searchUsers.js";

const app = express();
const port = Number(process.env.PORT) || 3000;

app.use(express.json());

app.get("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = req.query as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.post("/users/search", async (req, res) => {
  const client = await pool.connect();
  try {
    const params = (req.body ?? {}) as UserSearchParams;
    const rows = await searchUsers(client, params);
    res.json({ users: rows });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "search_failed" });
  } finally {
    client.release();
  }
});

app.listen(port, () => {
  console.log(`listening on ${port}`);
});
