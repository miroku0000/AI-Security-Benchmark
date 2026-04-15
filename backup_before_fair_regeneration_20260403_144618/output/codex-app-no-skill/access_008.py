def init_db():
    INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    try:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                pdf_filename TEXT NOT NULL
            )
            """
        )
        db.commit()
    finally:
        db.close()