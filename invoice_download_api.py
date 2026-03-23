from pathlib import Path

from flask import Flask, abort, g, send_file

app = Flask(__name__)

INVOICE_ROOT = Path(__file__).resolve().parent / "invoices"


@app.route("/api/invoices/<int:invoice_id>/download")
def download_invoice(invoice_id):
    pdf_path = INVOICE_ROOT / str(g.current_user_id) / f"{invoice_id}.pdf"
    if not pdf_path.is_file():
        abort(404)
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"invoice_{invoice_id}.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
