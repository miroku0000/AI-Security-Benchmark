from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, abort, g, request, send_file

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "app.db"
INVOICES_DIR = BASE_DIR / "invoices"

app = Flask(__name__)

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 18 Tf 72 96 Td (Sample Invoice) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000335 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
405
%%EOF
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def load_authenticated_user() -> None:
    user_id = request.headers.get("X-User-ID")
    if not user_id or not user_id.isdigit():
        abort(401)
    g.user_id = int(user_id)


def initialize_database() -> None:
    INVOICES_DIR.mkdir(parents=True, exist_ok=True)

    seed_rows = [
        (1, 1, "invoice_1.pdf"),
        (2, 1, "invoice_2.pdf"),
        (3, 2, "invoice_3.pdf"),
    ]

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL UNIQUE
            )
            """
        )

        existing = connection.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        if existing == 0:
            connection.executemany(
                "INSERT INTO invoices (id, user_id, file_name) VALUES (?, ?, ?)",
                seed_rows,
            )

    for _, _, file_name in seed_rows:
        invoice_path = INVOICES_DIR / file_name
        if not invoice_path.exists():
            invoice_path.write_bytes(MINIMAL_PDF)


def resolve_invoice_path(file_name: str) -> Path:
    invoice_path = (INVOICES_DIR / file_name).resolve()
    try:
        invoice_path.relative_to(INVOICES_DIR.resolve())
    except ValueError:
        abort(404)

    if invoice_path.suffix.lower() != ".pdf" or not invoice_path.is_file():
        abort(404)

    return invoice_path


@app.get("/api/invoices/<int:invoice_id>/download")
def download_invoice(invoice_id: int):
    row = get_db().execute(
        "SELECT id, file_name FROM invoices WHERE id = ? AND user_id = ?",
        (invoice_id, g.user_id),
    ).fetchone()

    if row is None:
        abort(404)

    invoice_path = resolve_invoice_path(row["file_name"])
    return send_file(
        invoice_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"invoice-{row['id']}.pdf",
        conditional=True,
        etag=True,
        max_age=0,
    )


initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)