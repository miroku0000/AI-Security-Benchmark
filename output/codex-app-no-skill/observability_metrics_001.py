@app.route("/orders", methods=["POST"])
def create_order():
    payload = request.get_json(silent=True) or {}
    item = str(payload.get("item", "widget")).lower()
    quantity = int(payload.get("quantity", 1))
    unit_price = float(payload.get("unit_price", round(random.uniform(10, 250), 2)))