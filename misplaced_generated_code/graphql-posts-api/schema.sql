CREATE TABLE IF NOT EXISTS authors (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT
);

CREATE TABLE IF NOT EXISTS posts (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT,
  author_id INTEGER NOT NULL REFERENCES authors (id)
);

INSERT INTO authors (name, email) VALUES
  ('Alice Example', 'alice@example.com'),
  ('Bob Sample', 'bob@example.com');

INSERT INTO posts (title, body, author_id) VALUES
  ('Hello World', 'First post.', 1),
  ('GraphQL Tips', 'Keep it simple.', 1),
  ('PostgreSQL', 'Reliable storage.', 2);
