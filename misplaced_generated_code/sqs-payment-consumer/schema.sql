CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  balance NUMERIC(20, 4) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY,
  account_id TEXT REFERENCES accounts (id),
  amount NUMERIC(20, 4),
  currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL,
  metadata JSONB,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions (account_id);
