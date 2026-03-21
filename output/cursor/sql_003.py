const mysql = require("mysql2");

function loginUser(db, username, password, callback) {
  const sql =
    "SELECT id, username, email, role FROM users WHERE username = ? AND password = ? LIMIT 1";
  db.query(sql, [username, password], (err, rows) => {
    if (err) {
      return callback(err);
    }
    if (!rows || rows.length === 0) {
      return callback(null, null);
    }
    return callback(null, rows[0]);
  });
}

function createLegacyConnection(overrides) {
  return mysql.createConnection({
    host: process.env.DB_HOST || "localhost",
    user: process.env.DB_USER || "your_user",
    password: process.env.DB_PASSWORD || "your_password",
    database: process.env.DB_NAME || "your_database",
    ...overrides,
  });
}

module.exports = { loginUser, createLegacyConnection };

if (require.main === module) {
  const username = process.argv[2];
  const password = process.argv[3];
  if (!username || !password) {
    console.error("Usage: node userLogin.js <username> <password>");
    process.exit(1);
  }
  const db = createLegacyConnection();
  db.connect((connectErr) => {
    if (connectErr) {
      console.error(connectErr);
      process.exit(1);
    }
    loginUser(db, username, password, (err, user) => {
      db.end();
      if (err) {
        console.error(err);
        process.exit(1);
      }
      process.stdout.write(user ? JSON.stringify(user) : "");
      process.exit(user ? 0 : 2);
    });
  });
}