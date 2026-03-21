from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from queue import Queue
from typing import Any, Dict, Optional

from flask import Flask, Response, jsonify, request

DB_PATH = os.environ.get("COUPON_DB", ":memory:")
POOL_SIZE = int(os.environ.get("COUPON_POOL_SIZE", "32"))


def _utc_now() -> float:
    return time.time()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY COLLATE NOCASE,
            discount_type TEXT NOT NULL CHECK (discount_type IN ('percent', 'fixed')),
            discount_value REAL NOT NULL CHECK (discount_value >= 0),
            valid_from REAL NOT NULL,
            valid_until REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0 CHECK (used IN (0, 1)),
            used_at REAL,
            max_uses INTEGER NOT NULL DEFAULT 1 CHECK (max_uses >= 1),
            times_used INTEGER NOT NULL DEFAULT 0 CHECK (times_used >= 0),
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coupons_valid_until ON coupons(valid_until);
        """
    )
    cur = conn.execute("SELECT COUNT(*) FROM coupons")
    if cur.fetchone()[0] == 0:
        now = _utc_now()
        seed = [
            ("SAVE10", "percent", 10.0, now - 86400, now + 86400 * 30, 0, None, 1, 0, now),
            ("FLAT5", "fixed", 5.0, now - 86400, now + 86400 * 7, 0, None, 100, 0, now),
            ("EXPIRED", "percent", 50.0, now - 86400 * 10, now - 1, 0, None, 1, 0, now),
        ]
        conn.executemany(
            """
            INSERT INTO coupons
            (code, discount_type, discount_value, valid_from, valid_until,
             used, used_at, max_uses, times_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seed,
        )
        conn.commit()


class ConnectionPool:
    def __init__(self, path: str, size: int) -> None:
        self._path = path
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=size)
        for _ in range(size):
            self._pool.put(self._create())

    def _create(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self):
        conn = self._pool.get()
        try:
            yield conn
        finally:
            self._pool.put(conn)


_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                p = ConnectionPool(DB_PATH, POOL_SIZE)
                with p.connection() as c:
                    _init_schema(c)
                _pool = p
    return _pool


app = Flask(__name__)


@app.teardown_appcontext
def close_db(_exc: Optional[BaseException]) -> None:
    pass


def redeem_atomic(
    conn: sqlite3.Connection, code: str, cart_total: float
) -> Dict[str, Any]:
    now = _utc_now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            """
            SELECT code, discount_type, discount_value, valid_from, valid_until,
                   used, max_uses, times_used
            FROM coupons WHERE code = ? COLLATE NOCASE
            """,
            (code,),
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "invalid_code", "message": "Unknown coupon code"}

        if now < row["valid_from"]:
            conn.rollback()
            return {"ok": False, "error": "not_yet_valid", "message": "Coupon not active yet"}

        if now > row["valid_until"]:
            conn.rollback()
            return {"ok": False, "error": "expired", "message": "Coupon has expired"}

        if row["times_used"] >= row["max_uses"]:
            conn.rollback()
            return {"ok": False, "error": "depleted", "message": "Coupon fully redeemed"}

        upd = conn.execute(
            """
            UPDATE coupons
            SET times_used = times_used + 1,
                used = CASE WHEN times_used + 1 >= max_uses THEN 1 ELSE used END,
                used_at = CASE WHEN times_used + 1 >= max_uses THEN ? ELSE used_at END
            WHERE code = ? COLLATE NOCASE
              AND times_used < max_uses
              AND ? BETWEEN valid_from AND valid_until
            """,
            (now, code, now),
        )
        if upd.rowcount != 1:
            conn.rollback()
            return {"ok": False, "error": "race_or_invalid", "message": "Could not apply coupon"}

        dtype = row["discount_type"]
        val = float(row["discount_value"])
        if dtype == "percent":
            discount = min(cart_total * (val / 100.0), cart_total)
        else:
            discount = min(val, cart_total)

        conn.commit()
        return {
            "ok": True,
            "code": row["code"],
            "discount": round(discount, 2),
            "new_total": round(max(cart_total - discount, 0.0), 2),
            "times_used_after": row["times_used"] + 1,
            "max_uses": row["max_uses"],
        }
    except Exception:
        conn.rollback()
        raise


@app.post("/redeem")
def redeem() -> Response:
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    try:
        cart_total = float(data.get("cart_total", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad_request", "message": "Invalid cart_total"}), HTTPStatus.BAD_REQUEST

    if not code or cart_total < 0:
        return jsonify({"ok": False, "error": "bad_request", "message": "code and non-negative cart_total required"}), HTTPStatus.BAD_REQUEST

    pool = get_pool()
    with pool.connection() as conn:
        result = redeem_atomic(conn, code, cart_total)

    status = HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT
    return jsonify(result), status


@app.get("/health")
def health() -> Response:
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})


def main() -> None:
    port = int(os.environ.get("PORT", "8765"))
    get_pool()
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()