CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    author TEXT,
    tags TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO documents (title, description, author, tags)
VALUES
    ('GraphQL Guide', 'Introduction to GraphQL APIs', 'Alice', 'api,graphql'),
    ('PostgreSQL Tips', 'Performance tuning for large datasets', 'Bob', 'database,sql'),
    ('Search Patterns', 'Building flexible search with raw SQL', 'Alice', 'search,sql');
