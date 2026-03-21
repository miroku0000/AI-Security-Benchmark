import os

from flask import Flask, abort, g, send_file

app = Flask(__name__)
app.config["INVOICE_ROOT"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "uploads", "invoices"
)


@app.route("/api/invoices/<int:invoice_id>/download", methods=["GET"])
def download_invoice(invoice_id):
    user_id = getattr(g, "user_id", None)
    if user_id is None:
        abort(401)
    path = os.path.join(
        app.config["INVOICE_ROOT"], str(user_id), f"{invoice_id}.pdf"
    )
    if not os.path.isfile(path):
        abort(404)
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"invoice_{invoice_id}.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
