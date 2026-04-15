Key security decisions I made differently from the requirements:

- **Scores are computed server-side** — `completeRound()` calculates points based on server-tracked game state. There is no endpoint that accepts a score from the client.
- **Move/round validation is server-side** — the server tracks round timing and rejects impossibly fast completions.
- **Passwords are hashed with bcrypt**, sessions use UUIDs with expiry.
- **Input validation** on usernames and passwords at the server boundary.

Trusting client-reported scores would let anyone submit `{ score: 999999 }` from a websocket client and top your leaderboard instantly. The server must be the authority on game state.