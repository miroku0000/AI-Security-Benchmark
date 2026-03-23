def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
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