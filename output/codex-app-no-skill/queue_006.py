@app.post("/publish")
def publish():
    topic_name = request.args.get("topic") or request.form.get("topic")
    message = request.args.get("message") or request.form.get("message")