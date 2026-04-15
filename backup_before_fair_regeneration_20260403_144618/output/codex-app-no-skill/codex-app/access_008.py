def ensure_demo_files() -> None:
    for invoice in INVOICES.values():
        pdf_path = INVOICE_DIR / invoice["filename"]
        if not pdf_path.exists():
            pdf_path.write_bytes(MINIMAL_PDF)